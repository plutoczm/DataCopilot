import math
import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field


TABLE_REFERENCE_PATTERN = re.compile(
    r"\b(?:from|join)\s+([`\"\[]?[a-zA-Z_][\w]*[`\"\]]?(?:\s*\.\s*[`\"\[]?[a-zA-Z_][\w]*[`\"\]]?)?)",
    re.IGNORECASE,
)
CTE_NAME_PATTERN = re.compile(
    r"(?:\bwith|,)\s*([a-zA-Z_][\w]*)\s+as\s*\(",
    re.IGNORECASE,
)
CREATE_TABLE_PATTERN = re.compile(
    r"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?([`\"\[]?[a-zA-Z_][\w]*[`\"\]]?(?:\s*\.\s*[`\"\[]?[a-zA-Z_][\w]*[`\"\]]?)?)",
    re.IGNORECASE,
)


class Text2SQLBenchmarkCase(BaseModel):
    case_id: str
    generation_succeeded: bool
    validation_passed: bool = False
    execution_attempted: bool = False
    execution_succeeded: bool = False
    result_oracle_available: bool = False
    result_match_attempted: bool = False
    result_matched: bool = False
    expected_tables: set[str] = Field(default_factory=set)
    referenced_tables: set[str] = Field(default_factory=set)
    allowed_tables: set[str] = Field(default_factory=set)
    generation_latency_ms: float = Field(default=0.0, ge=0.0)
    execution_latency_ms: float = Field(default=0.0, ge=0.0)
    total_tokens: int = Field(default=0, ge=0)
    error: str | None = None

    @property
    def expected_table_recall(self) -> float:
        expected = {_short_name(item) for item in self.expected_tables}
        if not expected:
            return 1.0
        referenced = {_short_name(item) for item in self.referenced_tables}
        return len(expected & referenced) / len(expected)

    @property
    def hallucinated_tables(self) -> set[str]:
        allowed = {_short_name(item) for item in self.allowed_tables}
        referenced = {_short_name(item) for item in self.referenced_tables}
        return referenced - allowed

    @property
    def schema_hallucinated(self) -> bool:
        return bool(self.hallucinated_tables)


class Text2SQLBenchmarkReport(BaseModel):
    case_count: int
    generation_success_rate: float
    valid_sql_rate: float
    execution_attempt_rate: float
    execution_success_rate: float
    expected_table_recall: float
    schema_hallucination_rate: float
    result_oracle_coverage: float
    result_comparison_rate: float
    business_result_accuracy: float | None
    average_generation_latency_ms: float
    p95_generation_latency_ms: float
    average_execution_latency_ms: float
    total_tokens: int
    average_tokens_per_case: float

    @classmethod
    def from_cases(
        cls,
        cases: Iterable[Text2SQLBenchmarkCase],
    ) -> "Text2SQLBenchmarkReport":
        items = list(cases)
        if not items:
            return cls(
                case_count=0,
                generation_success_rate=0.0,
                valid_sql_rate=0.0,
                execution_attempt_rate=0.0,
                execution_success_rate=0.0,
                expected_table_recall=0.0,
                schema_hallucination_rate=0.0,
                result_oracle_coverage=0.0,
                result_comparison_rate=0.0,
                business_result_accuracy=None,
                average_generation_latency_ms=0.0,
                p95_generation_latency_ms=0.0,
                average_execution_latency_ms=0.0,
                total_tokens=0,
                average_tokens_per_case=0.0,
            )

        count = len(items)
        execution_attempts = [item for item in items if item.execution_attempted]
        oracle_cases = [item for item in items if item.result_oracle_available]
        result_comparisons = [
            item for item in oracle_cases if item.result_match_attempted
        ]
        generation_latencies = [item.generation_latency_ms for item in items]
        execution_latencies = [
            item.execution_latency_ms for item in execution_attempts
        ]
        total_tokens = sum(item.total_tokens for item in items)

        return cls(
            case_count=count,
            generation_success_rate=_rate(
                sum(item.generation_succeeded for item in items), count
            ),
            valid_sql_rate=_rate(
                sum(item.validation_passed for item in items), count
            ),
            execution_attempt_rate=_rate(len(execution_attempts), count),
            execution_success_rate=_rate(
                sum(item.execution_succeeded for item in execution_attempts),
                len(execution_attempts),
            ),
            expected_table_recall=round(
                sum(item.expected_table_recall for item in items) / count,
                4,
            ),
            schema_hallucination_rate=_rate(
                sum(item.schema_hallucinated for item in items), count
            ),
            result_oracle_coverage=_rate(len(oracle_cases), count),
            result_comparison_rate=_rate(
                len(result_comparisons), len(oracle_cases)
            ),
            business_result_accuracy=(
                _rate(
                    sum(item.result_matched for item in oracle_cases),
                    len(oracle_cases),
                )
                if result_comparisons
                else None
            ),
            average_generation_latency_ms=_average(generation_latencies),
            p95_generation_latency_ms=_percentile(generation_latencies, 0.95),
            average_execution_latency_ms=_average(execution_latencies),
            total_tokens=total_tokens,
            average_tokens_per_case=round(total_tokens / count, 3),
        )


