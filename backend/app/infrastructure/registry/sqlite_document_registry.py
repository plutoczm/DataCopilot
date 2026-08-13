import sqlite3
from pathlib import Path

from backend.app.application.rag.models import IngestionResult


class SQLiteDocumentRegistry:
    """Persist knowledge-document metadata independently from the vector store.

    ChromaDB persists chunks and vectors, while this registry persists the metadata needed
    by document list/delete APIs across application restarts. A connection is opened per
    operation so the adapter is safe to reuse across FastAPI worker threads.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def add(self, result: IngestionResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    document_id,
                    filename,
                    file_type,
                    domain,
                    stored_path,
                    collection_name,
                    chunk_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    filename = excluded.filename,
                    file_type = excluded.file_type,
                    domain = excluded.domain,
                    stored_path = excluded.stored_path,
                    collection_name = excluded.collection_name,
                    chunk_count = excluded.chunk_count
                """,
                (
                    result.document_id,
                    result.filename,
                    result.file_type,
                    result.domain,
                    str(result.stored_path),
                    result.collection_name,
                    result.chunk_count,
                ),
            )

    def list(self) -> list[IngestionResult]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, filename, file_type, domain, stored_path,
                       collection_name, chunk_count
                FROM documents
                ORDER BY filename, document_id
                """
            ).fetchall()
        return [self._to_result(row) for row in rows]

    def get(self, document_id: str) -> IngestionResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT document_id, filename, file_type, domain, stored_path,
                       collection_name, chunk_count
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
        return self._to_result(row) if row is not None else None

    def delete(self, document_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE document_id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    collection_name TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL CHECK (chunk_count >= 0)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _to_result(self, row: sqlite3.Row) -> IngestionResult:
        return IngestionResult(
            document_id=row["document_id"],
            filename=row["filename"],
            file_type=row["file_type"],
            domain=row["domain"],
            stored_path=Path(row["stored_path"]),
            collection_name=row["collection_name"],
            chunk_count=int(row["chunk_count"]),
        )
