from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.application.evaluation import (  # noqa: E402
    SafetyPolicyCase,
    SafetyPolicyReport,
    Text2SQLBenchmarkCase,
    Text2SQLBenchmarkReport,
    extract_referenced_tables,
    extract_schema_tables,
)


DEFAULT_REPORT = PROJECT_ROOT / "data" / "evaluation" / "retail_text2sql_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the reproducible retail Text2SQL and safety benchmark."
    )
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--datasource", default="retail_demo")
    parser.add_argument("--questions", type=Path, default=HERE / "questions.json")
    parser.add_argument("--schema", type=Path, default=HERE / "schema.sql")
    parser.add_argument("--safety-cases", type=Path, default=HERE / "safety_cases.json")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--use-rag", action="store_true")
    args = parser.parse_args()

    backend_url = args.backend_url.rstrip("/")
    questions = _load_json(args.questions)
    safety_cases = _load_json(args.safety_cases)
    schema_sql = args.schema.read_text(encoding="utf-8")
    allowed_tables = extract_schema_tables(schema_sql)

    with httpx.Client(timeout=90.0) as client:
        execution_ready = _execution_ready(client, backend_url, args.datasource)
        text_cases = [
            _run_text2sql_case(
                client=client,
                backend_url=backend_url,
                datasource=args.datasource,
                item=item,
                schema_sql=schema_sql,
                allowed_tables=allowed_tables,
                execution_ready=execution_ready,
                use_rag=args.use_rag,
            )
            for item in questions
        ]
        safety_results = (
            [
                _run_safety_case(
                    client=client,
                    backend_url=backend_url,
                    datasource=args.datasource,
                    item=item,
                )
                for item in safety_cases
            ]
            if execution_ready
            else []
        )

    payload = {
        "metadata": {
            "backend_url": backend_url,
            "datasource": args.datasource,
            "execution_ready": execution_ready,
            "use_rag": args.use_rag,
            "note": (
                "Execution success is not semantic result accuracy. Add golden result "
                "oracles before reporting business-answer accuracy."
            ),
        },
        "text2sql": Text2SQLBenchmarkReport.from_cases(text_cases).model_dump(),
        "safety": SafetyPolicyReport.from_cases(safety_results).model_dump(),
        "cases": [item.model_dump(mode="json") for item in text_cases],
        "safety_cases": [item.model_dump(mode="json") for item in safety_results],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload["text2sql"], ensure_ascii=False, indent=2))
    print(json.dumps(payload["safety"], ensure_ascii=False, indent=2))
    print(f"Report written to: {args.report}")


def _run_text2sql_case(
    *,
    client: httpx.Client,
    backend_url: str,
    datasource: str,
    item: dict[str, Any],
    schema_sql: str,
    allowed_tables: set[str],
    execution_ready: bool,
    use_rag: bool,
) -> Text2SQLBenchmarkCase:
    started = time.perf_counter()
    try:
        response = client.post(
            f"{backend_url}/api/v1/text2sql",
            json={
                "question": item["question"],
                "engine": item.get("engine", "sqlite"),
                "schema_context": schema_sql,
                "use_rag": use_rag,
            },
        )
    except httpx.HTTPError as exc:
        return Text2SQLBenchmarkCase(
            case_id=item["id"],
            generation_succeeded=False,
            expected_tables=set(item.get("expected_tables", [])),
            allowed_tables=allowed_tables,
            generation_latency_ms=_elapsed_ms(started),
            error=str(exc),
        )

    generation_latency = _elapsed_ms(started)
    if response.status_code != 200:
        return Text2SQLBenchmarkCase(
            case_id=item["id"],
            generation_succeeded=False,
            expected_tables=set(item.get("expected_tables", [])),
            allowed_tables=allowed_tables,
            generation_latency_ms=generation_latency,
            error=f"Text2SQL HTTP {response.status_code}: {response.text[:500]}",
        )

    payload = response.json()
    sql = str(payload.get("sql", ""))
    validation_passed = bool(payload.get("validation", {}).get("is_valid"))
    tokens = int(payload.get("token_usage", {}).get("total_tokens", 0) or 0)
    result = Text2SQLBenchmarkCase(
        case_id=item["id"],
        generation_succeeded=True,
        validation_passed=validation_passed,
        expected_tables=set(item.get("expected_tables", [])),
        referenced_tables=extract_referenced_tables(sql),
        allowed_tables=allowed_tables,
        generation_latency_ms=generation_latency,
        total_tokens=tokens,
    )

    if execution_ready and validation_passed:
        execution_started = time.perf_counter()
        execution = client.post(
            f"{backend_url}/api/v1/query-execution",
            json={"datasource": datasource, "sql": sql, "max_rows": 200},
        )
        result.execution_attempted = True
        result.execution_latency_ms = _elapsed_ms(execution_started)
        result.execution_succeeded = execution.status_code == 200
        if execution.status_code != 200:
            result.error = f"Execution HTTP {execution.status_code}: {execution.text[:500]}"
    return result


def _run_safety_case(
    *,
    client: httpx.Client,
    backend_url: str,
    datasource: str,
    item: dict[str, Any],
) -> SafetyPolicyCase:
    response = client.post(
        f"{backend_url}/api/v1/query-execution",
        json={"datasource": datasource, "sql": item["sql"], "max_rows": 20},
    )
    error_code = None
    if response.status_code != 200:
        try:
            error_code = response.json().get("error", {}).get("code")
        except ValueError:
            error_code = None
    return SafetyPolicyCase(
        case_id=item["id"],
        expected_allowed=bool(item["expected_allowed"]),
        actual_allowed=response.status_code == 200,
        status_code=response.status_code,
        error_code=error_code,
    )


def _execution_ready(
    client: httpx.Client,
    backend_url: str,
    datasource: str,
) -> bool:
    try:
        response = client.get(f"{backend_url}/api/v1/query-execution/datasources")
    except httpx.HTTPError:
        return False
    if response.status_code != 200:
        return False
    payload = response.json()
    if not payload.get("execution_enabled"):
        return False
    return any(
        item.get("name") == datasource and item.get("available") is True
        for item in payload.get("datasources", [])
    )


def _load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


if __name__ == "__main__":
    main()
