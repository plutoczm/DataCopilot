import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.application.agent.graph import AgentGraph
from backend.app.application.agent.models import AgentRequest
from backend.app.presentation.api.dependencies.providers import get_agent_graph
from backend.app.presentation.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
)


router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Unified DataPilot-AI agent chat",
    description="Classify user intent and invoke the appropriate DataPilot-AI workflow.",
)
async def agent_chat(
    request: AgentChatRequest,
    agent_graph: AgentGraph = Depends(get_agent_graph),
) -> AgentChatResponse:
    response = await agent_graph.run(AgentRequest(**request.model_dump()))
    return AgentChatResponse(**response.model_dump())


@router.post(
    "/chat/stream",
    summary="Streaming DataPilot-AI agent chat",
    description="Return Server Sent Events for the unified DataPilot-AI agent workflow.",
)
async def agent_chat_stream(
    request: AgentChatRequest,
    agent_graph: AgentGraph = Depends(get_agent_graph),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for event in agent_graph.stream(AgentRequest(**request.model_dump())):
            yield _sse(event["event"], event["data"])

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
