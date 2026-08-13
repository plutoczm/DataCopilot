from typing import Any

from pydantic import BaseModel, Field

from backend.app.application.query_execution.models import DataSourceInfo


class QueryExecutionRequest(BaseModel):
    datasource: str = Field(min_length=1, max_length=64, examples=["retail_demo"])
    sql: str = Field(min_length=1, max_length=100000)
    max_rows: int | None = Field(default=None, ge=1, le=1000)


class QueryExecutionResponse(BaseModel):
    query_id: str
    datasource: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    elapsed_ms: float


class DataSourceListResponse(BaseModel):
    execution_enabled: bool
    datasources: list[DataSourceInfo]


class DataSourceSchemaResponse(BaseModel):
    datasource: str
    engine: str
    schema_context: str
    table_count: int = Field(ge=0)
    fingerprint: str
