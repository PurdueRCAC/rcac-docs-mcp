# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC documentation search and retrieval tools.

Provides MCP tools for searching and loading RCAC documentation from
the local FTS5-powered SQLite index. Agents use these tools to consult
authoritative documentation before advising users.

Also defines the shared tool-registration machinery (``TOOL_REGISTRY``
and the ``mcp_tool`` decorator) that the server uses to collect tools.
"""

# Type annotations
from __future__ import annotations
from typing import Optional, Set, List, Callable, Any

# Standard libs
import os
import re
import sqlite3

# External libs
from fastmcp.tools import Tool

# Internal libs
from rcac_docs_mcp.index.database import DocsDatabase
from rcac_docs_mcp.site import resolve_db_path

# Public interface
__all__ = ['TOOL_REGISTRY', 'mcp_tool']


# Registry of tool functions for us to add to server later
TOOL_REGISTRY: List[Tool] = []


def mcp_tool(func: Callable[..., Any]) -> Tool:
    """Decorator to register MCP tool functions."""
    tool = Tool.from_function(func)
    TOOL_REGISTRY.append(tool)
    return tool


# FTS5 operators that indicate the caller is already using query syntax
_FTS5_OPERATORS = re.compile(r'\bOR\b|\bAND\b|\bNOT\b|\bNEAR\b|["*]')

# Common English stopwords that add noise to search queries
_STOPWORDS: Set[str] = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'it', 'as', 'be', 'was', 'are',
    'been', 'do', 'does', 'did', 'has', 'have', 'had', 'this', 'that',
    'these', 'those', 'i', 'my', 'me', 'we', 'our', 'you', 'your',
    'how', 'what', 'when', 'where', 'which', 'who', 'can', 'will',
    'about', 'into', 'than', 'then', 'some', 'just', 'also',
}


# Term characters. Everything else is FTS5 operator syntax and must not reach
# the engine as part of a term — see _query_terms.
_TERM_CHARS = re.compile(r'[0-9A-Za-z_]+')


def _query_terms(query: str) -> List[str]:
    """Extract the searchable terms from a natural-language query.

    Terms are cut on non-word characters rather than on whitespace, because
    punctuation is operator syntax to FTS5. Splitting ``multi-node`` on
    whitespace yields one term, and the wildcard appended below turns it into
    ``multi-node*``, which SQLite rejects with ``no such column: node`` — a
    hard error rather than a poor result. The same held for ``a100-40gb``,
    ``C++``, an apostrophe, and a trailing question mark, so plain questions
    like "how do I transfer files to depot?" failed outright.

    A word that is itself a single character is kept: ``R`` and ``C`` name
    real software in this corpus, and dropping them searched for everything
    except the subject. Single characters that merely fall out of splitting a
    larger word ("user's" -> "user", "s") are noise and are discarded.
    """
    terms: List[str] = []
    for word in query.split():
        parts = _TERM_CHARS.findall(word)
        if not parts:
            continue
        if len(parts) > 1 or len(parts[0]) > 1:
            parts = [part for part in parts if len(part) > 1]
        terms.extend(part for part in parts if part.lower() not in _STOPWORDS)
    return terms


def _normalize_query(query: str) -> str:
    """Normalize a natural-language query into forgiving FTS5 syntax.

    If the query already contains FTS5 operators (OR, AND, NOT, NEAR,
    quoted phrases, or prefix wildcards), it is returned as-is: the caller
    has opted into the full query language and we must not rewrite it.

    Otherwise, stopwords are stripped and the remaining terms are joined
    with OR and given prefix wildcards so that a query like
    "ssh key config setup" becomes ``ssh* OR key* OR config* OR setup*``.
    This avoids the implicit-AND behavior that causes overly specific
    queries to return zero results.
    """
    if _FTS5_OPERATORS.search(query):
        return query

    terms = _query_terms(query)

    if not terms:
        return query

    # A one-character prefix matches most of the index, so single-character
    # terms are searched exactly rather than wildcarded.
    return ' OR '.join(term if len(term) == 1 else f'{term}*' for term in terms)


def _get_db_path() -> str:
    """Resolve the documentation database path.

    The index lives inside the site container (``<site>/index.db``),
    resolved from the ``RCAC_DOCS_SITE`` environment variable or the
    XDG-compliant default (~/.local/share/rcac-docs-mcp/index.db).
    """
    return resolve_db_path()


def _db_available() -> bool:
    """Check whether the documentation database exists on disk."""
    return os.path.isfile(_get_db_path())


_NO_DB_MESSAGE = (
    'Documentation index is not available. '
    'Build it with: rcac-docs-mcp --update-site && rcac-docs-mcp --index'
)


@mcp_tool
def doc_search(query: str, category: Optional[str] = None) -> str:
    """Search RCAC documentation for relevant sections.

    Performs full-text search over indexed RCAC documentation (user guides,
    software catalog, datasets, blog posts, workshops) using SQLite FTS5
    with BM25 ranking. Use this tool to find relevant documentation before
    advising users on storage, jobs, software, or any RCAC-specific topic.

    Search strategy — plain words are broadened, operators are for precision:
    - A query with no operator is normalized: stopwords removed, the rest
      joined with OR and prefix-matched. That is deliberately recall-heavy,
      so most plain queries fill all 20 result slots.
    - Any FTS5 operator switches normalization off and the query is passed
      through verbatim. That is how you narrow:
        "job array"                  exact phrase (3 hits, against 20 unquoted)
        gilbreth AND fortress        both terms must appear
        apptainer AND anvil NOT conda
        NEAR(scratch purge, 5)
    - The index is Porter-stemmed, so gpu/gpus and purge/purged/purging
      already match each other; * is rarely needed.
    - Punctuation is operator syntax. Write "multi node", or quote the term
      as "multi-node" to match it exactly.

    Args:
        query: The search query string (FTS5 syntax supported).
        category: Optional category filter to narrow results. Matches as a
            prefix, so 'userguides' matches 'userguides/anvil', etc.
            Common categories: 'userguides', 'software', 'datasets',
            'blog', 'workshops'. Deeper prefixes work and are sharper:
            'userguides/gilbreth' returns that cluster's own pages first.

    Returns:
        Formatted search results with document path, title, section heading,
        and a text snippet showing the matching context. Results are ranked
        by relevance (BM25). Returns up to 20 results.

    Examples:
        doc_search("scratch purge")
        doc_search("conda OR anaconda", category="software")
        doc_search("GPU job submission", category="userguides")
        doc_search("A100", category="userguides/gilbreth")
    """
    if not _db_available():
        return _NO_DB_MESSAGE

    normalized = _normalize_query(query)
    try:
        with DocsDatabase(_get_db_path(), read_only=True) as db:
            results = db.search(normalized, category=category, limit=20)
    except sqlite3.OperationalError as error:
        # A query the caller wrote in FTS5 syntax can still be malformed, and
        # normalization deliberately leaves those alone. Hand back the engine's
        # own words plus the way out; an exception here surfaces to the agent as
        # a tool failure it cannot act on, and it costs a whole research round.
        return (
            f'Invalid search query: {error}. Retry with two or three plain words, or '
            'fix the FTS5 syntax: balance the quotes, put OR/AND/NOT between terms, '
            'and use * only at the end of a term.'
        )

    if not results:
        msg = f'No documentation found matching: {query}'
        if category:
            msg += f' (category: {category})'
        return msg

    lines = [f'Found {len(results)} result(s):\n']
    for i, result in enumerate(results, 1):
        heading = f' > {result.heading}' if result.heading else ''
        lines.append(f'{i}. [{result.title}]{heading}')
        lines.append(f'   Path: {result.path}')
        lines.append(f'   {result.snippet}')
        lines.append('')

    return '\n'.join(lines)


@mcp_tool
def doc_load(path: str) -> str:
    """Load the full content of an RCAC documentation page.

    Returns the complete rendered markdown of a documentation page
    identified by its relative path. Use this after doc_search to
    read the full content of a relevant document.

    Args:
        path: Relative path to the document (e.g., 'userguides/gautschi/storage.md').
            This is the path shown in doc_search results.

    Returns:
        Full rendered markdown content of the document, with all snippets
        and templates already resolved.

    Examples:
        doc_load("userguides/gautschi/storage.md")
        doc_load("software/apps_md/conda.md")
        doc_load("blog/posts/scratch-purge.md")
    """
    if not _db_available():
        return _NO_DB_MESSAGE

    with DocsDatabase(_get_db_path(), read_only=True) as db:
        content = db.load_document(path)

    if content is None:
        return f'Document not found: {path}'

    return content
