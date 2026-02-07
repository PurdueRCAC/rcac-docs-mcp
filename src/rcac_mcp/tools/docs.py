# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC documentation search and retrieval tools.

Provides MCP tools for searching and loading RCAC documentation from
the local FTS5-powered SQLite index. Agents use these tools to consult
authoritative documentation before advising users.
"""

# Type annotations
from __future__ import annotations
from typing import Optional

# Standard libs
import os

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.docs.database import DocsDatabase, DEFAULT_DB_PATH

# Public interface
__all__: list[str] = []


def _get_db_path() -> str:
    """Resolve the documentation database path.

    Checks RCAC_DOCS_DB environment variable first, then falls back
    to the XDG-compliant default (~/.config/rcac-mcp/docs.db).
    """
    return os.environ.get('RCAC_DOCS_DB', DEFAULT_DB_PATH)


def _db_available() -> bool:
    """Check whether the documentation database exists on disk."""
    return os.path.isfile(_get_db_path())


_NO_DB_MESSAGE = (
    'Documentation index is not available. '
    'Build it with: rcac-mcp --index-docs --docs-path /path/to/RCAC-Docs'
)


@mcp_tool
def doc_search(query: str, category: Optional[str] = None) -> str:
    """Search RCAC documentation for relevant sections.

    Performs full-text search over indexed RCAC documentation (user guides,
    software catalog, datasets, blog posts, workshops) using SQLite FTS5
    with BM25 ranking. Use this tool to find relevant documentation before
    advising users on storage, jobs, software, or any RCAC-specific topic.

    Supports FTS5 query syntax:
    - Implicit AND: "scratch purge" matches sections containing both words
    - Explicit OR: "conda OR anaconda" matches either
    - Phrases: '"job submission"' matches the exact phrase
    - Prefix: "contai*" matches container, containers, etc.

    Args:
        query: The search query string (FTS5 syntax supported).
        category: Optional category filter to narrow results. Matches as a
            prefix, so 'userguides' matches 'userguides/anvil', etc.
            Common categories: 'userguides', 'software', 'datasets',
            'blog', 'workshops'.

    Returns:
        Formatted search results with document path, title, section heading,
        and a text snippet showing the matching context. Results are ranked
        by relevance (BM25). Returns up to 20 results.

    Examples:
        doc_search("scratch purge policy")
        doc_search("conda environment", category="software")
        doc_search("GPU job submission", category="userguides")
    """
    if not _db_available():
        return _NO_DB_MESSAGE

    with DocsDatabase(_get_db_path(), read_only=True) as db:
        results = db.search(query, category=category, limit=20)

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
