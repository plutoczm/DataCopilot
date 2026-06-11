import time
from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import END, StateGraph

from backend.app.application.agent.exceptions import AgentExecutionError
from backend.app.application.agent.models import (
    AgentIntent,
    AgentRequest,
    AgentResponse,
)
from backend.app.application.agent.nodes import AgentNodes
from backend.app.application.agent.router import IntentRouter
from backend.app.application.agent.state import AgentState
from backend.app.application.rag.rag_service import RAGService
from backend.app.application.sql_review.sql_review_service import SQLReviewService
from backend.app.application.text2sql.text2sql_service import Text2SQLService
from backend.app.application.warehouse_design.design_service import WarehouseDesignService
from backend.app.core.logger import get_logger
from backend.app.domain.ports.llm_provider import LLMProvider, LLMUsage


class AgentGraph:
    def __init__(
        self,
        *,
        rag_service: RAGService,
        text2sql_service: Text2SQLService,
        sql_review_service: SQLReviewService,
        warehouse_design_service: WarehouseDesignService,
        llm_provider: LLMProvider,
        intent_router: IntentRouter | None = None,
    ) -> None:
        self.intent_router = intent_router or IntentRouter()
        self.nodes = AgentNodes(
            intent_router=self.intent_router,
            rag_service=rag_service,
            text2sql_service=text2sql_service,
            sql_review_service=sql_review_service,
            warehouse_design_service=warehouse_design_service,
            llm_provider=llm_provider,
        )
        self.logger = get_logger("datacopilot.agent")
        self._graph = self._build_graph()

    async def run(self, request: AgentRequest) -> AgentResponse:
        started_at = time.perf_counter()
        initial_state = self._initial_state(request)
        try:
            state = await self._graph.ainvoke(initial_state)
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
            self.logger.exception(
                "Agent workflow failed",
                extra={
                    "intent": initial_state["intent"].value,
                    "routing_path": initial_state["routing_path"],
                    "execution_time_ms": elapsed_ms,
                    "tool_usage": initial_state["tool_usage"],
                    "errors": [str(exc)],
                },
            )
            raise AgentExecutionError("Agent workflow failed") from exc
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
        response = AgentResponse(
            intent=state["intent"],
            result=state["result"],
            routing_path=state["routing_path"],
            final_response=state["final_response"],
            token_usage=state["token_usage"],
            metadata={
                "intent_confidence": state["confidence"],
                "intent_reason": state["intent_reason"],
                "execution_time_ms": elapsed_ms,
                "tool_usage": state["tool_usage"],
                "errors": state["errors"],
            },
        )
        self.logger.info(
            "Agent workflow completed",
            extra={
                "intent": response.intent.value,
                "routing_path": response.routing_path,
                "execution_time_ms": elapsed_ms,
                "tool_usage": response.metadata["tool_usage"],
                "errors": response.metadata["errors"],
            },
        )
        return response

    async def stream(self, request: AgentRequest) -> AsyncIterator[dict[str, Any]]:
        response = await self.run(request)
        yield {
            "event": "metadata",
            "data": {
                "intent": response.intent.value,
                "routing_path": response.routing_path,
                "metadata": response.metadata,
            },
        }
        yield {"event": "token", "data": {"text": response.final_response}}
        yield {
            "event": "result",
            "data": {
                "intent": response.intent.value,
                "result": response.result,
                "token_usage": response.token_usage.model_dump(mode="json"),
            },
        }
        yield {"event": "done", "data": {"status": "complete"}}

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("classify_intent", self.nodes.classify_intent)
        graph.add_node("rag", self.nodes.rag)
        graph.add_node("text2sql", self.nodes.text2sql)
        graph.add_node("sql_review", self.nodes.sql_review)
        graph.add_node("warehouse_design", self.nodes.warehouse_design)
        graph.add_node("general_chat", self.nodes.general_chat)
        graph.add_node("unknown", self.nodes.unknown)
        graph.add_node("format_response", self.nodes.format_response)

        graph.set_entry_point("classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self._route_from_classification,
            {
                "rag": "rag",
                "text2sql": "text2sql",
                "sql_review": "sql_review",
                "warehouse_design": "warehouse_design",
                "general_chat": "general_chat",
                "unknown": "unknown",
            },
        )
        graph.add_conditional_edges(
            "text2sql",
            self._route_after_text2sql,
            {
                "sql_review": "sql_review",
                "format_response": "format_response",
            },
        )
        for node_name in ("rag", "sql_review", "warehouse_design", "general_chat", "unknown"):
            graph.add_edge(node_name, "format_response")
        graph.add_edge("format_response", END)
        return graph.compile()

    def _route_from_classification(self, state: AgentState) -> str:
        return self.intent_router.route_key(state["intent"])

    def _route_after_text2sql(self, state: AgentState) -> str:
        return self.intent_router.route_after_text2sql(state["intent"])

    def _initial_state(self, request: AgentRequest) -> AgentState:
        return {
            "request": request,
            "query": request.message,
            "intent": AgentIntent.UNKNOWN,
            "confidence": 0.0,
            "intent_reason": "",
            "history": request.history,
            "routing_path": [],
            "result": {},
            "final_response": "",
            "token_usage": LLMUsage(),
            "tool_usage": {},
            "errors": [],
        }
