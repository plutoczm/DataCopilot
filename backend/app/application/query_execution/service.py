import hashlib
import logging
from uuid import uuid4

from backend.app.application.query_execution.exceptions import (
    DataSourceNotFoundError,
    QueryExecutionDisabledError,
    QueryExecutionError,
    QueryRejectedError,
    SchemaDriftError,
)
from backend.app.application.query_execution.models import (
    DataSourceInfo,
    QueryExecutionResult,
)
from backend.app.application.query_execution.policy import ReadOnlySQLPolicy
from backend.app.domain.ports.query_executor import QueryExecutor
from backend.app.domain.ports.schema_catalog import (
    DataSourceSchemaSnapshot,
    SchemaCatalog,
)


class QueryExecutionService:
    def __init__(
        self,
        *,
        executors: dict[str, QueryExecutor],
        enabled: bool,
        max_rows: int,
        timeout_ms: int,
        schema_catalogs: dict[str, SchemaCatalog] | None = None,
        policy: ReadOnlySQLPolicy | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.executors = executors
        self.schema_catalogs = schema_catalogs or {}
        self.enabled = enabled
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms
        self.policy = policy or ReadOnlySQLPolicy()
        self.logger = logger or logging.getLogger("datacopilot.query_audit")

    def list_datasources(self) -> list[DataSourceInfo]:
        return [
            DataSourceInfo(
                name=name,
                kind=executor.kind,
                available=executor.available(),
                description="Configured read-only datasource",
            )
            for name, executor in sorted(self.executors.items())
        ]

    def get_schema(self, datasource: str) -> DataSourceSchemaSnapshot:
        """Return schema metadata without enabling arbitrary SQL execution."""

        catalog = self.schema_catalogs.get(datasource)
        if catalog is None:
            raise DataSourceNotFoundError(f"Unknown datasource '{datasource}'.")
        return catalog.load_schema()

    def execute(
        self,
        *,
        datasource: str,
        sql: str,
        max_rows: int | None = None,
        actor: str = "anonymous",
        expected_schema_fingerprint: str | None = None,
    ) -> QueryExecutionResult:
        query_id = str(uuid4())
        sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        requested_rows = max_rows or self.max_rows
        effective_rows = min(requested_rows, self.max_rows)

        if not self.enabled:
            self._audit(
                query_id=query_id,
                datasource=datasource,
                sql_hash=sql_hash,
                actor=actor,
                status="disabled",
            )
            raise QueryExecutionDisabledError("Read-only query execution is disabled.")

        executor = self.executors.get(datasource)
        if executor is None:
            self._audit(
                query_id=query_id,
                datasource=datasource,
                sql_hash=sql_hash,
                actor=actor,
                status="datasource_not_found",
            )
            raise DataSourceNotFoundError(f"Unknown datasource '{datasource}'.")

        if expected_schema_fingerprint:
            current_snapshot = self.get_schema(datasource)
            expected = expected_schema_fingerprint.lower()
            current = current_snapshot.fingerprint.lower()
            if current != expected:
                self._audit(
                    query_id=query_id,
                    datasource=datasource,
                    sql_hash=sql_hash,
                    actor=actor,
                    status="schema_drift",
                    expected_schema_fingerprint=expected,
                    current_schema_fingerprint=current,
                )
                raise SchemaDriftError(
                    "Datasource schema changed after SQL generation. "
                    "Regenerate and review the query before executing it."
                )

        policy_result = self.policy.validate(sql)
        if not policy_result.allowed:
            violation_codes = [item.code for item in policy_result.violations]
            self._audit(
                query_id=query_id,
                datasource=datasource,
                sql_hash=sql_hash,
                actor=actor,
                status="rejected",
                violations=violation_codes,
            )
            raise QueryRejectedError(
                "SQL rejected by read-only policy: " + ", ".join(violation_codes)
            )

        try:
            page = executor.execute(
                sql,
                max_rows=effective_rows,
                timeout_ms=self.timeout_ms,
            )
        except QueryExecutionError:
            self._audit(
                query_id=query_id,
                datasource=datasource,
                sql_hash=sql_hash,
                actor=actor,
                status="failed",
            )
            raise

        result = QueryExecutionResult(
            query_id=query_id,
            datasource=datasource,
            columns=list(page.columns),
            rows=list(page.rows),
            row_count=len(page.rows),
            truncated=page.truncated,
            elapsed_ms=page.elapsed_ms,
        )
        self._audit(
            query_id=query_id,
            datasource=datasource,
            sql_hash=sql_hash,
            actor=actor,
            status="success",
            row_count=result.row_count,
            truncated=result.truncated,
            elapsed_ms=result.elapsed_ms,
            schema_fingerprint=expected_schema_fingerprint,
        )
        return result

    def _audit(
        self,
        *,
        query_id: str,
        datasource: str,
        sql_hash: str,
        actor: str,
        status: str,
        **extra,
    ) -> None:
        self.logger.info(
            "Read-only query execution",
            extra={
                "event_type": "query_execution",
                "query_id": query_id,
                "actor": actor,
                "datasource": datasource,
                "sql_sha256": sql_hash,
                "status": status,
                **extra,
            },
        )
