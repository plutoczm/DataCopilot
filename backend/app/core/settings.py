from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.core.constants import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CHROMADB_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_CHAT_MODEL,
    DEFAULT_DEEPSEEK_TIMEOUT_SECONDS,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDINGS_DIR,
    DEFAULT_LOGS_DIR,
    DEFAULT_MODELS_DIR,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_CHAT_MODEL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_CHAT_MODEL,
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    DEFAULT_PROJECT_ROOT,
    DEFAULT_TEMP_DIR,
    DEFAULT_UPLOADS_DIR,
    ENV_DEVELOPMENT,
    ENV_PRODUCTION,
    ENV_TEST,
    PROJECT_NAME,
    PROVIDER_DEEPSEEK,
    PROVIDER_LOCAL,
    PROVIDER_OLLAMA,
    PROVIDER_OPENAI,
)


class Environment(StrEnum):
    DEVELOPMENT = ENV_DEVELOPMENT
    TEST = ENV_TEST
    PRODUCTION = ENV_PRODUCTION


class ProviderName(StrEnum):
    DEEPSEEK = PROVIDER_DEEPSEEK
    OPENAI = PROVIDER_OPENAI
    OLLAMA = PROVIDER_OLLAMA
    LOCAL = PROVIDER_LOCAL


class AppSettings(BaseModel):
    name: str = PROJECT_NAME
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: tuple[str, ...] = ("http://localhost:8501",)


class PathSettings(BaseModel):
    project_root: Path = DEFAULT_PROJECT_ROOT
    data_dir: Path = DEFAULT_DATA_DIR
    chromadb_dir: Path = DEFAULT_CHROMADB_DIR
    uploads_dir: Path = DEFAULT_UPLOADS_DIR
    logs_dir: Path = DEFAULT_LOGS_DIR
    cache_dir: Path = DEFAULT_CACHE_DIR
    embeddings_dir: Path = DEFAULT_EMBEDDINGS_DIR
    temp_dir: Path = DEFAULT_TEMP_DIR
    models_dir: Path = DEFAULT_MODELS_DIR

    @field_validator(
        "project_root",
        "data_dir",
        "chromadb_dir",
        "uploads_dir",
        "logs_dir",
        "cache_dir",
        "embeddings_dir",
        "temp_dir",
        "models_dir",
        mode="before",
    )
    @classmethod
    def expand_path(cls, value: Any) -> Path:
        return Path(value).expanduser()

    @model_validator(mode="after")
    def validate_paths_stay_inside_project_root(self) -> Self:
        project_root = self.project_root.resolve()
        object.__setattr__(self, "project_root", project_root)
        for field_name in (
            "data_dir",
            "chromadb_dir",
            "uploads_dir",
            "logs_dir",
            "cache_dir",
            "embeddings_dir",
            "temp_dir",
            "models_dir",
        ):
            path = _resolve_project_path(getattr(self, field_name), project_root)
            object.__setattr__(self, field_name, path)
            if not path.is_relative_to(project_root):
                raise ValueError(f"{field_name} must stay inside project_root")
        return self


class LLMSettings(BaseModel):
    default_provider: ProviderName = ProviderName.DEEPSEEK
    request_timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)
    streaming_enabled: bool = True


class EmbeddingSettings(BaseModel):
    default_model: str = DEFAULT_EMBEDDING_MODEL
    batch_size: int = Field(default=16, ge=1, le=256)
    cache_enabled: bool = True


class APIProviderSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    enabled: bool = True
    api_key: SecretStr | None = None
    base_url: AnyHttpUrl
    chat_model: str
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)


class DeepSeekSettings(APIProviderSettings):
    base_url: AnyHttpUrl = DEFAULT_DEEPSEEK_BASE_URL
    chat_model: str = DEFAULT_DEEPSEEK_CHAT_MODEL
    timeout_seconds: int = DEFAULT_DEEPSEEK_TIMEOUT_SECONDS


class OpenAISettings(APIProviderSettings):
    enabled: bool = False
    base_url: AnyHttpUrl = DEFAULT_OPENAI_BASE_URL
    chat_model: str = DEFAULT_OPENAI_CHAT_MODEL
    timeout_seconds: int = DEFAULT_OPENAI_TIMEOUT_SECONDS


