# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for CLI --index / --site integration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import requires_submodule


# ---------------------------------------------------------------------------
# Help output
# ---------------------------------------------------------------------------

class TestHelpOutput:

    def test_help_contains_actions(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'rcac_docs_mcp', '--help'],
            capture_output=True, text=True,
        )
        assert '--index' in result.stdout
        assert '--site' in result.stdout
        assert '--update-site' in result.stdout


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestCLIErrors:

    def test_index_invalid_site(self, tmp_path: Path) -> None:
        # A site whose repo/ does not exist cannot be indexed.
        result = subprocess.run(
            [
                sys.executable, '-m', 'rcac_docs_mcp',
                '--index',
                '--site', str(tmp_path / 'nonexistent'),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert 'not found' in result.stderr or 'not found' in result.stdout


# ---------------------------------------------------------------------------
# Successful build
# ---------------------------------------------------------------------------

@requires_submodule
class TestCLIBuild:

    def test_index_builds_database(self, site_with_repo: Path) -> None:
        result = subprocess.run(
            [
                sys.executable, '-m', 'rcac_docs_mcp',
                '--index',
                '--site', str(site_with_repo),
            ],
            capture_output=True, text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert 'Documentation index built successfully' in result.stdout
        assert 'Indexed:' in result.stdout
        assert (site_with_repo / 'index.db').exists()

    def test_index_incremental(self, site_with_repo: Path) -> None:
        args = [
            sys.executable, '-m', 'rcac_docs_mcp',
            '--index',
            '--site', str(site_with_repo),
        ]
        # First build
        subprocess.run(args, capture_output=True, text=True, timeout=120)
        # Second build — should skip all
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0
        assert 'Indexed:   0 documents' in result.stdout
        assert 'Skipped:' in result.stdout
