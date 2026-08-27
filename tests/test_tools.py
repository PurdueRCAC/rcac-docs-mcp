# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for rcac_docs_mcp.tools — MCP doc_search and doc_load tools."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from rcac_docs_mcp.index.database import DocsDatabase
from rcac_docs_mcp.index.indexer import DocsIndexer

from conftest import requires_submodule


# ---------------------------------------------------------------------------
# Query normalization
# ---------------------------------------------------------------------------

class TestNormalizeQuery:

    def test_plain_terms_become_or_prefix(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        result = _normalize_query('ssh key config setup')
        assert result == 'ssh* OR key* OR config* OR setup*'

    def test_stopwords_stripped(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        result = _normalize_query('how do I configure the ssh keys')
        assert 'how' not in result.lower().split()
        assert 'the' not in result.lower().split()
        assert 'ssh*' in result
        assert 'keys*' in result
        assert 'configure*' in result

    def test_explicit_or_passthrough(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        query = 'conda OR anaconda'
        assert _normalize_query(query) == query

    def test_quoted_phrase_passthrough(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        query = '"job array"'
        assert _normalize_query(query) == query

    def test_prefix_wildcard_passthrough(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        query = 'contai*'
        assert _normalize_query(query) == query

    def test_and_passthrough(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        query = 'scratch AND purge'
        assert _normalize_query(query) == query

    def test_single_term(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('conda') == 'conda*'

    def test_all_stopwords_returns_original(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        query = 'how do I'
        assert _normalize_query(query) == query

    def test_standalone_single_char_term_is_kept_unwildcarded(self) -> None:
        # 'R' and 'C' name real software in this corpus. Dropping them searched
        # for everything except the subject. A one-character prefix would match
        # most of the index, so they are searched exactly instead.
        from rcac_docs_mcp.tools import _normalize_query
        result = _normalize_query('R conda environment')
        assert 'R*' not in result
        assert result == 'R OR conda* OR environment*'

    def test_single_char_from_splitting_a_word_is_dropped(self) -> None:
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query("user's home directory") == 'user* OR home* OR directory*'

    # -- punctuation must not reach FTS5 as part of a term -------------------
    # Each of these was measured erroring against the live server; the comment
    # is the error the old whitespace split produced.

    def test_hyphen_is_split_not_carried(self) -> None:
        # was: 'multi-node*' -> no such column: node
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('multi-node') == 'multi* OR node*'

    def test_hyphenated_identifier(self) -> None:
        # was: 'a100-40gb*' -> no such column: 40gb
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('a100-40gb') == 'a100* OR 40gb*'

    def test_trailing_question_mark(self) -> None:
        # was: 'depot?*' -> fts5: syntax error near "?"
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('how do I transfer files to depot?') == \
            'transfer* OR files* OR depot*'

    def test_plus_signs(self) -> None:
        # was: 'C++*' -> fts5: syntax error near "+"
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('C++ compiler') == 'C OR compiler*'

    def test_brackets(self) -> None:
        # was: '(A100)*' -> fts5: syntax error near "*"
        from rcac_docs_mcp.tools import _normalize_query
        assert _normalize_query('GPU (A100)') == 'GPU* OR A100*'

    def test_every_normalized_query_is_valid_fts5(self) -> None:
        """The normalizer's whole job is to be forgiving. Prove it against the
        real engine rather than against an expected string."""
        import sqlite3
        from rcac_docs_mcp.tools import _normalize_query
        conn = sqlite3.connect(':memory:')
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(body, tokenize='porter unicode61')")
        conn.execute("INSERT INTO t VALUES ('run a multi-node mpi job on negishi')")
        cases = [
            'multi-node', 'a100-40gb', 'large-memory queue', 'x-11 forwarding',
            'how do I transfer files to depot?', "user's home directory",
            'C++ compiler', 'GPU (A100)', 'scratch purge', 'R packages',
            'depot: quota', 'gpu/cpu ratio', 'e-mail notification',
        ]
        for case in cases:
            normalized = _normalize_query(case)
            conn.execute('SELECT count(*) FROM t WHERE t MATCH ?', (normalized,)).fetchone()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

class TestToolRegistration:

    def test_doc_search_in_registry(self) -> None:
        from rcac_docs_mcp.tools import TOOL_REGISTRY
        names = [t.name for t in TOOL_REGISTRY]
        assert 'doc_search' in names

    def test_doc_load_in_registry(self) -> None:
        from rcac_docs_mcp.tools import TOOL_REGISTRY
        names = [t.name for t in TOOL_REGISTRY]
        assert 'doc_load' in names


# ---------------------------------------------------------------------------
# Missing database (graceful handling)
# ---------------------------------------------------------------------------

class TestMissingDatabase:

    def test_doc_search_no_db(self, tmp_path: Path) -> None:
        from rcac_docs_mcp.tools import doc_search
        empty_site = str(tmp_path / 'empty-site')
        with mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': empty_site}):
            result = doc_search.fn('scratch purge')
        assert 'not available' in result
        assert '--index' in result

    def test_doc_load_no_db(self, tmp_path: Path) -> None:
        from rcac_docs_mcp.tools import doc_load
        empty_site = str(tmp_path / 'empty-site')
        with mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': empty_site}):
            result = doc_load.fn('userguides/gautschi/storage.md')
        assert 'not available' in result


# ---------------------------------------------------------------------------
# With a built database
# ---------------------------------------------------------------------------

@requires_submodule
class TestDocSearchWithData:

    @pytest.fixture(autouse=True)
    def _setup_db(self, built_db: str) -> None:
        site = os.path.dirname(built_db)
        self._env_patch = mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': site})
        self._env_patch.start()

    @pytest.fixture(autouse=True)
    def _teardown_db(self) -> None:
        yield
        self._env_patch.stop()

    def test_search_returns_results(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('scratch purge policy')
        assert 'result(s)' in result
        assert 'Path:' in result

    def test_search_no_results(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('xyznonexistentqueryterm')
        assert 'No documentation found' in result

    def test_search_category_filter(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('conda', category='software')
        assert 'result(s)' in result

    def test_search_category_no_match(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('conda', category='nonexistent_category')
        assert 'No documentation found' in result

    def test_search_deeper_category_prefix(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('storage', category='userguides/gautschi')
        assert 'userguides/gautschi' in result

    # -- end to end: queries that used to be hard errors ---------------------

    def test_hyphenated_query_searches(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('multi-node')
        assert 'Invalid search query' not in result
        assert 'result(s)' in result or 'No documentation found' in result

    def test_natural_language_question_searches(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('how do I transfer files to depot?')
        assert 'Invalid search query' not in result
        assert 'result(s)' in result

    # -- malformed FTS5 the caller wrote themselves --------------------------

    def test_malformed_operator_query_is_reported_not_raised(self) -> None:
        # An operator is present, so normalization passes the query through
        # untouched and the engine rejects it. The caller gets the reason and
        # the fix instead of an exception.
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('"unterminated OR gpu')
        assert 'Invalid search query' in result
        assert 'plain words' in result

    def test_punctuation_only_query_does_not_raise(self) -> None:
        from rcac_docs_mcp.tools import doc_search
        result = doc_search.fn('?!?')
        assert 'Invalid search query' in result


@requires_submodule
class TestDocLoadWithData:

    @pytest.fixture(autouse=True)
    def _setup_db(self, built_db: str) -> None:
        site = os.path.dirname(built_db)
        self._env_patch = mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': site})
        self._env_patch.start()

    @pytest.fixture(autouse=True)
    def _teardown_db(self) -> None:
        yield
        self._env_patch.stop()

    def test_load_existing_document(self) -> None:
        from rcac_docs_mcp.tools import doc_load
        result = doc_load.fn('index.md')
        assert len(result) > 50  # non-trivial content

    def test_load_nonexistent_document(self) -> None:
        from rcac_docs_mcp.tools import doc_load
        result = doc_load.fn('does/not/exist.md')
        assert 'not found' in result.lower()
