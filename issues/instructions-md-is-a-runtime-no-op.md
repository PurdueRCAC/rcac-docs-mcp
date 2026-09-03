---
status: unshaped
kind: refactor
appetite: small
lane: public
---

# `INSTRUCTIONS.md` ships to nobody, and the constitution says it ships to everybody

## Problem

Nothing reads `INSTRUCTIONS.md` at runtime. The text FastMCP serves in the
`initialize` response is `SERVER_INSTRUCTIONS`, a triple-quoted literal in
`src/rcac_docs_mcp/server.py`, passed at `create_mcp_server()`. `INSTRUCTIONS.md`
is a near-copy of that literal that no code path opens, and it is not listed in
the *Where work is recorded* table in `AGENTS.md`, so its status is undefined.

Four places assert the opposite, and they are the load-bearing ones:

- `.agents/factory/invariants.md:175` — "Five places state the same contract,
  and `INSTRUCTIONS.md` is what ships to every downstream agent."
- `.agents/factory/invariants.md:30` — "agents hold `INSTRUCTIONS.md` and
  `SERVER_INSTRUCTIONS` as a system prompt".
- `AGENTS.md:145` — "every downstream agent holds `INSTRUCTIONS.md` as a system
  prompt".
- `AGENTS.md:36` — "a stale sentence in `INSTRUCTIONS.md` is a system prompt"
  (in the deploy-risk paragraph).

This is not a wording quibble. It has already cost a deploy cycle. When the
wildcard advice was corrected in `c2c943a`, the fix went to `README.md` and
`INSTRUCTIONS.md` — the two files the constitution names as the ones that reach
agents — and `SERVER_INSTRUCTIONS` was left stale. The change deployed, the live
handshake still served the old advice, and nobody noticed until the endpoint was
probed directly. Commit `7f8d98c` is the record of
that instance (the seed is retired; `git log --diff-filter=D --
issues/server-instructions-wildcard-drift.md` recovers it); this is the reason
it happened.

`7f8d98c` (now on `main`) added `tests/test_docs_contract.py`, which now fails if the three
copies disagree. That stops the drift from being *silent*. It does not remove
the copy — it promotes a file nothing reads into one that must be kept in step
forever, which is the wrong end of the problem to fix.

## Why it was deferred

Found while fixing the wildcard drift, which was a `docs` cycle with a `small`
appetite scoped to the text itself. Deleting a documented file, or adding a
package-data read to `server.py`, is a change to the packaging and to the
constitution — squarely outside what that cycle had agreed, and exactly the kind
of scope creep the same-commit rule is meant to *bound* rather than license.

It should have been filed then and was not. The decision to keep the duplication
and enforce it with a test was made mid-cycle and recorded only in the commit
body, so the rejected alternative — remove the copy — had no home. That is the
gap this file closes.

## Outcome / vision

There is one place a maintainer edits the agent-facing instructions, and reading
`AGENTS.md` tells them which one. Whether that place is the Python literal or
the markdown file matters less than that the answer is unambiguous and the
constitution states it correctly.

## Sketch of the acceptance criteria

Draft R-IDs, to be firmed up at promotion. Prefer EARS phrasing (see
[`ears.md`](../.agents/factory/ears.md)).

- **R1** — The repository SHALL hold exactly one editable source for the served
  instructions text.
- **R2** — `AGENTS.md` and `.agents/factory/invariants.md` SHALL name the served
  copy correctly, and the same-commit list in §12 SHALL be adjusted to whatever
  set of files actually survives.
- **R3** — WHERE the served text moves out of `server.py`, the packaged wheel
  SHALL contain it and a test SHALL prove it is readable from an installed
  distribution rather than only from a source checkout.

R1 is the argument worth having at promotion, and it is a real fork:

- **Delete `INSTRUCTIONS.md`.** Cheapest, no packaging change, drops the
  same-commit list from five files to four. Costs a human-readable rendering of
  the system prompt that is pleasant to review in a PR diff.
- **Make `INSTRUCTIONS.md` the source** and have `server.py` read it via
  `importlib.resources`. Keeps the reviewable markdown and makes the literal
  impossible to skew. Costs a move into `src/rcac_docs_mcp/`, a hatchling
  package-data entry, and a runtime read with a failure mode if the wheel is
  built wrong — which is what R3 exists to catch.

Note that either answer shrinks `tests/test_docs_contract.py` rather than
retiring it: `README.md` still states the contract in prose and still has to
agree.

## Notes

- Related: commit `7f8d98c` (the instance this
  explains; seed retired, see git history), `.agents/factory/invariants.md` §12 (the same-commit rule anchored
  on the wrong file), and `tests/test_docs_contract.py` in `7f8d98c` (the
  mitigation that made the drift loud).
- `APP_HELP` in `__init__.py` is the fifth file in §12's list. It carries no
  search guidance today, so it is unaffected — worth re-checking at promotion
  rather than assumed.
- Found by: probing the live `initialize` response after `c2c943a` deployed and
  finding it still served `contai*`.
