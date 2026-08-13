from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOST_PROJECT_PATH = str(PROJECT_ROOT)


def load_compose() -> dict:
    compose_file = Path("docker-compose.yml")
    assert compose_file.is_file()
    return yaml.safe_load(compose_file.read_text(encoding="utf-8"))


def test_compose_uses_single_node_embedded_chroma_topology() -> None:
    compose = load_compose()
    services = compose["services"]
    backend = services["backend"]
    backend_env = compose["x-backend-env"]

    assert {"backend", "frontend", "ollama"}.issubset(services)
    assert "chromadb" not in services
    assert "depends_on" not in backend
    assert backend_env["DATACOPILOT_PATHS__CHROMADB_DIR"] == "data/chromadb"
    assert {
        "type": "bind",
        "source": "./data",
        "target": "/app/data",
    } in backend["volumes"]
    assert services["frontend"]["depends_on"]["backend"]["condition"] == "service_healthy"
    assert services["ollama"]["profiles"] == ["ollama"]
    assert "datacopilot" in compose["networks"]


def test_compose_provider_and_query_execution_defaults_are_bounded() -> None:
    backend_env = load_compose()["x-backend-env"]

    assert backend_env["DATACOPILOT_LLM__DEFAULT_PROVIDER"] == "${LLM_PROVIDER:-deepseek}"
    assert backend_env["DATACOPILOT_OPENAI__ENABLED"] == "${OPENAI_ENABLED:-false}"
    assert backend_env["DATACOPILOT_OLLAMA__ENABLED"] == "${OLLAMA_ENABLED:-false}"
    assert "DATACOPILOT_LLM__ROUTING_ENABLED" not in backend_env
    assert "DATACOPILOT_LOCAL__ENABLED" not in backend_env
    assert backend_env["DATACOPILOT_QUERY_EXECUTION__ENABLED"] == "${QUERY_EXECUTION_ENABLED:-false}"
    assert backend_env["DATACOPILOT_QUERY_EXECUTION__MAX_ROWS"] == "${QUERY_EXECUTION_MAX_ROWS:-200}"
    assert backend_env["DATACOPILOT_QUERY_EXECUTION__TIMEOUT_MS"] == "${QUERY_EXECUTION_TIMEOUT_MS:-3000}"


def test_compose_uses_project_local_bind_mounts_and_resource_limits() -> None:
    compose = load_compose()
    services = compose["services"]

    for service_name, service in services.items():
        for volume in service.get("volumes", []):
            assert isinstance(volume, dict), f"{service_name} must use long volume syntax"
            assert volume["type"] == "bind"
            source = volume["source"]
            assert not Path(source).is_absolute()
            assert source.startswith("./data")

    assert services["backend"]["deploy"]["resources"]["limits"] == {
        "cpus": "4.0",
        "memory": "8G",
    }
    assert services["frontend"]["deploy"]["resources"]["limits"] == {
        "cpus": "1.0",
        "memory": "2G",
    }
    assert HOST_PROJECT_PATH not in Path("docker-compose.yml").read_text(encoding="utf-8")


def test_compose_application_services_have_healthchecks_and_restart_policy() -> None:
    services = load_compose()["services"]
    for service_name in ("backend", "frontend"):
        service = services[service_name]
        assert service["restart"] == "unless-stopped"
        assert service["healthcheck"]["interval"] == "30s"
        assert service["healthcheck"]["retries"] >= 3


def test_production_env_matches_embedded_chroma_topology() -> None:
    content = Path("docker/.env.production").read_text(encoding="utf-8")

    assert "DATACOPILOT_ENVIRONMENT=production" in content
    assert "DATACOPILOT_DEBUG=false" in content
    assert "DATACOPILOT_PATHS__CHROMADB_DIR=data/chromadb" in content
    assert "DATACOPILOT_QUERY_EXECUTION__ENABLED=false" in content
    assert "DATACOPILOT_QUERY_EXECUTION__MAX_ROWS=200" in content
    assert "DATACOPILOT_QUERY_EXECUTION__TIMEOUT_MS=3000" in content
    assert "BACKEND_URL=http://backend:8000" in content
    assert "CHROMADB_PORT=" not in content
    assert "CHROMA_SERVER_HOST=" not in content
    assert "CHROMA_SERVER_HTTP_PORT=" not in content
    assert "sk-" not in content.lower()
    assert HOST_PROJECT_PATH not in content
