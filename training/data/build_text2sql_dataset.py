from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "You are a Text2SQL model. Generate one read-only analytical query using only the "
    "provided schema and target SQL dialect. Return JSON with sql, explanation and "
    "optimization_suggestions. Never invent tables or columns."
)


def _load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("source JSON must be an array or use JSONL")
    return payload


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    required = ("id", "schema_id", "engine", "schema", "question", "sql")
    missing = [key for key in required if not str(record.get(key, "")).strip()]
    if missing:
        raise ValueError(f"record {record.get('id', '<unknown>')} missing: {missing}")

    output = {
        "sql": str(record["sql"]).strip(),
        "explanation": str(record.get("explanation") or "Generate the requested analytical result."),
        "optimization_suggestions": list(record.get("optimization_suggestions") or []),
    }
    user = "\n\n".join(
        [
            f"Target engine: {record['engine']}",
            f"Provided schema:\n{str(record['schema']).strip()}",
            f"Natural language request:\n{str(record['question']).strip()}",
        ]
    )
    return {
        "id": str(record["id"]),
        "schema_id": str(record["schema_id"]),
        "engine": str(record["engine"]),
        "question": str(record["question"]).strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False)},
        ],
    }


def _group_split(
    records: list[dict[str, Any]],
    *,
    seed: int,
    train_ratio: float,
    validation_ratio: float,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["schema_id"]].append(record)

    schema_ids = sorted(grouped)
    random.Random(seed).shuffle(schema_ids)
    if len(schema_ids) < 3:
        raise ValueError(
            "need at least 3 schema_id groups to produce leakage-resistant "
            "train/validation/test splits"
        )

    n = len(schema_ids)
    train_count = max(1, int(n * train_ratio))
    validation_count = max(1, int(n * validation_ratio))
    if train_count + validation_count >= n:
        train_count = max(1, n - 2)
        validation_count = 1

    train_ids = set(schema_ids[:train_count])
    validation_ids = set(schema_ids[train_count : train_count + validation_count])
    test_ids = set(schema_ids[train_count + validation_count :])

    return {
        "train": [r for r in records if r["schema_id"] in train_ids],
        "validation": [r for r in records if r["schema_id"] in validation_ids],
        "test": [r for r in records if r["schema_id"] in test_ids],
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build schema-grouped Text2SQL SFT datasets without schema leakage."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    args = parser.parse_args()

    normalized = [_normalize(record) for record in _load_records(args.source)]
    if len({record["id"] for record in normalized}) != len(normalized):
        raise ValueError("record ids must be unique")

    splits = _group_split(
        normalized,
        seed=args.seed,
        train_ratio=args.train_ratio,
        validation_ratio=args.validation_ratio,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, records in splits.items():
        _write_jsonl(args.output_dir / f"{name}.jsonl", records)

    manifest = {
        "source": str(args.source),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "seed": args.seed,
        "record_count": len(normalized),
        "schema_count": len({record["schema_id"] for record in normalized}),
        "splits": {
            name: {
                "records": len(records),
                "schema_ids": sorted({record["schema_id"] for record in records}),
            }
            for name, records in splits.items()
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
