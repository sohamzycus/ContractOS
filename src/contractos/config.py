"""Configuration loading for ContractOS — YAML with env var overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None
    base_url_env: str = "ANTHROPIC_BASE_URL"
    max_tokens: int = 4096
    temperature: float = 0.1


class ExtractionConfig(BaseModel):
    pipeline: list[str] = Field(default_factory=lambda: ["docx_parser", "pdf_parser"])
    spacy_model: str = "en_core_web_lg"


class ClauseTypesConfig(BaseModel):
    registry: str = "config/clause_types.yaml"
    custom_types_enabled: bool = True


class StorageConfig(BaseModel):
    backend: str = "sqlite"
    path: str = "~/.contractos/trustgraph.db"

    @property
    def database_path(self) -> str:
        """Resolve database path: env var CONTRACTOS_DB_PATH > config path.

        Supports ~ expansion and respects the CONTRACTOS_DB_PATH environment
        variable for container deployments where the home directory may not
        be writable.
        """
        import os
        from pathlib import Path as _Path

        env_path = os.environ.get("CONTRACTOS_DB_PATH")
        resolved = env_path if env_path else self.path
        return str(_Path(resolved).expanduser())


class WorkspaceConfig(BaseModel):
    auto_persist: bool = True
    session_history_limit: int = 100


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8742
    cors_origins: list[str] = Field(default_factory=lambda: ["https://localhost"])


class LoggingConfig(BaseModel):
    level: str = "INFO"
    audit_log: bool = True


class ContractOSConfig(BaseModel):
    """Root configuration for ContractOS."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    clause_types: ClauseTypesConfig = Field(default_factory=ClauseTypesConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: str | Path | None = None) -> ContractOSConfig:
    """Load configuration from YAML file, falling back to defaults.

    Args:
        config_path: Path to YAML config file. If None, uses defaults.

    Returns:
        Validated ContractOSConfig instance.
    """
    if config_path is None:
        return ContractOSConfig()

    path = Path(config_path)
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)

    with open(path) as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    # Config may be nested under 'contractos' key
    if "contractos" in raw:
        raw = raw["contractos"]

    return ContractOSConfig.model_validate(raw)
