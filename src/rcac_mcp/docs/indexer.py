# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Markdown parser and indexer for RCAC documentation.

Walks an RCAC-Docs repo checkout, resolves pymdownx snippet includes and
Jinja2 macros/templates, chunks documents on H2 boundaries, and upserts
them into the SQLite FTS5 index via DocsDatabase.
"""

# Type annotations
from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any

# Standard libs
import hashlib
import importlib.util
import logging
import os
import re
from pathlib import Path

# External libs
import yaml
import jinja2

# Internal libs
from rcac_mcp.docs.database import DocsDatabase

# Public interface
__all__ = ['DocsIndexer']

log = logging.getLogger(__name__)

# Directories under docs/ to skip when walking
_SKIP_DIRS = {'snippets', 'assets', 'stylesheets'}

# Minimum content length (after frontmatter removal) to consider non-empty
_MIN_CONTENT_LENGTH = 20


class DocsIndexer:
    """Indexes RCAC-Docs markdown files into a SQLite FTS5 database.

    Handles the full pipeline: walking the docs tree, parsing frontmatter,
    resolving pymdownx snippet includes, rendering Jinja2 templates and
    macros, chunking on H2 boundaries, and upserting into the database.

    Args:
        docs_repo_root: Path to the RCAC-Docs repository root (contains
            ``main.py``, ``mkdocs.yml``, and ``docs/``).
    """

    def __init__(self, docs_repo_root: str | os.PathLike) -> None:
        self.repo_root = Path(docs_repo_root).resolve()
        self.docs_dir = self.repo_root / 'docs'

        # Validate repo structure
        if not self.docs_dir.is_dir():
            raise FileNotFoundError(
                f'docs/ directory not found at {self.docs_dir}'
            )

        # Load configuration and macros at init time
        self._mkdocs_extra: Dict[str, Any] = self._load_mkdocs_extra()
        self._macros: Dict[str, Any] = self._load_macros()

    # ------------------------------------------------------------------
    # Configuration loading
    # ------------------------------------------------------------------

    def _load_mkdocs_extra(self) -> Dict[str, Any]:
        """Parse mkdocs.yml and extract ``extra:`` variables.

        Returns:
            Dictionary of extra variables (e.g., ``{'org': '...'}``).
            Returns empty dict if mkdocs.yml is missing or has no extra block.
        """
        mkdocs_path = self.repo_root / 'mkdocs.yml'
        if not mkdocs_path.exists():
            log.warning('mkdocs.yml not found at %s', mkdocs_path)
            return {}

        # mkdocs.yml may contain !!python/name tags (e.g., emoji extensions)
        # that yaml.safe_load cannot handle.  Use a permissive SafeLoader
        # subclass that returns the tag value as a string for unknown tags.
        class _PermissiveLoader(yaml.SafeLoader):
            pass

        _PermissiveLoader.add_multi_constructor(
            'tag:yaml.org,2002:python/',
            lambda loader, suffix, node: str(node.value),
        )

        with open(mkdocs_path) as f:
            config = yaml.load(f, Loader=_PermissiveLoader)

        extra = config.get('extra', {}) or {}

        # Filter to only simple key-value pairs useful as template variables.
        # Complex nested structures (social, analytics) are not template vars.
        result: Dict[str, Any] = {}
        for key, value in extra.items():
            if isinstance(value, (str, int, float, bool)):
                result[key] = value

        return result

    def _load_macros(self) -> Dict[str, Any]:
        """Dynamically load macro functions from ``main.py``.

        The docs repo defines macros via the mkdocs-macros ``define_env``
        pattern.  We create a minimal mock environment object, call
        ``define_env(env)``, and collect the registered macros.

        Returns:
            Dictionary mapping macro function names to callables.
        """
        main_path = self.repo_root / 'main.py'
        if not main_path.exists():
            log.warning('main.py not found at %s', main_path)
            return {}

        # Load main.py as a module
        spec = importlib.util.spec_from_file_location('_rcac_docs_main', main_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create a mock environment that captures @env.macro registrations
        macros: Dict[str, Any] = {}

        class _MockEnv:
            """Minimal mock of mkdocs-macros MacrosPlugin env."""

            def macro(self, func):
                """Decorator that registers a macro function."""
                macros[func.__name__] = func
                return func

        define_env = getattr(module, 'define_env', None)
        if define_env is None:
            log.warning('No define_env function found in %s', main_path)
            return {}

        define_env(_MockEnv())
        log.debug('Loaded %d macros from main.py: %s', len(macros), list(macros.keys()))
        return macros

    # ------------------------------------------------------------------
    # Snippet resolution
    # ------------------------------------------------------------------

    def _resolve_snippets(self, content: str) -> str:
        """Expand all ``--8<--`` pymdownx snippet directives.

        Handles three forms:
        1. Inline whole-file: ``--8<-- "path/to/file.md"``
        2. Inline named section: ``--8<-- "path/to/file.md:section"``
        3. Fenced multi-file block::

               --8<--
               path/to/file1.md
               path/to/file2.md
               --8<--

        Snippet paths are resolved relative to the repo root.

        Args:
            content: Raw markdown content with potential snippet directives.

        Returns:
            Content with all snippet directives replaced by their contents.
        """
        # Pass 1: Fenced multi-file blocks
        content = self._resolve_fenced_snippets(content)

        # Pass 2: Inline single-file includes (whole file and named sections)
        content = self._resolve_inline_snippets(content)

        return content

    def _resolve_fenced_snippets(self, content: str) -> str:
        """Resolve fenced multi-file snippet blocks."""
        pattern = re.compile(
            r'^--8<--\s*$\n(.*?)^--8<--\s*$',
            re.MULTILINE | re.DOTALL,
        )

        def _replace_fenced(match: re.Match) -> str:
            block = match.group(1)
            parts = []
            for line in block.strip().splitlines():
                path = line.strip()
                if path:
                    parts.append(self._read_snippet(path))
            return '\n'.join(parts)

        return pattern.sub(_replace_fenced, content)

    def _resolve_inline_snippets(self, content: str) -> str:
        """Resolve inline single-file snippet includes."""
        # Match: --8<-- "path" or --8<-- "path:section"
        # Must be the only content on the line (possibly with leading whitespace)
        pattern = re.compile(
            r'^(\s*)--8<--\s+"([^"]+)"\s*$',
            re.MULTILINE,
        )

        def _replace_inline(match: re.Match) -> str:
            indent = match.group(1)
            ref = match.group(2)
            resolved = self._read_snippet(ref)
            # Preserve indentation
            if indent:
                resolved = '\n'.join(
                    indent + line if line else line
                    for line in resolved.splitlines()
                )
            return resolved

        return pattern.sub(_replace_inline, content)

    def _read_snippet(self, ref: str) -> str:
        """Read a snippet file or named section.

        Args:
            ref: Snippet reference, either ``"path/to/file.md"`` or
                ``"path/to/file.md:section_name"``.

        Returns:
            The snippet content, or an empty string if the file is not found.
        """
        # Split off optional section name
        if ':' in ref:
            # Handle Windows-style paths and section refs carefully.
            # Section ref is always the last colon-delimited segment
            # unless it looks like a drive letter (e.g., C:).
            parts = ref.rsplit(':', 1)
            file_path_str, section = parts[0], parts[1]
        else:
            file_path_str = ref
            section = None

        file_path = self.repo_root / file_path_str
        if not file_path.exists():
            log.warning('Snippet file not found: %s', file_path)
            return ''

        text = file_path.read_text(encoding='utf-8')

        if section:
            return self._extract_section(text, section)

        return text

    @staticmethod
    def _extract_section(text: str, section: str) -> str:
        """Extract a named section from snippet text.

        Named sections are delimited by::

            # --8<-- [start:name]
            ...content...
            # --8<-- [end:name]

        Args:
            text: Full snippet file content.
            section: Section name to extract.

        Returns:
            Content between the start/end markers, or empty string if not found.
        """
        start_marker = f'# --8<-- [start:{section}]'
        end_marker = f'# --8<-- [end:{section}]'

        in_section = False
        lines: List[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped == start_marker:
                in_section = True
                continue
            elif stripped == end_marker:
                break
            elif in_section:
                lines.append(line)

        if not lines:
            log.warning('Section %r not found in snippet', section)

        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # Jinja2 rendering
    # ------------------------------------------------------------------

    def _render_jinja2(self, content: str, frontmatter: Dict[str, Any]) -> str:
        """Render Jinja2 templates in document content.

        Builds a template context from:
        1. mkdocs.yml ``extra:`` variables
        2. Document frontmatter variables (override extra)
        3. Macro functions from main.py

        Uses ``jinja2.Undefined`` to silently pass unresolvable variables.

        Args:
            content: Markdown content with potential Jinja2 syntax.
            frontmatter: Parsed YAML frontmatter from the document.

        Returns:
            Rendered content with templates expanded.
        """
        # Build context: extra vars < frontmatter vars
        context: Dict[str, Any] = {}
        context.update(self._mkdocs_extra)
        context.update(frontmatter)

        # Add macro functions to context
        context.update(self._macros)

        try:
            env = jinja2.Environment(undefined=jinja2.Undefined)
            template = env.from_string(content)
            return template.render(**context)
        except jinja2.TemplateSyntaxError as exc:
            log.warning('Jinja2 syntax error, returning content as-is: %s', exc)
            return content
        except Exception as exc:
            log.warning('Jinja2 rendering error, returning content as-is: %s', exc)
            return content

    # ------------------------------------------------------------------
    # Frontmatter and title parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
        """Split YAML frontmatter from markdown body.

        Args:
            raw: Raw file content (may or may not have frontmatter).

        Returns:
            Tuple of (metadata dict, body text without frontmatter).
        """
        if not raw.startswith('---'):
            return {}, raw

        # Find the closing ---
        end = raw.find('---', 3)
        if end == -1:
            return {}, raw

        # The frontmatter is between the first and second ---
        fm_text = raw[3:end].strip()
        body = raw[end + 3:].lstrip('\n')

        try:
            metadata = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            log.warning('Failed to parse frontmatter: %s', exc)
            metadata = {}

        if not isinstance(metadata, dict):
            metadata = {}

        return metadata, body

    @staticmethod
    def _extract_title(
        metadata: Dict[str, Any], body: str, rel_path: str,
    ) -> str:
        """Extract document title from frontmatter, first heading, or filename.

        Tries in order:
        1. ``title`` field in frontmatter
        2. First ``# `` (H1) heading in the body
        3. Filename without extension

        Args:
            metadata: Parsed frontmatter dictionary.
            body: Markdown body text.
            rel_path: Relative path to the file (for fallback).

        Returns:
            Document title string.
        """
        # 1. Frontmatter title
        if 'title' in metadata and metadata['title']:
            return str(metadata['title'])

        # 2. First H1 heading
        match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # 3. Filename
        return Path(rel_path).stem.replace('_', ' ').replace('-', ' ').title()

    @staticmethod
    def _derive_category(rel_path: str) -> str:
        """Derive document category from the relative path.

        Uses up to two levels of directory depth for the category.
        For example:
        - ``userguides/anvil/jobs.md`` → ``"userguides/anvil"``
        - ``software/apps_md/python.md`` → ``"software/apps_md"``
        - ``blog/posts/conda.md`` → ``"blog/posts"``
        - ``index.md`` → ``""``

        Args:
            rel_path: Path relative to docs/ directory.

        Returns:
            Category string derived from directory structure.
        """
        parts = Path(rel_path).parts
        if len(parts) <= 1:
            # Top-level file (e.g., index.md)
            return ''
        elif len(parts) == 2:
            return parts[0]
        else:
            return f'{parts[0]}/{parts[1]}'

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_by_h2(content: str) -> List[Tuple[Optional[str], str]]:
        """Split content on ``## `` (H2) heading boundaries.

        Returns a list of ``(heading, content)`` tuples where:
        - The first chunk (before any H2) has ``heading=None``
        - Subsequent chunks have the H2 heading text

        Content before the first H2 becomes chunk index 0.  If a document
        has no H2 headings, the entire content is returned as a single chunk.

        Args:
            content: Rendered markdown content.

        Returns:
            List of (heading, chunk_content) tuples in document order.
        """
        # Split on H2 boundaries (## at start of line)
        parts = re.split(r'^(## .+)$', content, flags=re.MULTILINE)

        chunks: List[Tuple[Optional[str], str]] = []

        # parts[0] is content before the first ## heading
        intro = parts[0].strip()
        if intro:
            chunks.append((None, intro))

        # Remaining parts alternate: heading, content, heading, content, ...
        for i in range(1, len(parts), 2):
            heading_line = parts[i].strip()
            heading = heading_line.lstrip('#').strip()

            body = parts[i + 1].strip() if i + 1 < len(parts) else ''
            # Include the heading line in the chunk content for search context
            chunk_content = f'{heading_line}\n{body}' if body else heading_line
            chunks.append((heading, chunk_content))

        # If no chunks were created (empty content), return a single empty chunk
        if not chunks:
            chunks.append((None, content.strip()))

        return chunks

    # ------------------------------------------------------------------
    # File filtering
    # ------------------------------------------------------------------

    def _should_skip(self, rel_path: str) -> bool:
        """Determine whether a file should be skipped during indexing.

        Skips:
        - Files in ``snippets/``, ``assets/``, ``stylesheets/`` directories
        - Non-markdown files
        - Draft blog posts (``draft: true`` in frontmatter)

        Args:
            rel_path: Path relative to the docs/ directory.

        Returns:
            True if the file should be skipped.
        """
        parts = Path(rel_path).parts

        # Check top-level directory against skip list
        if parts and parts[0] in _SKIP_DIRS:
            return True

        # Only index markdown files
        if not rel_path.endswith('.md'):
            return True

        return False

    def _is_empty_content(self, body: str) -> bool:
        """Check whether a document body is effectively empty.

        A document is considered empty if after stripping whitespace and
        removing common structural markers (like ``<!-- more -->``), the
        remaining content is too short to be meaningful.

        Args:
            body: Document body text (after frontmatter removal).

        Returns:
            True if the content is too short to index.
        """
        cleaned = body.replace('<!-- more -->', '').strip()
        return len(cleaned) < _MIN_CONTENT_LENGTH

    # ------------------------------------------------------------------
    # Main build method
    # ------------------------------------------------------------------

    def build(self, db_path: str) -> Dict[str, int]:
        """Build or update the documentation search index.

        Walks the docs directory, processes each markdown file through
        the full pipeline (frontmatter → snippets → Jinja2 → chunking),
        and upserts into the database.  Uses SHA-256 content hashing for
        incremental updates — unchanged files are skipped.  Stale documents
        (files that no longer exist) are removed from the index.

        Args:
            db_path: Path to the SQLite database file.

        Returns:
            Dictionary with build statistics:
            ``{'indexed': N, 'skipped': N, 'removed': N, 'chunks': N}``
        """
        db = DocsDatabase(db_path, read_only=False)
        db.create_schema()

        stats = {'indexed': 0, 'skipped': 0, 'removed': 0, 'chunks': 0}
        seen_paths: set[str] = set()

        for md_path in sorted(self.docs_dir.rglob('*.md')):
            rel_path = str(md_path.relative_to(self.docs_dir))

            if self._should_skip(rel_path):
                continue

            seen_paths.add(rel_path)

            # Compute source hash for incremental updates
            raw = md_path.read_text(encoding='utf-8')
            source_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()

            # Skip unchanged files
            existing_hash = db.get_source_hash(rel_path)
            if existing_hash == source_hash:
                stats['skipped'] += 1
                continue

            # Parse frontmatter
            metadata, body = self._parse_frontmatter(raw)

            # Skip drafts
            if metadata.get('draft', False):
                continue

            # Skip files excluded from search
            search_config = metadata.get('search', {})
            if isinstance(search_config, dict) and search_config.get('exclude', False):
                continue

            # Resolve snippet includes
            body = self._resolve_snippets(body)

            # Render Jinja2 templates
            body = self._render_jinja2(body, metadata)

            # Strip the <!-- more --> blog truncation marker
            body = body.replace('<!-- more -->', '')

            # Skip effectively empty documents
            if self._is_empty_content(body):
                continue

            # Extract title and category
            title = self._extract_title(metadata, body, rel_path)
            category = self._derive_category(rel_path)

            # Chunk on H2 boundaries
            chunks = self._chunk_by_h2(body)

            # Upsert into database
            db.upsert_document(
                path=rel_path,
                title=title,
                category=category,
                content=body,
                source_hash=source_hash,
                chunks=chunks,
            )
            stats['indexed'] += 1
            stats['chunks'] += len(chunks)
            log.debug('Indexed: %s (%d chunks)', rel_path, len(chunks))

        # Prune stale documents (existed in DB but no longer on disk)
        indexed_paths = set(db.list_paths())
        stale_paths = indexed_paths - seen_paths
        for stale_path in stale_paths:
            db.remove_document(stale_path)
            stats['removed'] += 1
            log.debug('Removed stale: %s', stale_path)

        db.close()
        return stats
