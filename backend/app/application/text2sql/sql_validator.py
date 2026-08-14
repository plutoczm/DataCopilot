from __future__ import annotations

from collections.abc import Iterable

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from backend.app.application.text2sql.models import (
    DatabaseSchema,
    SQLEngine,
    SQLValidationIssue,
    SQLValidationResult,
)


DIALECT_BY_ENGINE: dict[SQLEngine, str] = {
    SQLEngine.SQLITE: "sqlite",
    SQLEngine.MYSQL: "mysql",
    SQLEngine.HIVE: "hive",
    SQLEngine.SPARK_SQL: "spark",
    SQLEngine.CLICKHOUSE: "clickhouse",
}

DANGEROUS_NODE_CODES: dict[str, str] = {
    "delete": "dangerous_delete",
    "update": "dangerous_update",
    "insert": "dangerous_insert",
    "drop": "dangerous_drop",
    "alter": "dangerous_alter",
    "truncate": "dangerous_truncate",
    "create": "dangerous_create",
    "replace": "dangerous_replace",
    "merge": "dangerous_merge",
    "grant": "dangerous_grant",
    "revoke": "dangerous_revoke",
    "command": "dangerous_execute",
}

QUERY_NODE_TYPES = {"select", "union", "intersect", "except"}


class SQLValidator:
    """Validate generated SQL using a dialect-aware AST.

    This is an application guardrail, not a database authorization layer. Production
    execution must still use read-only credentials, statement timeouts, row limits and
    database-native resource controls.
    """

    def validate(
        self,
        sql: str,
        *,
        schema: DatabaseSchema,
        engine: SQLEngine,
    ) -> SQLValidationResult:
        issues: list[SQLValidationIssue] = []
        statements = self._parse(sql, engine=engine, issues=issues)
        if not statements:
            return SQLValidationResult(is_valid=False, issues=issues)

        if len(statements) > 1:
            issues.append(
                SQLValidationIssue(
                    code="multiple_statements",
                    severity="error",
                    message="Only one read-only SQL statement is allowed.",
                )
            )

        for statement in statements:
            issues.extend(self._detect_dangerous_statements(statement))
            if type(statement).__name__.lower() not in QUERY_NODE_TYPES:
                issues.append(
                    SQLValidationIssue(
                        code="invalid_sql_structure",
                        severity="error",
                        message="SQL must be a SELECT/WITH query for Text2SQL generation.",
                    )
                )

        statement = statements[0]
        if type(statement).__name__.lower() in QUERY_NODE_TYPES:
            aliases, physical_tables, table_issues = self._extract_table_aliases(
                statement,
                schema,
            )
            issues.extend(table_issues)
            issues.extend(
                self._detect_unknown_columns(
                    statement,
                    schema=schema,
                    aliases=aliases,
                    physical_tables=physical_tables,
                )
            )
            issues.extend(self._detect_select_star(statement))
            issues.extend(self._detect_join_issues(statement))
            issues.extend(self._detect_engine_warnings(statement, engine))

        issues = self._deduplicate(issues)
        return SQLValidationResult(
            is_valid=not any(issue.severity == "error" for issue in issues),
            issues=issues,
        )

    def _parse(
        self,
        sql: str,
        *,
        engine: SQLEngine,
        issues: list[SQLValidationIssue],
    ) -> list[exp.Expression]:
        if not sql.strip():
            issues.append(
                SQLValidationIssue(
                    code="invalid_sql_structure",
                    severity="error",
                    message="SQL must not be empty.",
                )
            )
            return []
        try:
            return [
                statement
                for statement in parse(sql, read=DIALECT_BY_ENGINE[engine])
                if statement is not None
            ]
        except ParseError as exc:
            issues.append(
                SQLValidationIssue(
                    code="invalid_sql_structure",
                    severity="error",
                    message=f"SQL could not be parsed for {engine.value}: {exc}",
                )
            )
            return []

    def _detect_dangerous_statements(
        self,
        statement: exp.Expression,
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        seen: set[str] = set()
        for node in statement.walk():
            node_name = type(node).__name__.lower()
            code = DANGEROUS_NODE_CODES.get(node_name)
            if not code or code in seen:
                continue
            seen.add(code)
            issues.append(
                SQLValidationIssue(
                    code=code,
                    severity="error",
                    message=f"{node_name.upper()} statements are not allowed.",
                )
            )
        return issues

    def _extract_table_aliases(
        self,
        statement: exp.Expression,
        schema: DatabaseSchema,
    ) -> tuple[dict[str, str | None], list[str], list[SQLValidationIssue]]:
        cte_names = {
            cte.alias_or_name.lower()
            for cte in statement.find_all(exp.CTE)
            if cte.alias_or_name
        }
        aliases: dict[str, str | None] = {name: None for name in cte_names}
        physical_tables: list[str] = []
        issues: list[SQLValidationIssue] = []

        for table in statement.find_all(exp.Table):
            short_name = table.name.lower()
            if short_name in cte_names:
                aliases[table.alias_or_name.lower()] = None
                continue

            database = str(table.db or "").lower()
            full_name = f"{database}.{short_name}" if database else short_name
            if (
                full_name not in schema.table_names
                and short_name not in schema.table_names
            ):
                issues.append(
                    SQLValidationIssue(
                        code="unknown_table",
                        severity="error",
                        message=f"Unknown table '{full_name}'.",
                        object_name=full_name,
                    )
                )
                continue

            resolved = full_name if full_name in schema.table_names else short_name
            physical_tables.append(resolved)
            aliases[short_name] = resolved
            alias = table.alias_or_name
            if alias:
                aliases[alias.lower()] = resolved

        return aliases, physical_tables, issues

    def _detect_unknown_columns(
        self,
        statement: exp.Expression,
        *,
        schema: DatabaseSchema,
        aliases: dict[str, str | None],
        physical_tables: list[str],
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        projection_aliases = {
            expression.alias.lower()
            for select in statement.find_all(exp.Select)
            for expression in select.expressions
            if expression.alias
        }

        for column in statement.find_all(exp.Column):
            if isinstance(column.this, exp.Star):
                continue

            column_name = column.name.lower()
            qualifier = column.table.lower() if column.table else ""
            if not qualifier and column_name in projection_aliases:
                continue

            if qualifier:
                resolved_table = aliases.get(qualifier)
                if resolved_table is None:
                    # CTE/derived-table columns are validated by their inner query.
                    continue
                if not self._table_has_column(schema, resolved_table, column_name):
                    issues.append(
                        SQLValidationIssue(
                            code="unknown_column",
                            severity="error",
                            message=f"Unknown column '{qualifier}.{column.name}'.",
                            object_name=f"{qualifier}.{column.name}",
                        )
                    )
                continue

            candidate_tables = [
                table_name
                for table_name in physical_tables
                if self._table_has_column(schema, table_name, column_name)
            ]
            if physical_tables and not candidate_tables:
                issues.append(
                    SQLValidationIssue(
                        code="unknown_column",
                        severity="error",
                        message=f"Unknown column '{column.name}'.",
                        object_name=column.name,
                    )
                )

        return issues

    def _table_has_column(
        self,
        schema: DatabaseSchema,
        table_name: str,
        column_name: str,
    ) -> bool:
        try:
            table = schema.require_table(table_name)
        except KeyError:
            return False
        return column_name.lower() in table.column_names

    def _detect_select_star(
        self,
        statement: exp.Expression,
    ) -> list[SQLValidationIssue]:
        for star in statement.find_all(exp.Star):
            parent_name = type(star.parent).__name__.lower() if star.parent else ""
            if parent_name == "count":
                continue
            return [
                SQLValidationIssue(
                    code="select_star",
                    severity="warning",
                    message="Avoid SELECT * in production analytical SQL.",
                )
            ]
        return []

    def _detect_join_issues(
        self,
        statement: exp.Expression,
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        for join in statement.find_all(exp.Join):
            kind = str(join.args.get("kind") or "").upper()
            has_condition = join.args.get("on") is not None or bool(join.args.get("using"))
            if kind == "CROSS":
                issues.append(
                    SQLValidationIssue(
                        code="cartesian_join",
                        severity="warning",
                        message="CROSS JOIN may create a Cartesian product.",
                    )
                )
            if not has_condition:
                issues.append(
                    SQLValidationIssue(
                        code="missing_join_condition",
                        severity="error",
                        message="Every JOIN must include an ON or USING condition.",
                    )
                )
        return issues

    def _detect_engine_warnings(
        self,
        statement: exp.Expression,
        engine: SQLEngine,
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        has_where = any(True for _ in statement.find_all(exp.Where))

        if engine in {SQLEngine.HIVE, SQLEngine.SPARK_SQL} and not has_where:
            issues.append(
                SQLValidationIssue(
                    code="missing_partition_filter",
                    severity="warning",
                    message="Consider partition pruning with a WHERE filter for large tables.",
                )
            )

        if engine is SQLEngine.CLICKHOUSE and has_where:
            rendered = statement.sql(dialect=DIALECT_BY_ENGINE[engine]).lower()
            if "prewhere" not in rendered:
                issues.append(
                    SQLValidationIssue(
                        code="clickhouse_prewhere_candidate",
                        severity="warning",
                        message="Consider PREWHERE for highly selective ClickHouse filters.",
                    )
                )
        return issues

    def _deduplicate(
        self,
        issues: Iterable[SQLValidationIssue],
    ) -> list[SQLValidationIssue]:
        result: list[SQLValidationIssue] = []
        seen: set[tuple[str, str | None]] = set()
        for issue in issues:
            key = (issue.code, issue.object_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(issue)
        return result
