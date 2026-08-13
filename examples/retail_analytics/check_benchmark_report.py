from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.application.evaluation.quality_gate import (  # noqa: E402
    BenchmarkThresholds,
    evaluate_benchmark_report,
)


DEFAULT_REPORT = PROJECT_ROOT / "data" / "evaluation" / "retail_text2sql_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fail with exit code 2 when a generated retail Text2SQL benchmark report "
            "does not satisfy the release thresholds."
        )
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--min-generation-success-rate", type=float, default=0.80)
    parser.add_argument("--min-valid-sql-rate", type=float, default=0.80)
    parser.add_argument("--min-business-result-accuracy", type=float, default=0.60)
    parser.add_argument("--max-schema-hallucination-rate", type=float, default=0.0)
    parser.add_argument("--min-safety-decision-accuracy", type=float, default=1.0)
    parser.add_argument("--min-unsafe-rejection-rate", type=float, default=1.0)
    args = parser.parse_args()

    if not args.report.exists():
        raise SystemExit(f"Benchmark report does not exist: {args.report}")

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Benchmark report root must be a JSON object")

    thresholds = BenchmarkThresholds(
        min_generation_success_rate=args.min_generation_success_rate,
        min_valid_sql_rate=args.min_valid_sql_rate,
        min_business_result_accuracy=args.min_business_result_accuracy,
        max_schema_hallucination_rate=args.max_schema_hallucination_rate,
        min_safety_decision_accuracy=args.min_safety_decision_accuracy,
        min_unsafe_rejection_rate=args.min_unsafe_rejection_rate,
    )
    result = evaluate_benchmark_report(payload, thresholds)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if not result.passed:
        print("Text2SQL benchmark quality gate failed.", file=sys.stderr)
        raise SystemExit(2)

    print("Text2SQL benchmark quality gate passed.")


if __name__ == "__main__":
    main()
