"""Unit tests for playbook loader — T202.

TDD Red: Write tests FIRST, verify they FAIL, then implement loader.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml


class TestLoadPlaybook:
    """Verify load_playbook loads YAML into PlaybookConfig."""

    def test_load_valid_yaml(self, tmp_path: Path):
        from contractos.tools.playbook_loader import load_playbook

        playbook_data = {
            "playbook": {
                "name": "Test Playbook",
                "version": "2.0",
                "positions": {
                    "termination": {
                        "clause_type": "termination",
                        "standard_position": "30 days notice",
                        "escalation_triggers": ["Immediate termination"],
                        "priority": "tier_1",
                        "required": True,
                    },
                },
            }
        }
        yaml_path = tmp_path / "test_playbook.yaml"
        yaml_path.write_text(yaml.dump(playbook_data))

        config = load_playbook(str(yaml_path))
        assert config.name == "Test Playbook"
        assert config.version == "2.0"
        assert "termination" in config.positions
        assert config.positions["termination"].required is True

    def test_load_validates_schema(self, tmp_path: Path):
        """Invalid position data should raise ValidationError."""
        from pydantic import ValidationError

        from contractos.tools.playbook_loader import load_playbook

        # Missing required fields in position
        playbook_data = {
            "playbook": {
                "name": "Bad Playbook",
                "positions": {
                    "termination": {
                        # Missing clause_type and standard_position
                        "priority": "tier_1",
                    },
                },
            }
        }
        yaml_path = tmp_path / "bad_playbook.yaml"
        yaml_path.write_text(yaml.dump(playbook_data))

        with pytest.raises(ValidationError):
            load_playbook(str(yaml_path))

    def test_load_missing_file_raises(self):
        from contractos.tools.playbook_loader import load_playbook

        with pytest.raises(FileNotFoundError):
            load_playbook("/nonexistent/path/playbook.yaml")

    def test_load_malformed_yaml(self, tmp_path: Path):
        """Malformed YAML should raise an error."""
        from contractos.tools.playbook_loader import load_playbook

        yaml_path = tmp_path / "malformed.yaml"
        yaml_path.write_text("{{{{not: valid: yaml: [[[")

        with pytest.raises(Exception):
            load_playbook(str(yaml_path))

    def test_load_multiple_positions(self, tmp_path: Path):
        from contractos.tools.playbook_loader import load_playbook

        playbook_data = {
            "playbook": {
                "name": "Multi-Position",
                "positions": {
                    "termination": {
                        "clause_type": "termination",
                        "standard_position": "30 days notice",
                    },
                    "payment": {
                        "clause_type": "payment",
                        "standard_position": "Net 30",
                    },
                    "liability": {
                        "clause_type": "liability",
                        "standard_position": "Mutual cap at 12 months",
                        "acceptable_range": {
                            "min_position": "6 months",
                            "max_position": "24 months",
                        },
                    },
                },
            }
        }
        yaml_path = tmp_path / "multi.yaml"
        yaml_path.write_text(yaml.dump(playbook_data))

        config = load_playbook(str(yaml_path))
        assert len(config.positions) == 3
        assert config.positions["liability"].acceptable_range is not None


class TestLoadDefaultPlaybook:
    """Verify load_default_playbook returns built-in default."""

    def test_returns_playbook_config(self):
        from contractos.models.playbook import PlaybookConfig
        from contractos.tools.playbook_loader import load_default_playbook

        config = load_default_playbook()
        assert isinstance(config, PlaybookConfig)

    def test_default_has_standard_positions(self):
        from contractos.tools.playbook_loader import load_default_playbook

        config = load_default_playbook()
        assert config.name != ""
        # Default should have at least the 10 standard clause types
        assert len(config.positions) >= 10

    def test_default_has_key_clause_types(self):
        from contractos.tools.playbook_loader import load_default_playbook

        config = load_default_playbook()
        expected_types = [
            "limitation_of_liability",
            "indemnification",
            "confidentiality",
            "termination",
            "governing_law",
        ]
        for ct in expected_types:
            assert ct in config.positions, f"Missing position for {ct}"
