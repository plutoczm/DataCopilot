from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.app.application.agent.models import AgentIntent
from backend.app.application.text2sql.models import SQLEngine
from backend.app.domain.ports.llm_provider import LLMUsage


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, examples=["统计最近7天活跃用户并检查SQL"])
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    history: list[dict[str, str]] = Field(default_factory=list)
    collection_name: str = "knowledge_base"
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_filter: dict[str, str | int | float | bool] | None = None
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    engine: SQLEngine = SQLEngine.HIVE
    schema_context: str | None = None
    database_name: str | None = None
    use_rag: bool = False
    rag_collection_name: str = "knowledge_base"
    retrieval_mode: str = Field(default="hybrid", pattern="^(vector|hybrid)$")

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: Any) -> Any:
        if isinstance(value, str) and value.lower() == "spark":
            return SQLEngine.SPARK_SQL
        return value


class AgentChatResponse(BaseModel):
    intent: AgentIntent
    result: dict[str, Any]
    routing_path: list[str]
    final_response: str
    metadata: dict[str, Any]
    token_usage: LLMUsage
