# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""SQLite FTS5 database for RCAC documentation search.

Manages the documentation index database including schema creation,
document upsert/removal, full-text search with BM25 ranking, and
document retrieval.
"""

# Type annotations
from __future__ import annotations
from typing import Optional, List, Tuple
from dataclasses import dataclass

# Standard libs
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Public interface
__all__ = ['DocsDatabase', 'SearchResult', 'DocStats', 'DEFAULT_DB_PATH']


# XDG-compliant default location for the docs database
DEFAULT_DB_PATH: str = os.path.join(
    os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
    'rcac-mcp',
    'docs.db',
)

# Path to schema.sql relative to this module
_SCHEMA_PATH = Path(__file__).parent / 'schema.sql'


@dataclass
class SearchResult:
    """A single search result from the documentation index."""

    path: str
    """Relative path to the source document."""

    title: str
    """Document title."""

    heading: Optional[str]
    """Section heading within the document, if any."""

    snippet: str
    """FTS5-generated snippet with match highlighting."""

    rank: float
    """BM25 relevance score (lower is more relevant)."""


@dataclass
class DocStats:
    """Summary statistics for the documentation index."""

    document_count: int
    """Total number of indexed documents."""

    chunk_count: int
    """Total number of indexed chunks (sections)."""


class DocsDatabase:
    """SQLite FTS5 database for searching RCAC documentation.

    Provides methods for creating the schema, upserting/removing
    documents, searching with BM25 ranking, and loading full
    document content.

    Args:
        db_path: Path to the SQLite database file, or ':memory:' for testing.
        read_only: Open the database in read-only mode (for MCP tool use).
    """

    def __init__(self, db_path: str, read_only: bool = False) -> None:
        if read_only:
            uri = f'file:{db_path}?mode=ro'
            self._conn = sqlite3.connect(uri, uri=True)
        else:
            self._conn = sqlite3.connect(db_path)

        # Enable foreign key enforcement
        self._conn.execute('PRAGMA foreign_keys = ON')
        self._conn.row_factory = sqlite3.Row

    def create_schema(self) -> None:
        """Create all tables, indexes, triggers, and FTS virtual table.

        Safe to call multiple times — uses IF NOT EXISTS throughout.
        """
        schema_sql = _SCHEMA_PATH.read_text()
        self._conn.executescript(schema_sql)

    def upsert_document(
        self,
        path: str,
        title: str,
        category: Optional[str],
        content: str,
        source_hash: str,
        chunks: List[Tuple[Optional[str], str]],
    ) -> None:
        """Insert or update a document and its chunks.

        If a document with the same path already exists, its old chunks
        are deleted (cascading to FTS via triggers) and replaced.

        Args:
            path: Relative path to the document (e.g., 'userguides/anvil/jobs.md').
            title: Document title.
            category: Document category (e.g., 'userguides/anvil').
            content: Full rendered markdown content.
            source_hash: SHA-256 hex digest of the source file.
            chunks: List of (heading, content) tuples in document order.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.cursor()

        try:
            # Upsert the document row
            cursor.execute(
                '''
                INSERT INTO documents (path, title, category, last_updated, source_hash, content)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    category = excluded.category,
                    last_updated = excluded.last_updated,
                    source_hash = excluded.source_hash,
                    content = excluded.content
                ''',
                (path, title, category, now, source_hash, content),
            )
            doc_id = cursor.execute(
                'SELECT doc_id FROM documents WHERE path = ?', (path,)
            ).fetchone()['doc_id']

            # Delete old chunks (triggers will clean up FTS)
            cursor.execute('DELETE FROM chunks WHERE doc_id = ?', (doc_id,))

            # Insert new chunks (title denormalized for FTS5 content reads)
            for idx, (heading, chunk_content) in enumerate(chunks):
                cursor.execute(
                    '''
                    INSERT INTO chunks (doc_id, title, heading, content, chunk_index)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (doc_id, title, heading, chunk_content, idx),
                )

            self._conn.commit()

        except Exception:
            self._conn.rollback()
            raise

    def remove_document(self, path: str) -> bool:
        """Remove a document and its chunks by path.

        Args:
            path: Relative path to the document.

        Returns:
            True if a document was removed, False if not found.
        """
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM documents WHERE path = ?', (path,))
        removed = cursor.rowcount > 0
        self._conn.commit()
        return removed

    def get_source_hash(self, path: str) -> Optional[str]:
        """Get the stored source hash for a document.

        Used by the indexer to check if a file has changed since
        it was last indexed.

        Args:
            path: Relative path to the document.

        Returns:
            SHA-256 hex digest, or None if the document is not indexed.
        """
        row = self._conn.execute(
            'SELECT source_hash FROM documents WHERE path = ?', (path,)
        ).fetchone()
        return row['source_hash'] if row else None

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Search the documentation index using FTS5 full-text search.

        Supports SQLite FTS5 query syntax including implicit AND,
        explicit OR, quoted phrases, and prefix matching with *.

        Args:
            query: The search query string.
            category: Optional category filter (prefix match, e.g., 'userguides').
            limit: Maximum number of results to return.

        Returns:
            List of SearchResult objects ranked by BM25 relevance.
        """
        if category:
            rows = self._conn.execute(
                '''
                SELECT
                    d.path,
                    d.title,
                    c.heading,
                    snippet(chunks_fts, 2, '>>>', '<<<', '...', 64) AS snippet,
                    bm25(chunks_fts, 10.0, 5.0, 1.0) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.chunk_id = chunks_fts.rowid
                JOIN documents d ON d.doc_id = c.doc_id
                WHERE chunks_fts MATCH ?
                  AND d.category LIKE ? || '%'
                ORDER BY rank
                LIMIT ?
                ''',
                (query, category, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                '''
                SELECT
                    d.path,
                    d.title,
                    c.heading,
                    snippet(chunks_fts, 2, '>>>', '<<<', '...', 64) AS snippet,
                    bm25(chunks_fts, 10.0, 5.0, 1.0) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.chunk_id = chunks_fts.rowid
                JOIN documents d ON d.doc_id = c.doc_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                ''',
                (query, limit),
            ).fetchall()

        return [
            SearchResult(
                path=row['path'],
                title=row['title'],
                heading=row['heading'],
                snippet=row['snippet'],
                rank=row['rank'],
            )
            for row in rows
        ]

    def load_document(self, path: str) -> Optional[str]:
        """Load the full rendered content of a document by path.

        Args:
            path: Relative path to the document.

        Returns:
            Full markdown content, or None if not found.
        """
        row = self._conn.execute(
            'SELECT content FROM documents WHERE path = ?', (path,)
        ).fetchone()
        return row['content'] if row else None

    def list_paths(self) -> List[str]:
        """List all indexed document paths.

        Used by the indexer to detect stale documents that should
        be removed after a rebuild.

        Returns:
            List of all document paths in the index.
        """
        rows = self._conn.execute('SELECT path FROM documents').fetchall()
        return [row['path'] for row in rows]

    def stats(self) -> DocStats:
        """Get summary statistics for the documentation index.

        Returns:
            DocStats with document and chunk counts.
        """
        doc_count = self._conn.execute(
            'SELECT COUNT(*) AS n FROM documents'
        ).fetchone()['n']
        chunk_count = self._conn.execute(
            'SELECT COUNT(*) AS n FROM chunks'
        ).fetchone()['n']
        return DocStats(document_count=doc_count, chunk_count=chunk_count)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> DocsDatabase:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
