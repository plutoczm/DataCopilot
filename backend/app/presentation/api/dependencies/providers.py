from backend.app.application.agent.graph import AgentGraph
from backend.app.application.query_execution.service import QueryExecutionService
from backend.app.application.rag.chunking_service import ChunkingService
from backend.app.application.rag.citation_service import CitationService
from backend.app.application.rag.document_catalog_service import DocumentCatalogService
from backend.app.application.rag.document_ingestion_service import DocumentIngestionService
from backend.app.application.rag.document_registry import DocumentRegistry
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
from backend.app.infrastructure.registry import SQLiteDocumentRegistry
from backend.app.infrastructure.vectorstore import ChromaDBVectorStore


DEFAULT_KNOWLEDGE_COLLECTION = "knowledge_base"


_vector_store: VectorStore | None = None
_embedding_provider: EmbeddingProvider | None = None
_llm_provider: LLMProvider | None = None
_document_registry: DocumentRegistry | None = None
_query_executor: SQLiteReadOnlyExecutor | None = None
_query_execution_service: QueryExecutionService | None = None
_agent_graph: AgentGraph | None = None


def get_app_settings() -> Settings:
    return get_settings()


def get_document_registry() -> DocumentRegistry:
    global _document_registry
    if _document_registry is None:
        settings = get_app_settings()
        registry_path = settings.paths.data_dir / "metadata" / "knowledge_registry.db"
        _document_registry = SQLiteDocumentRegistry(registry_path)
    return _document_registry


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
    """Select one runtime LLM provider at the application composition root."""

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


def _get_query_executor() -> SQLiteReadOnlyExecutor:
    global _query_executor
    if _query_executor is None:
        resolved = get_app_settings()
        execution = resolved.query_execution
        _query_executor = SQLiteReadOnlyExecutor(
            name=execution.datasource_name,
            database_path=execution.sqlite_path,
        )
    return _query_executor


def _get_schema_catalogs() -> dict[str, SQLiteReadOnlyExecutor]:
    executor = _get_query_executor()
    return {executor.name: executor}


def get_query_execution_service() -> QueryExecutionService:
    """FastAPI dependency for governed read-only query execution.

    Keep this dependency parameter-free. A complex Settings argument would be inferred by
    FastAPI as another body parameter and silently change the public POST contract.
    """

    global _query_execution_service
    if _query_execution_service is None:
        resolved = get_app_settings()
        execution = resolved.query_execution
        executor = _get_query_executor()
        _query_execution_service = QueryExecutionService(
            executors={executor.name: executor},
            schema_catalogs=_get_schema_catalogs(),
            enabled=execution.enabled,
            max_rows=execution.max_rows,
            timeout_ms=execution.timeout_ms,
        )
    return _query_execution_service


def get_document_catalog_service() -> DocumentCatalogService:
    settings = get_app_settings()
    return DocumentCatalogService(
        registry=get_document_registry(),
        vector_store=get_vector_store(settings),
        uploads_dir=settings.paths.uploads_dir,
    )


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
        schema_catalogs=_get_schema_catalogs(),
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
