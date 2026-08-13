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


class BenchmarkGateResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    observed: dict[str, float | int | None] = Field(default_factory=dict)
    thresholds: BenchmarkThresholds


def evaluate_benchmark_report(
    report: dict[str, Any],
    thresholds: BenchmarkThresholds,
) -> BenchmarkGateResult:
    """Evaluate a serialized benchmark artifact without rerunning the model.

    This lets a model-enabled evaluation job produce the artifact while a separate CI or
    release job enforces the quality policy without requiring model credentials.
    """

    text2sql = _mapping(report.get("text2sql"))
    safety = _mapping(report.get("safety"))
    observed: dict[str, float | int | None] = {
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

    return BenchmarkGateResult(
        passed=not failures,
        failures=failures,
        observed=observed,
        thresholds=thresholds,
    )


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
