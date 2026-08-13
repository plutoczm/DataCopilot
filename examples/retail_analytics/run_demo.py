from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


HERE = Path(__file__).resolve().parent
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def main() -> None:
    schema_context = (HERE / "schema.sql").read_text(encoding="utf-8")
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))

    print(f"DataPilot-AI retail demo -> {BACKEND_URL}")
    with httpx.Client(timeout=90.0) as client:
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
            print(f"confidence={payload['confidence']}, valid={payload['validation']['is_valid']}")
            print(f"issues={issue_codes}")
            print(payload["sql"])


if __name__ == "__main__":
    main()
