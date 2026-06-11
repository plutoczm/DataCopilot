from fastapi import APIRouter, Depends

from backend.app.core.constants import APP_VERSION
from backend.app.core.settings import Settings
from backend.app.domain.ports.llm_provider import LLMProvider
from backend.app.domain.ports.vector_store import VectorStore
from backend.app.infrastructure.vectorstore.exceptions import CollectionNotFoundError
from backend.app.presentation.api.dependencies.providers import (
    DEFAULT_KNOWLEDGE_COLLECTION,
    get_app_settings,
    get_llm_provider,
    get_vector_store,
)
from backend.app.presentation.api.schemas.health import (
    HealthResponse,
    ProviderHealthResponse,
    RootResponse,
    VectorStoreHealthResponse,
)


router = APIRouter(tags=["Health"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="Service metadata",
    description="Return service metadata and API documentation links.",
)
def root(settings: Settings = Depends(get_app_settings)) -> RootResponse:
    return RootResponse(
        service=settings.app.name,
        version=APP_VERSION,
        status="running",
        docs="/docs",
        openapi="/openapi.json",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health",
    description="Validate application, LLM provider, and vector store status.",
)
async def health(
    settings: Settings = Depends(get_app_settings),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> HealthResponse:
    llm_status = await llm_provider.health_check()
    try:
        stats = vector_store.collection_stats(DEFAULT_KNOWLEDGE_COLLECTION)
        vector_status = "ok"
        document_count = stats.document_count
    except CollectionNotFoundError:
        vector_status = "missing"
        document_count = 0
    return HealthResponse(
        service=settings.app.name,
        status="ok" if llm_status.ok and vector_status == "ok" else "degraded",
        environment=settings.environment.value,
        llm_provider=ProviderHealthResponse(**llm_status.model_dump(exclude={"latency_ms"})),
        vector_store=VectorStoreHealthResponse(
            status=vector_status,
            collection_name=DEFAULT_KNOWLEDGE_COLLECTION,
            document_count=document_count,
        ),
    )
