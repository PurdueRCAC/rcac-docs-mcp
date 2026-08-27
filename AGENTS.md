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
symlink; `CLAUDE.md -> AGENTS.md`).

> **Both are superseded and awaiting deletion.** They predate the `.agents/`
> factory and still assume the retired `wip` branch and `WIP: ` prefix, so
> where they disagree with *Branch posture and commits* above, that section
> wins. `/continue` is replaced by `/proj-build`, `/release` by
> `/proj-release`; the descriptions below stand only until those land.

- **`/continue`** — execute the next incomplete `ROADMAP.md` stage: run the
  checklist, update the tracker, land one `WIP:` commit, run the `pytest`
  gate. Conservative by default (one stage, then stop); supports
  `status` / `dry run` / `through N` / `next N` / `stages X..Y` / `bundle`.
- **`/release`** — ship `wip` to `main`: strip `WIP:` prefixes (scripted
  rebase), fast-forward merge, optionally bump `pyproject.toml` + tag + cut a
  GitHub release, then return to `wip` and force-push. The `pytest` suite is
  the ship gate.

## Branch posture and commits (Geoffrey's rules)

- **Branch off `main`.** Lifecycle work goes on `feature/{slug}` or
  `fix/{slug}` and lands on `main` by squash. There is no `wip` branch and no
  `WIP: ` prefix — both were retired when the factory landed. Never force-push
  `main`.
- **A merge to `main` is a deploy.** `.github/workflows/build-and-push.yml`
  fires on push, moves `ghcr.io/purduercac/rcac-docs-mcp:latest`, and the
  Geddes poller rolls the pod. Confirm the live endpoint, not just the CI run:
  the poller has taken over 26 minutes to reconcile, and a green build says
  nothing about what is being served.
- **Commit subjects are `[category] Imperative summary`.** Categories in use:
  `feature`, `fix`, `docs`, `refactor`, `release`, and `harness` (the
  `.agents/` factory). The set is not closed — coin a lowercase category when
  one genuinely fits.
- **Commit messages are short.** Subject at most 72 characters. A body is
  optional and earns its place the way a comment does: it records a decision,
  a rejected alternative, or a consequence the diff does not show. It never
  narrates the diff or lists the files touched. Two or three lines is a normal
  body; past about fifteen, the commit should have been two commits. The
  *Prose and comments* rules below apply here too.
- **No `Co-Authored-By:` trailer** of any kind.
- The user has aliased `rm` away — prefer `del` for file removals (and
  `git rm` for tracked files).

## Code conventions (Geoffrey's rules)

- **SPDX headers** on every source file:
  ```python
  # SPDX-FileCopyrightText: 2025 Purdue University
  # SPDX-License-Identifier: MIT
  ```
  The holder is `Purdue University`, which is what all 17 existing source
  files say and what `.agents/factory/bin/lint.sh` enforces. The year is not
  checked — a file added later is correct as it stands.
- **Structured import blocks** with section labels, in order: type
  annotations (`from __future__ import annotations`), `# Standard libs`,
  `# External libs`, `# Internal libs`, then `# Public interface` with
  `__all__`.
- Double blank lines between the module docstring and the first import, and
  between module-level definitions; a leading newline for multi-line
  docstrings.
- CLI tools follow the **CmdKit** layout (see `__init__.py`; cf. `hypershell`,
  `tts`).

## Prose and comments

The project's documentation, comments and commit messages have a voice. Keep
it. Overly verbose prose — the padding, hedging and marketing adjectives that
generated text tends toward — is a tic that costs a reader's confidence in
code that is otherwise correct. This server answers questions for other
agents and for the people who trust them; it has to be taken seriously to be
used. Match the existing voice.

**Write:**

- Declarative statements. `# Reserved id, exempt from gating.` — not
  `# This function will check...`.
- The **why**, not the what. The code says what it does. A comment earns its
  place by explaining a constraint, a failure mode, or a rejected alternative.
- Concrete failure modes. "`multi-node` became `multi-node*`, which SQLite
  rejects with `no such column: node`" beats "this could cause problems."
- Whole sentences with terminal punctuation, in the style already in the file.

**Do not write:**

- Filler and hedging: "simply", "just", "note that", "it's worth noting",
  "essentially", "basically".
- Marketing adjectives: "comprehensive", "robust", "seamless", "powerful",
  "elegant", "leverage", "utilize". If a property matters, state the
  measurement.
- "This ensures that…", "This allows us to…", "In order to…" — usually a
  sentence that has not decided what it is claiming.
- Restatements of the adjacent line. A comment that paraphrases the code is
  worse than none.
- Emoji, decorative Unicode, or exclamation marks in source, `README.md`, or
  `INSTRUCTIONS.md`.
- Bulleted lists where two sentences would do. Tables are for reference
  material; prose is for reasoning.
- Symmetry for its own sake — three parallel bullets where only two facts
  exist.

**Never embed feature-scoped spec ids** (`R1`, `P3`) in `src/rcac_docs_mcp/**`,
`README.md`, or `INSTRUCTIONS.md`. They restart per feature, live in
`spec/{slug}/`, and collide across branches. Requirement provenance lives in
the commit, the PR, and the retained `spec/{slug}/` record;
`git blame → commit → PR → spec/{slug}/` recovers it when you need it.
`.agents/factory/bin/lint.sh` enforces this. Referencing stable things is
fine: real function names, real environment variables, documented FTS5
behavior.

`INSTRUCTIONS.md` and `SERVER_INSTRUCTIONS` are held as a system prompt by
every downstream agent. Padding there is not a style question — it is tokens
spent on every single call, forever.

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
