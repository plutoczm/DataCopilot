import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.application.query_execution.models import QueryExecutionResult
from backend.app.core.settings import Settings
from backend.app.main import create_app
from backend.app.presentation.api.dependencies.providers import (
    get_app_settings,
    get_query_execution_service,
)


ADMIN_KEY = "admin-key-0123456789abcdef"
ANALYST_KEY = "analyst-key-0123456789abcdef"
READER_KEY = "reader-key-0123456789abcdef"


class StubQueryExecutionService:
    enabled = True

    def list_datasources(self):
        return []

    def execute(self, *, datasource, sql, max_rows=None, actor="anonymous"):
        return QueryExecutionResult(
            query_id=actor,
            datasource=datasource,
            columns=["value"],
            rows=[{"value": 1}],
            row_count=1,
            truncated=False,
            elapsed_ms=1.0,
        )


def secure_settings(**security_overrides) -> Settings:
    security = {
        "auth_enabled": True,
        "reader_api_key": READER_KEY,
        "analyst_api_key": ANALYST_KEY,
        "admin_api_key": ADMIN_KEY,
    }
    security.update(security_overrides)
    return Settings(_env_file=None, security=security)


def test_security_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.security.auth_enabled is False


def test_enabling_auth_requires_strong_unique_admin_key() -> None:
    with pytest.raises(ValidationError, match="admin_api_key is required"):
        Settings(_env_file=None, security={"auth_enabled": True})

    with pytest.raises(ValidationError, match="at least 16 characters"):
        Settings(
            _env_file=None,
            security={"auth_enabled": True, "admin_api_key": "short"},
        )

    with pytest.raises(ValidationError, match="must be unique"):
        Settings(
            _env_file=None,
            security={
                "auth_enabled": True,
                "reader_api_key": ADMIN_KEY,
                "admin_api_key": ADMIN_KEY,
            },
        )


def test_production_query_execution_requires_authentication() -> None:
    with pytest.raises(
        ValidationError,
        match="query execution requires API authentication in production",
    ):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            query_execution={"enabled": True},
        )

    settings = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        query_execution={"enabled": True},
        security={"auth_enabled": True, "admin_api_key": ADMIN_KEY},
    )
    assert settings.security.auth_enabled is True


def make_secure_client() -> TestClient:
    app = create_app()
    settings = secure_settings()
    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_query_execution_service] = (
        lambda: StubQueryExecutionService()
    )
    return TestClient(app, raise_server_exceptions=False)


def test_health_stays_public_but_api_requires_key_when_auth_enabled() -> None:
    client = make_secure_client()

    health = client.get("/health")
    assert health.status_code == 200

    protected = client.get("/api/v1/config/runtime")
    assert protected.status_code == 401
    assert protected.headers["www-authenticate"] == "ApiKey"

    invalid = client.get(
        "/api/v1/config/runtime",
        headers={"X-API-Key": "invalid-key-0123456789"},
    )
    assert invalid.status_code == 401

    reader = client.get(
        "/api/v1/config/runtime",
        headers={"X-API-Key": READER_KEY},
    )
    assert reader.status_code == 200


def test_auth_me_reports_role_without_echoing_secret() -> None:
    client = make_secure_client()

    response = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": ANALYST_KEY},
    )

    assert response.status_code == 200
    assert response.json() == {
        "auth_enabled": True,
        "authenticated": True,
        "subject": "api-key:analyst",
        "role": "analyst",
    }
    assert ANALYST_KEY not in response.text


def test_query_execution_requires_analyst_or_admin_role() -> None:
    client = make_secure_client()
    payload = {
        "datasource": "retail_demo",
        "sql": "SELECT 1 AS value",
        "max_rows": 10,
    }

    reader = client.post(
        "/api/v1/query-execution",
        headers={"X-API-Key": READER_KEY},
        json=payload,
    )
    assert reader.status_code == 403

    analyst = client.post(
        "/api/v1/query-execution",
        headers={"X-API-Key": ANALYST_KEY},
        json=payload,
    )
    assert analyst.status_code == 200
    assert analyst.json()["query_id"] == "api-key:analyst"

    admin = client.post(
        "/api/v1/query-execution",
        headers={"X-API-Key": ADMIN_KEY},
        json=payload,
    )
    assert admin.status_code == 200
    assert admin.json()["query_id"] == "api-key:admin"
