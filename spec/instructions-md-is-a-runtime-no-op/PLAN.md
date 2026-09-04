# PLAN — Delete `INSTRUCTIONS.md`, leave `SERVER_INSTRUCTIONS` standing alone

> **Status:** Draft for review · **Last updated:** 2026-09-03
> **Authoritative technical design.** The *how*. The contract is [`GOAL.md`](GOAL.md); the phased
> executable roadmap is [`TECH.md`](TECH.md). Backing detail is in [`research/`](research/).
> Every design element traces to a GOAL R-ID.

## 1. Summary

`git rm INSTRUCTIONS.md` and repair the six live references that name it:
the contract test drops its third source, the constitution (`AGENTS.md`,
`invariants.md`) names `SERVER_INSTRUCTIONS` as the served copy, and
`.dockerignore` plus the `lint.sh` pathspec drop the deleted path. No module
under `src/rcac_docs_mcp/` changes; the served text is bit-identical before
and after. Two sequential phases: the deletion with its mechanical
followers, then the constitution prose.

## 2. Design

No `src/` module changes. The runtime already has the desired shape — one
literal, served directly — so the entire diff is deletion plus reference
repair:

- `INSTRUCTIONS.md` — `git rm`. The file is a near-copy of
  `SERVER_INSTRUCTIONS` that no code path opens (`src/` holds no
  `INSTRUCTIONS` reference outside `server.py:62,102`; build and deploy files
  hold none). R1.
- `tests/test_docs_contract.py` — drop `INSTRUCTIONS.md` from `_sources()`.
  Rewrite the module docstring from the three-copy incident narrative to the
  two-copy standing rule: `README.md` prose must agree with
  `SERVER_INSTRUCTIONS`, and the retired wildcard advice must appear in
  neither. `CONTRACT_CLAIMS` and `RETIRED_ADVICE` stay as written. R3.
- `AGENTS.md` — four passages name the deleted file as served or as
  user-facing docs: the deploy-risk paragraph (`:36`), the tool-surface
  paragraph (`:145`), the emoji rule (`:292`), the spec-id rule (`:299`), and
  the system-prompt paragraph (`:307`). Each is reworded onto
  `SERVER_INSTRUCTIONS` in `server.py`. R2.
- `.agents/factory/invariants.md` — §1 (`:30`) names both copies as the held
  system prompt; reword onto `SERVER_INSTRUCTIONS`. §12 (`:171-178`) drops
  `INSTRUCTIONS.md` from the same-commit list ("five places" becomes four)
  and from the spec-id rule. R2.
- `.dockerignore:39` — remove the `INSTRUCTIONS.md` entry. The `lint.sh`
  completeness gate asserts only `.agents .claude spec issues .security docs
  tests`, so the removal breaks no check. R5.
- `.agents/factory/bin/lint.sh:117-118` — remove `INSTRUCTIONS.md` from the
  spec-id census pathspec, leaving `-- src README.md`. R5.

What is being **removed**: the tracked `INSTRUCTIONS.md`; the three-way
comparison in the contract test (replaced by a two-way one); five constitution
sentences asserting the deleted file ships; two mechanical path entries. What
is not: the served text, any tool, any transport, any index behavior.

The five places stating the same contract, and this change's relation to each:

| Place | Disposition |
|-------|-------------|
| `README.md` | Untouched. It keeps stating the search contract in prose and stays the second copy the test compares. |
| `INSTRUCTIONS.md` | Deleted. |
| `AGENTS.md` | Edited. Names the surviving source. |
| `APP_HELP` in `__init__.py` | Untouched. Rechecked: carries no search guidance. |
| `SERVER_INSTRUCTIONS` in `server.py` | Untouched. The canonical and now only source. |

### Requirement → design map

| R-ID | Design element(s) that satisfy it |
|------|-----------------------------------|
| R1 | `git rm INSTRUCTIONS.md`; absence from tree and index. |
| R2 | `AGENTS.md` and `invariants.md` reworded onto `SERVER_INSTRUCTIONS`; §12 list at four entries. |
| R3 | Contract test compares `README.md` against `SERVER_INSTRUCTIONS` only; claims and retired-advice assertions unchanged. |
| R4 | Empty diff on `src/rcac_docs_mcp/server.py`; fingerprint in `research/00-baseline.md` still matches. |
| R5 | `.dockerignore` entry and `lint.sh` pathspec pruned; `lint.sh` exits 0. |

