# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for rcac_mcp.docs.indexer — markdown parsing and indexing pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from rcac_mcp.docs.database import DocsDatabase
from rcac_mcp.docs.indexer import DocsIndexer

from conftest import requires_submodule


# ---------------------------------------------------------------------------
# Pure unit tests (no submodule needed)
# ---------------------------------------------------------------------------

class TestParseFrontmatter:

    def test_with_frontmatter(self) -> None:
        raw = '---\ntitle: Hello\ntags: [a, b]\n---\nBody text'
        meta, body = DocsIndexer._parse_frontmatter(raw)
        assert meta['title'] == 'Hello'
        assert meta['tags'] == ['a', 'b']
        assert body == 'Body text'

    def test_without_frontmatter(self) -> None:
        raw = '# Just a heading\n\nSome content.'
        meta, body = DocsIndexer._parse_frontmatter(raw)
        assert meta == {}
        assert body == raw

    def test_empty_frontmatter(self) -> None:
        raw = '---\n---\nBody'
        meta, body = DocsIndexer._parse_frontmatter(raw)
        assert meta == {}
        assert body == 'Body'

    def test_invalid_yaml(self) -> None:
        raw = '---\n[invalid yaml\n---\nBody'
        meta, body = DocsIndexer._parse_frontmatter(raw)
        assert meta == {}
        assert body == 'Body'


class TestExtractTitle:

    def test_from_frontmatter(self) -> None:
        assert DocsIndexer._extract_title({'title': 'My Page'}, '', 'x.md') == 'My Page'

    def test_from_h1_heading(self) -> None:
        body = 'Some intro\n\n# The Real Title\n\nMore content'
        assert DocsIndexer._extract_title({}, body, 'x.md') == 'The Real Title'

    def test_from_filename(self) -> None:
        assert DocsIndexer._extract_title({}, 'no heading here', 'my-cool-page.md') == 'My Cool Page'

    def test_frontmatter_takes_precedence(self) -> None:
        body = '# Heading Title'
        assert DocsIndexer._extract_title({'title': 'FM Title'}, body, 'x.md') == 'FM Title'


class TestDeriveCategory:

    def test_top_level_file(self) -> None:
        assert DocsIndexer._derive_category('index.md') == ''

    def test_one_level(self) -> None:
        assert DocsIndexer._derive_category('software/index.md') == 'software'

    def test_two_levels(self) -> None:
        assert DocsIndexer._derive_category('userguides/anvil/jobs.md') == 'userguides/anvil'

    def test_deep_path(self) -> None:
        assert DocsIndexer._derive_category('a/b/c/d.md') == 'a/b'


class TestChunkByH2:

    def test_no_h2(self) -> None:
        content = 'Just some content\nwith no headings.'
        chunks = DocsIndexer._chunk_by_h2(content)
        assert len(chunks) == 1
        assert chunks[0][0] is None

    def test_single_h2(self) -> None:
        content = 'Intro text\n\n## Section One\n\nSection content'
        chunks = DocsIndexer._chunk_by_h2(content)
        assert len(chunks) == 2
        assert chunks[0] == (None, 'Intro text')
        assert chunks[1][0] == 'Section One'
        assert 'Section content' in chunks[1][1]

    def test_multiple_h2(self) -> None:
        content = 'Intro\n\n## A\n\nContent A\n\n## B\n\nContent B'
        chunks = DocsIndexer._chunk_by_h2(content)
        assert len(chunks) == 3
        assert chunks[0][0] is None
        assert chunks[1][0] == 'A'
        assert chunks[2][0] == 'B'

    def test_no_intro(self) -> None:
        content = '## First Section\n\nSome content'
        chunks = DocsIndexer._chunk_by_h2(content)
        assert len(chunks) == 1
        assert chunks[0][0] == 'First Section'

    def test_empty_content(self) -> None:
        chunks = DocsIndexer._chunk_by_h2('')
        assert len(chunks) == 1


