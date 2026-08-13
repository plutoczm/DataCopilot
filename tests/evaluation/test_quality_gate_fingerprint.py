from backend.app.application.evaluation.quality_gate import (
    BenchmarkThresholds,
    evaluate_benchmark_report,
)


def test_quality_gate_rejects_benchmark_fingerprint_drift() -> None:
    base = {
        "metadata": {"benchmark_fingerprint": "a" * 64},
        "text2sql": {"case_count": 5},
        "safety": {"case_count": 4},
    }
    candidate = {
        "metadata": {"benchmark_fingerprint": "b" * 64},
        "text2sql": {"case_count": 5},
        "safety": {"case_count": 4},
    }

    result = evaluate_benchmark_report(
        candidate,
        BenchmarkThresholds(),
        baseline_report=base,
    )

    assert result.passed is False
    assert any("metadata.benchmark_fingerprint" in item for item in result.failures)
