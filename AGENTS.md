# AGENTS.md

Guidance for AI agents (and humans) working in this repository. Read this
first, then the active implementation plan and `ROADMAP.md`. Keep this file
current as the project evolves.

## What this repo is

**`rcac-docs-mcp`** — a single-purpose [FastMCP](https://gofastmcp.com)
server that exposes Purdue RCAC's documentation to AI agents via full-text
search. It is intended to run **unauthenticated**, hosted at
`docs.rcac.purdue.edu/mcp`.

The server provides exactly two tools:
- `doc_search(query, category=None)` — FTS5 / BM25 full-text search over the
  indexed RCAC documentation (user guides, software catalog, datasets, blog
  posts, workshops).
- `doc_load(path)` — return the full rendered markdown of one document by its
  relative path.

This project began as a fork of the broader `rcac-mcp` server (HPC cluster
operations: Slurm, SFTP, LMOD, plus JWT/OIDC auth and SSH/delegate
executors). **All of that is being stripped out here.** Cluster operations
are out of scope and will live in a separate, pluggable `hpc-mcp` project.
This repo is documentation search **only**.

## Current state (keep this accurate)

The repo is mid-refactor on the `wip` branch. The work is tracked stage by
stage in `ROADMAP.md` and detailed in the linked implementation plan
(`plan_id` in the ROADMAP frontmatter).

- **Naming:** migrating from package `rcac_mcp` / distribution `rcac-mcp` to
  package `rcac_docs_mcp` / distribution + script `rcac-docs-mcp`. Until the
  rename stage lands, the importable package is still `rcac_mcp`.
- **Layout target:** the indexer (database + markdown pipeline + schema)
  moves into an `index/` subpackage; the two MCP tools and the tool-registry
  machinery collapse into a single top-level `tools.py`.
- **Transports:** `stdio` (local clients) and `http` (hosted). `sse` and all
  auth modes are being removed.
- **Expected mid-refactor breakage:** the package is intentionally
  **non-importable between Stage 1 and the end of Stage 3** (deletions
  precede the rewire). A red `pytest` during that window is expected and
  documented — it is green again from Stage 4 on. See `ROADMAP.md`.

## Architecture (target)

```
src/rcac_docs_mcp/
  __init__.py     # CmdKit CLI: serve (stdio|http) OR --update-site OR --index
  __main__.py     # python -m rcac_docs_mcp
  server.py       # create_mcp_server(): FastMCP, no auth, docs-only instructions
  tools.py        # mcp_tool + TOOL_REGISTRY + doc_search + doc_load
  site.py         # resolve/clone/update the site (repo + index); git via subprocess
  index/
    __init__.py   # re-exports DocsDatabase, DocsIndexer
    database.py   # SQLite FTS5 DocsDatabase (schema, upsert, search, load, stats)
    indexer.py    # DocsIndexer: walk docs, resolve snippets + Jinja2, H2-chunk, upsert
    schema.sql    # FTS5 DDL (documents, chunks, chunks_fts, triggers)
  static/purdue-favicon.ico
```

**Indexing pipeline** (`index/indexer.py`): walk the RCAC-Docs `docs/` tree →
parse YAML frontmatter → resolve pymdownx `--8<--` snippet includes → render
Jinja2 macros/templates (from the docs repo's `main.py` + `mkdocs.yml`
`extra:`) → strip the `<!-- more -->` blog marker → chunk on `##` (H2)
boundaries → upsert into SQLite with SHA-256 incremental hashing and stale-doc
pruning.

**Search** (`index/database.py`): FTS5 virtual table with BM25 ranking and
`snippet()` highlighting; category filtering is a path-prefix match.

## Data locations & environment variables

A **site** is a single container directory that holds both the local checkout
of the RCAC-Docs repo (`https://github.com/PurdueRCAC/RCAC-Docs`) under
`repo/` and the built SQLite index as `index.db`. The CLI can clone that repo
fresh or update it (`git pull --rebase`) before indexing, and `--index`
writes the index alongside it.

- `RCAC_DOCS_SITE` — path to the local site container. Default:
  `~/.local/share/rcac-docs-mcp`. The docs checkout lives at `<site>/repo`
  and the search index at `<site>/index.db`.
- `RCAC_DOCS_URL` — upstream clone URL. Default:
  `https://github.com/PurdueRCAC/RCAC-Docs`.

Typical operator flow:
```bash
rcac-docs-mcp --update-site      # clone or git-pull <site>/repo
rcac-docs-mcp --index            # build/refresh <site>/index.db from <site>/repo
rcac-docs-mcp -t http -H 0.0.0.0 # serve (hosted); default transport is stdio
```
`--site PATH` overrides the container location (otherwise `$RCAC_DOCS_SITE`
or the default); the repo source and index output are always derived from it
(`<site>/repo` and `<site>/index.db`).

## Document split (load-bearing)

- **The implementation plan** (Warp plan, `plan_id` in ROADMAP frontmatter) —
  *rationale and design*: why each refactor stage exists and what it changes.
- **`ROADMAP.md`** — *execution tracker*: YAML frontmatter (`current_stage`,
  `stages_completed`, decisions) plus a checklist per stage. This is the
  **resume ground truth**.
- **`AGENTS.md`** — *orientation*: this file. What the repo is and how to work
  in it.

If `ROADMAP.md` and the plan disagree on what a stage entails, surface the
discrepancy rather than silently following one. Record progress only in
`ROADMAP.md`.

## Workflow skills

Two skills under `.agents/skills/` drive the repo (mirrored to `.claude/` via
symlink; `CLAUDE.md -> AGENTS.md`):

- **`/continue`** — execute the next incomplete `ROADMAP.md` stage: run the
  checklist, update the tracker, land one `WIP:` commit, run the `pytest`
  gate. Conservative by default (one stage, then stop); supports
  `status` / `dry run` / `through N` / `next N` / `stages X..Y` / `bundle`.
- **`/release`** — ship `wip` to `main`: strip `WIP:` prefixes (scripted
  rebase), fast-forward merge, optionally bump `pyproject.toml` + tag + cut a
  GitHub release, then return to `wip` and force-push. The `pytest` suite is
  the ship gate.

## Branch posture and commits (Geoffrey's rules)

- **Work on `wip`.** Commit often with **`WIP: `**-prefixed messages and
  descriptive bodies. `wip` is the only branch where force-push is allowed.
- Never commit to `main` directly from feature work; never force-push `main`.
- The intent: collapse `WIP:` commits into clean logical commits later
  (`/release`), fast-forward into `main`, then open a PR.
- **Co-author trailer on every commit:** a trailing
  `Co-Authored-By: Oz <oz-agent@warp.dev>` line.
- The user has aliased `rm` away — prefer `del` for file removals (and
  `git rm` for tracked files).

## Code conventions (Geoffrey's rules)

- **SPDX headers** on every source file:
  ```python
  # SPDX-FileCopyrightText: 2025 Purdue RCAC
  # SPDX-License-Identifier: MIT
  ```
- **Structured import blocks** with section labels, in order: type
  annotations (`from __future__ import annotations`), `# Standard libs`,
  `# External libs`, `# Internal libs`, then `# Public interface` with
  `__all__`.
- Double blank lines between the module docstring and the first import, and
  between module-level definitions; a leading newline for multi-line
  docstrings.
- CLI tools follow the **CmdKit** layout (see `__init__.py`; cf. `hypershell`,
  `tts`).

## Testing

```bash
uv sync
uv run pytest -q
```
Tests live in `tests/` (`test_database.py`, `test_indexer.py`,
`test_tools.py`, `test_cli.py`, `test_site.py`). Many integration tests
depend on the **RCAC-Docs git submodule** fixture at `tests/fixtures/RCAC-Docs`;
when it is not initialized those tests **skip cleanly**. To run them:
```bash
git submodule update --init tests/fixtures/RCAC-Docs
```

> Note: `tests/fixtures/RCAC-Docs/WARP.md` belongs to the **upstream RCAC-Docs
> repo** (it documents that MkDocs site, not this server). Do not rename or
> edit it from this project — it is the submodule's own file.

## Reference materials

- FastMCP — https://gofastmcp.com
- RCAC-Docs site repo — https://github.com/PurdueRCAC/RCAC-Docs
- CmdKit (CLI layout) — https://cmdkit.readthedocs.io
- Sibling tools for CLI/style prior art: `../../glentner/hypershell`,
  `../../glentner/tts`.
