import json
import re
from typing import Any

from backend.app.application.rag.rag_service import RAGService
from backend.app.application.text2sql.exceptions import SQLGenerationError
from backend.app.application.text2sql.models import (
    SQLEngine,
    SQLValidationResult,
    Text2SQLResult,
)
from backend.app.application.text2sql.prompt_builder import PromptBuilder
from backend.app.application.text2sql.schema_service import SchemaService
from backend.app.application.text2sql.sql_validator import SQLValidator
from backend.app.domain.ports.llm_provider import LLMProvider
from backend.app.domain.ports.schema_catalog import SchemaCatalog


DEFAULT_OPTIMIZATION_HINTS: dict[SQLEngine, list[str]] = {
    SQLEngine.SQLITE: [
        "Use indexes on join keys and selective filter columns.",
        "Keep result sets bounded with LIMIT for exploratory queries.",
    ],
    SQLEngine.MYSQL: [
        "Use indexes on join keys and high-selectivity filter columns.",
        "Check LIMIT with ORDER BY for top-N queries.",
    ],
    SQLEngine.HIVE: [
        "Use partition pruning for date filters when partition columns exist.",
        "Consider MapJoin suggestions for small dimension tables.",
        "Avoid SELECT * to reduce scan volume.",
    ],
    SQLEngine.SPARK_SQL: [
        "Use partition pruning and filter pushdown for large fact tables.",
        "Consider Broadcast Join suggestions for small dimension tables.",
        "Review AQE settings for skewed joins and shuffle-heavy aggregations.",
    ],
    SQLEngine.CLICKHOUSE: [
        "Consider PREWHERE for highly selective filters.",
        "Align filters with ORDER BY and primary key definitions.",
        "Use aggregation keys that match common query patterns.",
    ],
}