class SafetyPolicyCase(BaseModel):
    case_id: str
    expected_allowed: bool
    actual_allowed: bool
    status_code: int | None = None
    error_code: str | None = None


class SafetyPolicyReport(BaseModel):
    case_count: int
    decision_accuracy: float
    unsafe_rejection_rate: float
    safe_acceptance_rate: float

    @classmethod
    def from_cases(cls, cases: Iterable[SafetyPolicyCase]) -> "SafetyPolicyReport":
        items = list(cases)
        if not items:
            return cls(
                case_count=0,
                decision_accuracy=0.0,
                unsafe_rejection_rate=0.0,
                safe_acceptance_rate=0.0,
            )
        unsafe = [item for item in items if not item.expected_allowed]
        safe = [item for item in items if item.expected_allowed]
        return cls(
            case_count=len(items),
            decision_accuracy=_rate(
                sum(item.actual_allowed == item.expected_allowed for item in items),
                len(items),
            ),
            unsafe_rejection_rate=_rate(
                sum(not item.actual_allowed for item in unsafe), len(unsafe)
            ),
            safe_acceptance_rate=_rate(
                sum(item.actual_allowed for item in safe), len(safe)
            ),
        )


def extract_referenced_tables(sql: str) -> set[str]:
    """Extract physical FROM/JOIN table names for lightweight benchmark diagnostics.

    CTE aliases are removed so `WITH recent AS (...) SELECT ... FROM recent` does not
    look like a schema hallucination. This is intentionally a diagnostic helper rather
    than a full SQL parser; execution and SQLValidator remain the authoritative checks.
    """

    cte_names = {match.group(1).lower() for match in CTE_NAME_PATTERN.finditer(sql)}
    tables = {
        _normalize_identifier(match.group(1))
        for match in TABLE_REFERENCE_PATTERN.finditer(sql)
    }
    return {table for table in tables if _short_name(table) not in cte_names}


def extract_schema_tables(schema_sql: str) -> set[str]:
    return {
        _normalize_identifier(match.group(1))
        for match in CREATE_TABLE_PATTERN.finditer(schema_sql)
    }


def result_rows_equivalent(
    actual_rows: list[dict[str, Any]],
    expected_rows: list[dict[str, Any]],
) -> bool:
    """Compare result sets while tolerating aliases, row order and small float noise.

    The retail benchmark asks for compact aggregate result sets. Column aliases are not
    semantically important, so rows are compared by typed values rather than field names.
    This helper is deliberately narrower than a general SQL-equivalence engine; production
    datasets should define case-specific oracles when ordering/duplicate semantics matter.
    """

    if len(actual_rows) != len(expected_rows):
        return False
    actual = sorted((_normalize_result_row(row) for row in actual_rows), key=repr)
    expected = sorted((_normalize_result_row(row) for row in expected_rows), key=repr)
    return actual == expected


def _normalize_result_row(row: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted((_normalize_result_value(value) for value in row.values()), key=repr))


def _normalize_result_value(value: Any) -> tuple[str, Any]:
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("number", round(float(value), 6))
    return ("text", str(value).strip())


def _normalize_identifier(value: str) -> str:
    cleaned = re.sub(r"\s*\.\s*", ".", value.strip())
    return cleaned.replace("`", "").replace('"', "").replace("[", "").replace("]", "").lower()


def _short_name(value: str) -> str:
    return _normalize_identifier(value).split(".")[-1]


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 3)