class OllamaSettings(BaseModel):
    model_config = ConfigDict(validate_default=True)

    enabled: bool = False
    base_url: AnyHttpUrl = DEFAULT_OLLAMA_BASE_URL
    chat_model: str = DEFAULT_OLLAMA_CHAT_MODEL
    timeout_seconds: int = Field(default=DEFAULT_OLLAMA_TIMEOUT_SECONDS, ge=1, le=600)
    keep_alive: str = "5m"


class RuntimeSettings(BaseModel):
    api_only: bool = False
    gpu_enabled: bool = False
    cpu_only: bool = True

    @model_validator(mode="after")
    def validate_cpu_gpu_mode(self) -> Self:
        if self.gpu_enabled and self.cpu_only:
            raise ValueError("gpu_enabled and cpu_only cannot both be true")
        return self


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_enabled: bool = True
    console_enabled: bool = True
    file_enabled: bool = True
    file_path: Path = DEFAULT_LOGS_DIR / "datacopilot.log"
    max_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)
    backup_count: int = Field(default=10, ge=1, le=100)
    request_id_header: str = "x-request-id"
    trace_id_header: str = "x-trace-id"

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: Any) -> str:
        normalized = str(value).upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError("level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return normalized

    @field_validator("file_path", mode="before")
    @classmethod
    def expand_file_path(cls, value: Any) -> Path:
        return Path(value).expanduser()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            DEFAULT_PROJECT_ROOT / ".env.example",
            DEFAULT_PROJECT_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        env_prefix="DATACOPILOT_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
        validate_assignment=True,
    )

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    app: AppSettings = Field(default_factory=AppSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    deepseek: DeepSeekSettings = Field(default_factory=DeepSeekSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="DEEPSEEK_API_KEY",
        exclude=True,
        repr=False,
    )
    deepseek_base_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias="DEEPSEEK_BASE_URL",
        exclude=True,
        repr=False,
    )
    deepseek_model: str | None = Field(
        default=None,
        validation_alias="DEEPSEEK_MODEL",
        exclude=True,
        repr=False,
    )
    deepseek_timeout: int | None = Field(
        default=None,
        validation_alias="DEEPSEEK_TIMEOUT",
        exclude=True,
        repr=False,
    )
    deepseek_max_retries: int | None = Field(
        default=None,
        validation_alias="DEEPSEEK_MAX_RETRIES",
        exclude=True,
        repr=False,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def default_debug_by_environment(cls, value: Any, info: ValidationInfo) -> bool:
        if value is not None:
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"1", "true", "t", "yes", "y", "on"}:
                    return True
                if normalized in {"0", "false", "f", "no", "n", "off", ""}:
                    return False
            return bool(value)
        environment = info.data.get("environment", Environment.DEVELOPMENT)
        return environment is not Environment.PRODUCTION

    @model_validator(mode="after")
    def resolve_logging_paths_against_project_root(self) -> Self:
        logging_data = self.logging.model_dump()
        logging_data["file_path"] = _resolve_project_path(
            self.logging.file_path,
            self.paths.project_root,
        )
        object.__setattr__(self, "logging", LoggingSettings(**logging_data))
        return self

    @model_validator(mode="after")
    def apply_direct_deepseek_environment_aliases(self) -> Self:
        alias_values = {
            "api_key": self.deepseek_api_key,
            "base_url": self.deepseek_base_url,
            "chat_model": self.deepseek_model,
            "timeout_seconds": self.deepseek_timeout,
            "max_retries": self.deepseek_max_retries,
        }
        updates = {
            field_name: value
            for field_name, value in alias_values.items()
            if value is not None and value != ""
        }
        if updates:
            deepseek_data = self.deepseek.model_dump()
            deepseek_data.update(updates)
            object.__setattr__(
                self,
                "deepseek",
                DeepSeekSettings(**deepseek_data),
            )
        return self

    @model_validator(mode="after")
    def validate_environment_safety(self) -> Self:
        if self.environment is Environment.PRODUCTION and self.debug:
            raise ValueError("debug must be false in production")
        return self


def _resolve_project_path(path: Path, project_root: Path) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (project_root / expanded).resolve()
