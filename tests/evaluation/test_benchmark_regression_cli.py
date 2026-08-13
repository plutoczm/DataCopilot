import json
import subprocess
import sys
from pathlib import Path


def _report(valid_sql_rate: float) -> dict:
    return {
        "metadata": {"benchmark_fingerprint": "a" * 64},
        "text2sql": {
            "case_count": 5,
            "generation_success_rate": 1.0,
            "valid_sql_rate": valid_sql_rate,
            "business_result_accuracy": 0.8,
            "schema_hallucination_rate": 0.0,
        },
        "safety": {
            "case_count": 4,
            "decision_accuracy": 1.0,
            "unsafe_rejection_rate": 1.0,
        },
    }


def _run(candidate: Path, baseline: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "examples/retail_analytics/compare_benchmark_reports.py",
            "--candidate",
            str(candidate),
            "--baseline",
            str(baseline),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_regression_cli_passes_small_drift_and_rejects_large_drop(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text(json.dumps(_report(0.80)), encoding="utf-8")

    candidate.write_text(json.dumps(_report(0.77)), encoding="utf-8")
    passed = _run(candidate, baseline)
    assert passed.returncode == 0, passed.stderr

    candidate.write_text(json.dumps(_report(0.70)), encoding="utf-8")
    failed = _run(candidate, baseline)
    assert failed.returncode == 2
    assert "valid_sql_rate regressed" in failed.stdout
