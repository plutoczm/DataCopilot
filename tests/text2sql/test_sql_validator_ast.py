from backend.app.application.text2sql.models import SQLEngine
from backend.app.application.text2sql.schema_service import SchemaService
from backend.app.application.text2sql.sql_validator import SQLValidator


SCHEMA = """
CREATE TABLE users (
    user_id INTEGER,
    province TEXT
);
CREATE TABLE orders (
    order_id INTEGER,
    user_id INTEGER,
    amount REAL
);
"""


def _validator():
    return SQLValidator(), SchemaService().parse_schema_context(SCHEMA)


def test_ast_validator_understands_cte_and_count_star():
    validator, schema = _validator()
    result = validator.validate(
        "WITH paid AS ("
        "SELECT o.user_id, SUM(o.amount) AS amount FROM orders o GROUP BY o.user_id"
        ") "
        "SELECT COUNT(*) AS user_count FROM paid",
        schema=schema,
        engine=SQLEngine.SQLITE,
    )
    assert result.is_valid is True
    assert result.has_issue("unknown_table") is False
    assert result.has_issue("select_star") is False


def test_ast_validator_rejects_unknown_column_inside_nested_query():
    validator, schema = _validator()
    result = validator.validate(
        "SELECT x.user_id FROM (SELECT o.fake_column AS user_id FROM orders o) x",
        schema=schema,
        engine=SQLEngine.SQLITE,
    )
    assert result.is_valid is False
    assert result.has_issue("unknown_column")


def test_ast_validator_does_not_treat_keywords_in_literals_as_statements():
    validator, schema = _validator()
    result = validator.validate(
        "SELECT u.user_id FROM users u WHERE u.province = 'drop table orders'",
        schema=schema,
        engine=SQLEngine.SQLITE,
    )
    assert result.is_valid is True
    assert result.has_issue("dangerous_drop") is False


def test_ast_validator_rejects_multiple_statements():
    validator, schema = _validator()
    result = validator.validate(
        "SELECT user_id FROM users; DELETE FROM orders",
        schema=schema,
        engine=SQLEngine.SQLITE,
    )
    assert result.is_valid is False
    assert result.has_issue("multiple_statements")
    assert result.has_issue("dangerous_delete")
