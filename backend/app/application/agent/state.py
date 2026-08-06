from typing import Any, NotRequired, TypedDict

from backend.app.application.agent.models import AgentIntent, AgentRequest
from backend.app.application.rag.models import RAGResponse
from backend.app.application.sql_review.models import SQLReviewResult
from backend.app.application.text2sql.models import Text2SQLResult
from backend.app.application.warehouse_design.models import WarehouseDesignResult
from backend.app.domain.ports.llm_provider import LLMUsage


class AgentState(TypedDict):
    request: AgentRequest
    query: str
    intent: AgentIntent
    confidence: float
    intent_reason: str
    history: list[dict[str, str]]
    routing_path: list[str]
    retrieved_context: NotRequired[RAGResponse]
    generated_sql: NotRequired[Text2SQLResult]
    review_result: NotRequired[SQLReviewResult]
    warehouse_design: NotRequired[WarehouseDesignResult]
    general_answer: NotRequired[str]
    result: dict[str, Any]
    final_response: str
    token_usage: LLMUsage
    tool_usage: dict[str, int]
    errors: list[str]
    validation: NotRequired[dict[str, Any]]
