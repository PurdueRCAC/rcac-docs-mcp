# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Shared pytest fixtures for rcac-docs-mcp tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rcac_docs_mcp.index.database import DocsDatabase
from rcac_docs_mcp.index.indexer import DocsIndexer


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
RCAC_DOCS_DIR = FIXTURES_DIR / 'RCAC-Docs'


def _submodule_available() -> bool:
    """Check if the RCAC-Docs submodule has been cloned."""
    return (RCAC_DOCS_DIR / 'docs').is_dir()


requires_submodule = pytest.mark.skipif(
    not _submodule_available(),
    reason='RCAC-Docs submodule not cloned (run: git submodule update --init)',
)


@pytest.fixture
def docs_repo_path() -> Path:
    """Path to the RCAC-Docs repo root (submodule)."""
    if not _submodule_available():
        pytest.skip('RCAC-Docs submodule not cloned')
    return RCAC_DOCS_DIR


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_db() -> DocsDatabase:
    """In-memory DocsDatabase with schema created."""
    db = DocsDatabase(':memory:')
    db.create_schema()
    return db


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    """Temporary file path for a docs database."""
    return str(tmp_path / 'index.db')


@pytest.fixture
def sample_db(mem_db: DocsDatabase) -> DocsDatabase:
    """In-memory database pre-loaded with sample documents."""
    mem_db.upsert_document(
        path='userguides/gautschi/storage.md',
        title='Gautschi Storage',
        category='userguides/gautschi',
        content='# Gautschi Storage\n\nScratch is purged every 60 days.\n\n## Home Directory\n\nHome is 25GB.',
        source_hash='aaa111',
        chunks=[
            (None, 'Scratch is purged every 60 days.'),
            ('Home Directory', '## Home Directory\nHome is 25GB.'),
        ],
    )
    mem_db.upsert_document(
        path='software/apps_md/conda.md',
        title='Conda',
        category='software/apps_md',
        content='# Conda\n\nUse conda for Python environments.\n\n## Installation\n\nLoad the module.',
        source_hash='bbb222',
        chunks=[
            (None, 'Use conda for Python environments.'),
            ('Installation', '## Installation\nLoad the module.'),
        ],
    )
    mem_db.upsert_document(
        path='blog/posts/scratch-purge.md',
        title='Scratch Purge Policy Update',
        category='blog/posts',
        content='# Scratch Purge\n\nFiles on scratch older than 60 days are purged automatically.',
        source_hash='ccc333',
        chunks=[
            (None, 'Files on scratch older than 60 days are purged automatically.'),
        ],
    )
    return mem_db


# ---------------------------------------------------------------------------
# Indexer fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def indexer(docs_repo_path: Path) -> DocsIndexer:
    """DocsIndexer pointed at the RCAC-Docs submodule."""
    return DocsIndexer(docs_repo_path)


@pytest.fixture
def built_db(indexer: DocsIndexer, tmp_db_path: str) -> str:
    """Build the full index against the submodule and return the DB path."""
    indexer.build(tmp_db_path)
    return tmp_db_path


# ---------------------------------------------------------------------------
# Site fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def site_with_repo(tmp_path: Path) -> Path:
    """Site container whose repo/ links to the RCAC-Docs submodule.

    Mirrors the on-disk layout the CLI expects (``<site>/repo`` holds the
    docs checkout; ``<site>/index.db`` is written by --index) without
    cloning anything.
    """
    if not _submodule_available():
        pytest.skip('RCAC-Docs submodule not cloned')
    site = tmp_path / 'site'
    site.mkdir()
    (site / 'repo').symlink_to(RCAC_DOCS_DIR)
    return site
