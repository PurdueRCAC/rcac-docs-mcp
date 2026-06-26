---
project: rcac-docs-mcp
feature: docs-only-refactor
plan_id: 90ac50ab-77f6-4a6e-811c-21b42630de21
branch: wip
current_stage: 6
stages_completed:
  - "0"
  - "1"
  - "2"
  - "3"
  - "4"
  - "5"
last_updated: "2026-06-26"
decisions:
  rename: full            # rcac_mcp -> rcac_docs_mcp; rcac-mcp -> rcac-docs-mcp
  indexer_subpackage: index/   # was docs/
  tools_layout: single-tools.py   # collapse tools/ package
  auth: none             # strip JWT/OIDC; straight FastMCP
  transports:            # drop sse
    - stdio
    - http
  site_layout: single-container       # <site>/ holds repo/ and index.db
  cli_actions: [--index, --site, --update-site]   # dropped --index-docs/--docs-path/--docs-output
  site_default: "~/.local/share/rcac-docs-mcp"    # container; repo at <site>/repo
  site_env_override: RCAC_DOCS_SITE
  db_default: "<site>/index.db"       # derived from site; no separate override
  docs_site_url: "https://github.com/PurdueRCAC/RCAC-Docs"
  docs_site_url_env_override: RCAC_DOCS_URL
  site_update: clone-or-pull   # --update-site clones fresh or git pull --rebase
  hosted_at: "docs.rcac.purdue.edu/mcp"
deps_removed:
  - pyjwt
  - fabric
  - pytest-asyncio   # dev; no async tests
deps_kept:
  - fastmcp
  - cmdkit
  - pyyaml
  - jinja2
non_importable_window: "stage1..stage3"   # expected red pytest; green again stage 4+
---

# ROADMAP: RCAC-Docs MCP Refactor

## Overview

Separate the documentation-search capability out of the forked `rcac-mcp`
codebase into a focused, **no-auth** `rcac-docs-mcp` service hosted at
`docs.rcac.purdue.edu/mcp`. Strip every HPC cluster operation (Slurm, SFTP,
LMOD/env), all authentication (JWT/OIDC), and the container/TLS
infrastructure; keep only the docs indexer and the `doc_search` / `doc_load`
tools. Restructure so the indexer lives in an `index/` subpackage and the two
tools live in a single `tools.py`, rename the package/distribution, and add a
CLI step that clones or updates the local RCAC-Docs checkout before indexing.

This file is the **resume ground truth**. The *why* lives in the
implementation plan (`plan_id` above); this tracker holds the *what* and the
*progress*. See `AGENTS.md` for orientation.

## How to use this tracker

- Work happens on `wip`, one stage at a time, each landing a `WIP:` commit.
- Drive it with the **`/continue`** skill (`.agents/skills/continue`); ship
  with **`/release`** (`.agents/skills/release`).
- When a stage's items are all `[x]`, bump `current_stage` and append the
  stage number to `stages_completed`.
- **Expected mid-refactor breakage:** the package is intentionally
  non-importable from the start of Stage 1 through the end of Stage 3
  (deletions precede the rewire). A red `pytest` in that window is expected;
  it goes green again at Stage 4.

## Naming & layout target

```
src/rcac_docs_mcp/
  __init__.py     # CmdKit CLI: serve (stdio|http) | --update-site | --index
  __main__.py
  server.py       # create_mcp_server(): FastMCP, no auth, docs-only instructions
  tools.py        # mcp_tool + TOOL_REGISTRY + doc_search + doc_load
  site.py         # clone/update the local RCAC-Docs checkout (git via subprocess)
  index/
    __init__.py   # re-exports DocsDatabase, DocsIndexer
    database.py
    indexer.py
    schema.sql
  static/purdue-favicon.ico
```

---

## Stage 0 — Governance & execution harness

Additive only; package stays importable. Committed before any pruning.

