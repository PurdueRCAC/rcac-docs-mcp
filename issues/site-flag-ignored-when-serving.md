---
status: unshaped
kind: fix
appetite: small
lane: public
---

# `--site` is honored when indexing and ignored when serving

## Problem

`rcac-docs-mcp --index --site PATH` builds the index at `PATH/index.db`, but
`rcac-docs-mcp --transport http --site PATH` serves from
`$RCAC_DOCS_SITE`, or from `~/.local/share/rcac-docs-mcp` when that is unset.
The flag is silently ignored on the path where it matters most.

`src/rcac_docs_mcp/__init__.py` threads `self.site` into `update_site(self.site)`,
`resolve_repo_path(self.site)` and `resolve_db_path(self.site)` for the
`--update-site` and `--index` actions. The serving action calls
`create_mcp_server()`, which takes no arguments, and
`src/rcac_docs_mcp/tools.py::_get_db_path()` calls `resolve_db_path()` with no
argument. Nothing exports `RCAC_DOCS_SITE` from the flag, so the two halves of
the CLI disagree about where the site is.

Reproduced against a temporary site:

```
$ env -u RCAC_DOCS_SITE uv run rcac-docs-mcp --index --site "$A"   # writes $A/index.db
$ env -u RCAC_DOCS_SITE uv run python -c \
    "from rcac_docs_mcp.tools import _get_db_path; print(_get_db_path())"
/Users/…/.local/share/rcac-docs-mcp/index.db
```

The failure is quiet in the worst way. With no default-site index present the
server answers every query with "Documentation index is not available", pointing
the operator at the `--index` command they just ran successfully. With a stale
default-site index present it serves stale results and reports nothing at all.

**Production is not affected.** `docker-entrypoint.sh` never passes `--site`; the
container relies on `RCAC_DOCS_SITE`, which both halves honor. This bites an
operator running two sites on one host, or anyone testing a rebuilt index before
promoting it.

## Why it was deferred

Found while writing `.agents/factory/invariants.md` §3 during the factory port,
which is a harness cycle — fixing product code there would have been scope creep,
and the fix needs a decision the port had no standing to make (below).

Pre-existing on `main`; not introduced by that pass. It predates the factory and
appears to date from the Stage 4 CLI consolidation recorded in
`spec/docs-only-refactor/STAGES.md`, which replaced `--docs-site` with `--site`.

## Outcome / vision

`--site` means the same thing for every action, or it is rejected for the actions
that cannot honor it. No silent divergence.

## Sketch of the acceptance criteria

Draft R-IDs, to be firmed up at promotion. Prefer EARS phrasing (see
[`ears.md`](../.agents/factory/ears.md)).

- **R1** — WHEN the server is started with `--site PATH`, `doc_search` and
  `doc_load` SHALL read the index at `PATH/index.db`.
- **R2** — WHILE `--site` is unset, resolution SHALL remain
  `$RCAC_DOCS_SITE` → `$XDG_DATA_HOME/rcac-docs-mcp` →
  `~/.local/share/rcac-docs-mcp`, unchanged.

The shaping conversation has one real question, and it should not be
pre-answered here: whether the fix threads a resolved path down through
`create_mcp_server()` into the tools, or whether the CLI simply exports
`RCAC_DOCS_SITE` from the flag before serving. The first keeps the tools free of
ambient state and touches the tool signatures; the second is three lines and
makes the flag a synonym for the variable. Invariant §3 says there is exactly one
resolution order, and either fix can honor it.

## Notes

- Related: `.agents/factory/invariants.md` §3 (the site is one container
  directory, with no second override for the index path).
- Found by: the factory port, while grounding invariants.md against the source.
