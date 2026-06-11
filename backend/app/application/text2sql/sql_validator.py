import re

from backend.app.application.text2sql.models import (
    DatabaseSchema,
    SQLEngine,
    SQLValidationIssue,
    SQLValidationResult,
)


TABLE_REFERENCE_PATTERN = re.compile(
    r"\b(?:from|join)\s+(`?[a-zA-Z_][\w]*`?(?:\.`?[a-zA-Z_][\w]*`?)?)"
    r"(?:\s+(?:as\s+)?([a-zA-Z_][\w]*))?",
    re.IGNORECASE,
)

QUALIFIED_COLUMN_PATTERN = re.compile(
    r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b",
    re.IGNORECASE,
)


class SQLValidator:
    def validate(
        self,
        sql: str,
        *,
        schema: DatabaseSchema,
        engine: SQLEngine,
    ) -> SQLValidationResult:
        issues: list[SQLValidationIssue] = []
        normalized_sql = self._normalize_sql(sql)

        if not self._has_valid_structure(normalized_sql):
            issues.append(
                SQLValidationIssue(
                    code="invalid_sql_structure",
                    severity="error",
                    message="SQL must be a SELECT query for Text2SQL generation.",
                )
            )

        issues.extend(self._detect_dangerous_dml(normalized_sql))
        table_aliases, table_issues = self._extract_table_aliases(sql, schema)
        issues.extend(table_issues)
        issues.extend(self._detect_unknown_columns(sql, schema, table_aliases))
        issues.extend(self._detect_select_star(normalized_sql))
        issues.extend(self._detect_join_issues(normalized_sql))
        issues.extend(self._detect_engine_warnings(normalized_sql, engine))

        is_valid = not any(issue.severity == "error" for issue in issues)
        return SQLValidationResult(is_valid=is_valid, issues=issues)

    def _normalize_sql(self, sql: str) -> str:
        return re.sub(r"\s+", " ", sql.strip()).lower()

    def _has_valid_structure(self, normalized_sql: str) -> bool:
        if not normalized_sql:
            return False
        return normalized_sql.startswith("select") or normalized_sql.startswith("with")

    def _detect_dangerous_dml(self, normalized_sql: str) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        if re.search(r"\bdelete\s+from\b", normalized_sql):
            issues.append(
                SQLValidationIssue(
                    code="dangerous_delete",
                    severity="error",
                    message="DELETE statements are not allowed.",
                )
            )
        if re.search(r"\bupdate\s+[a-zA-Z_][\w.]*\b", normalized_sql):
            issues.append(
                SQLValidationIssue(
                    code="dangerous_update",
                    severity="error",
                    message="UPDATE statements are not allowed.",
                )
            )
        return issues

    def _extract_table_aliases(
        self,
        sql: str,
        schema: DatabaseSchema,
    ) -> tuple[dict[str, str], list[SQLValidationIssue]]:
        aliases: dict[str, str] = {}
        issues: list[SQLValidationIssue] = []
        for match in TABLE_REFERENCE_PATTERN.finditer(sql):
            raw_table = self._clean_identifier(match.group(1))
            alias = match.group(2)
            table_key = raw_table.lower()
            short_name = table_key.split(".")[-1]
            if table_key not in schema.table_names and short_name not in schema.table_names:
                issues.append(
                    SQLValidationIssue(
                        code="unknown_table",
                        severity="error",
                        message=f"Unknown table '{raw_table}'.",
                        object_name=raw_table,
                    )
                )
                continue
            aliases[short_name] = short_name
            if alias and alias.lower() not in {"where", "on", "group", "order", "limit", "join"}:
                aliases[alias.lower()] = short_name
        return aliases, issues

    def _detect_unknown_columns(
        self,
        sql: str,
        schema: DatabaseSchema,
        table_aliases: dict[str, str],
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        for alias, column in QUALIFIED_COLUMN_PATTERN.findall(sql):
            normalized_alias = alias.lower()
            if normalized_alias not in table_aliases:
                continue
            table_name = table_aliases[normalized_alias]
            try:
                table = schema.require_table(table_name)
            except KeyError:
                continue
            if column.lower() not in table.column_names:
                issues.append(
                    SQLValidationIssue(
                        code="unknown_column",
                        severity="error",
                        message=f"Unknown column '{alias}.{column}'.",
                        object_name=f"{alias}.{column}",
                    )
                )
        return issues

    def _detect_select_star(self, normalized_sql: str) -> list[SQLValidationIssue]:
        if re.search(r"\bselect\s+\*", normalized_sql) or re.search(r"\b[a-zA-Z_][\w]*\.\*", normalized_sql):
            return [
                SQLValidationIssue(
                    code="select_star",
                    severity="warning",
                    message="Avoid SELECT * in production analytical SQL.",
                )
            ]
        return []

    def _detect_join_issues(self, normalized_sql: str) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        join_count = len(re.findall(r"\bjoin\b", normalized_sql))
        if join_count == 0:
            from_clause = self._extract_from_clause(normalized_sql)
            if self._has_top_level_comma(from_clause):
                issues.append(
                    SQLValidationIssue(
                        code="cartesian_join",
                        severity="error",
                        message="Comma-separated table joins can create Cartesian joins.",
                    )
                )
            return issues

        on_count = len(re.findall(r"\bon\b", normalized_sql))
        using_count = len(re.findall(r"\busing\s*\(", normalized_sql))
        if on_count + using_count < join_count:
            issues.append(
                SQLValidationIssue(
                    code="missing_join_condition",
                    severity="error",
                    message="Every JOIN must include an ON or USING condition.",
                )
            )
        if re.search(r"\bcross\s+join\b", normalized_sql):
            issues.append(
                SQLValidationIssue(
                    code="cartesian_join",
                    severity="warning",
                    message="CROSS JOIN may create a Cartesian product.",
                )
            )
        return issues

    def _extract_from_clause(self, normalized_sql: str) -> str:
        match = re.search(
            r"\bfrom\b(?P<from_clause>.*?)(?:\bwhere\b|\bgroup\s+by\b|\border\s+by\b|\bhaving\b|\blimit\b|$)",
            normalized_sql,
        )
        if match is None:
            return ""
        return match.group("from_clause")

    def _has_top_level_comma(self, clause: str) -> bool:
        depth = 0
        quote: str | None = None
        for char in clause:
            if char in {"'", '"'}:
                quote = None if quote == char else char
            elif quote is None:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth = max(0, depth - 1)
                elif char == "," and depth == 0:
                    return True
        return False

    def _detect_engine_warnings(
        self,
        normalized_sql: str,
        engine: SQLEngine,
    ) -> list[SQLValidationIssue]:
        issues: list[SQLValidationIssue] = []
        if engine in {SQLEngine.HIVE, SQLEngine.SPARK_SQL} and " where " not in f" {normalized_sql} ":
            issues.append(
                SQLValidationIssue(
                    code="missing_partition_filter",
                    severity="warning",
                    message="Consider partition pruning with a WHERE filter for large tables.",
                )
            )
        if engine is SQLEngine.CLICKHOUSE and "prewhere" not in normalized_sql and " where " in f" {normalized_sql} ":
            issues.append(
                SQLValidationIssue(
                    code="clickhouse_prewhere_candidate",
                    severity="warning",
                    message="Consider PREWHERE for highly selective ClickHouse filters.",
                )
            )
        return issues

    def _clean_identifier(self, value: str) -> str:
        return value.replace("`", "")
