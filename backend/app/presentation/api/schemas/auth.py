from pydantic import BaseModel

from backend.app.presentation.api.dependencies.security import SecurityRole


class AuthMeResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool
    subject: str
    role: SecurityRole