class TestShouldSkip:

    @pytest.fixture
    def indexer_for_skip(self, docs_repo_path: Path) -> DocsIndexer:
        return DocsIndexer(docs_repo_path)

    @requires_submodule
    def test_skip_snippets(self, indexer_for_skip: DocsIndexer) -> None:
        assert indexer_for_skip._should_skip('snippets/apps/python.md') is True

    @requires_submodule
    def test_skip_assets(self, indexer_for_skip: DocsIndexer) -> None:
        assert indexer_for_skip._should_skip('assets/images/logo.png') is True

    @requires_submodule
    def test_skip_stylesheets(self, indexer_for_skip: DocsIndexer) -> None:
        assert indexer_for_skip._should_skip('stylesheets/extra.css') is True

    @requires_submodule
    def test_skip_non_markdown(self, indexer_for_skip: DocsIndexer) -> None:
        assert indexer_for_skip._should_skip('userguides/image.png') is True

    @requires_submodule
    def test_allow_normal_md(self, indexer_for_skip: DocsIndexer) -> None:
        assert indexer_for_skip._should_skip('userguides/gautschi/storage.md') is False


# ---------------------------------------------------------------------------
# Integration tests (require submodule)
# ---------------------------------------------------------------------------

@requires_submodule
class TestSnippetResolution:

    def test_inline_snippet_resolved(self, indexer: DocsIndexer) -> None:
        content = '--8<-- "docs/snippets/apps/python.md"'
        resolved = indexer._resolve_snippets(content)
        # Should have replaced the directive with actual content
        assert '--8<--' not in resolved or len(resolved) > len(content)

    def test_missing_snippet_returns_empty(self, indexer: DocsIndexer) -> None:
        content = '--8<-- "docs/snippets/nonexistent_file_xyz.md"'
        resolved = indexer._resolve_snippets(content)
        assert resolved.strip() == ''


@requires_submodule
class TestJinja2Rendering:

    def test_simple_variable(self, indexer: DocsIndexer) -> None:
        content = 'Welcome to {{ org }}'
        rendered = indexer._render_jinja2(content, {})
        # org should come from mkdocs.yml extra, or be silently left
        assert '{{' not in rendered or 'org' not in rendered

    def test_frontmatter_variable(self, indexer: DocsIndexer) -> None:
        content = 'Cluster: {{ resource }}'
        rendered = indexer._render_jinja2(content, {'resource': 'Gautschi'})
        assert 'Gautschi' in rendered

    def test_syntax_error_returns_as_is(self, indexer: DocsIndexer) -> None:
        bad = 'Hello {% invalid syntax'
        rendered = indexer._render_jinja2(bad, {})
        assert rendered == bad


@requires_submodule
class TestFullBuild:
    """Integration tests for the full index build pipeline."""

    def test_build_produces_documents(self, built_db: str) -> None:
        with DocsDatabase(built_db, read_only=True) as db:
            stats = db.stats()
            assert stats.document_count > 300
            assert stats.chunk_count > stats.document_count

    def test_build_indexes_userguides(self, built_db: str) -> None:
        with DocsDatabase(built_db, read_only=True) as db:
            results = db.search('scratch storage purge')
            assert len(results) >= 1

    def test_build_indexes_software(self, built_db: str) -> None:
        with DocsDatabase(built_db, read_only=True) as db:
            results = db.search('conda', category='software')
            assert len(results) >= 1

    def test_build_skips_snippets(self, built_db: str) -> None:
        with DocsDatabase(built_db, read_only=True) as db:
            paths = db.list_paths()
            assert not any(p.startswith('snippets/') for p in paths)

    def test_incremental_skips_unchanged(
        self, indexer: DocsIndexer, built_db: str,
    ) -> None:
        stats = indexer.build(built_db)
        # All documents should be skipped on second run
        assert stats['indexed'] == 0
        assert stats['skipped'] > 0

    def test_stale_document_removal(
        self, indexer: DocsIndexer, tmp_db_path: str,
    ) -> None:
        # Build first
        indexer.build(tmp_db_path)

        # Insert a fake document that has no source file
        with DocsDatabase(tmp_db_path) as db:
            db.upsert_document(
                path='fake/stale-doc.md', title='Stale', category='fake',
                content='gone', source_hash='zzz',
                chunks=[(None, 'gone')],
            )
            assert db.load_document('fake/stale-doc.md') is not None

        # Re-build — the stale doc should be removed
        stats = indexer.build(tmp_db_path)
        assert stats['removed'] >= 1

        with DocsDatabase(tmp_db_path, read_only=True) as db:
            assert db.load_document('fake/stale-doc.md') is None


@requires_submodule
class TestIndexerInit:

    def test_invalid_repo_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match='docs/ directory not found'):
            DocsIndexer(tmp_path)

    def test_valid_repo_path(self, docs_repo_path: Path) -> None:
        indexer = DocsIndexer(docs_repo_path)
        assert indexer.docs_dir.is_dir()
