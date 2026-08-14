from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HIGHER_IS_BETTER = (
    "generation_success_rate",
    "valid_sql_rate",
    "execution_success_rate",
    "expected_table_recall",
    "business_result_accuracy",
)
LOWER_IS_BETTER = (
    "schema_hallucination_rate",
    "average_generation_latency_ms",
    "p95_generation_latency_ms",
    "average_tokens_per_case",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _delta(base: Any, candidate: Any) -> float | None:
    if base is None or candidate is None:
        return None
    return round(float(candidate) - float(base), 6)


def compare(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    base_meta = base.get("metadata", {})
    candidate_meta = candidate.get("metadata", {})
    if base_meta.get("benchmark_fingerprint") != candidate_meta.get("benchmark_fingerprint"):
        raise ValueError("benchmark_fingerprint mismatch; reports are not comparable")
    if base_meta.get("use_rag") != candidate_meta.get("use_rag"):
        raise ValueError("use_rag mismatch; compare like-for-like configurations")

    base_metrics = base["text2sql"]
    candidate_metrics = candidate["text2sql"]
    metrics = {}
    for name in HIGHER_IS_BETTER + LOWER_IS_BETTER:
        metrics[name] = {
            "base": base_metrics.get(name),
            "candidate": candidate_metrics.get(name),
            "delta": _delta(base_metrics.get(name), candidate_metrics.get(name)),
            "direction": "higher_is_better" if name in HIGHER_IS_BETTER else "lower_is_better",
        }
    return {
        "benchmark_fingerprint": base_meta.get("benchmark_fingerprint"),
        "base_model": base_meta.get("llm_model"),
        "candidate_model": candidate_meta.get("llm_model"),
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare base and fine-tuned Golden Result reports.")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--min-business-accuracy-delta", type=float, default=0.0)
    parser.add_argument("--max-hallucination-regression", type=float, default=0.0)
    args = parser.parse_args()

    report = compare(_load(args.base), _load(args.candidate))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")

    business_delta = report["metrics"]["business_result_accuracy"]["delta"]
    hallucination_delta = report["metrics"]["schema_hallucination_rate"]["delta"]
    if business_delta is None:
        raise SystemExit("business_result_accuracy unavailable; execute benchmark with Golden Result oracle")
    if business_delta < args.min_business_accuracy_delta:
        raise SystemExit(
            f"business_result_accuracy delta {business_delta:.4f} "
            f"< required {args.min_business_accuracy_delta:.4f}"
        )
    if hallucination_delta is not None and hallucination_delta > args.max_hallucination_regression:
        raise SystemExit(
            f"schema_hallucination_rate regressed by {hallucination_delta:.4f}"
        )


if __name__ == "__main__":
    main()
