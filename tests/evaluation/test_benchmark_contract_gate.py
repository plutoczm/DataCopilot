import json
from pathlib import Path

from examples.retail_analytics.validate_benchmark_definition import (
    validate_benchmark_definition,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETAIL = PROJECT_ROOT / "examples" / "retail_analytics"


def test_repository_retail_benchmark_contract_is_valid() -> None:
    result = validate_benchmark_definition(
        questions_path=RETAIL / "questions.json",
        schema_path=RETAIL / "schema.sql",
        safety_cases_path=RETAIL / "safety_cases.json",
    )

    assert result["passed"] is True, result["failures"]
    assert result["question_count"] == 5
    assert result["safety_case_count"] >= 1
    assert {"orders", "customers", "products", "order_items", "refunds"}.issubset(
        result["schema_tables"]
    )


def test_contract_gate_rejects_definition_drift(tmp_path: Path) -> None:
    schema = tmp_path / "schema.sql"
    questions = tmp_path / "questions.json"
    safety = tmp_path / "safety.json"
    schema.write_text("CREATE TABLE orders(order_id INTEGER);", encoding="utf-8")
    questions.write_text(
        json.dumps(
            [
                {
                    "id": "q1",
                    "question": "count orders",
                    "engine": "sqlite",
                    "expected_tables": ["orders"],
                    "golden_sql": "SELECT COUNT(*) FROM orders",
                },
                {
                    "id": "q1",
                    "question": "bad table",
                    "engine": "sqlite",
                    "expected_tables": ["missing"],
                    "golden_sql": "SELECT * FROM missing",
                },
            ]
        ),
        encoding="utf-8",
    )
    safety.write_text(
        json.dumps(
            [
                {
                    "id": "safe_select",
                    "sql": "SELECT order_id FROM orders",
                    "expected_allowed": False,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_benchmark_definition(
        questions_path=questions,
        schema_path=schema,
        safety_cases_path=safety,
    )

    assert result["passed"] is False
    assert any("duplicate question id" in failure for failure in result["failures"])
    assert any("unknown schema tables" in failure for failure in result["failures"])
    assert any("disagrees with ReadOnlySQLPolicy" in failure for failure in result["failures"])
