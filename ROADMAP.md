---
feature: rcac-docs-search-index
plan_id: bb88ff3d-7742-44f5-bfbb-6cece6050034
status: approved
branch: wip
docs_repo: ../RCAC-Docs
current_phase: 4
last_updated: "2026-02-07"
decisions:
  architecture: local-to-mcp-process
  cli_approach: flags-on-existing-app
  db_default_path: "~/.config/rcac-mcp/docs.db"
  db_env_override: RCAC_DOCS_DB
  docs_path_target: repo-root  # not docs/ subdirectory
  snippet_resolution: full  # resolve --8<-- and Jinja2 at index time
  skip_dirs:
    - snippets
    - assets
    - stylesheets
  skip_empty_files: true
  index_app_catalog: true
  blog_full_content: true
  jinja2_undefined: silent  # unresolvable vars left as-is
dependencies_added:
  - pyyaml
  - jinja2
---

# ROADMAP: RCAC Documentation Search Index

## Overview

Add FTS5-powered SQLite documentation search to the RCAC MCP server so agents
can consult our 432+ markdown documentation files (user guides, software catalog,
datasets, blog posts, workshops) before advising users. This prevents suboptimal
or policy-violating suggestions by grounding agent responses in authoritative
RCAC documentation.

The implementation plan is tracked in `<plan: bb88ff3d-7742-44f5-bfbb-6cece6050034>`.

## Key Architecture Decisions

- **Local to MCP process**: Doc search runs against a local SQLite database, no
  SSH needed. Works in all execution modes (stdio, http, local).
- **CLI build step**: `rcac-mcp --index-docs --docs-path PATH` builds/updates
  the database. Incremental via SHA-256 content hashing.
- **XDG default path**: `~/.config/rcac-mcp/docs.db` with `RCAC_DOCS_DB` env
  var override.
- **Full snippet/template resolution**: `--8<--` pymdownx snippets are inlined,
  Jinja2 `{{ vars }}` and `{{ macro(args) }}` are rendered using frontmatter,
  `mkdocs.yml` extra vars, and `main.py` macros from the docs repo.
- **`--docs-path` points at repo root**: Needs access to `main.py`, `mkdocs.yml`,
  and `docs/` together.

## File Layout

```
src/rcac_mcp/
  docs/
    __init__.py         # Package init, public API
    schema.sql          # DDL: documents, chunks, chunks_fts, triggers, indexes
    database.py         # SQLite connection management, search/load/upsert queries
    indexer.py          # Markdown walking, frontmatter parsing, snippet resolution,
                        #   Jinja2 rendering, H2 chunking, incremental indexing
  tools/
    docs.py             # doc_search and doc_load MCP tools
```

## Relevant Source Files (rcac-mcp)

- `src/rcac_mcp/__init__.py` — CLI app (MCPServerApp), add --index-docs flags here
- `src/rcac_mcp/server.py` — SERVER_INSTRUCTIONS, create_mcp_server()
- `src/rcac_mcp/tools/__init__.py` — TOOL_REGISTRY, @mcp_tool decorator, tool imports
- `src/rcac_mcp/tools/rcac.py` — Example tool pattern to follow
- `src/rcac_mcp/resources.py` — RESOURCE_REGISTRY pattern (for reference)
- `src/rcac_mcp/context.py` — ContextVar pattern (for reference)
- `pyproject.toml` — Dependencies

## Relevant Source Files (RCAC-Docs)

- `main.py` — Jinja2 macro functions (login_snippet, ssh_keys_snippet, etc.)
- `mkdocs.yml` — `extra:` vars (org), `nav:` structure, plugin config
- `docs/` — All markdown content
- `docs/snippets/` — Include fragments (skip from indexing, resolve into parents)
- `docs/software/apps_md/` — 270 auto-generated per-app docs

## Document Structure Notes

- Frontmatter fields: `tags`, `authors`, `date` (blog), `title`, `slug`,
  `categories` (blog), `resource`/`cluster`/`host` (template vars), `hide`,
  `search` (boost), `draft`
- Snippet syntax: `--8<-- "docs/snippets/file.md"` (whole file),
  `--8<-- "docs/snippets/file.md:section"` (named section),
  fenced multi-file blocks
- Macro syntax: `{{ variable }}`, `{{ function(args) }}`, `{% set %}`, `{% raw %}`
- Blog truncation: `<!-- more -->` marker (include full content, ignore marker)

---

## Implementation Phases

### Phase 1: Schema and Database Layer
- [x] Create `src/rcac_mcp/docs/__init__.py` with public API exports
- [x] Create `src/rcac_mcp/docs/schema.sql` with full DDL (documents, chunks, chunks_fts, triggers, index)
- [x] Create `src/rcac_mcp/docs/database.py` with DocsDatabase class:
  - [x] `__init__(db_path, read_only=False)` — open/create connection
  - [x] `create_schema()` — execute schema.sql
  - [x] `upsert_document(path, title, category, content, source_hash)` — insert/update doc + chunks
  - [x] `remove_document(path)` — delete doc and cascading chunks
  - [x] `get_source_hash(path)` — for incremental checks
  - [x] `search(query, category=None, limit=20)` — FTS5 BM25-ranked search with snippet()
  - [x] `load_document(path)` — return full document content
  - [x] `stats()` — document/chunk counts
  - [x] `close()` — cleanup
