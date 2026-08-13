from dataclasses import dataclass, field

from backend.app.application.agent.graph import AgentGraph
from backend.app.application.query_execution.service import QueryExecutionService
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
from backend.app.domain.ports.llm_provider import LLMProvider
from backend.app.domain.ports.vector_store import VectorStore
from backend.app.infrastructure.document_loaders import DocumentLoaderFactory
from backend.app.infrastructure.embeddings import BGEM3EmbeddingProvider, EmbeddingProvider
from backend.app.infrastructure.llm import DeepSeekProvider, OllamaProvider, OpenAIProvider
from backend.app.infrastructure.query_execution import SQLiteReadOnlyExecutor
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
_query_execution_service: QueryExecutionService | None = None
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
    """根据单一运行时配置选择 LLM provider。

    业务服务只依赖统一 LLMProvider 端口；模型切换发生在应用启动边界，
    避免把任务级模型路由逻辑扩散到 RAG、Text2SQL 等业务服务内部。
    """

    global _llm_provider
    if _llm_provider is None:
        resolved = settings or get_app_settings()
        if resolved.llm.default_provider is ProviderName.OLLAMA:
            _llm_provider = OllamaProvider(resolved)
        elif resolved.llm.default_provider is ProviderName.OPENAI:
            _llm_provider = OpenAIProvider(config=resolved.openai, provider_name="openai")
        else:
            _llm_provider = DeepSeekProvider(resolved)
    return _llm_provider


def get_query_execution_service() -> QueryExecutionService:
    """FastAPI dependency for the governed query execution service.

    Keep this dependency parameter-free. Adding a complex Settings parameter here would make
    FastAPI infer an additional request body field and silently change the public POST contract.
    """

    global _query_execution_service
    if _query_execution_service is None:
        resolved = get_app_settings()
        execution = resolved.query_execution
        executor = SQLiteReadOnlyExecutor(
            name=execution.datasource_name,
            database_path=execution.sqlite_path,
        )
        _query_execution_service = QueryExecutionService(
            executors={execution.datasource_name: executor},
            enabled=execution.enabled,
            max_rows=execution.max_rows,
            timeout_ms=execution.timeout_ms,
        )
    return _query_execution_service


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
        llm_provider=get_llm_provider(settings),
    )


def get_text2sql_service() -> Text2SQLService:
    settings = get_app_settings()
    return Text2SQLService(
        llm_provider=get_llm_provider(settings),
        rag_service=get_rag_service(),
    )


def get_sql_review_service() -> SQLReviewService:
    settings = get_app_settings()
    return SQLReviewService(
        llm_provider=get_llm_provider(settings),
        text2sql_service=get_text2sql_service(),
    )


def get_warehouse_design_service() -> WarehouseDesignService:
    settings = get_app_settings()
    return WarehouseDesignService(
        llm_provider=get_llm_provider(settings),
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
            llm_provider=get_llm_provider(settings),
        )
    return _agent_graph
