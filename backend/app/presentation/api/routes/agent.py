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


@router.get("/tools", summary="查看智能体工具及 JSON 输入模型")
def list_agent_tools(
    agent_graph: AgentGraph = Depends(get_agent_graph),
) -> dict[str, list[dict]]:
    return {"tools": agent_graph.tool_catalog()}


@router.delete("/sessions/{session_id}", summary="清除会话记忆")
def clear_agent_session(
    session_id: str,
    agent_graph: AgentGraph = Depends(get_agent_graph),
) -> dict[str, str | bool]:
    return {"session_id": session_id, "cleared": agent_graph.clear_memory(session_id)}


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="DataPilot-AI 统一智能体对话",
    description="识别用户意图并调用对应的 DataPilot-AI 工作流。",
)
async def agent_chat(
    request: AgentChatRequest,
    agent_graph: AgentGraph = Depends(get_agent_graph),
) -> AgentChatResponse:
    response = await agent_graph.run(AgentRequest(**request.model_dump()))
    return AgentChatResponse(**response.model_dump())


@router.post(
    "/chat/stream",
    summary="DataPilot-AI 智能体流式对话",
    description="以服务器发送事件返回统一智能体工作流结果。",
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
