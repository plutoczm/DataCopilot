import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BACKEND_URL = "http://backend:8000"
FRONTEND_API_KEY_ENV = "DATACOPILOT_API_KEY"


class BackendClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = 60.0,
        http_client: Any | None = None,
        trust_env: bool = False,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_URL") or DEFAULT_BACKEND_URL).rstrip("/")
        resolved_api_key = (api_key or os.getenv(FRONTEND_API_KEY_ENV) or "").strip()
        headers = {"X-API-Key": resolved_api_key} if resolved_api_key else None
        self._owns_client = http_client is None
        self.client = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            trust_env=trust_env,
            headers=headers,
        )

    def health(self) -> dict[str, Any]:
        return self._json(self.client.get("/health"))

    def list_documents(self) -> dict[str, Any]:
        return self._json(self.client.get("/api/v1/knowledge/documents"))

    def upload_document(
        self,
        *,
        file_name: str,
        file_bytes: bytes,
        collection_name: str = "knowledge_base",
        domain: str = "general",
        tags: str = "",
    ) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/knowledge/documents",
            data={"collection_name": collection_name, "domain": domain, "tags": tags},
            files={"file": (Path(file_name).name, file_bytes)},
        )
        return self._json(response)

    def delete_document(self, document_id: str) -> dict[str, Any]:
        return self._json(self.client.delete(f"/api/v1/knowledge/documents/{document_id}"))

    def query_knowledge(
        self,
        question: str,
        *,
        collection_name: str = "knowledge_base",
        top_k: int = 5,
    ) -> dict[str, Any]:
        return self._json(
            self.client.post(
                "/api/v1/knowledge/query",
                json={
                    "question": question,
                    "collection_name": collection_name,
                    "top_k": top_k,
                },
            )
        )

    def stream_chat(
        self,
        message: str,
        *,
        collection_name: str = "knowledge_base",
        top_k: int = 5,
    ) -> Iterator[dict[str, Any]]:
        with self.client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={
                "message": message,
                "collection_name": collection_name,
                "top_k": top_k,
            },
        ) as response:
            response.raise_for_status()
            yield from self._parse_sse_lines(response.iter_lines())

    def agent_chat(
        self,
        message: str,
        *,
        engine: str = "hive",
        schema_context: str | None = None,
        collection_name: str = "knowledge_base",
        top_k: int = 5,
        use_rag: bool = False,
        session_id: str | None = None,
        retrieval_mode: str = "hybrid",
    ) -> dict[str, Any]:
        payload = {
            "message": message,
            "engine": engine,
            "schema_context": schema_context,
            "collection_name": collection_name,
            "top_k": top_k,
            "use_rag": use_rag,
        }
        if session_id:
            payload["session_id"] = session_id
        if retrieval_mode != "hybrid":
            payload["retrieval_mode"] = retrieval_mode
        return self._json(
            self.client.post(
                "/api/v1/agent/chat",
                json=payload,
            )
        )

    def stream_agent_chat(
        self,
        message: str,
        *,
        engine: str = "hive",
        schema_context: str | None = None,
        collection_name: str = "knowledge_base",
        top_k: int = 5,
        use_rag: bool = False,
        session_id: str | None = None,
        retrieval_mode: str = "hybrid",
    ) -> Iterator[dict[str, Any]]:
        payload = {
            "message": message,
            "engine": engine,
            "schema_context": schema_context,
            "collection_name": collection_name,
            "top_k": top_k,
            "use_rag": use_rag,
        }
        if session_id:
            payload["session_id"] = session_id
        if retrieval_mode != "hybrid":
            payload["retrieval_mode"] = retrieval_mode
        with self.client.stream(
            "POST",
            "/api/v1/agent/chat/stream",
            json=payload,
        ) as response:
            response.raise_for_status()
            yield from self._parse_sse_lines(response.iter_lines())

    def text2sql(
        self,
        question: str,
        engine: str | None = None,
        schema_context: str | None = None,
        *,
        datasource: str | None = None,
        use_rag: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "question": question,
            "use_rag": use_rag,
        }
        if engine:
            payload["engine"] = engine
        if schema_context:
            payload["schema_context"] = schema_context
        if datasource:
            payload["datasource"] = datasource
        return self._json(
            self.client.post(
                "/api/v1/text2sql",
                json=payload,
            )
        )

    def list_query_datasources(self) -> dict[str, Any]:
        return self._json(
            self.client.get("/api/v1/query-execution/datasources")
        )

    def get_query_datasource_schema(self, datasource: str) -> dict[str, Any]:
        return self._json(
            self.client.get(
                f"/api/v1/query-execution/datasources/{datasource}/schema"
            )
        )

    def execute_query(
        self,
        *,
        datasource: str,
        sql: str,
        max_rows: int = 200,
    ) -> dict[str, Any]:
        return self._json(
            self.client.post(
                "/api/v1/query-execution",
                json={
                    "datasource": datasource,
                    "sql": sql,
                    "max_rows": max_rows,
                },
            )
        )

    def sql_review(
        self,
        sql: str,
        engine: str,
        *,
        include_llm_explanation: bool = True,
    ) -> dict[str, Any]:
        return self._json(
            self.client.post(
                "/api/v1/sql-review",
                json={
                    "sql": sql,
                    "engine": engine,
                    "include_llm_explanation": include_llm_explanation,
                },
            )
        )

    def warehouse_design(
        self,
        requirement: str,
        *,
        use_rag: bool = False,
        recommendation_language: str = "zh-CN",
    ) -> dict[str, Any]:
        return self._json(
            self.client.post(
                "/api/v1/warehouse-design",
                json={
                    "requirement": requirement,
                    "use_rag": use_rag,
                    "recommendation_language": recommendation_language,
                },
            )
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _json(self, response) -> dict[str, Any]:
        response.raise_for_status()
        return response.json()

    def _parse_sse_lines(self, lines: Iterator[str]) -> Iterator[dict[str, Any]]:
        event: str | None = None
        for line in lines:
            if not line:
                event = None
                continue
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
                continue
            if line.startswith("data:"):
                payload = line.removeprefix("data:").strip()
                yield {
                    "event": event or "message",
                    "data": json.loads(payload),
                }
