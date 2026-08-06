import re

from backend.app.application.agent.models import AgentIntent, IntentClassification


class IntentRouter:
    """基于规则的意图路由器，为生产降级提供确定性行为。"""

    SQL_REVIEW_PATTERNS = (
        "检查sql",
        "检查这段sql",
        "review sql",
        "sql review",
        "优化sql",
        "sql优化",
        "explain plan",
    )
    TEXT2SQL_PATTERNS = (
        "统计",
        "查询",
        "生成sql",
        "写sql",
        "最近",
        "top",
        "select",
        "count",
        "sum",
        "活跃用户",
        "gmv",
    )
    WAREHOUSE_PATTERNS = (
        "数仓",
        "数据仓库",
        "warehouse",
        "ods",
        "dwd",
        "dws",
        "ads",
        "维度表",
        "事实表",
    )
    GENERAL_PATTERNS = (
        "介绍一下你",
        "你是谁",
        "你能做什么",
        "hello",
        "hi",
        "你好",
        "help",
    )
    RAG_PATTERNS = (
        "什么是",
        "解释",
        "介绍",
        "原理",
        "怎么",
        "如何",
        "spark",
        "hive",
        "flink",
        "kafka",
        "aqe",
        "data engineering",
    )

    def classify(self, query: str) -> IntentClassification:
        normalized = self._normalize(query)
        has_sql_review = self._contains_any(normalized, self.SQL_REVIEW_PATTERNS)
        has_text2sql = self._contains_any(normalized, self.TEXT2SQL_PATTERNS)
        has_warehouse = self._contains_any(normalized, self.WAREHOUSE_PATTERNS)
        has_general = self._contains_any(normalized, self.GENERAL_PATTERNS)
        has_rag = self._contains_any(normalized, self.RAG_PATTERNS)
        contains_sql = self._contains_sql(normalized)

        if has_text2sql and has_sql_review and not contains_sql:
            return IntentClassification(
                intent=AgentIntent.TEXT2SQL_SQL_REVIEW,
                confidence=0.95,
                reason="Request asks to generate SQL and review it.",
                requires_sql_review=True,
            )
        if has_sql_review or contains_sql:
            return IntentClassification(
                intent=AgentIntent.SQL_REVIEW,
                confidence=0.9,
                reason="Request asks for SQL review or includes SQL text.",
            )
        if has_warehouse:
            return IntentClassification(
                intent=AgentIntent.WAREHOUSE_DESIGN,
                confidence=0.94,
                reason="Request contains warehouse design terminology.",
            )
        if has_text2sql:
            return IntentClassification(
                intent=AgentIntent.TEXT2SQL,
                confidence=0.88,
                reason="Request asks for a data query or metric calculation.",
            )
        if has_general:
            return IntentClassification(
                intent=AgentIntent.GENERAL_CHAT,
                confidence=0.84,
                reason="Request is a general assistant introduction or greeting.",
            )
        if has_rag:
            return IntentClassification(
                intent=AgentIntent.RAG,
                confidence=0.8,
                reason="Request asks for a technical explanation.",
            )
        return IntentClassification(
            intent=AgentIntent.UNKNOWN,
            confidence=0.35,
            reason="No supported DataPilot-AI workflow matched confidently.",
        )

    def route_key(self, intent: AgentIntent) -> str:
        return {
            AgentIntent.RAG: "rag",
            AgentIntent.TEXT2SQL: "text2sql",
            AgentIntent.SQL_REVIEW: "sql_review",
            AgentIntent.TEXT2SQL_SQL_REVIEW: "text2sql",
            AgentIntent.WAREHOUSE_DESIGN: "warehouse_design",
            AgentIntent.GENERAL_CHAT: "general_chat",
            AgentIntent.UNKNOWN: "unknown",
        }[intent]

    def route_after_text2sql(self, intent: AgentIntent) -> str:
        if intent is AgentIntent.TEXT2SQL_SQL_REVIEW:
            return "sql_review"
        return "validate_result"

    def _normalize(self, query: str) -> str:
        return re.sub(r"\s+", " ", query.strip().lower())

    def _contains_any(self, query: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in query for pattern in patterns)

    def _contains_sql(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(select|insert|update|delete|merge|create|with|from|join|where|group by)\b",
                query,
            )
        )
