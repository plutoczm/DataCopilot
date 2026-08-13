from pathlib import Path

from backend.app.application.rag.document_catalog_service import DocumentCatalogService
from backend.app.application.rag.models import IngestionResult


class FakeRegistry:
    def __init__(self) -> None:
        self.items: dict[str, IngestionResult] = {}

    def add(self, result: IngestionResult) -> None:
        self.items[result.document_id] = result

    def list(self) -> list[IngestionResult]:
        return list(self.items.values())

    def get(self, document_id: str) -> IngestionResult | None:
        return self.items.get(document_id)

    def delete(self, document_id: str) -> bool:
        return self.items.pop(document_id, None) is not None


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, list[str]]] = []

    def delete_documents(self, collection_name: str, ids, *, batch_size: int = 100) -> None:
        self.deleted.append((collection_name, list(ids)))


def make_result(stored_path: Path) -> IngestionResult:
    return IngestionResult(
        document_id="doc-1",
        filename=stored_path.name,
        file_type="md",
        domain="retail",
        stored_path=stored_path,
        collection_name="knowledge_base",
        chunk_count=2,
    )


def test_catalog_delete_cleans_vectors_registry_and_uploaded_file(tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    stored_path = uploads_dir / "metrics.md"
    stored_path.write_text("metrics", encoding="utf-8")
    registry = FakeRegistry()
    vector_store = FakeVectorStore()
    service = DocumentCatalogService(
        registry=registry,
        vector_store=vector_store,
        uploads_dir=uploads_dir,
    )
    service.register(make_result(stored_path))

    assert service.delete("doc-1") is True
    assert not stored_path.exists()
    assert registry.get("doc-1") is None
    assert vector_store.deleted == [
        ("knowledge_base", ["doc-1:0", "doc-1:1"])
    ]
    assert service.delete("doc-1") is False


def test_catalog_never_deletes_file_outside_uploads_directory(tmp_path: Path) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    outside = tmp_path / "do-not-delete.md"
    outside.write_text("keep", encoding="utf-8")
    registry = FakeRegistry()
    vector_store = FakeVectorStore()
    service = DocumentCatalogService(
        registry=registry,
        vector_store=vector_store,
        uploads_dir=uploads_dir,
    )
    service.register(make_result(outside))

    assert service.delete("doc-1") is True
    assert outside.exists()
    assert registry.get("doc-1") is None
