from fastapi import APIRouter, Depends

from backend.app.presentation.api.dependencies.security import (
    SecurityPrincipal,
    get_current_principal,
)
from backend.app.presentation.api.schemas.auth import AuthMeResponse


router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="查看当前 API 身份",
)
def auth_me(
    principal: SecurityPrincipal = Depends(get_current_principal),
) -> AuthMeResponse:
    return AuthMeResponse(
        auth_enabled=principal.auth_enabled,
        authenticated=principal.authenticated,
        subject=principal.subject,
        role=principal.role,
    )
