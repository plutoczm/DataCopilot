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
    QueryExecutionRequest,
    QueryExecutionResponse,
)


router = APIRouter(prefix="/api/v1/query-execution", tags=["Query Execution"])


@router.get(
    "/datasources",
    response_model=DataSourceListResponse,
    summary="列出可用只读数据源",
    description="只返回非敏感的数据源名称、类型和可用状态，不返回数据库文件路径或凭据。",
)
def list_datasources(
    service: QueryExecutionService = Depends(get_query_execution_service),
) -> DataSourceListResponse:
    return DataSourceListResponse(
        execution_enabled=service.enabled,
        datasources=service.list_datasources(),
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
