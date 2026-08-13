import secrets
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from backend.app.core.settings import Settings
from backend.app.presentation.api.dependencies.providers import get_app_settings


class SecurityRole(StrEnum):
    READER = "reader"
    ANALYST = "analyst"
    ADMIN = "admin"


ROLE_RANK = {
    SecurityRole.READER: 10,
    SecurityRole.ANALYST: 20,
    SecurityRole.ADMIN: 30,
}


@dataclass(frozen=True)
class SecurityPrincipal:
    subject: str
    role: SecurityRole
    authenticated: bool
    auth_enabled: bool


_api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="DataPilotApiKey",
    description="DataPilot-AI API key. Configure reader/analyst/admin keys in server settings.",
    auto_error=False,
)


def get_current_principal(
    api_key: str | None = Depends(_api_key_header),
    settings: Settings = Depends(get_app_settings),
) -> SecurityPrincipal:
    if not settings.security.auth_enabled:
        return SecurityPrincipal(
            subject="anonymous-development",
            role=SecurityRole.ADMIN,
            authenticated=False,
            auth_enabled=False,
        )

    candidate = (api_key or "").strip()
    if not candidate:
        raise _unauthorized("Missing API key")

    configured = (
        (SecurityRole.ADMIN, settings.security.admin_api_key),
        (SecurityRole.ANALYST, settings.security.analyst_api_key),
        (SecurityRole.READER, settings.security.reader_api_key),
    )
    for role, secret in configured:
        if secret is None:
            continue
        expected = secret.get_secret_value().strip()
        if secrets.compare_digest(candidate, expected):
            return SecurityPrincipal(
                subject=f"api-key:{role.value}",
                role=role,
                authenticated=True,
                auth_enabled=True,
            )

    raise _unauthorized("Invalid API key")


def require_minimum_role(required_role: SecurityRole):
    def dependency(
        principal: SecurityPrincipal = Depends(get_current_principal),
    ) -> SecurityPrincipal:
        if ROLE_RANK[principal.role] < ROLE_RANK[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher is required",
            )
        return principal

    return dependency


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "ApiKey"},
    )