- [x] Add `.agents/skills/release/SKILL.md` (`/release`, adapted to uv/pytest)
- [x] Add `.agents/skills/continue/SKILL.md` (`/continue`, stage-based executor)
- [x] Add convention symlinks `.claude -> .agents` and `CLAUDE.md -> AGENTS.md`
- [x] Author clean root `AGENTS.md` for the docs-only service
- [x] Overwrite `ROADMAP.md` with this staged tracker (frontmatter + checklists)

## Stage 1 — Prune dead code, infra, and dependencies

Starts the non-importable window.

- [x] Delete cluster/auth modules: `auth.py`, `token.py`, `middleware.py`,
      `context.py`, `resources.py`
- [x] Delete the `executor/` package (`base.py`, `delegate.py`, `shell.py`,
      `ssh.py`, `__init__.py`)
- [x] Delete cluster tool modules: `tools/{shell,filesystem,transfer,rcac,slurm}.py`
- [x] `git rm` infra: `Dockerfile`, `compose.yml`, `nginx-dev.conf`, `SECURITY.md`
- [x] Remove untracked `.env` and `certs/` from disk (use `del`)
- [x] `pyproject.toml`: drop `pyjwt`, `fabric`, and dev `pytest-asyncio`

## Stage 2 — Restructure & rename package

- [x] Rename `src/rcac_mcp/` → `src/rcac_docs_mcp/` (`git mv`)
- [x] Rename `docs/` subpackage → `index/`
- [x] Collapse `tools/` package into a single `tools.py` (move `mcp_tool` +
      `TOOL_REGISTRY` from old `tools/__init__.py` alongside the tools)
- [x] Update internal imports in kept modules to `rcac_docs_mcp.*`
- [x] `index/__init__.py` re-exports `DocsDatabase`, `DocsIndexer`
- [x] `DEFAULT_DB_PATH` → `~/.config/rcac-docs-mcp/docs.db` (later removed in
      Stage 4 in favor of the site-derived `<site>/index.db`)
- [x] `pyproject.toml`: rename `name`, `[project.scripts]`, and the hatchling
      wheel `packages` entry to `rcac-docs-mcp` / `src/rcac_docs_mcp`

## Stage 3 — Rewire server & CLI (docs-only, no auth) + site management

- [x] `server.py`: drop `AUTH_MODES` / `RESOURCE_REGISTRY` imports and the
      auth/resource/middleware wiring; `create_mcp_server()` takes no args
- [x] `server.py`: rewrite `SERVER_INSTRUCTIONS` to docs-only; server name
      `RCAC Docs`; keep the favicon custom route
- [x] `__init__.py`: remove token/auth/exec-mode/ssh CLI args, the `sse`
      transport, and the executor/middleware/token code paths
- [x] `__init__.py`: `--index-docs` / `--docs-path` / `--docs-output`;
      `run()` becomes index-or-serve over stdio/http (flags reworked in Stage 4
      — see the design-revision note there)
- [x] `__init__.py`: `__version__ = get_version('rcac-docs-mcp')`; update
      `APP_NAME`, usage/help, website, description
- [x] `__main__.py`: import from `rcac_docs_mcp`
- [x] Add `site.py`: resolve checkout from `--docs-site` / `RCAC_DOCS_SITE` /
      default; clone if missing else `git -C <site> pull --rebase --autostash
      origin main`; upstream from `RCAC_DOCS_SITE_URL` / default (git via
      `subprocess`, no new Python deps) — restructured to the single-container
      model in Stage 4
- [x] CLI: add `--update-site` (clone/update then exit); default `--docs-path`
      to the resolved site checkout

## Stage 4 — Update tests (suite green again)

- [x] `conftest.py`, `test_database.py`, `test_indexer.py`, `test_tools.py`:
      `rcac_mcp.docs.*` → `rcac_docs_mcp.index.*`, `rcac_mcp.tools.docs` →
      `rcac_docs_mcp.tools`
