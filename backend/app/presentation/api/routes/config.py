from fastapi import APIRouter, Depends

from backend.app.core.settings import ProviderName, Settings
from backend.app.presentation.api.dependencies.providers import get_app_settings
from backend.app.presentation.api.schemas.knowledge import RuntimeConfigResponse


router = APIRouter(prefix="/api/v1/config", tags=["Config"])


@router.get(
    "/runtime",
    response_model=RuntimeConfigResponse,
    summary="运行时能力",
    description="返回不含敏感信息的运行能力和提供方选择。",
)
def runtime_config(settings: Settings = Depends(get_app_settings)) -> RuntimeConfigResponse:
    return RuntimeConfigResponse(
        environment=settings.environment.value,
        api_only=settings.runtime.api_only,
        gpu_enabled=settings.runtime.gpu_enabled,
        cpu_only=settings.runtime.cpu_only,
        default_llm_provider=settings.llm.default_provider.value,
        default_llm_model=_active_llm_model(settings),
        embedding_model=settings.embeddings.default_model,
        vector_store="chromadb",
        capabilities={
            "rag": True,
            "streaming": settings.llm.streaming_enabled,
            "document_upload": True,
            "gpu_optional": True,
            "read_only_query_execution": settings.query_execution.enabled,
        },
    )


def _active_llm_model(settings: Settings) -> str:
    if settings.llm.default_provider is ProviderName.OPENAI:
        return settings.openai.chat_model
    if settings.llm.default_provider is ProviderName.OLLAMA:
        return settings.ollama.chat_model
    return settings.deepseek.chat_model
