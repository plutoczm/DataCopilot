from pathlib import Path

from backend.app.application.rag.models import IngestionResult
from backend.app.infrastructure.registry import SQLiteDocumentRegistry


def make_result(
    *,
    document_id: str = "doc-1",
    filename: str = "metrics.md",
    chunk_count: int = 3,
) -> IngestionResult:
    return IngestionResult(
        document_id=document_id,
        filename=filename,
        file_type="md",
        domain="retail",
        stored_path=Path("data/uploads/metrics.md"),
        collection_name="knowledge_base",
        chunk_count=chunk_count,
    )


def test_sqlite_document_registry_persists_across_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata" / "knowledge_registry.db"
    first = SQLiteDocumentRegistry(database_path)
    first.add(make_result())

    restarted = SQLiteDocumentRegistry(database_path)
    loaded = restarted.get("doc-1")

    assert loaded is not None
    assert loaded.filename == "metrics.md"
    assert loaded.chunk_count == 3
    assert restarted.list() == [loaded]


def test_sqlite_document_registry_upserts_and_deletes(tmp_path: Path) -> None:
    database_path = tmp_path / "registry.db"
    registry = SQLiteDocumentRegistry(database_path)
    registry.add(make_result(chunk_count=2))
    registry.add(make_result(filename="metrics-v2.md", chunk_count=5))

    loaded = registry.get("doc-1")
    assert loaded is not None
    assert loaded.filename == "metrics-v2.md"
    assert loaded.chunk_count == 5

    assert registry.delete("doc-1") is True
    assert registry.get("doc-1") is None
    assert registry.delete("doc-1") is False