- [x] `test_cli.py`: `python -m rcac_mcp` → `python -m rcac_docs_mcp`
- [x] add a unit test for `site.py` path/URL/repo/db resolution (`test_site.py`)
- [x] `uv run pytest -q` collects and passes (submodule tests skip cleanly)

### Stage 4 design revision (Geoffrey) — consolidate the CLI/site model

The app is docs-only, so the redundant `docs` prefixes and the separate
repo/db flags were dropped. A *site* is now one container directory holding
the docs checkout and the index. This revises the Stage 2/3 contract:

- [x] CLI: `--index-docs` → `--index`; `--docs-site` → `--site`; remove
      `--docs-path` / `--docs-output`
- [x] `--site` holds the repo at `<site>/repo` and the index at
      `<site>/index.db`; `--index` builds the latter from the former
- [x] drop `DEFAULT_DB_PATH` (was `~/.config/rcac-docs-mcp/docs.db`); the index
      path is derived from the site by `site.py`
- [x] env vars: `RCAC_DOCS_SITE` (container) + `RCAC_DOCS_URL`; remove
      `RCAC_DOCS_DB` and `RCAC_DOCS_SITE_URL`
- [x] `site.py`: add `resolve_repo_path` / `resolve_db_path` (+ `REPO_DIRNAME`
      / `DB_FILENAME`); `update_site` clones/updates `<site>/repo`
- [x] tests track the new model (`site_with_repo` fixture; `RCAC_DOCS_SITE`);
      `uv run pytest -q` → 90 passed

## Stage 5 — Documentation

- [x] Rewrite `README.md` for the docs-only, no-auth, hosted service
- [x] Trim `INSTRUCTIONS.md` to docs-search guidance only
- [x] Remove stale `certs/` / `.env` lines from `.gitignore`
- [x] Reconcile this `ROADMAP.md` with any deltas discovered during execution

> Delta folded in during Stage 5: `pyproject.toml` `description` still
> advertised HPC clusters/storage; updated it to the docs-only description so
> package metadata matches `__description__` in `__init__.py`.

## Stage 6 — Validation

- [ ] `uv lock` + `uv sync` so `rcac-docs-mcp` resolves for `importlib.metadata`
- [ ] `uv run pytest -q` green
- [ ] Smoke: `rcac-docs-mcp --help`
- [ ] Smoke: `rcac-docs-mcp --index --site <site>` (with `<site>/repo` →
      `tests/fixtures/RCAC-Docs`) writes `<site>/index.db`
- [ ] Confirm `schema.sql` resolves from the installed package (non-editable)
- [ ] Confirm the server starts over stdio with no `index.db` present (graceful)

---

## Verification gate

```bash
uv sync --quiet
uv run pytest -q
```

- **Stages 1–3:** import/collection failure is **expected** (non-importable
  window) — record and proceed.
- **Stage 4+:** the suite must collect and pass; submodule-dependent tests
  skip cleanly when `tests/fixtures/RCAC-Docs` is not initialized.
- **Stage 6:** also run the CLI smoke tests listed above.

## Resume / bootstrap prompt

```
We are refactoring the rcac-docs-mcp project: isolating the docs-only MCP
service out of the forked rcac-mcp server. The implementation plan is at
<plan: 90ac50ab-77f6-4a6e-811c-21b42630de21> and the tracker is ROADMAP.md.

Please:
1. Read AGENTS.md, then ROADMAP.md, then the plan, to re-establish context.
2. Check ROADMAP.md frontmatter `current_stage` for where we left off.
3. Run `/continue` (one stage, then stop) — or `/continue status` for a
   read-only summary first.
4. Honor the non-importable window (Stages 1–3): a red pytest there is
   expected, not a regression.
5. After the stage: check off items, bump `current_stage` / `stages_completed`
   / `last_updated`, land one `WIP:` commit (Oz co-author), and report.
```
