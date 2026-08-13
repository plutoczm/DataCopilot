import re

from pydantic import BaseModel, Field


PROHIBITED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "replace",
    "merge",
    "grant",
    "revoke",
    "call",
    "execute",
    "attach",
    "detach",
    "vacuum",
    "reindex",
    "analyze",
    "pragma",
}

PROHIBITED_FUNCTION_PATTERN = re.compile(
    r"\b(?:load_extension|writefile)\s*\(",
    re.IGNORECASE,
)


class PolicyViolation(BaseModel):
    code: str
    message: str


class ReadOnlyPolicyResult(BaseModel):
    allowed: bool
    violations: list[PolicyViolation] = Field(default_factory=list)


class ReadOnlySQLPolicy:
    """数据库执行边界的确定性只读策略。

    该策略负责拦截明显的写入、DDL、管理语句与多语句输入；数据库侧仍必须使用
    只读连接和最小权限账号，不能把应用层字符串检查当作权限系统。
    """

    def validate(self, sql: str) -> ReadOnlyPolicyResult:
        sanitized = self._strip_literals_and_comments(sql)
        normalized = re.sub(r"\s+", " ", sanitized).strip().lower()
        violations: list[PolicyViolation] = []

        if not normalized:
            violations.append(
                PolicyViolation(code="empty_sql", message="SQL cannot be empty.")
            )
            return ReadOnlyPolicyResult(allowed=False, violations=violations)

        if not (normalized.startswith("select") or normalized.startswith("with")):
            violations.append(
                PolicyViolation(
                    code="read_only_required",
                    message="Only SELECT or WITH queries are allowed.",
                )
            )

        if self._has_multiple_statements(sanitized):
            violations.append(
                PolicyViolation(
                    code="multiple_statements",
                    message="Only one SQL statement is allowed.",
                )
            )

        for keyword in sorted(PROHIBITED_KEYWORDS):
            if re.search(rf"\b{keyword}\b", normalized):
                violations.append(
                    PolicyViolation(
                        code=f"prohibited_{keyword}",
                        message=f"{keyword.upper()} is not allowed in read-only execution.",
                    )
                )

        if PROHIBITED_FUNCTION_PATTERN.search(normalized):
            violations.append(
                PolicyViolation(
                    code="prohibited_function",
                    message="File or extension loading functions are not allowed.",
                )
            )

        return ReadOnlyPolicyResult(
            allowed=not violations,
            violations=violations,
        )

    def _has_multiple_statements(self, sanitized_sql: str) -> bool:
        stripped = sanitized_sql.strip()
        if stripped.endswith(";"):
            stripped = stripped[:-1]
        return ";" in stripped

    def _strip_literals_and_comments(self, sql: str) -> str:
        result: list[str] = []
        index = 0
        length = len(sql)

        while index < length:
            char = sql[index]
            next_char = sql[index + 1] if index + 1 < length else ""

            if char == "-" and next_char == "-":
                index += 2
                while index < length and sql[index] not in "\r\n":
                    index += 1
                result.append(" ")
                continue

            if char == "/" and next_char == "*":
                index += 2
                while index + 1 < length and not (
                    sql[index] == "*" and sql[index + 1] == "/"
                ):
                    index += 1
                index = min(length, index + 2)
                result.append(" ")
                continue

            if char in {"'", '"'}:
                quote = char
                result.append("''")
                index += 1
                while index < length:
                    if sql[index] == quote:
                        if index + 1 < length and sql[index + 1] == quote:
                            index += 2
                            continue
                        index += 1
                        break
                    index += 1
                continue

            result.append(char)
            index += 1

        return "".join(result)
