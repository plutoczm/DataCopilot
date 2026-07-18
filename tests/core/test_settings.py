from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.core.config import clear_settings_cache, get_settings, load_settings
from backend.app.core.constants import DEFAULT_PROJECT_ROOT
from backend.app.core.settings import Environment, ProviderName, Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_settings_defaults_are_project_local_and_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATACOPILOT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATACOPILOT_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.paths.project_root == DEFAULT_PROJECT_ROOT
    assert settings.paths.data_dir == PROJECT_ROOT / "data"
    assert settings.paths.chromadb_dir == PROJECT_ROOT / "data" / "chromadb"
    assert settings.paths.uploads_dir == PROJECT_ROOT / "data" / "uploads"
    assert settings.paths.logs_dir == PROJECT_ROOT / "data" / "logs"
    assert settings.paths.cache_dir == PROJECT_ROOT / "data" / "cache"
    assert settings.paths.embeddings_dir == PROJECT_ROOT / "data" / "embeddings"
    assert settings.paths.temp_dir == PROJECT_ROOT / "data" / "temp"
    assert settings.paths.models_dir == PROJECT_ROOT / "models"
    assert settings.llm.default_provider is ProviderName.DEEPSEEK
    assert str(settings.deepseek.base_url).rstrip("/") == "https://api.deepseek.com/v1"
    assert settings.deepseek.chat_model == "deepseek-chat"
    assert settings.openai.enabled is False
    assert settings.ollama.enabled is False


def test_relative_paths_are_resolved_against_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "copied-project"

    settings = Settings(
        _env_file=None,
        paths={
            "project_root": project_root,
            "data_dir": "data",
            "chromadb_dir": "data/chromadb",
            "uploads_dir": "data/uploads",
            "logs_dir": "data/logs",
            "cache_dir": "data/cache",
            "embeddings_dir": "data/embeddings",
            "temp_dir": "data/temp",
            "models_dir": "models",
        },
        logging={"file_path": "data/logs/datacopilot.log"},
    )

    assert settings.paths.project_root == project_root
    assert settings.paths.data_dir == project_root / "data"
    assert settings.paths.chromadb_dir == project_root / "data" / "chromadb"
    assert settings.paths.uploads_dir == project_root / "data" / "uploads"
    assert settings.paths.logs_dir == project_root / "data" / "logs"
    assert settings.paths.cache_dir == project_root / "data" / "cache"
    assert settings.paths.embeddings_dir == project_root / "data" / "embeddings"
    assert settings.paths.temp_dir == project_root / "data" / "temp"
    assert settings.paths.models_dir == project_root / "models"
    assert settings.logging.file_path == project_root / "data" / "logs" / "datacopilot.log"


def test_env_files_load_example_then_env_override(tmp_path: Path) -> None:
    example_file = tmp_path / ".env.example"
    env_file = tmp_path / ".env"
    example_file.write_text(
        "\n".join(
            [
                "DATACOPILOT_ENVIRONMENT=development",
                "DATACOPILOT_DEEPSEEK__CHAT_MODEL=from-example",
                "DATACOPILOT_LLM__DEFAULT_PROVIDER=deepseek",
            ]
        ),
        encoding="utf-8",
    )
    env_file.write_text(
        "\n".join(
            [
                "DATACOPILOT_ENVIRONMENT=test",
                "DATACOPILOT_DEEPSEEK__CHAT_MODEL=from-env",
                "DATACOPILOT_LLM__DEFAULT_PROVIDER=ollama",
                "DATACOPILOT_OLLAMA__ENABLED=true",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=(example_file, env_file))

    assert settings.environment is Environment.TEST
    assert settings.deepseek.chat_model == "from-env"
    assert settings.llm.default_provider is ProviderName.OLLAMA
    assert settings.ollama.enabled is True


def test_paths_must_stay_inside_project_root() -> None:
    with pytest.raises(ValidationError, match="must stay inside project_root"):
        Settings(
            _env_file=None,
            paths={
                "project_root": DEFAULT_PROJECT_ROOT,
                "data_dir": "/var/lib/datacopilot",
            },
        )


def test_production_environment_disallows_debug() -> None:
    with pytest.raises(ValidationError, match="debug must be false"):
        Settings(_env_file=None, environment="production", debug=True)

    settings = Settings(_env_file=None, environment="production", debug=False)

    assert settings.environment is Environment.PRODUCTION
    assert settings.debug is False


def test_debug_environment_strings_are_parsed_as_booleans() -> None:
    assert Settings(_env_file=None, debug="false").debug is False
    assert Settings(_env_file=None, debug="0").debug is False
    assert Settings(_env_file=None, debug="true").debug is True


def test_config_helpers_cache_and_clear_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATACOPILOT_ENVIRONMENT", "test")
    clear_settings_cache()

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.environment is Environment.TEST

    clear_settings_cache()
    third = get_settings()

    assert third is not first
    assert third.environment is Environment.TEST


def test_load_settings_can_use_explicit_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATACOPILOT_ENVIRONMENT=test\n", encoding="utf-8")

    settings = load_settings(env_file=env_file)

    assert settings.environment is Environment.TEST


def test_deepseek_direct_environment_aliases_are_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "direct-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.example/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT", "33")
    monkeypatch.setenv("DEEPSEEK_MAX_RETRIES", "4")

    settings = Settings(_env_file=None)

    assert settings.deepseek.api_key is not None
    assert settings.deepseek.api_key.get_secret_value() == "direct-key"
    assert str(settings.deepseek.base_url).rstrip("/") == "https://deepseek.example/v1"
    assert settings.deepseek.chat_model == "deepseek-reasoner"
    assert settings.deepseek.timeout_seconds == 33
    assert settings.deepseek.max_retries == 4
