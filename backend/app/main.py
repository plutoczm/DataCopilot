import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.application.agent.exceptions import AgentError
from backend.app.core.constants import APP_VERSION
from backend.app.core.config import get_settings
from backend.app.core.logging_config import setup_fastapi_logging
from backend.app.infrastructure.llm.exceptions import LLMProviderError
from backend.app.infrastructure.vectorstore.exceptions import VectorStoreError
from backend.app.presentation.api.router import api_router
from backend.app.presentation.api.schemas.common import ErrorDetail, ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    logger = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if logger is not None:
            logger.info(
                "Application startup",
                extra={
                    "environment": settings.environment.value,
                    "api_only": settings.runtime.api_only,
                    "gpu_enabled": settings.runtime.gpu_enabled,
                },
            )
        yield
        if logger is not None:
            logger.info("Application shutdown")

    app = FastAPI(
        title=settings.app.name,
        description="AI Data Engineering Copilot Platform API",
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Health", "description": "Application and dependency health."},
            {"name": "Config", "description": "Runtime capability discovery."},
            {"name": "Knowledge Base", "description": "Document ingestion and RAG query APIs."},
            {"name": "Chat", "description": "Streaming chat APIs."},
            {"name": "Text2SQL", "description": "Natural language to SQL generation APIs."},
            {"name": "SQL Review", "description": "SQL quality, risk, and optimization review APIs."},
            {"name": "Warehouse Design", "description": "Layered data warehouse design generation APIs."},
            {"name": "Agent", "description": "Unified LangGraph agent routing APIs."},
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.app.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger = setup_fastapi_logging(app, settings)

    @app.middleware("http")
    async def request_timing(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        response.headers["x-process-time-ms"] = str(duration_ms)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="validation_error",
                    message="Request validation failed",
                    details=[dict(error) for error in exc.errors()],
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(LLMProviderError)
    async def llm_exception_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        logger.error("LLM provider error", extra={"error": str(exc)})
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error=ErrorDetail(code="llm_provider_error", message=str(exc))
            ).model_dump(mode="json"),
        )

    @app.exception_handler(VectorStoreError)
    async def vector_exception_handler(request: Request, exc: VectorStoreError) -> JSONResponse:
        logger.error("Vector store error", extra={"error": str(exc)})
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(code="vector_store_error", message=str(exc))
            ).model_dump(mode="json"),
        )

    @app.exception_handler(AgentError)
    async def agent_exception_handler(request: Request, exc: AgentError) -> JSONResponse:
        logger.error("Agent error", extra={"error": str(exc)})
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(code="agent_error", message=str(exc))
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API exception")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="internal_server_error",
                    message="Internal server error",
                )
            ).model_dump(mode="json"),
        )

    app.include_router(api_router)
    return app


app = create_app()
