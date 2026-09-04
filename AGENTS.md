# AGENTS.md

Guidance for AI agents (and humans) working in this repository. `CLAUDE.md` is
a symlink to this file — edit `AGENTS.md`, never a separate copy. (`.claude` is
likewise a symlink to `.agents`, so Claude Code finds the factory skills and
settings through it.)

This is the operating manual: the architecture, the load-bearing invariants,
and the process rules an agent needs to make correct changes here without
rediscovering them. When something below disagrees with the code, **the code is
ground truth — fix this file.**

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
executors). **All of that was removed.** Cluster operations are out of scope
and will live in a separate, pluggable `hpc-mcp` project. This repo is
documentation search **only**. The refactor that made it so is complete; its
retained record is [`spec/docs-only-refactor/`](spec/docs-only-refactor/).

The server is small, finished, and **deployed**. Its failure modes are quiet:
a malformed query returns an error an agent cannot act on, a torn index breaks
live readers mid-query, and a stale sentence in `SERVER_INSTRUCTIONS` is a system
prompt handed to every downstream client on every call. None of it produces a
stack trace anyone will see. Prefer deleting to adding.

## Architecture

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
parse YAML frontmatter → **render Jinja2 macros/templates** (from the docs
repo's `main.py` + `mkdocs.yml` `extra:`) → **then resolve pymdownx `--8<--`
snippet includes**, verbatim and never re-rendered → strip the `<!-- more -->`
blog marker → chunk on `##` (H2) boundaries → upsert into SQLite with SHA-256
incremental hashing and stale-doc pruning.

That order is load-bearing and easy to get backwards. It mirrors MkDocs, where
`mkdocs-macros` renders templates and `pymdownx.snippets` includes files later
during conversion. Snippet text contains brace sequences that are not
templates, so handing it to the Jinja parser is a crash.

**Search** (`index/database.py`): FTS5 virtual table with BM25 ranking and
`snippet()` highlighting; category filtering is a path-prefix match. The
tokenizer is `porter unicode61 remove_diacritics 1`, so `gpu` and `gpus`
already match and advising callers to add prefix wildcards is wrong.

**Publication** (`index/indexer.py`): a rebuild seeds `<db>.tmp` from the live
index with `VACUUM INTO`, builds into it, and swaps with `os.replace`. The
deployed pod shares one PVC between the indexer and the readers, so an
in-place write is a live outage.

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

## Where work is recorded (load-bearing)

`AGENTS.md` is the constitution. Everything else has one home, and the
boundaries are not a matter of taste:

| File | Holds | Written by |
|------|-------|------------|
| `spec/{slug}/` | work **actually in flight**, and the retained record after it lands | the lifecycle skills |
| `spec/{slug}/TECH.md` | the **resume ground truth** — an FSM in YAML frontmatter, mutated only by `.agents/factory/bin/set_phase.py` | `proj-plan`, then `proj-build` |
| `spec/{slug}/META.md` | **harness/skill feedback only** — "was this the *factory's* fault". Never code follow-ups. | the lifecycle skills |
| `issues/{slug}.md` | **deferred code work**, pre-shaped from `.agents/factory/templates/ISSUE.md` | whoever defers it |
| `ROADMAP.md` | the **ordered index** — one entry per issue, `**Seed:**` pointing at the file | whoever defers it |
| `.security/issues/{slug}.md` + `.security/ROADMAP.md` | the same two, for **unremediated security findings** — gitignored, never published | whoever defers it |

An `issues/{slug}.md` is a *candidate, not a contract*. `/proj-feature`
promotes it into a `GOAL.md`, and that promotion is where appetite, non-goals
and the R-IDs get negotiated with a human. Never copy one into a `GOAL.md`
verbatim.

**A deferral is retired, not kept forever.** When the cycle that adopted a seed
lands on `main`, `/proj-roadmap` deletes the seed and its `ROADMAP.md` entry:
`spec/{slug}/` is the retained account and git history holds the file.

**The security lane is not optional.** A deferral describing an unremediated
weakness goes in `.security/`, which is gitignored. This server is
unauthenticated and on the public internet; a public roadmap of live
vulnerabilities is an attacker's work plan. The *fixes* land as ordinary public
commits when they ship — only the standing inventory stays private. When in
doubt which lane, use `.security/` and ask.

## Invariants

The curated, enumerated form is
[`.agents/factory/invariants.md`](.agents/factory/invariants.md), kept **in
lockstep with this file** — if the two drift, this file wins; if this file and
the code drift, the code wins and both get fixed. `/proj-review` grades against
it, so a section left asserting a decision a change reversed turns correct code
into an auto-CRITICAL finding. Summarized:

**Exactly two tools**, `doc_search(query, category=None)` and `doc_load(path)`,
both returning a string and never raising — an exception reaches the caller as
a tool failure it cannot act on. Renaming or re-signaturing one is a contract
change: every downstream agent holds `SERVER_INSTRUCTIONS` as a system prompt, and
a rename does not fail loudly, it just stops being called.

**Read-only and unauthenticated.** `doc_load` resolves its argument through the
database, not the filesystem, so there is no path-traversal surface today. That
is the property to preserve.

**The site is one directory.** `<site>/repo` and `<site>/index.db`, resolved
explicit → `$RCAC_DOCS_SITE` → XDG default. There is deliberately no second
override for the index path.

**The index is published atomically** and rebuilt incrementally by SHA-256,
with stale documents pruned through the FTS triggers.

**The render pipeline order is Jinja2 before snippets** (see *Architecture*),
and `mkdocs.yml` is parsed with a loader tolerant of `!ENV`, `!relative` and
`!!python/name:` tags.

**Every normalized query is valid FTS5**, for every input. A malformed
caller-written expression is reported, not raised.

**Two transports**, `stdio` and `http`. `sse` and all auth modes were removed
deliberately.

**The container entrypoint** runs `--update-site` → `--index` → serve under
`set -eu`, so a failed update or index means the pod never becomes ready.
`git` is a runtime dependency and `uv.lock` must stay tracked.

## High-risk files

A confirmed defect in any of these forces a human sign-off gate at review:
`index/indexer.py`, `index/database.py`, `index/schema.sql`, `tools.py`,
`site.py`, `Dockerfile`, `docker-entrypoint.sh`, and
`.github/workflows/build-and-push.yml` — the last because a merge to `main` is
a deploy, and that file decides what reaches production and when.

## Working on this codebase as an agent

**Use the factory for non-trivial work.** A feature, fix or refactor flows
through the `.agents/` lifecycle, each stage on a branch with artifacts
committed under `spec/{slug}/`:

**`/proj-feature`** (shape `GOAL.md`, or promote an `issues/{slug}.md`) →
**`/proj-plan`** (research + `PLAN.md`/`TECH.md`) → **`/proj-build`** (execute
one phase, verify, commit, stop) → **`/proj-review`** (blind, externally
verified QA) → **`/proj-publish`** (squash PR to `main`).

[`.agents/factory/methodology.md`](.agents/factory/methodology.md) is the
*why*; [`.agents/factory/invariants.md`](.agents/factory/invariants.md) is the
footgun checklist derived from this file. **Ceremony scales to appetite** — a
one-sentence change skips the lifecycle entirely.

Three operational siblings sit outside it: **`/proj-harness`** applies the
factory's own self-improvement findings back to `.agents/`, **`/proj-roadmap`**
retires the seeds whose cycles have landed and keeps `ROADMAP.md` true, and
**`/proj-release`** cuts a tagged version. `/proj-release` does **not** ship —
`/proj-publish` does, because a merge to `main` is the deploy.

**Verify by driving the server, not by reading it.** `uv run pytest -q` is
necessary and not sufficient: with the RCAC-Docs submodule absent it reports
`76 passed, 31 skipped` and still exits 0. Anything touching the indexer, the
tools, or the CLI goes through `.agents/factory/bin/temp_site.sh`, which builds
a throwaway site from the pinned fixture and exits 3 rather than reporting a
pass it cannot support.

**This file is the map, and it drifts.** For a deep change, re-verify the
specific invariant against the code before relying on it, and update this file
when the code moves.

## Branch posture and commits (Geoffrey's rules)

- **Branch off `main`.** Lifecycle work goes on `feature/{slug}`, `fix/{slug}`,
  `docs/{slug}` or `refactor/{slug}` and lands on `main` by squash. Harness
  work uses `harness/{slug}`. The prefix follows the cycle's `kind:`; the set
  is open, like the commit categories. There is no `wip` branch and no
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
  `SERVER_INSTRUCTIONS`.
- Bulleted lists where two sentences would do. Tables are for reference
  material; prose is for reasoning.
- Symmetry for its own sake — three parallel bullets where only two facts
  exist.

**Never embed feature-scoped spec ids** (`R1`, `P3`) in `src/rcac_docs_mcp/**` or
`README.md`. They restart per feature, live in
`spec/{slug}/`, and collide across branches. Requirement provenance lives in
the commit, the PR, and the retained `spec/{slug}/` record;
`git blame → commit → PR → spec/{slug}/` recovers it when you need it.
`.agents/factory/bin/lint.sh` enforces this. Referencing stable things is
fine: real function names, real environment variables, documented FTS5
behavior.

`SERVER_INSTRUCTIONS` is held as a system prompt by
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
