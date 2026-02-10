"""Unit tests for document change detection (T102).

Tests file hash computation and change detection logic:
- Compute hash of a file
- Modify file → verify hash changes
- Same file → same hash (deterministic)
- Different files → different hashes
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from contractos.tools.change_detection import compute_file_hash, detect_change


class TestComputeFileHash:
    def test_returns_sha256_hex(self, tmp_path: Path) -> None:
        f = tmp_path / "test.docx"
        f.write_bytes(b"contract content here")
        h = compute_file_hash(f)
        assert len(h) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.docx"
        f2 = tmp_path / "b.docx"
        content = b"identical contract content"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert compute_file_hash(f1) == compute_file_hash(f2)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.docx"
        f2 = tmp_path / "b.docx"
        f1.write_bytes(b"version 1")
        f2.write_bytes(b"version 2")
        assert compute_file_hash(f1) != compute_file_hash(f2)

    def test_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.docx"
        f.write_bytes(b"stable content")
        h1 = compute_file_hash(f)
        h2 = compute_file_hash(f)
        assert h1 == h2

    def test_matches_manual_sha256(self, tmp_path: Path) -> None:
        content = b"hello world contract"
        f = tmp_path / "test.docx"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert compute_file_hash(f) == expected

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            compute_file_hash(tmp_path / "nonexistent.docx")

    def test_empty_file_has_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.docx"
        f.write_bytes(b"")
        h = compute_file_hash(f)
        assert len(h) == 64  # Even empty files get a hash


class TestDetectChange:
    def test_no_change_when_hash_matches(self, tmp_path: Path) -> None:
        f = tmp_path / "contract.docx"
        f.write_bytes(b"original content")
        original_hash = compute_file_hash(f)
        result = detect_change(f, original_hash)
        assert result.changed is False
        assert result.current_hash == original_hash

    def test_change_detected_when_file_modified(self, tmp_path: Path) -> None:
        f = tmp_path / "contract.docx"
        f.write_bytes(b"original content")
        original_hash = compute_file_hash(f)
        # Modify the file
        f.write_bytes(b"modified content")
        result = detect_change(f, original_hash)
        assert result.changed is True
        assert result.current_hash != original_hash
        assert result.previous_hash == original_hash

    def test_change_result_has_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "contract.docx"
        f.write_bytes(b"content")
        h = compute_file_hash(f)
        result = detect_change(f, h)
        assert result.file_path == str(f)

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            detect_change(tmp_path / "gone.docx", "abc123")