- [x] Add `pyyaml` and `jinja2` to pyproject.toml dependencies
- [x] Verify schema works: quick smoke test creating an in-memory DB

### Phase 2: Markdown Parser and Indexer
- [x] Create `src/rcac_mcp/docs/indexer.py` with DocsIndexer class:
  - [x] `__init__(docs_repo_root)` — validate repo structure (main.py, mkdocs.yml, docs/)
  - [x] `_load_mkdocs_extra()` — parse mkdocs.yml, extract `extra:` vars
  - [x] `_load_macros()` — dynamically load main.py macro functions via define_env pattern
  - [x] `_resolve_snippets(content, base_path)` — expand all --8<-- directives
  - [x] `_render_jinja2(content, frontmatter)` — render templates with full context
  - [x] `_parse_frontmatter(raw)` — split YAML frontmatter from body, return (metadata, body)
  - [x] `_extract_title(metadata, body)` — from frontmatter title, first # heading, or filename
  - [x] `_derive_category(rel_path)` — from top-level directory path
  - [x] `_chunk_by_h2(content)` — split on ## boundaries, return list of (heading, content) tuples
  - [x] `_should_skip(rel_path)` — skip snippets/, assets/, stylesheets/, empty files
  - [x] `build(db_path)` — main entry point: walk, parse, resolve, chunk, upsert, prune stale docs
- [x] Test snippet resolution against real RCAC-Docs files (running_jobs_python.md, etc.)
- [x] Test Jinja2 rendering against docs with {{ resource }}, {{ cluster }}, macro calls

### Phase 3: MCP Tools
- [x] Create `src/rcac_mcp/tools/docs.py`:
  - [x] `doc_search(query, category=None)` — FTS5 search, return formatted ranked results
  - [x] `doc_load(path)` — return full document markdown by relative path
  - [x] Handle missing docs.db gracefully (return helpful message)
  - [x] Module-level DB path resolution (RCAC_DOCS_DB env var → ~/.config/rcac-mcp/docs.db)
- [x] Register docs tool module in `src/rcac_mcp/tools/__init__.py`
- [x] Verify tools appear in TOOL_REGISTRY when imported

### Phase 4: CLI Integration
- [ ] Add `--index-docs` flag to MCPServerApp
- [ ] Add `--docs-path` argument to MCPServerApp
- [ ] Add `--docs-output` argument with default `~/.config/rcac-mcp/docs.db`
- [ ] Implement index-docs flow in MCPServerApp.run(): detect flag, run indexer, print summary, exit
- [ ] Create ~/.config/rcac-mcp/ directory if it doesn't exist
- [ ] Test: `rcac-mcp --index-docs --docs-path ../RCAC-Docs`

### Phase 5: Server Instructions and Agent Guidance
- [ ] Update SERVER_INSTRUCTIONS in server.py with doc search tool descriptions
- [ ] Add agent guidance: "Before advising on storage, jobs, or software, use doc_search"
- [ ] Update APP_HELP with --index-docs documentation
- [ ] Review INSTRUCTIONS.md for consistency with new capabilities

### Phase 6: Validation and Polish
- [ ] Run full index build against RCAC-Docs repo, verify document/chunk counts
- [ ] Test doc_search with representative queries (scratch purge, conda vs anaconda, GPU jobs, etc.)
- [ ] Test doc_load with various document paths
- [ ] Test incremental update (re-run indexer, verify skipped unchanged files)
- [ ] Test stale document removal (delete a doc, re-run indexer)
- [ ] Verify server starts cleanly with and without docs.db present
- [ ] Run any existing tests (pytest), ensure nothing is broken
- [ ] Final review of all new code for consistency with project patterns

---

## Bootstrap Prompt

Use the following prompt to resume work on this feature in a new session:

````
We are implementing a documentation search index feature for the rcac-mcp
project. The implementation plan is at <plan: bb88ff3d-7742-44f5-bfbb-6cece6050034>
and the project roadmap is at ROADMAP.md in the project root.

Please:
1. Read the plan and ROADMAP.md to re-establish full context.
2. Check the YAML frontmatter `current_phase` to find where we left off.
3. Review the checkbox state in the current phase to find the next incomplete task.
4. Implement the sub-tasks for that step.
5. Review your work — verify the code compiles/runs and follows project patterns.
6. Update ROADMAP.md — check off completed items, bump `current_phase` and
   `last_updated` in frontmatter if the phase is done.
7. Commit with `WIP: <descriptive message>` and push to the `wip` branch.
8. Check back in with me to see if we want to proceed to next phase or stop.
````
