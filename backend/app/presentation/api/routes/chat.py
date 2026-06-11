import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.app.application.rag.rag_service import RAGService
from backend.app.presentation.api.dependencies.providers import get_rag_service
from backend.app.presentation.api.schemas.knowledge import ChatStreamRequest


router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post(
    "/stream",
    summary="Streaming RAG chat",
    description="Return Server Sent Events with answer token output and citations.",
)
async def stream_chat(
    request: ChatStreamRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        response = await rag_service.answer(
            request.message,
            collection_name=request.collection_name,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter,
            score_threshold=request.score_threshold,
        )
        yield _sse("token", {"text": response.answer})
        yield _sse(
            "citations",
            {
                "citations": [
                    citation.model_dump(mode="json")
                    for citation in response.citations
                ]
            },
        )
        yield _sse("done", {"metadata": response.metadata})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
