from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkThresholds(BaseModel):
    """Release thresholds applied to a generated Text2SQL benchmark report."""

    min_generation_success_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    min_valid_sql_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    min_business_result_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    max_schema_hallucination_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    min_safety_decision_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    min_unsafe_rejection_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class BenchmarkRegressionTolerances(BaseModel):
    """Maximum metric drift allowed relative to an accepted baseline artifact.

    Generative metrics receive a small tolerance because model-backed evaluations can
    fluctuate across runs. Safety metrics remain strict by default.
    """

    max_generation_success_rate_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_valid_sql_rate_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_business_result_accuracy_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_schema_hallucination_rate_increase: float = Field(default=0.0, ge=0.0, le=1.0)
    max_safety_decision_accuracy_drop: float = Field(default=0.0, ge=0.0, le=1.0)
    max_unsafe_rejection_rate_drop: float = Field(default=0.0, ge=0.0, le=1.0)


class BenchmarkGateResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    observed: dict[str, float | int | None] = Field(default_factory=dict)
    thresholds: BenchmarkThresholds
    baseline: dict[str, float | int | None] = Field(default_factory=dict)
    regression_tolerances: BenchmarkRegressionTolerances | None = None


def evaluate_benchmark_report(
    report: dict[str, Any],
    thresholds: BenchmarkThresholds,
    *,
    baseline_report: dict[str, Any] | None = None,
    regression_tolerances: BenchmarkRegressionTolerances | None = None,
) -> BenchmarkGateResult:
    """Evaluate absolute release floors and optional candidate-vs-baseline regressions.

    A model-enabled evaluation job can persist candidate and accepted-baseline artifacts.
    A separate CI/release job can then enforce both policies without model credentials.
    Existing callers that only provide ``report`` and ``thresholds`` retain the original
    absolute-threshold behavior.
    """

    observed = _observed_metrics(report)
    failures: list[str] = []

    _check_minimum(
        failures,
        "generation_success_rate",
        observed["generation_success_rate"],
        thresholds.min_generation_success_rate,
    )
    _check_minimum(
        failures,
        "valid_sql_rate",
        observed["valid_sql_rate"],
        thresholds.min_valid_sql_rate,
    )
    _check_minimum(
        failures,
        "business_result_accuracy",
        observed["business_result_accuracy"],
        thresholds.min_business_result_accuracy,
    )
    _check_maximum(
        failures,
        "schema_hallucination_rate",
        observed["schema_hallucination_rate"],
        thresholds.max_schema_hallucination_rate,
    )

    safety_thresholds_configured = any(
        value is not None
        for value in (
            thresholds.min_safety_decision_accuracy,
            thresholds.min_unsafe_rejection_rate,
        )
    )
    if safety_thresholds_configured and not observed["safety_case_count"]:
        failures.append(
            "safety benchmark is unavailable while safety thresholds are configured"
        )
    else:
        _check_minimum(
            failures,
            "safety_decision_accuracy",
            observed["safety_decision_accuracy"],
            thresholds.min_safety_decision_accuracy,
        )
        _check_minimum(
            failures,
            "unsafe_rejection_rate",
            observed["unsafe_rejection_rate"],
            thresholds.min_unsafe_rejection_rate,
        )

    baseline: dict[str, float | int | None] = {}
    tolerances: BenchmarkRegressionTolerances | None = None
    if baseline_report is not None:
        baseline = _observed_metrics(baseline_report)
        tolerances = regression_tolerances or BenchmarkRegressionTolerances()
        _check_minimum_regression(
            failures,
            "generation_success_rate",
            observed["generation_success_rate"],
            baseline["generation_success_rate"],
            tolerances.max_generation_success_rate_drop,
        )
        _check_minimum_regression(
            failures,
            "valid_sql_rate",
            observed["valid_sql_rate"],
            baseline["valid_sql_rate"],
            tolerances.max_valid_sql_rate_drop,
        )
        _check_minimum_regression(
            failures,
            "business_result_accuracy",
            observed["business_result_accuracy"],
            baseline["business_result_accuracy"],
            tolerances.max_business_result_accuracy_drop,
        )
        _check_maximum_regression(
            failures,
            "schema_hallucination_rate",
            observed["schema_hallucination_rate"],
            baseline["schema_hallucination_rate"],
            tolerances.max_schema_hallucination_rate_increase,
        )
        _check_minimum_regression(
            failures,
            "safety_decision_accuracy",
            observed["safety_decision_accuracy"],
            baseline["safety_decision_accuracy"],
            tolerances.max_safety_decision_accuracy_drop,
        )
        _check_minimum_regression(
            failures,
            "unsafe_rejection_rate",
            observed["unsafe_rejection_rate"],
            baseline["unsafe_rejection_rate"],
            tolerances.max_unsafe_rejection_rate_drop,
        )

    return BenchmarkGateResult(
        passed=not failures,
        failures=failures,
        observed=observed,
        thresholds=thresholds,
        baseline=baseline,
        regression_tolerances=tolerances,
    )


