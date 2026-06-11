import importlib
from pathlib import Path

import httpx

from frontend.services.backend_client import BackendClient


class StubResponse:
    def __init__(self, payload=None, status_code: int = 200, text: str = "") -> None:
        self.payload = payload or {}
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "http://backend"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self.payload

    def iter_lines(self):
        yield 'event: token'
        yield 'data: {"text": "hello"}'
        yield ''
        yield 'event: citations'
        yield 'data: {"citations": []}'
        yield ''


class StubHTTPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, path: str, **kwargs):
        self.calls.append(("GET", path, kwargs))
        if path == "/health":
            return StubResponse({"status": "ok"})
        if path == "/api/v1/knowledge/documents":
            return StubResponse({"documents": []})
        return StubResponse({})

    def post(self, path: str, **kwargs):
        self.calls.append(("POST", path, kwargs))
        if path == "/api/v1/agent/chat":
            return StubResponse(
                {
                    "intent": "GENERAL_CHAT",
                    "final_response": "done",
                    "result": {"answer": "done"},
                    "routing_path": ["classify_intent", "general_chat", "format_response"],
                    "metadata": {},
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                }
            )
        return StubResponse({"ok": True, "sql": "SELECT 1", "answer": "done"})

    def delete(self, path: str, **kwargs):
        self.calls.append(("DELETE", path, kwargs))
        return StubResponse({"deleted": True})

    def stream(self, method: str, path: str, **kwargs):
        self.calls.append((method, path, kwargs))
        return _StreamContext(StubResponse())


class _StreamContext:
    def __init__(self, response: StubResponse) -> None:
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, exc_type, exc, tb):
        return False


def test_backend_client_defaults_to_docker_backend_url(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_URL", raising=False)

    client = BackendClient()

    assert client.base_url == "http://backend:8000"


def test_backend_client_calls_expected_api_paths() -> None:
    http_client = StubHTTPClient()
    client = BackendClient(http_client=http_client)

    assert client.health()["status"] == "ok"
    client.list_documents()
    client.query_knowledge("What is AQE?")
    client.text2sql("统计GMV", "hive", "orders(order_id bigint)")
    client.sql_review("SELECT * FROM t", "spark")
    client.warehouse_design("设计电商订单分析数仓", use_rag=True)
    client.agent_chat("介绍一下你")
    chunks = list(client.stream_chat("hello"))
    agent_chunks = list(client.stream_agent_chat("hello"))

    paths = [call[1] for call in http_client.calls]
    assert "/health" in paths
    assert "/api/v1/knowledge/documents" in paths
    assert "/api/v1/knowledge/query" in paths
    assert "/api/v1/text2sql" in paths
    assert "/api/v1/sql-review" in paths
    assert "/api/v1/warehouse-design" in paths
    assert "/api/v1/agent/chat" in paths
    assert "/api/v1/agent/chat/stream" in paths
    assert "/api/v1/chat/stream" in paths
    assert chunks[0]["event"] == "token"
    assert chunks[0]["data"]["text"] == "hello"
    assert agent_chunks[0]["event"] == "token"


def test_streamlit_pages_expose_render_functions() -> None:
    modules = [
        "frontend.app",
        "frontend.pages.chat",
        "frontend.pages.knowledge_base",
        "frontend.pages.text2sql",
        "frontend.pages.sql_review",
        "frontend.pages.warehouse_design",
        "frontend.components.sidebar",
        "frontend.components.api_client",
        "frontend.components.chat_message",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert hasattr(module, "render") or hasattr(module, "main") or hasattr(module, "get_client")


def test_frontend_dockerfile_exposes_streamlit_port() -> None:
    dockerfile = Path("frontend/Dockerfile")

    assert dockerfile.is_file()
    content = dockerfile.read_text(encoding="utf-8")
    assert "EXPOSE 8501" in content
    assert "streamlit" in content
    assert "frontend/app.py" in content
