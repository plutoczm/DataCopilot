from fastapi import APIRouter, Depends

from backend.app.application.query_execution.service import QueryExecutionService
from backend.app.presentation.api.dependencies.providers import get_query_execution_service
from backend.app.presentation.api.dependencies.security import (
    SecurityPrincipal,
    SecurityRole,
    require_minimum_role,
)
from backend.app.presentation.api.schemas.query_execution import (
    DataSourceListResponse,
    DataSourceSchemaResponse,
    QueryExecutionRequest,
    QueryExecutionResponse,
)


router = APIRouter(prefix="/api/v1/query-execution", tags=["Query Execution"])


@router.get(
    "/datasources",
    response_model=DataSourceListResponse,
    summary="列出已配置数据源",
    description=(
        "返回非敏感的数据源名称、类型和物理可用状态。execution_enabled 单独表示"
        "服务端是否允许执行模型生成 SQL；即使执行关闭，Schema 元数据仍可用于 Text2SQL。"
    ),
)
def list_datasources(
    service: QueryExecutionService = Depends(get_query_execution_service),
) -> DataSourceListResponse:
    return DataSourceListResponse(
        execution_enabled=service.enabled,
        datasources=service.list_datasources(),
    )


@router.get(
    "/datasources/{datasource}/schema",
    response_model=DataSourceSchemaResponse,
    summary="读取数据源 Schema Snapshot",
    description=(
        "读取用于 Text2SQL 的非凭据 Schema 快照与 fingerprint。Schema 访问和 SQL 执行"
        "使用不同权限边界；该接口不会开启任意 SQL 执行能力。"
    ),
)
def get_datasource_schema(
    datasource: str,
    _: SecurityPrincipal = Depends(require_minimum_role(SecurityRole.READER)),
    service: QueryExecutionService = Depends(get_query_execution_service),
) -> DataSourceSchemaResponse:
    snapshot = service.get_schema(datasource)
    return DataSourceSchemaResponse(
        datasource=snapshot.datasource,
        engine=snapshot.engine,
        schema_context=snapshot.schema_context,
        table_count=snapshot.table_count,
        fingerprint=snapshot.fingerprint,
    )


@router.post(
    "",
    response_model=QueryExecutionResponse,
    summary="受治理地执行只读 SQL",
    description=(
        "仅允许 analyst/admin 显式执行单条 SELECT/WITH 查询，并叠加服务器端"
        "行数上限、超时、只读数据库连接和结构化审计日志。"
    ),
)
def execute_query(
    request: QueryExecutionRequest,
    principal: SecurityPrincipal = Depends(
        require_minimum_role(SecurityRole.ANALYST)
    ),
    service: QueryExecutionService = Depends(get_query_execution_service),
) -> QueryExecutionResponse:
    result = service.execute(
        datasource=request.datasource,
        sql=request.sql,
        max_rows=request.max_rows,
        actor=principal.subject,
    )
    return QueryExecutionResponse(**result.model_dump())