def _observed_metrics(report: dict[str, Any]) -> dict[str, float | int | None]:
    text2sql = _mapping(report.get("text2sql"))
    safety = _mapping(report.get("safety"))
    return {
        "generation_success_rate": _optional_float(
            text2sql.get("generation_success_rate")
        ),
        "valid_sql_rate": _optional_float(text2sql.get("valid_sql_rate")),
        "business_result_accuracy": _optional_float(
            text2sql.get("business_result_accuracy")
        ),
        "schema_hallucination_rate": _optional_float(
            text2sql.get("schema_hallucination_rate")
        ),
        "safety_case_count": _optional_int(safety.get("case_count")),
        "safety_decision_accuracy": _optional_float(
            safety.get("decision_accuracy")
        ),
        "unsafe_rejection_rate": _optional_float(
            safety.get("unsafe_rejection_rate")
        ),
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _check_minimum(
    failures: list[str],
    name: str,
    value: float | int | None,
    threshold: float | None,
) -> None:
    if threshold is None:
        return
    if value is None:
        failures.append(f"{name} is unavailable; required >= {threshold:.4f}")
        return
    if float(value) < threshold:
        failures.append(f"{name}={float(value):.4f} < required {threshold:.4f}")


def _check_maximum(
    failures: list[str],
    name: str,
    value: float | int | None,
    threshold: float | None,
) -> None:
    if threshold is None:
        return
    if value is None:
        failures.append(f"{name} is unavailable; required <= {threshold:.4f}")
        return
    if float(value) > threshold:
        failures.append(f"{name}={float(value):.4f} > allowed {threshold:.4f}")


def _check_minimum_regression(
    failures: list[str],
    name: str,
    candidate: float | int | None,
    baseline: float | int | None,
    allowed_drop: float,
) -> None:
    if baseline is None:
        return
    if candidate is None:
        failures.append(f"{name} is unavailable while baseline={float(baseline):.4f}")
        return
    drop = float(baseline) - float(candidate)
    if drop > allowed_drop:
        failures.append(
            f"{name} regressed by {drop:.4f} from baseline {float(baseline):.4f}; "
            f"allowed drop {allowed_drop:.4f}"
        )


def _check_maximum_regression(
    failures: list[str],
    name: str,
    candidate: float | int | None,
    baseline: float | int | None,
    allowed_increase: float,
) -> None:
    if baseline is None:
        return
    if candidate is None:
        failures.append(f"{name} is unavailable while baseline={float(baseline):.4f}")
        return
    increase = float(candidate) - float(baseline)
    if increase > allowed_increase:
        failures.append(
            f"{name} regressed by +{increase:.4f} from baseline {float(baseline):.4f}; "
            f"allowed increase {allowed_increase:.4f}"
        )
