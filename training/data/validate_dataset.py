from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return records


def _question_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _benchmark_questions(path: Path | None) -> set[str]:
    if path is None:
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("benchmark questions must be a JSON array")
    return {_question_key(str(item["question"])) for item in payload if item.get("question")}


def validate(
    paths: list[Path],
    *,
    benchmark_questions: Path | None = None,
) -> dict[str, Any]:
    benchmark = _benchmark_questions(benchmark_questions)
    seen_ids: set[str] = set()
    schema_owners: dict[str, str] = {}
    overlap: list[str] = []
    counts: dict[str, int] = {}

    for path in paths:
        split = path.stem
        records = _load_jsonl(path)
        counts[split] = len(records)
        if not records:
            raise ValueError(f"{path} is empty")

        for record in records:
            record_id = str(record.get("id", "")).strip()
            schema_id = str(record.get("schema_id", "")).strip()
            question = str(record.get("question", "")).strip()
            messages = record.get("messages")
            if not record_id or not schema_id or not question:
                raise ValueError(f"{path}: id/schema_id/question are required")
            if record_id in seen_ids:
                raise ValueError(f"duplicate id across splits: {record_id}")
            seen_ids.add(record_id)

            owner = schema_owners.setdefault(schema_id, split)
            if owner != split:
                raise ValueError(
                    f"schema leakage: schema_id={schema_id} appears in {owner} and {split}"
                )

            if not isinstance(messages, list) or [m.get("role") for m in messages] != [
                "system",
                "user",
                "assistant",
            ]:
                raise ValueError(f"{record_id}: messages must be system/user/assistant")

            assistant = json.loads(str(messages[-1].get("content", "")))
            if not str(assistant.get("sql", "")).strip():
                raise ValueError(f"{record_id}: assistant output requires sql")
            if _question_key(question) in benchmark:
                overlap.append(record_id)

    if overlap:
        raise ValueError(
            "training/eval contamination: benchmark question overlap for records "
            + ", ".join(sorted(overlap))
        )

    return {
        "records": len(seen_ids),
        "schemas": len(schema_owners),
        "splits": counts,
        "benchmark_overlap": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasets", nargs="+", type=Path)
    parser.add_argument("--benchmark-questions", type=Path)
    args = parser.parse_args()
    report = validate(
        args.datasets,
        benchmark_questions=args.benchmark_questions,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
