# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for CLI --index-docs integration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import requires_submodule, RCAC_DOCS_DIR


# ---------------------------------------------------------------------------
# Help output
# ---------------------------------------------------------------------------

class TestHelpOutput:

    def test_help_contains_index_docs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'rcac_mcp', '--help'],
            capture_output=True, text=True,
        )
        assert '--index-docs' in result.stdout
        assert '--docs-path' in result.stdout
        assert '--docs-output' in result.stdout


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestCLIErrors:

    def test_index_docs_without_docs_path(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'rcac_mcp', '--index-docs'],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert '--docs-path' in result.stderr or '--docs-path' in result.stdout

    def test_index_docs_invalid_path(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable, '-m', 'rcac_mcp',
                '--index-docs',
                '--docs-path', str(tmp_path / 'nonexistent'),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Successful build
# ---------------------------------------------------------------------------

@requires_submodule
class TestCLIBuild:

    def test_index_docs_builds_database(self, tmp_path: Path) -> None:
        db_path = tmp_path / 'docs.db'
        result = subprocess.run(
            [
                sys.executable, '-m', 'rcac_mcp',
                '--index-docs',
                '--docs-path', str(RCAC_DOCS_DIR),
                '--docs-output', str(db_path),
            ],
            capture_output=True, text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert 'Documentation index built successfully' in result.stdout
        assert 'Indexed:' in result.stdout
        assert db_path.exists()

    def test_index_docs_incremental(self, tmp_path: Path) -> None:
        db_path = tmp_path / 'docs.db'
        args = [
            sys.executable, '-m', 'rcac_mcp',
            '--index-docs',
            '--docs-path', str(RCAC_DOCS_DIR),
            '--docs-output', str(db_path),
        ]
        # First build
        subprocess.run(args, capture_output=True, text=True, timeout=120)
        # Second build — should skip all
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0
        assert 'Indexed:   0 documents' in result.stdout
        assert 'Skipped:' in result.stdout