## 3. Invariant gate (AGENTS.md constitution check)

Checked against `invariants.md` **before** research (§1, §12 identified as the
only touched sections) and **again** after this design was drafted.

- §1 (exactly two tools) — honored. The tool surface is untouched; only the
  prose naming the held system prompt changes, from two copies to the one
  that is actually served.
- §12 (same-commit rule) — honored by editing it. The list drops the deleted
  file; the surviving four still move together. A §12 violation is HIGH, not
  CRITICAL, but leaving the rule naming a file the same commit deletes turns
  the next correct change into a finding against itself.
- §2–§11 — untouched. No auth, filesystem, site, index, query, transport, or
  container behavior changes. No high-blast-radius file changes behavior;
  `server.py` does not change at all.

### Deviation justifications

| Deviation | Why needed | Simpler alternative rejected because |
|-----------|-----------|--------------------------------------|
| — | — | — |

## 4. Rabbit holes (resolved)

Appetite is small, the root cause is known, and no high-blast-radius file
changes behavior, so there was no subagent fan-out — four targeted reads,
each recorded here:

- Does anything read the file at runtime or build time? → No. `git grep`
  over `src/`, `Dockerfile`, `docker-entrypoint.sh`, `.github/`,
  `pyproject.toml`, and `uv.lock` finds only `SERVER_INSTRUCTIONS` in
  `server.py`. Deletion has no runtime follower.
  ([`research/00-baseline.md`](research/00-baseline.md)).
- Does removing the `.dockerignore` entry break the lint completeness gate?
  → No. `lint.sh` asserts exactly `.agents .claude spec issues .security
  docs tests`; the `INSTRUCTIONS.md` line is unasserted surplus.
- Does `git grep` fail on a pathspec naming a deleted file? → Moot. The
  design removes `INSTRUCTIONS.md` from the `lint.sh` pathspec in the same
  commit that deletes it, so the question never reaches a gate.
- What is the served text, exactly? → Fingerprinted:
  sha256 `fd2dd5cd…96dd575`, 1566 chars
  ([`research/00-baseline.md`](research/00-baseline.md)). R4 compares against
  it.

## 5. Risks & open questions

- Constitution prose is judgment, not assertion. The P2 gate proves the stale
  name is gone and the surviving name is present; whether the replacement
  sentences read correctly is inspection-only for `proj-review`, stated as
  such in `TECH.md` P2.
- Wider factory prose (`methodology.md`, `review-rubric.md`, skill docs,
  templates) keeps naming `INSTRUCTIONS.md`. GOAL records that as a
  non-goal; a future reader of those files could repeat the old mistake, but
  refreshing harness prose is `proj-harness` territory, not this cycle.
- Nothing here is observable only in the deployed pod. No runtime changes, so
  there is no digest-poller lag to wait out; the live `initialize` response
  is unchanged by construction. Post-publish probing would confirm a no-op,
  not a fix.

## 6. Verification strategy

Two layers carry the gates; the third (sandbox drive) has nothing to drive,
since no index, tool, or CLI behavior changes:

- `uv run pytest -q tests/test_docs_contract.py` — proves R3: the two
  surviving copies agree and the retired advice is absent from both.
- `.agents/factory/bin/lint.sh` — proves R5's tail: the repository shape the
  skills assume still holds after the pathspec edit.
- Census commands with inverted assertions (`if git grep …; then … exit 1`)
  prove the absences R1, R2, and R5 require. Absence gates use the
  single-token anchors `INSTRUCTIONS[.]md` (gone) and `SERVER_INSTRUCTIONS`
  (present) — never a wrapped sentence, which hard-wrapping near column 100
  would split across lines and silently miss.
- `git diff main -- src/rcac_docs_mcp/server.py` proves R4: the cycle leaves
  the served text alone. The sha256 in `research/00-baseline.md` is the
  cross-check if the diff ever looks non-obvious.

Each TECH phase `verify:` names its post-condition per R-ID `Checked by`
clause, in both directions: every clause in `satisfies` is asserted by the
gate, and the gate asserts nothing outside them except `lint.sh`, which is
the standing shape invariant.

---

*Backing research: [`research/00-baseline.md`](research/00-baseline.md).*
