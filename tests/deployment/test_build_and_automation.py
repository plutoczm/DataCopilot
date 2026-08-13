from pathlib import Path

import yaml


def test_env_example_avoids_removed_provider_variables_and_secrets() -> None:
    content = Path(".env.example").read_text(encoding="utf-8")

    assert "CHROMA_DB_IMPL" not in content
    assert "CHROMA_PERSIST_DIRECTORY" not in content
    assert "DATACOPILOT_LOCAL__" not in content
    assert "DATACOPILOT_LLM__ROUTING_" not in content
    assert "DATACOPILOT_QUERY_EXECUTION__ENABLED=false" in content
    assert "sk-" not in content.lower()


def test_backend_dockerfile_is_production_optimized() -> None:
    content = Path("backend/Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12-slim" in content
    assert "DATACOPILOT_UID=1014" in content
    assert "DATACOPILOT_GID=1015" in content
    assert "useradd" in content
    assert "pip install --no-cache-dir" in content
    assert "backend/requirements.txt" in content
    assert "HEALTHCHECK" in content
    assert "uvicorn" in content
    assert "--host=0.0.0.0" in content
    assert "EXPOSE 8000" in content


def test_frontend_dockerfile_is_production_optimized() -> None:
    content = Path("frontend/Dockerfile").read_text(encoding="utf-8")

    assert "python:3.12-slim" in content
    assert "DATACOPILOT_UID=1014" in content
    assert "DATACOPILOT_GID=1015" in content
    assert "useradd" in content
    assert "pip install --no-cache-dir" in content
    assert "HEALTHCHECK" in content
    assert "streamlit" in content
    assert "EXPOSE 8501" in content


def test_ci_workflow_enforces_dependency_integrity_and_resource_bounds() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/test.yml").read_text(encoding="utf-8"))
    quality = workflow["jobs"]["quality"]
    steps = {step["name"]: step for step in quality["steps"]}

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True
    assert quality["timeout-minutes"] == 15
    assert steps["Checkout"]["uses"] == "actions/checkout@v6"
    assert steps["Set up Python"]["uses"] == "actions/setup-python@v6"
    assert "python -m pip check" in steps["Install dependencies"]["run"]
    assert "--cov-fail-under=85" in steps["Run tests and coverage gate"]["run"]


def test_dependabot_monitors_python_and_github_actions_dependencies() -> None:
    config = yaml.safe_load(Path(".github/dependabot.yml").read_text(encoding="utf-8"))
    updates = {entry["package-ecosystem"]: entry for entry in config["updates"]}

    assert config["version"] == 2
    assert set(updates) == {"pip", "github-actions"}
    assert set(updates["pip"]["directories"]) == {"/", "/backend", "/frontend"}
    assert updates["pip"]["schedule"]["interval"] == "weekly"
    assert updates["github-actions"]["directory"] == "/"
    assert updates["github-actions"]["schedule"]["interval"] == "weekly"
