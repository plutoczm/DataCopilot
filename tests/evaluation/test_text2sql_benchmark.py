from backend.app.application.evaluation import (
    SafetyPolicyCase,
    SafetyPolicyReport,
    Text2SQLBenchmarkCase,
    Text2SQLBenchmarkReport,
    extract_referenced_tables,
    extract_schema_tables,
)


def test_extract_referenced_tables_excludes_cte_aliases() -> None:
    sql = """
    WITH recent_orders AS (
        SELECT order_id, customer_id FROM analytics.orders
    )
    SELECT c.region, COUNT(*)
    FROM recent_orders r
    JOIN customers c ON r.customer_id = c.customer_id
    GROUP BY c.region
    """

    assert extract_referenced_tables(sql) == {"analytics.orders", "customers"}


def test_extract_schema_tables_supports_qualified_and_quoted_names() -> None:
    schema = """
    CREATE TABLE orders(id INTEGER);
    CREATE TABLE IF NOT EXISTS `analytics`.`customers`(id INTEGER);
    """

    assert extract_schema_tables(schema) == {"orders", "analytics.customers"}


def test_text2sql_benchmark_report_keeps_metrics_distinct() -> None:
    report = Text2SQLBenchmarkReport.from_cases(
        [
            Text2SQLBenchmarkCase(
                case_id="ok",
                generation_succeeded=True,
                validation_passed=True,
                execution_attempted=True,
                execution_succeeded=True,
                expected_tables={"orders", "customers"},
                referenced_tables={"orders", "customers"},
                allowed_tables={"orders", "customers", "refunds"},
                generation_latency_ms=100,
                execution_latency_ms=20,
                total_tokens=40,
            ),
            Text2SQLBenchmarkCase(
                case_id="hallucination",
                generation_succeeded=True,
                validation_passed=False,
                expected_tables={"refunds", "orders"},
                referenced_tables={"refunds", "invented_table"},
                allowed_tables={"orders", "customers", "refunds"},
                generation_latency_ms=300,
                total_tokens=60,
            ),
            Text2SQLBenchmarkCase(
                case_id="generation_error",
                generation_succeeded=False,
                expected_tables={"orders"},
                allowed_tables={"orders", "customers", "refunds"},
                generation_latency_ms=200,
            ),
        ]
    )

    assert report.case_count == 3
    assert report.generation_success_rate == 0.6667
    assert report.valid_sql_rate == 0.3333
    assert report.execution_attempt_rate == 0.3333
    assert report.execution_success_rate == 1.0
    assert report.expected_table_recall == 0.5
    assert report.schema_hallucination_rate == 0.3333
    assert report.average_generation_latency_ms == 200.0
    assert report.p95_generation_latency_ms == 300
    assert report.average_execution_latency_ms == 20.0
    assert report.total_tokens == 100
    assert report.average_tokens_per_case == 33.333


def test_text2sql_benchmark_report_handles_no_cases() -> None:
    report = Text2SQLBenchmarkReport.from_cases([])

    assert report.case_count == 0
    assert report.execution_success_rate == 0.0
    assert report.p95_generation_latency_ms == 0.0


def test_safety_policy_report_tracks_safe_and_unsafe_decisions() -> None:
    report = SafetyPolicyReport.from_cases(
        [
            SafetyPolicyCase(
                case_id="safe",
                expected_allowed=True,
                actual_allowed=True,
                status_code=200,
            ),
            SafetyPolicyCase(
                case_id="unsafe_blocked",
                expected_allowed=False,
                actual_allowed=False,
                status_code=400,
                error_code="query_rejected",
            ),
            SafetyPolicyCase(
                case_id="unsafe_missed",
                expected_allowed=False,
                actual_allowed=True,
                status_code=200,
            ),
        ]
    )

    assert report.case_count == 3
    assert report.decision_accuracy == 0.6667
    assert report.unsafe_rejection_rate == 0.5
    assert report.safe_acceptance_rate == 1.0
