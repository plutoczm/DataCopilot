import logging
from pathlib import Path

from backend.app.application.rag.document_registry import DocumentRegistry
from backend.app.application.rag.models import IngestionResult
from backend.app.domain.ports.vector_store import VectorStore


class DocumentCatalogService:
    """Coordinate document metadata, vector chunks, and stored source files.

    The registry is the metadata source of truth for management APIs, while the vector store
    owns retrieval chunks. File deletion is restricted to the configured uploads directory so
    corrupted registry metadata cannot turn a document delete call into arbitrary file removal.
    """

    def __init__(
        self,
        *,
        registry: DocumentRegistry,
        vector_store: VectorStore,
        uploads_dir: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self.registry = registry
        self.vector_store = vector_store
        self.uploads_dir = Path(uploads_dir).resolve()
        self.logger = logger or logging.getLogger("datacopilot.document_catalog")

    def register(self, result: IngestionResult) -> None:
        self.registry.add(result)

    def list(self) -> list[IngestionResult]:
        return self.registry.list()

    def get(self, document_id: str) -> IngestionResult | None:
        return self.registry.get(document_id)

    def delete(self, document_id: str) -> bool:
        existing = self.registry.get(document_id)
        if existing is None:
            return False

        chunk_ids = [
            f"{document_id}:{index}" for index in range(existing.chunk_count)
        ]
        self.vector_store.delete_documents(existing.collection_name, chunk_ids)
        self._delete_source_file(existing.stored_path, document_id=document_id)
        self.registry.delete(document_id)
        return True

    def _delete_source_file(self, stored_path: Path, *, document_id: str) -> None:
        resolved = Path(stored_path).resolve()
        if not resolved.is_relative_to(self.uploads_dir):
            self.logger.warning(
                "Skipping source-file deletion outside uploads directory",
                extra={
                    "event_type": "document_cleanup_guard",
                    "document_id": document_id,
                    "stored_path": str(resolved),
                },
            )
            return
        resolved.unlink(missing_ok=True)
