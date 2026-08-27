---
status: unshaped
kind: docs
appetite: small
lane: public
---

# `SERVER_INSTRUCTIONS` still tells agents to use prefix wildcards

## Problem

`src/rcac_docs_mcp/server.py` advises callers to use "prefix wildcards for
variants (`contai*`)". Commit `c2c943a` corrected exactly that advice in
`README.md` and `INSTRUCTIONS.md`, which now read:

> The index is Porter-stemmed, so `gpu`/`gpus` and `purge`/`purged` already
> match each other and `*` is rarely needed.

`SERVER_INSTRUCTIONS` was not updated in that commit, so the two disagree.

This is not a cosmetic inconsistency, for two reasons.

**It is the copy that actually reaches agents.** `SERVER_INSTRUCTIONS` is served
in the MCP `initialize` response and is held as a system prompt by every
downstream client, on every call. `README.md` and `INSTRUCTIONS.md` are read by
humans, occasionally.

**The advice actively defeats the normalizer.** Any FTS5 operator in a query
turns normalization off and runs the string verbatim — that is deliberate, so a
caller who wants precision can have it. `*` is such an operator. So an agent
following this instruction routes itself around the stopword-dropping,
OR-joining, prefix-matching broadening that `c2c943a` added to make
natural-language queries work, and gets *worse* recall for the trouble. The
tokenizer is `porter unicode61 remove_diacritics 1`
(`src/rcac_docs_mcp/index/schema.sql`), so the stemming it recommends working
around is already doing the job.

## Why it was deferred

Found during the factory port while writing `.agents/factory/invariants.md` §8.
That was a harness cycle; editing the server's user-facing text there would have
been scope creep, and this text deserves a pass of its own rather than a
one-line patch.

Pre-existing on `main`. It is a clean instance of the same-commit rule
(`invariants.md` §12) being missed: five files state this contract and `c2c943a`
updated three of them.

## Outcome / vision

The instructions an agent receives match the ones a human reads, and both match
what the index actually does. A good first cycle for the factory to run on
itself — small, real, and entirely in the surface the factory most cares about.

## Sketch of the acceptance criteria

Draft R-IDs, to be firmed up at promotion. Prefer EARS phrasing (see
[`ears.md`](../.agents/factory/ears.md)).

- **R1** — The `SERVER_INSTRUCTIONS` search guidance SHALL state that the index
  is Porter-stemmed and that `*` is rarely needed, consistent with `README.md`
  and `INSTRUCTIONS.md`.
- **R2** — The `SERVER_INSTRUCTIONS` guidance SHALL state that any FTS5 operator
  disables normalization and runs the query verbatim, since that is the actual
  lever a caller has.
- **R3** — WHEN the tool-usage guidance changes, `README.md`, `INSTRUCTIONS.md`
  and `SERVER_INSTRUCTIONS` SHALL agree, verified by a command named in the plan
  rather than by reading.

R3 is the one worth arguing about at promotion. Making it checkable is the
difference between fixing this instance and stopping the class, and the obvious
mechanism — grepping for a shared phrase — is defeated by the hard-wrapped prose
in all three files (see `review-rubric.md`, *Verification traps*).

## Notes

- Related: `.agents/factory/invariants.md` §8 (search semantics) and §12 (the
  same-commit rule). Commit `c2c943a` is the partial fix.
- Found by: the factory port, while grounding invariants.md against the source.
