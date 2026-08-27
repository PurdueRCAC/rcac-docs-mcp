# Invariants — the footgun checklist

The curated, enumerated form of `AGENTS.md` § *Invariants*, kept **in lockstep with it**. If the two
drift, `AGENTS.md` wins; if `AGENTS.md` and the code drift, **the code wins and both files get
fixed**. `proj-plan` checks a design against this list before and after drafting; `proj-review` grades
the diff against it.

**Severity.** A violation of §1–§11 is **auto-CRITICAL**. A §12 project-conventions violation is
**HIGH**, not CRITICAL — a convention nit must not block an otherwise correct cycle.

**High-blast-radius files.** A confirmed defect in any of these forces a human sign-off gate at
review, per [`review-rubric.md`](review-rubric.md):

| File | Why |
|---|---|
| `src/rcac_docs_mcp/index/indexer.py` | The render pipeline. Two shipped bugs already came from ordering and YAML tolerance. |
| `src/rcac_docs_mcp/index/database.py` | Index integrity and the atomic swap that protects live readers. |
| `src/rcac_docs_mcp/index/schema.sql` | FTS5 DDL and the triggers that keep the index in sync. |
| `src/rcac_docs_mcp/tools.py` | The entire public contract. Every downstream agent holds it. |
| `src/rcac_docs_mcp/site.py` | Resolves where the checkout and index live; a mistake writes into the wrong tree. |
| `Dockerfile`, `docker-entrypoint.sh` | What production actually runs. |
| `.github/workflows/build-and-push.yml` | A merge to `main` is a deploy; this file decides what reaches it and when. |

---

## §1 — The tool surface is exactly two tools

`doc_search(query, category=None)` and `doc_load(path)`. Adding, renaming, or re-signaturing one is a
contract change and needs an explicit `GOAL.md` criterion saying why two are not enough. Downstream
agents hold `INSTRUCTIONS.md` and `SERVER_INSTRUCTIONS` as a system prompt; a silent rename does not
fail loudly, it just stops being called.

Both return a **string**. A tool that raises surfaces to the caller as a tool failure it cannot act
on, costing an agent a whole research round. Error states are returned as readable text.

## §2 — Read-only, unauthenticated, and no filesystem surface

The server runs with no auth, hosted publicly at `docs.rcac.purdue.edu/mcp`. Both tools open the
index with `read_only=True`.

`doc_load(path)` resolves its argument through `db.load_document(path)` — a lookup key into the
index, **not a filesystem path**. There is therefore no path-traversal surface today, and that is the
property to preserve: no tool may read the filesystem from caller-supplied input, execute a
subprocess, or reach outside `<site>`. Reintroducing a filesystem read here reintroduces a class of
vulnerability this design currently does not have.

## §3 — The site is one container directory

`<site>/repo` holds the git checkout; `<site>/index.db` is the index. Resolution precedence, in
`site.py`, is explicit argument → `$RCAC_DOCS_SITE` → `$XDG_DATA_HOME/rcac-docs-mcp` →
`~/.local/share/rcac-docs-mcp`. The clone URL is explicit argument → `$RCAC_DOCS_URL` →
`https://github.com/PurdueRCAC/RCAC-Docs`.

There is **no separate override for the index path** — it is always derived from the site. The
earlier `RCAC_DOCS_DB` and `RCAC_DOCS_SITE_URL` variables were removed deliberately; do not
reintroduce a second way to say where the database is.

`update_site` clones when `<site>/repo/.git` is absent, otherwise runs
`git -C <repo> pull --rebase --autostash origin main`.

## §4 — The index is published atomically

A rebuild seeds a sibling `<db>.tmp` from the current index with `VACUUM INTO`, builds into the temp
file, and swaps it onto `db_path` with `os.replace`.

**Never write the live database in place.** In the deployed pod the indexer and the readers share one
PVC, so a torn write is a live outage for every agent mid-query. `os.replace` is atomic within a
filesystem, which is why the temp file is a sibling and not in `$TMPDIR`.

## §5 — Incremental hashing, and pruning that reaches the FTS rows

Each source document carries a SHA-256 of its raw text. The `VACUUM INTO` seed carries those hashes
into the temp database, which is what makes a no-op rebuild report `Indexed: 0 documents` with every
document `Skipped: unchanged`. A rebuild that reindexes everything has lost the seed.

Documents present in the index but absent from disk are pruned. Pruning must remove the `chunks` rows
too, so the FTS triggers clear `chunks_fts`; orphaned FTS rows return search hits for documents that
no longer exist.

## §6 — Render pipeline ordering (load-bearing; the source of two shipped bugs)

Per document: parse frontmatter → **render Jinja2 macros/templates** → **then resolve `--8<--`
snippet includes** → strip the `<!-- more -->` blog marker → chunk on `##` (H2).

**Jinja2 runs before snippets, not after.** This mirrors MkDocs, where `mkdocs-macros` renders
templates and `pymdownx.snippets` includes files later during conversion. Included snippet text is
inserted **verbatim and never re-rendered**, because snippets contain brace sequences that are not
templates and handing them to the Jinja parser is a crash. Reversing this order is the bug commit
`4cd09fe` fixed.

`mkdocs.yml` is read with a permissive `SafeLoader` subclass that tolerates MkDocs' `!ENV` and
`!relative` tags and `!!python/name:` (the emoji extensions). A plain `safe_load` raises on the
upstream config — the bug commit `9717172` fixed. Macro definitions and `extra:` values come from the
docs repo's own `main.py` and `mkdocs.yml`, so **upstream can drift**: the fixture is a pinned
submodule and is not evidence about today's upstream.

