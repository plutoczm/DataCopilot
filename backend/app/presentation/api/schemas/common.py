from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class DeleteResponse(BaseModel):
    deleted: bool
    document_id: str
