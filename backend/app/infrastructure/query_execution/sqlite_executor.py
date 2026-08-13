import sqlite3
import time
from pathlib import Path

from backend.app.application.query_execution.exceptions import (
    DataSourceUnavailableError,
    QueryExecutionError,
    QueryTimeoutError,
)
from backend.app.domain.ports.query_executor import QueryPage


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
        uri = f"{self.database_path.as_uri()}?mode=ro"

        try:
            connection = sqlite3.connect(
                uri,
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
