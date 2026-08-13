from typing import Any

from pydantic import BaseModel, Field


class DataSourceInfo(BaseModel):
    name: str
    kind: str
    available: bool
    description: str | None = None


class QueryExecutionResult(BaseModel):
    query_id: str
    datasource: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int = Field(ge=0)
    truncated: bool
    elapsed_ms: float = Field(ge=0.0)
