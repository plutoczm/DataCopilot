from dataclasses import dataclass, field

from backend.app.application.agent.graph import AgentGraph
from backend.app.application.rag.chunking_service import ChunkingService
from backend.app.application.rag.citation_service import CitationService
from backend.app.application.rag.document_ingestion_service import DocumentIngestionService
from backend.app.application.rag.models import IngestionResult
from backend.app.application.rag.rag_service import RAGService
from backend.app.application.rag.retrieval_service import RetrievalService
from backend.app.application.sql_review.sql_review_service import SQLReviewService
from backend.app.application.text2sql.text2sql_service import Text2SQLService
from backend.app.application.warehouse_design.design_service import WarehouseDesignService
from backend.app.core.config import get_settings
from backend.app.core.settings import ProviderName, Settings
from backend.app.domain.ports.llm_provider import LLMProvider, TaskType
from backend.app.domain.ports.vector_store import VectorStore
from backend.app.infrastructure.document_loaders import DocumentLoaderFactory
from backend.app.infrastructure.embeddings import BGEM3EmbeddingProvider, EmbeddingProvider
from backend.app.infrastructure.llm import (
    DeepSeekProvider,
    OllamaProvider,
    OpenAIProvider,
    RoutingLLMProvider,
    TaskBoundLLMProvider,
)
from backend.app.infrastructure.vectorstore import ChromaDBVectorStore


DEFAULT_KNOWLEDGE_COLLECTION = "knowledge_base"


@dataclass
class DocumentRegistry:
    documents: dict[str, IngestionResult] = field(default_factory=dict)

    def add(self, result: IngestionResult) -> None:
        self.documents[result.document_id] = result

    def list(self) -> list[IngestionResult]:
        return list(self.documents.values())

    def delete(self, document_id: str) -> bool:
        return self.documents.pop(document_id, None) is not None


_registry = DocumentRegistry()
_vector_store: VectorStore | None = None
_embedding_provider: EmbeddingProvider | None = None
_llm_provider: LLMProvider | None = None
_agent_graph: AgentGraph | None = None


def get_app_settings() -> Settings:
    return get_settings()


def get_document_registry() -> DocumentRegistry:
    return _registry


def get_vector_store(settings: Settings = None) -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaDBVectorStore(settings=settings or get_app_settings())
        if DEFAULT_KNOWLEDGE_COLLECTION not in _vector_store.list_collections():
            _vector_store.create_collection(
                DEFAULT_KNOWLEDGE_COLLECTION,
                metadata={"purpose": "default knowledge base"},
            )
    return _vector_store


def get_embedding_provider(settings: Settings = None) -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = BGEM3EmbeddingProvider(settings or get_app_settings())
    return _embedding_provider


def get_llm_provider(settings: Settings = None) -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        resolved = settings or get_app_settings()
        if resolved.llm.routing_enabled:
            cloud_name = resolved.llm.cloud_provider or resolved.llm.default_provider
            cloud = _build_cloud_provider(resolved, cloud_name)
            if resolved.local.enabled:
                local = OpenAIProvider(config=resolved.local, provider_name="local")
            else:
                local = OllamaProvider(resolved)
            _llm_provider = RoutingLLMProvider(
                local=local,
                cloud=cloud,
                local_tasks=set(resolved.local.routing_tasks),
                fallback_on_error=resolved.llm.routing_fallback_to_cloud,
            )
        elif resolved.llm.default_provider is ProviderName.OLLAMA:
            _llm_provider = OllamaProvider(resolved)
        elif resolved.llm.default_provider is ProviderName.OPENAI:
            _llm_provider = OpenAIProvider(config=resolved.openai, provider_name="openai")
        elif resolved.llm.default_provider is ProviderName.LOCAL:
            _llm_provider = OpenAIProvider(config=resolved.local, provider_name="local")
        else:
            _llm_provider = DeepSeekProvider(resolved)
    return _llm_provider


def _build_cloud_provider(resolved: Settings, provider_name: ProviderName) -> LLMProvider:
    if provider_name is ProviderName.OPENAI:
        return OpenAIProvider(config=resolved.openai, provider_name="openai")
    if provider_name is ProviderName.OLLAMA:
        return OllamaProvider(resolved)
    if provider_name is ProviderName.LOCAL:
        return OpenAIProvider(config=resolved.local, provider_name="local")
    return DeepSeekProvider(resolved)


def _task_bound(provider: LLMProvider, task: TaskType) -> LLMProvider:
    """按业务任务绑定 provider；仅在多 LLM 路由开启时生效。"""
    if get_app_settings().llm.routing_enabled:
        return TaskBoundLLMProvider(provider, task)
    return provider


def get_document_ingestion_service() -> DocumentIngestionService:
    settings = get_app_settings()
    return DocumentIngestionService(
        loader_factory=DocumentLoaderFactory(),
        chunking_service=ChunkingService(),
        embedding_provider=get_embedding_provider(settings),
        vector_store=get_vector_store(settings),
        uploads_dir=settings.paths.uploads_dir,
    )


def get_rag_service() -> RAGService:
    settings = get_app_settings()
    retrieval_service = RetrievalService(
        embedding_provider=get_embedding_provider(settings),
        vector_store=get_vector_store(settings),
    )
    return RAGService(
        retrieval_service=retrieval_service,
        citation_service=CitationService(),
        llm_provider=_task_bound(get_llm_provider(settings), TaskType.RAG),
    )


def get_text2sql_service() -> Text2SQLService:
    settings = get_app_settings()
    return Text2SQLService(
        llm_provider=_task_bound(get_llm_provider(settings), TaskType.TEXT2SQL),
        rag_service=get_rag_service(),
    )


def get_sql_review_service() -> SQLReviewService:
    settings = get_app_settings()
    return SQLReviewService(
        llm_provider=_task_bound(get_llm_provider(settings), TaskType.SQL_REVIEW),
        text2sql_service=get_text2sql_service(),
    )


def get_warehouse_design_service() -> WarehouseDesignService:
    settings = get_app_settings()
    return WarehouseDesignService(
        llm_provider=_task_bound(get_llm_provider(settings), TaskType.WAREHOUSE_DESIGN),
        rag_service=get_rag_service(),
        text2sql_service=get_text2sql_service(),
        sql_review_service=get_sql_review_service(),
    )


def get_agent_graph() -> AgentGraph:
    global _agent_graph
    if _agent_graph is None:
        settings = get_app_settings()
        _agent_graph = AgentGraph(
            rag_service=get_rag_service(),
            text2sql_service=get_text2sql_service(),
            sql_review_service=get_sql_review_service(),
            warehouse_design_service=get_warehouse_design_service(),
            llm_provider=_task_bound(get_llm_provider(settings), TaskType.GENERAL_CHAT),
        )
    return _agent_graph
