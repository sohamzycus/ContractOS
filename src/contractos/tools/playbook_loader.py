"""Playbook loader — parse and validate YAML playbook configurations.

Loads organizational playbook definitions from YAML files and validates
them against the PlaybookConfig schema.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from contractos.models.playbook import (
    AcceptableRange,
    PlaybookConfig,
    PlaybookPosition,
)

logger = logging.getLogger(__name__)


def load_playbook(path: str) -> PlaybookConfig:
    """Load a playbook from a YAML file.

    Args:
        path: Path to the YAML playbook file.

    Returns:
        Validated PlaybookConfig.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValidationError: If the YAML does not match the schema.
        yaml.YAMLError: If the YAML is malformed.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Playbook not found: {path}")

    with open(file_path) as f:
        raw = yaml.safe_load(f)

    playbook_data = raw.get("playbook", raw)

    # Parse positions
    positions: dict[str, PlaybookPosition] = {}
    raw_positions = playbook_data.get("positions", {})
    for key, pos_data in raw_positions.items():
        # Handle acceptable_range nested dict
        if "acceptable_range" in pos_data and isinstance(pos_data["acceptable_range"], dict):
            ar_data = pos_data["acceptable_range"]
            # Support both "min"/"max" shorthand and full field names
            pos_data["acceptable_range"] = AcceptableRange(
                min_position=ar_data.get("min_position", ar_data.get("min", "")),
                max_position=ar_data.get("max_position", ar_data.get("max", "")),
                description=ar_data.get("description", ""),
            )
        positions[key] = PlaybookPosition(**pos_data)

    return PlaybookConfig(
        name=playbook_data.get("name", ""),
        version=playbook_data.get("version", "1.0"),
        positions=positions,
    )


def _find_default_playbook_path() -> Path:
    """Locate the default playbook in multiple possible locations."""
    import os

    candidates = [
        # Dev: src/contractos/tools/playbook_loader.py → 4 levels up → project root
        Path(__file__).resolve().parent.parent.parent.parent / "config" / "default_playbook.yaml",
        # Docker: /app/config/default_playbook.yaml
        Path("/app/config/default_playbook.yaml"),
        # cwd fallback
        Path(os.getcwd()) / "config" / "default_playbook.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Default playbook not found. Searched: {[str(c) for c in candidates]}"
    )


def load_default_playbook() -> PlaybookConfig:
    """Load the built-in default playbook.

    Returns:
        The default PlaybookConfig with standard commercial positions.
    """
    path = _find_default_playbook_path()
    return load_playbook(str(path))
