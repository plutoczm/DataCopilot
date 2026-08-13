from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.application.evaluation.quality_gate import (  # noqa: E402
    BenchmarkThresholds,
    evaluate_benchmark_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a candidate Text2SQL benchmark report with an accepted baseline."
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()

    candidate = _load_report(args.candidate)
    baseline = _load_report(args.baseline)
    result = evaluate_benchmark_report(
        candidate,
        BenchmarkThresholds(),
        baseline_report=baseline,
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.passed else 2


def _load_report(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
