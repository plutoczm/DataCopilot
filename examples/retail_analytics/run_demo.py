from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


HERE = Path(__file__).resolve().parent
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
DATASOURCE = os.getenv("DATACOPILOT_DEMO_DATASOURCE", "retail_demo")


def main() -> None:
    schema_context = (HERE / "schema.sql").read_text(encoding="utf-8")
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

    print(f"DataPilot-AI retail demo -> {BACKEND_URL}")
    with httpx.Client(timeout=90.0) as client:
        execution_ready = _query_execution_ready(client)
        for item in questions:
            response = client.post(
                f"{BACKEND_URL}/api/v1/text2sql",
                json={
                    "question": item["question"],
                    "engine": item["engine"],
                    "schema_context": schema_context,
                    "use_rag": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            issue_codes = [
                issue["code"] for issue in payload["validation"].get("issues", [])
            ]
            print("\n" + "=" * 72)
            print(f"[{item['id']}] {item['question']}")
            print(
                f"confidence={payload['confidence']}, "
                f"valid={payload['validation']['is_valid']}"
            )
            print(f"issues={issue_codes}")
            print(payload["sql"])

            if execution_ready and payload["validation"]["is_valid"]:
                execution = client.post(
                    f"{BACKEND_URL}/api/v1/query-execution",
                    json={
                        "datasource": DATASOURCE,
                        "sql": payload["sql"],
                        "max_rows": 20,
                    },
                )
                execution.raise_for_status()
                executed = execution.json()
                print(
                    f"executed rows={executed['row_count']} "
                    f"truncated={executed['truncated']} "
                    f"elapsed_ms={executed['elapsed_ms']}"
                )
                for row in executed["rows"]:
                    print(row)


def _query_execution_ready(client: httpx.Client) -> bool:
    response = client.get(f"{BACKEND_URL}/api/v1/query-execution/datasources")
    if response.status_code != 200:
        return False
    payload = response.json()
    if not payload.get("execution_enabled"):
        return False
    return any(
        item["name"] == DATASOURCE and item["available"]
        for item in payload.get("datasources", [])
    )


if __name__ == "__main__":
    main()
