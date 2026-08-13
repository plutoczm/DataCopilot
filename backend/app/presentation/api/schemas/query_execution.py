from typing import Any

from pydantic import BaseModel, Field

from backend.app.application.query_execution.models import DataSourceInfo


class QueryExecutionRequest(BaseModel):
    datasource: str = Field(min_length=1, max_length=64, examples=["retail_demo"])
    sql: str = Field(min_length=1, max_length=100000)
    max_rows: int | None = Field(default=None, ge=1, le=1000)
    expected_schema_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
        description=(
            "可选的生成时 Schema SHA-256。提供后，执行前会重新读取数据源 Schema；"
            "若 fingerprint 不一致则以 409 schema_drift 拒绝执行。"
        ),
    )


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
