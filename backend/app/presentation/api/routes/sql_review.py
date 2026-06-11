from fastapi import APIRouter, Depends

from backend.app.application.sql_review.sql_review_service import SQLReviewService
from backend.app.presentation.api.dependencies.providers import get_sql_review_service
from backend.app.presentation.api.schemas.sql_review import (
    GeneratedSQLReviewRequest,
    GeneratedSQLReviewResponse,
    SQLReviewRequest,
    SQLReviewResponse,
)


router = APIRouter(prefix="/api/v1/sql-review", tags=["SQL Review"])


@router.post(
    "",
    response_model=SQLReviewResponse,
    summary="Review SQL quality and performance",
    description="Analyze SQL risks, score quality, and return rule-based optimization guidance.",
)
async def review_sql(
    request: SQLReviewRequest,
    service: SQLReviewService = Depends(get_sql_review_service),
) -> SQLReviewResponse:
    result = await service.review(
        sql=request.sql,
        engine=request.engine,
        include_llm_explanation=request.include_llm_explanation,
    )
    return SQLReviewResponse(**result.model_dump())


@router.post(
    "/generated",
    response_model=GeneratedSQLReviewResponse,
    summary="Generate SQL and immediately review it",
    description="Run Text2SQL and SQL Review in one workflow.",
)
async def review_generated_sql(
    request: GeneratedSQLReviewRequest,
    service: SQLReviewService = Depends(get_sql_review_service),
) -> GeneratedSQLReviewResponse:
    result = await service.review_generated_sql(
        question=request.question,
        engine=request.engine,
        schema_context=request.schema_context,
        database_name=request.database_name,
        use_rag=request.use_rag,
    )
    return GeneratedSQLReviewResponse(**result.model_dump())
