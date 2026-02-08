# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for rcac_mcp.docs.database — SQLite FTS5 database layer."""

from __future__ import annotations

from rcac_mcp.docs.database import DocsDatabase, SearchResult, DocStats


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    """Verify schema initialisation is safe and idempotent."""

    def test_create_schema_in_memory(self, mem_db: DocsDatabase) -> None:
        stats = mem_db.stats()
        assert stats.document_count == 0
        assert stats.chunk_count == 0

    def test_create_schema_idempotent(self, mem_db: DocsDatabase) -> None:
        mem_db.create_schema()  # second call should not raise
        assert mem_db.stats().document_count == 0


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

class TestUpsertDocument:
    """Verify document insert and update."""

    def test_insert_new_document(self, mem_db: DocsDatabase) -> None:
        mem_db.upsert_document(
            path='test/doc.md',
            title='Test Doc',
            category='test',
            content='Hello world',
            source_hash='abc123',
            chunks=[(None, 'Hello world')],
        )
        stats = mem_db.stats()
        assert stats.document_count == 1
        assert stats.chunk_count == 1

    def test_upsert_replaces_chunks(self, mem_db: DocsDatabase) -> None:
        mem_db.upsert_document(
            path='test/doc.md', title='V1', category='test',
            content='v1', source_hash='v1',
            chunks=[(None, 'chunk1'), ('H2', 'chunk2')],
        )
        assert mem_db.stats().chunk_count == 2

        # Upsert same path with different chunks
        mem_db.upsert_document(
            path='test/doc.md', title='V2', category='test',
            content='v2', source_hash='v2',
            chunks=[(None, 'only-one-chunk')],
        )
        assert mem_db.stats().document_count == 1
        assert mem_db.stats().chunk_count == 1

    def test_upsert_updates_content(self, mem_db: DocsDatabase) -> None:
        mem_db.upsert_document(
            path='a.md', title='A', category='',
            content='old', source_hash='old',
            chunks=[(None, 'old')],
        )
        mem_db.upsert_document(
            path='a.md', title='A', category='',
            content='new', source_hash='new',
            chunks=[(None, 'new')],
        )
        assert mem_db.load_document('a.md') == 'new'


# ---------------------------------------------------------------------------
# Remove
# ---------------------------------------------------------------------------

class TestRemoveDocument:
    """Verify document removal cascades to chunks and FTS."""

    def test_remove_existing(self, sample_db: DocsDatabase) -> None:
        assert sample_db.remove_document('software/apps_md/conda.md') is True
        assert sample_db.stats().document_count == 2
        assert sample_db.load_document('software/apps_md/conda.md') is None

    def test_remove_nonexistent(self, sample_db: DocsDatabase) -> None:
        assert sample_db.remove_document('does/not/exist.md') is False

    def test_remove_cleans_fts(self, sample_db: DocsDatabase) -> None:
        sample_db.remove_document('software/apps_md/conda.md')
        # Search for conda-specific content should return no results
        results = sample_db.search('conda environments')
        paths = [r.path for r in results]
        assert 'software/apps_md/conda.md' not in paths


# ---------------------------------------------------------------------------
# Source hash
# ---------------------------------------------------------------------------

class TestGetSourceHash:

    def test_existing_document(self, sample_db: DocsDatabase) -> None:
        assert sample_db.get_source_hash('userguides/gautschi/storage.md') == 'aaa111'

    def test_nonexistent_document(self, sample_db: DocsDatabase) -> None:
        assert sample_db.get_source_hash('no/such/file.md') is None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:

    def test_basic_search(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('scratch purge')
        assert len(results) >= 1
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_returns_ranked(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('scratch')
        # Results should be sorted by rank (lower is more relevant)
        ranks = [r.rank for r in results]
        assert ranks == sorted(ranks)

    def test_search_category_filter(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('scratch', category='blog')
        assert all(r.path.startswith('blog/') for r in results)

    def test_search_category_prefix_match(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('scratch', category='userguides')
        assert all(r.path.startswith('userguides/') for r in results)

    def test_search_no_results(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('xyznonexistentterm')
        assert results == []

    def test_search_limit(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('scratch', limit=1)
        assert len(results) <= 1

    def test_search_result_has_snippet(self, sample_db: DocsDatabase) -> None:
        results = sample_db.search('conda')
        assert len(results) >= 1
        assert results[0].snippet  # non-empty


# ---------------------------------------------------------------------------
# Load document
# ---------------------------------------------------------------------------

class TestLoadDocument:

    def test_load_existing(self, sample_db: DocsDatabase) -> None:
        content = sample_db.load_document('userguides/gautschi/storage.md')
        assert content is not None
        assert 'Scratch is purged' in content

    def test_load_nonexistent(self, sample_db: DocsDatabase) -> None:
        assert sample_db.load_document('does/not/exist.md') is None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:

    def test_sample_counts(self, sample_db: DocsDatabase) -> None:
        stats = sample_db.stats()
        assert isinstance(stats, DocStats)
        assert stats.document_count == 3
        assert stats.chunk_count == 5  # 2 + 2 + 1


# ---------------------------------------------------------------------------
# List paths
# ---------------------------------------------------------------------------

class TestListPaths:

    def test_lists_all_paths(self, sample_db: DocsDatabase) -> None:
        paths = sample_db.list_paths()
        assert set(paths) == {
            'userguides/gautschi/storage.md',
            'software/apps_md/conda.md',
            'blog/posts/scratch-purge.md',
        }


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:

    def test_context_manager_closes(self, tmp_db_path: str) -> None:
        with DocsDatabase(tmp_db_path) as db:
            db.create_schema()
            db.upsert_document(
                path='a.md', title='A', category='', content='x',
                source_hash='h', chunks=[(None, 'x')],
            )
        # Connection should be closed — reopen to verify data persisted
        with DocsDatabase(tmp_db_path, read_only=True) as db2:
            assert db2.stats().document_count == 1
