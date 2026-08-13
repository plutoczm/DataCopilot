from backend.app.application.evaluation.quality_gate import (
    BenchmarkThresholds,
    evaluate_benchmark_report,
)


def _report() -> dict:
    return {
        "text2sql": {
            "generation_success_rate": 1.0,
            "valid_sql_rate": 0.8,
            "business_result_accuracy": 0.8,
            "schema_hallucination_rate": 0.0,
        },
        "safety": {"case_count": 4},
    }


def test_quality_gate_passes_when_thresholds_are_met() -> None:
    result = evaluate_benchmark_report(
        _report(),
        BenchmarkThresholds(
            min_generation_success_rate=0.8,
            min_valid_sql_rate=0.8,
            min_business_result_accuracy=0.6,
            max_schema_hallucination_rate=0.0,
        ),
    )

    assert result.passed is True
    assert result.failures == []


def test_quality_gate_reports_multiple_regressions() -> None:
    report = _report()
    report["text2sql"]["valid_sql_rate"] = 0.4
    report["text2sql"]["business_result_accuracy"] = 0.2
    report["text2sql"]["schema_hallucination_rate"] = 0.2

    result = evaluate_benchmark_report(
        report,
        BenchmarkThresholds(
            min_valid_sql_rate=0.8,
            min_business_result_accuracy=0.6,
            max_schema_hallucination_rate=0.0,
        ),
    )

    assert result.passed is False
    assert len(result.failures) == 3


def test_quality_gate_fails_when_required_metric_is_missing() -> None:
    report = _report()
    report["text2sql"]["business_result_accuracy"] = None

    result = evaluate_benchmark_report(
        report,
        BenchmarkThresholds(min_business_result_accuracy=0.6),
    )

    assert result.passed is False
    assert "business_result_accuracy is unavailable" in result.failures[0]


def test_quality_gate_treats_malformed_metric_as_unavailable() -> None:
    report = _report()
    report["text2sql"]["generation_success_rate"] = "not-a-number"

    result = evaluate_benchmark_report(
        report,
        BenchmarkThresholds(min_generation_success_rate=0.8),
    )

    assert result.passed is False
    assert "generation_success_rate is unavailable" in result.failures[0]


def test_quality_gate_allows_small_drop_against_baseline() -> None:
    baseline = _report()
    candidate = _report()
    candidate["text2sql"]["generation_success_rate"] = 0.96
    candidate["text2sql"]["valid_sql_rate"] = 0.76
    candidate["text2sql"]["business_result_accuracy"] = 0.76

    result = evaluate_benchmark_report(
        candidate,
        BenchmarkThresholds(),
        baseline_report=baseline,
    )

    assert result.passed is True
    assert result.failures == []


def test_quality_gate_rejects_baseline_regression_and_schema_increase() -> None:
    baseline = _report()
    candidate = _report()
    candidate["text2sql"]["valid_sql_rate"] = 0.70
    candidate["text2sql"]["business_result_accuracy"] = 0.70
    candidate["text2sql"]["schema_hallucination_rate"] = 0.01

    result = evaluate_benchmark_report(
        candidate,
        BenchmarkThresholds(),
        baseline_report=baseline,
    )

    assert result.passed is False
    assert len(result.failures) == 3
    assert any("valid_sql_rate regressed" in failure for failure in result.failures)
    assert any("business_result_accuracy regressed" in failure for failure in result.failures)
    assert any("schema_hallucination_rate regressed" in failure for failure in result.failures)
