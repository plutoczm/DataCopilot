import hashlib
import sqlite3
import time
from pathlib import Path

from backend.app.application.query_execution.exceptions import (
    DataSourceUnavailableError,
    QueryExecutionError,
    QueryTimeoutError,
)
from backend.app.domain.ports.query_executor import QueryPage
from backend.app.domain.ports.schema_catalog import DataSourceSchemaSnapshot


class SQLiteReadOnlyExecutor:
    def __init__(self, *, name: str, database_path: Path) -> None:
        self._name = name
        self.database_path = Path(database_path).resolve()

    @property
    def name(self) -> str:
        return self._name

    @property
    def kind(self) -> str:
        return "sqlite"

    def available(self) -> bool:
        return self.database_path.is_file()

    def load_schema(self) -> DataSourceSchemaSnapshot:
        """Return a deterministic, non-secret schema snapshot for Text2SQL.

        Schema introspection is intentionally separate from arbitrary query execution: it
        remains available when the execution feature flag is off, so users can generate
        and review SQL without granting the application permission to execute model output.
        """

        if not self.available():
            raise DataSourceUnavailableError(
                f"Datasource '{self.name}' is unavailable. Initialize the demo database first."
            )

        try:
            connection = sqlite3.connect(self._read_only_uri(), uri=True)
            try:
                rows = connection.execute(
                    """
                    SELECT name, sql
                    FROM sqlite_schema
                    WHERE type = 'table'
                      AND name NOT LIKE 'sqlite_%'
                      AND sql IS NOT NULL
                    ORDER BY name
                    """
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.DatabaseError as exc:
            raise QueryExecutionError(
                f"SQLite schema introspection failed: {exc}"
            ) from exc

        statements = [str(row[1]).strip().rstrip(";") + ";" for row in rows]
        schema_context = "\n\n".join(statements)
        fingerprint = hashlib.sha256(schema_context.encode("utf-8")).hexdigest()
        return DataSourceSchemaSnapshot(
            datasource=self.name,
            engine=self.kind,
            schema_context=schema_context,
            table_count=len(statements),
            fingerprint=fingerprint,
        )

    def execute(
        self,
        sql: str,
        *,
        max_rows: int,
        timeout_ms: int,
    ) -> QueryPage:
        if not self.available():
            raise DataSourceUnavailableError(
                f"Datasource '{self.name}' is unavailable. Initialize the demo database first."
            )

        started_at = time.perf_counter()
        deadline = started_at + (timeout_ms / 1000.0)

        try:
            connection = sqlite3.connect(
                self._read_only_uri(),
                uri=True,
                timeout=max(0.1, timeout_ms / 1000.0),
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            connection.set_progress_handler(
                lambda: 1 if time.perf_counter() > deadline else 0,
                1000,
            )
            try:
                cursor = connection.execute(sql)
                columns = tuple(
                    description[0] for description in (cursor.description or ())
                )
                fetched = cursor.fetchmany(max_rows + 1)
            finally:
                connection.close()
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise QueryTimeoutError(
                    f"Query exceeded the {timeout_ms} ms execution timeout."
                ) from exc
            raise QueryExecutionError(f"SQLite query failed: {exc}") from exc
        except sqlite3.DatabaseError as exc:
            raise QueryExecutionError(f"SQLite query failed: {exc}") from exc

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
        truncated = len(fetched) > max_rows
        rows = fetched[:max_rows]
        return QueryPage(
            columns=columns,
            rows=tuple(dict(row) for row in rows),
            truncated=truncated,
            elapsed_ms=elapsed_ms,
        )

    def _read_only_uri(self) -> str:
        return f"{self.database_path.as_uri()}?mode=ro"
