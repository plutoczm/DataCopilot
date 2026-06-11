from backend.app.application.rag.models import RetrievedChunk
from backend.app.domain.ports.vector_store import VectorStore
from backend.app.infrastructure.embeddings.embedding_provider import EmbeddingProvider


class RetrievalService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def retrieve(
        self,
        question: str,
        *,
        collection_name: str,
        top_k: int = 5,
        metadata_filter: dict[str, str | int | float | bool] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = await self.embedding_provider.embed_query(question)
        results = self.vector_store.similarity_search_with_scores(
            collection_name,
            query_embedding.embedding,
            limit=top_k,
            metadata_filter=metadata_filter,
        )
        retrieved = [
            RetrievedChunk(chunk=result.chunk, score=result.score)
            for result in results
        ]
        if score_threshold is not None:
            retrieved = [
                item for item in retrieved if item.score >= score_threshold
            ]
        return retrieved
