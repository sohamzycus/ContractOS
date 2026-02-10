"""Unit tests for configuration loading (T032)."""

from pathlib import Path

import pytest

from contractos.config import ContractOSConfig, load_config


class TestContractOSConfig:
    def test_defaults(self):
        cfg = ContractOSConfig()
        assert cfg.llm.provider == "anthropic"
        assert cfg.storage.backend == "sqlite"
        assert cfg.server.port == 8742
        assert cfg.extraction.pipeline == ["docx_parser", "pdf_parser"]

    def test_load_from_yaml(self, tmp_path: Path):
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
contractos:
  llm:
    provider: openai
    model: gpt-4o
  server:
    port: 9000
""")
        cfg = load_config(config_file)
        assert cfg.llm.provider == "openai"
        assert cfg.llm.model == "gpt-4o"
        assert cfg.server.port == 9000
        # Defaults still apply for unspecified fields
        assert cfg.storage.backend == "sqlite"

    def test_load_default_yaml(self):
        cfg = load_config(Path("config/default.yaml"))
        assert cfg.llm.provider == "anthropic"
        assert cfg.server.port == 8742

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("/nonexistent/path.yaml")

    def test_none_path_returns_defaults(self):
        cfg = load_config(None)
        assert cfg.llm.provider == "anthropic"

    def test_empty_yaml_returns_defaults(self, tmp_path: Path):
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        cfg = load_config(config_file)
        assert cfg.llm.provider == "anthropic"

    def test_partial_override(self, tmp_path: Path):
        config_file = tmp_path / "partial.yaml"
        config_file.write_text("""
contractos:
  llm:
    temperature: 0.5
""")
        cfg = load_config(config_file)
        assert cfg.llm.temperature == 0.5
        assert cfg.llm.provider == "anthropic"  # default preserved
