import httpx

from examples.retail_analytics.evaluate_text2sql import _runtime_metadata


def test_runtime_metadata_records_non_secret_model_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/config/runtime"
        return httpx.Response(
            200,
            json={
                "environment": "test",
                "default_llm_provider": "deepseek",
                "default_llm_model": "chat-model",
                "embedding_model": "embedding-model",
                "vector_store": "chromadb",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        metadata = _runtime_metadata(client, "http://backend")

    assert metadata == {
        "runtime_provenance_available": True,
        "runtime_environment": "test",
        "llm_provider": "deepseek",
        "llm_model": "chat-model",
        "embedding_model": "embedding-model",
        "vector_store": "chromadb",
    }


def test_runtime_metadata_marks_unavailable_endpoint() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    with httpx.Client(transport=transport) as client:
        metadata = _runtime_metadata(client, "http://backend")

    assert metadata == {"runtime_provenance_available": False}
