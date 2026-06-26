# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for rcac_docs_mcp.index.indexer — markdown parsing and indexing pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from rcac_docs_mcp.index.database import DocsDatabase
from rcac_docs_mcp.index.indexer import DocsIndexer

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


class TestLoadMkdocsExtra:
    """mkdocs.yml parsing must tolerate MkDocs custom YAML tags (!ENV, !!python/...)."""

    def test_custom_tags_tolerated(self, tmp_path: Path) -> None:
        (tmp_path / 'docs').mkdir()
        (tmp_path / 'mkdocs.yml').write_text(
            'site_name: Test\n'
            'plugins:\n'
            '  - git-revision-date-localized:\n'
            '      enabled: !ENV [CI, false]\n'
            'markdown_extensions:\n'
            '  - pymdownx.emoji:\n'
            '      emoji_index: !!python/name:material.extensions.emoji.twemoji\n'
            'extra:\n'
            '  org: Test Org\n'
        )
        indexer = DocsIndexer(tmp_path)
        assert indexer._mkdocs_extra.get('org') == 'Test Org'


class TestRenderPipeline:
    """Hermetic build tests for the Jinja2/snippet pipeline (no submodule).

    These reproduce two production bugs without the RCAC-Docs submodule:
    1. main.py macros read snippet files via repo-relative paths, so the
       render must run from the repo root.
    2. Jinja2 must render before snippets are included, so snippet text
       containing brace sequences is not parsed as a template.
    """

    @staticmethod
    def _build_repo(root: Path) -> None:
        docs = root / 'docs'
        (docs / 'snippets').mkdir(parents=True)
        (root / 'mkdocs.yml').write_text('site_name: Test\nextra:\n  org: RCAC\n')
        # A macro that reads a repo-relative snippet file, as RCAC's main.py does.
        (root / 'main.py').write_text(
            'def define_env(env):\n'
            '    @env.macro\n'
            '    def cluster_info(resource):\n'
            '        with open("docs/snippets/info.md") as f:\n'
            '            return f.read().replace("{cluster}", resource.lower())\n'
        )
        (docs / 'snippets' / 'info.md').write_text(
            'Welcome to the {cluster} cluster documentation section.\n'
        )
        # A literal snippet containing brace sequences that are NOT templates
        # (e.g. Mathematica output) plus a stray Jinja-looking tag.
        (docs / 'snippets' / 'literal.md').write_text(
            'Mathematica output example follows here for the docs.\n'
            'Out[4]= {{x -> -1}, {x -> -1}}\n'
            '{% endraw %}\n'
        )
        # A page that both calls a macro and includes the literal snippet.
        (docs / 'page.md').write_text(
            '---\ntitle: Test Page\nresource: Gautschi\n---\n'
            '{{ cluster_info("Gautschi") }}\n\n'
            '## Examples\n\n'
            '--8<-- "docs/snippets/literal.md"\n'
        )

    def test_macro_reads_relative_snippet(self, tmp_path: Path) -> None:
        self._build_repo(tmp_path)
        db_path = str(tmp_path / 'index.db')
        DocsIndexer(tmp_path).build(db_path)
        with DocsDatabase(db_path, read_only=True) as db:
            doc = db.load_document('page.md')
        assert doc is not None
        # Macro output materialized (repo-relative open resolved via chdir)
        assert 'Welcome to the gautschi cluster' in doc
        # No unrendered macro call left behind
        assert 'cluster_info' not in doc

    def test_snippet_braces_not_parsed_as_jinja(self, tmp_path: Path) -> None:
        self._build_repo(tmp_path)
        db_path = str(tmp_path / 'index.db')
        DocsIndexer(tmp_path).build(db_path)
        with DocsDatabase(db_path, read_only=True) as db:
            doc = db.load_document('page.md')
        assert doc is not None
        # Snippet text is included verbatim because snippets resolve after
        # Jinja2 — the brace sequences survive instead of erroring out.
        assert 'Out[4]= {{x -> -1}, {x -> -1}}' in doc
        assert '--8<--' not in doc


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
