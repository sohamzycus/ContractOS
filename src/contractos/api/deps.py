"""Dependency injection for the ContractOS API.

Provides shared instances of TrustGraph, WorkspaceStore, and LLMProvider
that are initialised once at startup and injected into route handlers.
"""

from __future__ import annotations

from pathlib import Path

from contractos.config import ContractOSConfig, load_config
from contractos.fabric.trust_graph import TrustGraph
from contractos.fabric.workspace_store import WorkspaceStore
from contractos.llm.provider import LLMProvider, MockLLMProvider


class AppState:
    """Singleton holding shared resources for the application lifetime."""

    def __init__(self, config: ContractOSConfig | None = None) -> None:
        self.config = config or load_config()
        db_path = self.config.storage.database_path
        # Ensure parent directory exists (skip for in-memory)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.trust_graph = TrustGraph(db_path)
        self.workspace_store = WorkspaceStore(self.trust_graph._conn)
        self.llm: LLMProvider = self._build_llm()

    def _build_llm(self) -> LLMProvider:
        cfg = self.config.llm
        if cfg.provider == "mock":
            return MockLLMProvider()
        if cfg.provider == "anthropic":
            import os

            from contractos.llm.provider import AnthropicProvider

            api_key = cfg.api_key or os.environ.get(cfg.api_key_env)
            base_url = cfg.base_url or os.environ.get(cfg.base_url_env)
            model = os.environ.get("ANTHROPIC_MODEL", cfg.model)
            if not api_key:
                # Fallback to mock provider when no API key is available
                import logging

                logging.getLogger("contractos").warning(
                    "No ANTHROPIC_API_KEY found — falling back to mock LLM provider. "
                    "Set the environment variable or use provider: mock in config."
                )
                return MockLLMProvider()
            return AnthropicProvider(api_key=api_key, model=model, base_url=base_url)
        msg = f"Unknown LLM provider: {cfg.provider}"
        raise ValueError(msg)

    def close(self) -> None:
        self.trust_graph.close()


# Module-level singleton — set during app startup
_state: AppState | None = None


def get_state() -> AppState:
    if _state is None:
        msg = "AppState not initialised — call init_state() first"
        raise RuntimeError(msg)
    return _state


def init_state(config: ContractOSConfig | None = None) -> AppState:
    global _state
    _state = AppState(config)
    return _state


def shutdown_state() -> None:
    global _state
    if _state is not None:
        _state.close()
        _state = None
