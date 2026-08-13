from typing import Protocol

from backend.app.application.rag.models import IngestionResult


class DocumentRegistry(Protocol):
    """Application contract for persistent knowledge-document metadata."""

    def add(self, result: IngestionResult) -> None:
        raise NotImplementedError

    def list(self) -> list[IngestionResult]:
        raise NotImplementedError

    def get(self, document_id: str) -> IngestionResult | None:
        raise NotImplementedError

    def delete(self, document_id: str) -> bool:
        raise NotImplementedError
