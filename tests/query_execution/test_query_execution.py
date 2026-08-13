import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.application.query_execution.exceptions import (
    DataSourceNotFoundError,
    DataSourceUnavailableError,
    QueryExecutionDisabledError,
    QueryRejectedError,
    SchemaDriftError,
)
from backend.app.application.query_execution.policy import ReadOnlySQLPolicy
from backend.app.application.query_execution.service import QueryExecutionService
from backend.app.core.settings import Settings
from backend.app.infrastructure.query_execution import SQLiteReadOnlyExecutor
from backend.app.main import create_app
from backend.app.presentation.api.dependencies.providers import get_query_execution_service


def build_database(path: Path) -> None:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                amount REAL NOT NULL,
                status TEXT NOT NULL
            );
            INSERT INTO orders(order_id, amount, status) VALUES
                (1, 10.0, 'paid'),
                (2, 20.0, 'paid'),
                (3, 30.0, 'refunded');
            """
        )
        connection.commit()
    finally:
        connection.close()


def make_service(
    tmp_path: Path,
    *,
    enabled: bool = True,
    max_rows: int = 2,
    timeout_ms: int = 1000,
) -> QueryExecutionService:
    database_path = tmp_path / "demo.db"
    build_database(database_path)
    executor = SQLiteReadOnlyExecutor(
        name="retail_demo",
        database_path=database_path,
    )
    return QueryExecutionService(
        executors={"retail_demo": executor},
        schema_catalogs={"retail_demo": executor},
        enabled=enabled,
        max_rows=max_rows,
        timeout_ms=timeout_ms,
        logger=logging.getLogger("test.query_audit"),
    )


def test_query_execution_settings_are_disabled_and_project_local_by_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.query_execution.enabled is False
    assert settings.query_execution.datasource_name == "retail_demo"
    assert settings.query_execution.max_rows == 200
    assert settings.query_execution.timeout_ms == 3000
    assert settings.query_execution.sqlite_path.is_relative_to(settings.paths.project_root)

    with pytest.raises(
        ValidationError,
        match="query_execution.sqlite_path must stay inside project_root",
    ):
        Settings(
            _env_file=None,
            query_execution={
                "enabled": True,
                "sqlite_path": "/var/lib/datacopilot/demo.db",
            },
        )


def test_read_only_policy_rejects_mutation_and_multiple_statements() -> None:
    policy = ReadOnlySQLPolicy()

    assert policy.validate("SELECT order_id FROM orders").allowed is True
    assert policy.validate("WITH x AS (SELECT 1) SELECT * FROM x").allowed is True
    assert policy.validate("SELECT 'drop table orders' AS note").allowed is True
    assert policy.validate("SELECT 1; SELECT 2").allowed is False
    assert policy.validate("DELETE FROM orders").allowed is False
    assert policy.validate("WITH x AS (SELECT 1) DELETE FROM orders").allowed is False
    assert policy.validate("SELECT load_extension('x')").allowed is False
    assert policy.validate("-- DELETE\nSELECT 1").allowed is True


def test_schema_discovery_is_available_even_when_execution_is_disabled(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path, enabled=False)

    datasource = service.list_datasources()[0]
    assert datasource.available is True
    assert service.enabled is False

    first = service.get_schema("retail_demo")
    second = service.get_schema("retail_demo")

    assert first.datasource == "retail_demo"
    assert first.engine == "sqlite"
    assert first.table_count == 1
    assert "CREATE TABLE orders" in first.schema_context
    assert len(first.fingerprint) == 64
    assert first.fingerprint == second.fingerprint

    with pytest.raises(DataSourceNotFoundError):
        service.get_schema("missing")


def test_sqlite_executor_is_read_only_and_enforces_row_cap(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    result = service.execute(
        datasource="retail_demo",
        sql="SELECT order_id, amount FROM orders ORDER BY order_id",
        max_rows=1000,
    )

    assert result.columns == ["order_id", "amount"]
    assert result.row_count == 2
    assert result.truncated is True
    assert [row["order_id"] for row in result.rows] == [1, 2]
    assert result.elapsed_ms >= 0


def test_execution_accepts_matching_schema_fingerprint_and_rejects_drift(
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path)
    snapshot = service.get_schema("retail_demo")

    ok = service.execute(
        datasource="retail_demo",
        sql="SELECT COUNT(*) AS n FROM orders",
        expected_schema_fingerprint=snapshot.fingerprint,
    )
    assert ok.row_count == 1

    executor = service.executors["retail_demo"]
    assert isinstance(executor, SQLiteReadOnlyExecutor)
    connection = sqlite3.connect(executor.database_path)
    try:
        connection.execute("CREATE TABLE customers(customer_id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    current = service.get_schema("retail_demo")
    assert current.fingerprint != snapshot.fingerprint
    with pytest.raises(SchemaDriftError, match="Regenerate and review"):
        service.execute(
            datasource="retail_demo",
            sql="SELECT COUNT(*) AS n FROM orders",
            expected_schema_fingerprint=snapshot.fingerprint,
        )


def test_service_rejects_dangerous_sql_before_database_execution(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    with pytest.raises(QueryRejectedError, match="prohibited_delete"):
        service.execute(datasource="retail_demo", sql="DELETE FROM orders")


def test_service_reports_disabled_unknown_and_unavailable_datasources(
    tmp_path: Path,
) -> None:
    disabled = make_service(tmp_path, enabled=False)
    with pytest.raises(QueryExecutionDisabledError):
        disabled.execute(datasource="retail_demo", sql="SELECT 1")

    enabled = make_service(tmp_path)
    with pytest.raises(DataSourceNotFoundError):
        enabled.execute(datasource="missing", sql="SELECT 1")

    missing_executor = SQLiteReadOnlyExecutor(
        name="missing_file",
        database_path=tmp_path / "missing.db",
    )
    unavailable = QueryExecutionService(
        executors={"missing_file": missing_executor},
        schema_catalogs={"missing_file": missing_executor},
        enabled=True,
        max_rows=10,
        timeout_ms=1000,
    )
    with pytest.raises(DataSourceUnavailableError):
        unavailable.execute(datasource="missing_file", sql="SELECT 1")
    with pytest.raises(DataSourceUnavailableError):
        unavailable.get_schema("missing_file")


def test_query_execution_api_returns_datasources_schema_and_rows(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    app = create_app()
    app.dependency_overrides[get_query_execution_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)

    datasources = client.get("/api/v1/query-execution/datasources")
    assert datasources.status_code == 200
    payload = datasources.json()
    assert payload["execution_enabled"] is True
    assert payload["datasources"][0]["name"] == "retail_demo"
    assert payload["datasources"][0]["available"] is True

    schema = client.get("/api/v1/query-execution/datasources/retail_demo/schema")
    assert schema.status_code == 200, schema.text
    schema_payload = schema.json()
    assert schema_payload["engine"] == "sqlite"
    assert schema_payload["table_count"] == 1
    assert "CREATE TABLE orders" in schema_payload["schema_context"]
    assert len(schema_payload["fingerprint"]) == 64

    response = client.post(
        "/api/v1/query-execution",
        json={
            "datasource": "retail_demo",
            "sql": "SELECT order_id, amount FROM orders ORDER BY order_id",
            "max_rows": 1,
            "expected_schema_fingerprint": schema_payload["fingerprint"],
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["row_count"] == 1
    assert result["truncated"] is True
    assert result["rows"][0]["order_id"] == 1
    assert response.headers["x-request-id"]


def test_query_execution_api_returns_conflict_on_schema_drift(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    app = create_app()
    app.dependency_overrides[get_query_execution_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/query-execution",
        json={
            "datasource": "retail_demo",
            "sql": "SELECT COUNT(*) AS n FROM orders",
            "expected_schema_fingerprint": "0" * 64,
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "schema_drift"

    invalid = client.post(
        "/api/v1/query-execution",
        json={
            "datasource": "retail_demo",
            "sql": "SELECT 1",
            "expected_schema_fingerprint": "not-a-sha256",
        },
    )
    assert invalid.status_code == 422


def test_query_execution_api_maps_policy_errors_to_client_error(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    app = create_app()
    app.dependency_overrides[get_query_execution_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/query-execution",
        json={"datasource": "retail_demo", "sql": "DROP TABLE orders"},
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "query_rejected"
