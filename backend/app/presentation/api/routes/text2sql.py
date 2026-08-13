from fastapi import APIRouter, Depends

from backend.app.application.text2sql.text2sql_service import Text2SQLService
from backend.app.presentation.api.dependencies.providers import get_text2sql_service
from backend.app.presentation.api.schemas.text2sql import (
    Text2SQLRequest,
    Text2SQLResponse,
)


router = APIRouter(prefix="/api/v1/text2sql", tags=["Text2SQL"])


@router.post(
    "",
    response_model=Text2SQLResponse,
    summary="根据自然语言生成 SQL",
    description=(
        "支持手工 Schema 或已配置 datasource。选择 datasource 时服务端会自动发现"
        "表结构并绑定对应 SQL 引擎，再执行确定性 SQL 校验。"
    ),
)
async def generate_text2sql(
    request: Text2SQLRequest,
    service: Text2SQLService = Depends(get_text2sql_service),
) -> Text2SQLResponse:
    result = await service.generate(
        question=request.question,
        engine=request.engine,
        schema_context=request.schema_context,
        datasource=request.datasource,
        database_name=request.database_name,
        use_rag=request.use_rag,
        rag_collection_name=request.rag_collection_name,
    )
    return Text2SQLResponse(**result.model_dump())