class Text2SQLService:
    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        rag_service: RAGService | None = None,
        schema_catalogs: dict[str, SchemaCatalog] | None = None,
        schema_service: SchemaService | None = None,
        prompt_builder: PromptBuilder | None = None,
        sql_validator: SQLValidator | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.rag_service = rag_service
        self.schema_catalogs = schema_catalogs or {}
        self.schema_service = schema_service or SchemaService()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.sql_validator = sql_validator or SQLValidator()

    async def generate(
        self,
        *,
        question: str,
        engine: SQLEngine | None = None,
        schema_context: str | None = None,
        database_name: str | None = None,
        datasource: str | None = None,
        use_rag: bool = False,
        rag_collection_name: str = "knowledge_base",
    ) -> Text2SQLResult:
        (
            resolved_engine,
            resolved_schema_context,
            schema_metadata,
        ) = self._resolve_schema_source(
            engine=engine,
            schema_context=schema_context,
            datasource=datasource,
        )
        schema = self.schema_service.parse_schema_context(
            resolved_schema_context,
            database_name=database_name,
        )
        rag_context = await self._retrieve_rag_context(
            question,
            use_rag=use_rag,
            collection_name=rag_collection_name,
        )
        messages = self.prompt_builder.build_messages(
            question=question,
            engine=resolved_engine,
            schema=schema,
            rag_context=rag_context,
        )
        llm_response = await self.llm_provider.chat(messages, temperature=0.0)
        payload = self._parse_llm_payload(llm_response.content)
        sql = str(payload.get("sql", "")).strip()
        if not sql:
            raise SQLGenerationError("LLM response did not include SQL")

        validation = self.sql_validator.validate(
            sql,
            schema=schema,
            engine=resolved_engine,
        )
        suggestions = self._merge_optimization_suggestions(
            payload.get("optimization_suggestions"),
            resolved_engine,
        )
        confidence = self._normalize_confidence(payload.get("confidence"), validation)
        metadata: dict[str, str | int | float | bool] = {
            "llm_provider": llm_response.provider,
            "llm_model": llm_response.model,
            "rag_used": use_rag,
            "schema_table_count": len(schema.tables),
            "confidence_source": "deterministic_validation_heuristic",
            **schema_metadata,
        }
        return Text2SQLResult(
            sql=sql,
            explanation=str(payload.get("explanation", "")).strip()
            or "SQL generated from the provided natural language request and schema.",
            optimization_suggestions=suggestions,
            engine=resolved_engine,
            confidence=confidence,
            validation=validation,
            token_usage=llm_response.usage,
            metadata=metadata,
        )

    def _resolve_schema_source(
        self,
        *,
        engine: SQLEngine | None,
        schema_context: str | None,
        datasource: str | None,
    ) -> tuple[SQLEngine, str | None, dict[str, str | int | float | bool]]:
        normalized_datasource = (datasource or "").strip()
        explicit_schema = (schema_context or "").strip()

        if not normalized_datasource:
            return (
                engine or SQLEngine.HIVE,
                schema_context,
                {"schema_source": "request" if explicit_schema else "none"},
            )

        if explicit_schema:
            raise SQLGenerationError(
                "Provide either datasource or schema_context, not both. "
                "Use RAG for business definitions that augment datasource metadata."
            )

        catalog = self.schema_catalogs.get(normalized_datasource)
        if catalog is None:
            raise SQLGenerationError(
                f"Unknown datasource '{normalized_datasource}' for schema discovery."
            )
        if not catalog.available():
            raise SQLGenerationError(
                f"Datasource '{normalized_datasource}' is unavailable for schema discovery."
            )

        snapshot = catalog.load_schema()
        try:
            datasource_engine = SQLEngine(snapshot.engine)
        except ValueError as exc:
            raise SQLGenerationError(
                f"Datasource '{normalized_datasource}' uses unsupported SQL engine "
                f"'{snapshot.engine}'."
            ) from exc

        if engine is not None and engine is not datasource_engine:
            raise SQLGenerationError(
                f"Requested engine '{engine.value}' does not match datasource engine "
                f"'{datasource_engine.value}'."
            )

        return (
            datasource_engine,
            snapshot.schema_context,
            {
                "schema_source": "datasource",
                "datasource": snapshot.datasource,
                "schema_fingerprint": snapshot.fingerprint,
                "schema_table_count_discovered": snapshot.table_count,
            },
        )

    async def _retrieve_rag_context(
        self,
        question: str,
        *,
        use_rag: bool,
        collection_name: str,
    ) -> str | None:
        if not use_rag or self.rag_service is None:
            return None

        retrieve_context = getattr(self.rag_service, "retrieve_context", None)
        if callable(retrieve_context):
            return await retrieve_context(
                question,
                collection_name=collection_name,
                top_k=3,
            )

        # Backward-compatible fallback for test doubles or older RAG implementations.
        response = await self.rag_service.answer(
            question,
            collection_name=collection_name,
            top_k=3,
        )
        if response.retrieved_chunks:
            sections = []
            for chunk in response.retrieved_chunks:
                metadata = chunk.metadata
                sections.append(
                    "\n".join(
                        [
                            f"{metadata.filename}#chunk-{metadata.chunk_index}",
                            chunk.content,
                        ]
                    )
                )
            return "\n\n".join(sections)
        return response.answer

    def _parse_llm_payload(self, content: str) -> dict[str, Any]:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SQLGenerationError("LLM response must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise SQLGenerationError("LLM response JSON must be an object")
        return payload

    def _merge_optimization_suggestions(
        self,
        llm_suggestions: Any,
        engine: SQLEngine,
    ) -> list[str]:
        suggestions: list[str] = []
        if isinstance(llm_suggestions, list):
            suggestions.extend(str(item).strip() for item in llm_suggestions if str(item).strip())
        elif isinstance(llm_suggestions, str) and llm_suggestions.strip():
            suggestions.append(llm_suggestions.strip())

        for hint in DEFAULT_OPTIMIZATION_HINTS[engine]:
            if not any(hint.lower() == existing.lower() for existing in suggestions):
                suggestions.append(hint)
        return suggestions

    def _normalize_confidence(
        self,
        _model_reported_value: Any,
        validation: SQLValidationResult,
    ) -> float:
        """Return a deterministic quality signal instead of trusting model self-reporting."""
        if not validation.is_valid:
            return 0.2
        warning_count = sum(issue.severity == "warning" for issue in validation.issues)
        if warning_count == 0:
            return 0.95
        if warning_count == 1:
            return 0.85
        return 0.75