## §7 — Every normalized query is valid FTS5

Every string `_normalize_query` emits must be syntactically valid FTS5, for every input — including
punctuation-only, hyphenated, and operator-laden ones. Terms are cut on non-word characters, so
punctuation never rides into a term and collects a wildcard: `multi-node` must not become
`multi-node*`, which SQLite rejects with `no such column: node`.

Standalone single-character words are kept and emitted **unwildcarded** — `R` and `C` name real
software here, and a one-character prefix matches most of the index.

Normalization deliberately leaves operator queries alone, so a caller can still hand the engine
something it rejects. That is **reported** to the caller, never raised. Guarded by
`test_every_normalized_query_is_valid_fts5`.

## §8 — Search semantics

BM25 ranking with column weights `bm25(chunks_fts, 10.0, 5.0, 1.0)` and `snippet()` highlighting with
`>>>`/`<<<` delimiters. The category filter is a **prefix match** (`d.category LIKE ? || '%'`), not an
exact match, so `userguides` matches `userguides/gautschi`.

The FTS5 table is `tokenize='porter unicode61 remove_diacritics 1'`. Porter stemming is why `gpu` and
`gpus` already match and why advising callers to add prefix wildcards is wrong. The `chunks_ai`,
`chunks_ad` and `chunks_au` triggers keep `chunks_fts` in sync with `chunks`; a write path that
bypasses them silently desynchronizes the index. Schema changes are additive or come with a full
rebuild.

## §9 — Two transports

`stdio` and `http` only. `sse` and every auth mode were removed deliberately in the docs-only
refactor and are not to be reintroduced. See `spec/docs-only-refactor/` for that decision record.

## §10 — The container and deploy contract

`docker-entrypoint.sh` runs under `set -eu` and executes `--update-site` → `--index` → serve, so a
failed update or a failed index means the pod never becomes ready. That is deliberate: serving a
stale or absent index silently is worse than not starting.

`git` and `ca-certificates` are genuine **runtime** dependencies, not build-only — `--update-site`
shells out to `git` on every pod start.

`uv.lock` must stay **tracked**. The Dockerfile bind-mounts it for the cached `uv sync --frozen`
layer, and gitignoring it broke CI once already (fixed in `db6dd83`). Any build-context file the
Dockerfile mounts must be committed.

`provenance: false` in the workflow keeps `:latest` a plain single-arch manifest, which is what the
Geddes digest poller expects. Tags are `latest` plus `sha-<short>`.

**A push to `main` is a deploy.** The poller has taken over 26 minutes to reconcile, so a green CI run
is not evidence the fix is live — probe the endpoint.

## §11 — Test-fixture posture, and the false green it creates

Integration tests skip cleanly when `tests/fixtures/RCAC-Docs` is uninitialized. With the submodule
absent the suite reports **76 passed, 31 skipped** and exits **0**.

**Twenty-nine percent of the suite can vanish without changing the exit status.** A `verify:` gate,
a review, or a release gate that reads only the exit code cannot tell a real pass from a hollow one.
Assert the counts, or drive through `.agents/factory/bin/temp_site.sh`, which exits 3 rather than
reporting a pass it cannot support.

`tests/test_cli.py`, `tests/test_indexer.py` and `tests/test_tools.py` use a bare
`from conftest import requires_submodule`, which resolves only through pytest's default rootdir
`sys.path` insertion. **Do not set `importmode = "importlib"`** — it breaks all three.

The Python floor is 3.14 and `uv` is the dependency manager.

## §12 — Project conventions *(violations are HIGH, not CRITICAL)*

- **SPDX two-line header** on every source file: `# SPDX-FileCopyrightText: <year> Purdue University`
  and `# SPDX-License-Identifier: MIT`. The holder is `Purdue University`; the year is not checked.
- **Structured import blocks** in order: `from __future__ import annotations`, `# Standard libs`,
  `# External libs`, `# Internal libs`, then `# Public interface` with `__all__`.
- Double blank lines between module-level definitions; a leading newline for multi-line docstrings.
- CLI follows the **CmdKit** layout.
- **The same-commit rule.** A change to the tool surface, the environment contract
  (`RCAC_DOCS_SITE`, `RCAC_DOCS_URL`, `HOST`, `PORT`), the CLI flags, or the site layout updates
  whichever of these it invalidates, **in the same commit**: `README.md`, `INSTRUCTIONS.md`,
  `AGENTS.md`, `APP_HELP` in `__init__.py`, and `SERVER_INSTRUCTIONS` in `server.py`. Five places
  state the same contract, and `INSTRUCTIONS.md` is what ships to every downstream agent.
- **No `Co-Authored-By:` trailer.** `del`, not `rm` (`git rm` for tracked files).
- **No feature-scoped spec ids** (`R1`, `P3`) in `src/rcac_docs_mcp/**`, `README.md`, or
  `INSTRUCTIONS.md`. `lint.sh` enforces this.
- **Prose and comment voice** per `AGENTS.md` § *Prose and comments*.

An edit to *this file* sits inside the graded diff, so it revises the standard and is judged on its
merits — never read as license for the change shipping beside it. A change that **overturns** an
invariant updates `AGENTS.md` § *Invariants* and this file in the same commit; leaving a section
asserting the decision a change reversed turns correct code into an auto-CRITICAL finding.
Overturning one is a design decision: it belongs in the plan's deviation table and in front of a
human, never in the diff alone.
