from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str


class LLMUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str
    finish_reason: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    raw_response_id: str | None = None


class LLMStreamChunk(BaseModel):
    provider: str
    model: str
    content: str
    finish_reason: str | None = None
    usage: LLMUsage | None = None


class LLMHealthStatus(BaseModel):
    provider: str
    ok: bool
    api_key_configured: bool
    reachable: bool
    model_available: bool
    model: str | None = None
    message: str
    latency_ms: float | None = None


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError

    async def stream_chat(
        self,
        messages: Sequence[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        raise NotImplementedError

    async def health_check(self) -> LLMHealthStatus:
        raise NotImplementedError

    def token_count(self, text_or_messages: str | Sequence[LLMMessage]) -> int:
        raise NotImplementedError

    def provider_name(self) -> str:
        raise NotImplementedError
