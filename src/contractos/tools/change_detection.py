"""Document change detection — compute file hashes and detect modifications."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel


class ChangeResult(BaseModel):
    """Result of a change detection check."""

    file_path: str
    changed: bool
    current_hash: str
    previous_hash: str | None = None


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hex digest of the SHA-256 hash.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_change(file_path: str | Path, stored_hash: str) -> ChangeResult:
    """Check if a file has changed since it was last hashed.

    Args:
        file_path: Path to the file.
        stored_hash: The previously stored hash to compare against.

    Returns:
        ChangeResult indicating whether the file has changed.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)
    current_hash = compute_file_hash(path)
    changed = current_hash != stored_hash
    return ChangeResult(
        file_path=str(path),
        changed=changed,
        current_hash=current_hash,
        previous_hash=stored_hash if changed else None,
    )
