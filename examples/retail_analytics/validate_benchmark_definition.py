from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.application.evaluation import (  # noqa: E402
    extract_referenced_tables,
    extract_schema_tables,
)
from backend.app.application.query_execution.policy import ReadOnlySQLPolicy  # noqa: E402


def validate_benchmark_definition(
    *,
    questions_path: Path,
    schema_path: Path,
    safety_cases_path: Path,
) -> dict[str, Any]:
    questions = _load_array(questions_path)
    safety_cases = _load_array(safety_cases_path)
    schema_tables = extract_schema_tables(schema_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    policy = ReadOnlySQLPolicy()

    _check_unique_ids(questions, label="question", failures=failures)
    _check_unique_ids(safety_cases, label="safety case", failures=failures)

    for item in questions:
        case_id = str(item.get("id", "<missing-id>"))
        question = str(item.get("question", "")).strip()
        golden_sql = str(item.get("golden_sql", "")).strip()
        expected_tables = {
            str(table).strip().lower()
            for table in item.get("expected_tables", [])
            if str(table).strip()
        }

        if not question:
            failures.append(f"{case_id}: question is empty")
        if str(item.get("engine", "")).strip().lower() != "sqlite":
            failures.append(f"{case_id}: engine must be sqlite for the retail benchmark")
        if not golden_sql:
            failures.append(f"{case_id}: golden_sql is required")
            continue

        unknown_expected = expected_tables - schema_tables
        if unknown_expected:
            failures.append(
                f"{case_id}: expected_tables reference unknown schema tables "
                f"{sorted(unknown_expected)}"
            )

        referenced_tables = {
            table.split(".")[-1] for table in extract_referenced_tables(golden_sql)
        }
        unknown_golden = referenced_tables - schema_tables
        if unknown_golden:
            failures.append(
                f"{case_id}: golden_sql references unknown schema tables "
                f"{sorted(unknown_golden)}"
            )

        policy_result = policy.validate(golden_sql)
        if not policy_result.allowed:
            violations = [item.code for item in policy_result.violations]
            failures.append(
                f"{case_id}: golden_sql violates read-only policy {violations}"
            )

    for item in safety_cases:
        case_id = str(item.get("id", "<missing-id>"))
        sql = str(item.get("sql", "")).strip()
        expected_allowed = item.get("expected_allowed")
        if not sql:
            failures.append(f"{case_id}: safety SQL is empty")
            continue
        if not isinstance(expected_allowed, bool):
            failures.append(f"{case_id}: expected_allowed must be boolean")
            continue

        actual_allowed = policy.validate(sql).allowed
        if actual_allowed is not expected_allowed:
            failures.append(
                f"{case_id}: safety expectation disagrees with ReadOnlySQLPolicy "
                f"(expected={expected_allowed}, actual={actual_allowed})"
            )

    return {
        "passed": not failures,
        "question_count": len(questions),
        "safety_case_count": len(safety_cases),
        "schema_tables": sorted(schema_tables),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the retail Text2SQL benchmark definition before running model-backed "
            "evaluation. This gate is deterministic and requires no API key."
        )
    )
    parser.add_argument("--questions", type=Path, default=HERE / "questions.json")
    parser.add_argument("--schema", type=Path, default=HERE / "schema.sql")
    parser.add_argument("--safety-cases", type=Path, default=HERE / "safety_cases.json")
    args = parser.parse_args()

    result = validate_benchmark_definition(
        questions_path=args.questions,
        schema_path=args.schema,
        safety_cases_path=args.safety_cases,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 2


def _load_array(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain JSON objects")
    return payload


def _check_unique_ids(
    items: list[dict[str, Any]],
    *,
    label: str,
    failures: list[str],
) -> None:
    seen: set[str] = set()
    for item in items:
        case_id = str(item.get("id", "")).strip()
        if not case_id:
            failures.append(f"{label} id is required")
            continue
        if case_id in seen:
            failures.append(f"duplicate {label} id: {case_id}")
        seen.add(case_id)


if __name__ == "__main__":
    raise SystemExit(main())
