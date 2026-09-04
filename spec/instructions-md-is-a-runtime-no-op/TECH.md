---
slug: instructions-md-is-a-runtime-no-op
title: Delete INSTRUCTIONS.md; SERVER_INSTRUCTIONS stands alone
kind: refactor
appetite: small
status: done
branch: feature/instructions-md-is-a-runtime-no-op
base: main
current_phase: done
last_updated: '2026-09-04'
phases:
- id: P1
  name: Delete the file and shrink the contract test
  status: done
  satisfies:
  - R1
  - R3
  - R5
  depends_on: []
  parallel: false
  hammerable: false
  hill: uphill
  verify: 'if git ls-files | grep -qx ''INSTRUCTIONS.md''; then echo ''FAIL: INSTRUCTIONS.md
    still tracked'' >&2; exit 1; fi && test ! -e INSTRUCTIONS.md && uv run pytest
    -q tests/test_docs_contract.py && .agents/factory/bin/lint.sh && if git grep -n
    ''INSTRUCTIONS[.]md'' -- .dockerignore .agents/factory/bin/lint.sh src tests README.md;
    then echo ''FAIL: stale INSTRUCTIONS.md reference survives'' >&2; exit 1; fi'
- id: P2
  name: Reword the constitution onto SERVER_INSTRUCTIONS
  status: done
  satisfies:
  - R2
  - R4
  depends_on:
  - P1
  parallel: false
  hammerable: false
  hill: uphill
  verify: 'if git grep -n ''INSTRUCTIONS[.]md'' -- AGENTS.md .agents/factory/invariants.md;
    then echo ''FAIL: constitution still names INSTRUCTIONS.md as served'' >&2; exit
    1; fi && grep -q ''SERVER_INSTRUCTIONS'' AGENTS.md && grep -q ''SERVER_INSTRUCTIONS''
    .agents/factory/invariants.md && if git diff main -- src/rcac_docs_mcp/server.py
    | grep -q .; then echo ''FAIL: server.py changed in a no-behavior-change cycle''
    >&2; exit 1; fi'
review:
  last_reviewed_commit: 1270e6c322e04bccb20ecc68cbbe90fad83c20a3
  verdict: approved
  blocked_reason: ''
  cycle: 1
---
# TECH.md — Delete INSTRUCTIONS.md; SERVER_INSTRUCTIONS stands alone

The **context engine and finite-state machine** for building this feature. The YAML frontmatter above
is the resume ground truth (read it with
`uv run .agents/factory/bin/next_phase.py spec/instructions-md-is-a-runtime-no-op/TECH.md`); the per-phase checklists below are the
work. `proj-build` executes the next actionable phase, runs its `verify:` command, updates state via
`uv run .agents/factory/bin/set_phase.py …`, and makes one atomic code-plus-state commit.

- **Vision / requirements (locked):** [`GOAL.md`](GOAL.md) — R-IDs are the contract.
- **Authoritative design:** [`PLAN.md`](PLAN.md).
- **Backing research:** [`research/00-baseline.md`](research/00-baseline.md).

## Frontmatter field reference

- `status` (top): `planned | in_progress | blocked | in_review | done`. `proj-plan` writes `planned`;
  `/proj-build` flips it to `in_progress` on the first completed phase and to `in_review` on the last;
  `done` is stamped by `proj-publish` after confirmation, just before landing — the terminal state of
  the retained record.
- `appetite`: `small | big` — caps phase count and build-iteration budget (the circuit breaker).
- phase `status`: `pending | in_progress | done | blocked`.
- `satisfies`: GOAL R-IDs this phase delivers. The traceability anchor for `proj-review`.
- `depends_on`: phase ids that must be `done` first. A phase is actionable only when they are.
  A cycle here is refused by `next_phase.py` rather than reported as "all done".
- `parallel`: **almost always `false`.** The indexing core is tightly coupled — `index/indexer.py`,
  `index/database.py`, `index/schema.sql` and `tools.py` are one mechanism wearing four filenames, and
  two phases that touch any of them are not independent. Reserve `true` for genuinely disjoint work
  such as a documentation-only or CI-only phase.
- `hammerable`: `false` marks a correctness phase that scope-hammering must never cut. Anything
  touching `invariants.md` §1–§11 is `false`.
- `hill`: `uphill` (still figuring it out) → `crest` (unknowns resolved) → `downhill` (just
  executing). A phase stuck `uphill` across builds is a raised hand — escalate.
- `attempts`: durable failed-verify counter (absent means 0), bumped by
  `set_phase.py --phase P<n> --record-attempt` on every terminally red gate. `next_phase.py` warns at
  3. The circuit breaker runs on this file, not on session memory.
- `verify`: the exact command that proves the phase. Assert a **post-condition**, not just exit 0.
  The value is a YAML scalar before it is a shell command: in double-quoted style — the style the
  frontmatter above uses, because deferring `$` expansion into `sh -c '…'` requires it — `\n`, `\t`
  and `\\` are YAML escapes, not shell ones, and a `\n` splits the command where no shell ever sees
  it. Keep the command free of backslashes apart from `\"`, or use a block scalar.
- `review.cycle`: completed review passes, auto-incremented by every `set_phase.py --verdict` other
  than `none`. `REVIEW.md`'s "Cycle {n}" mirrors it and the two-to-three-cycle bound is graded
  against it.

> `set_phase.py` regenerates this block canonically and **drops any YAML comments** in it. Document
> enums here in the body, never as inline comments in the frontmatter — they will not survive the
> next state change.

## Conventions (apply to every phase)

- Commit conventions, code style, prose voice and load-bearing invariants come from
  [`AGENTS.md`](../../AGENTS.md) — it is the constitution. Consult
  [`invariants.md`](../../.agents/factory/invariants.md) for the footgun checklist relevant to this
  change.
- One phase per `proj-build` invocation by default; one atomic commit containing **both** the code and
  the `TECH.md` state change. Subjects follow `[{category}] Build {slug} P<n>: …` — they are squashed
  into the single PR-title commit at `proj-publish`.
- **No `Co-Authored-By:` trailer.**
- A change to the tool surface, the environment contract, the CLI flags, or the site layout updates
  `README.md`, `INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` and `SERVER_INSTRUCTIONS` — whichever it
  invalidates — **in the same commit**.
- No feature-scoped spec ids (`R1`, `P3`) in `src/rcac_docs_mcp/**`, `README.md`, or
  `INSTRUCTIONS.md`. `lint.sh` enforces this.

---

## Phase P1 — Delete the file and shrink the contract test
**Satisfies:** R1, R3, R5 · **Depends on:** —
**Goal:** The tracked copy is gone, the contract test enforces the two surviving
copies, and the mechanical path references follow the deletion.

- [x] `git rm INSTRUCTIONS.md`.
- [x] `tests/test_docs_contract.py`: drop `INSTRUCTIONS.md` from `_sources()`,
  rewrite the module docstring onto the two-copy rule. The rewritten file must
  not contain the literal string `INSTRUCTIONS.md` anywhere — not even in a
  historical aside — or this phase's own census gate goes red on the file it
  just edited.
- [x] `.dockerignore`: remove the `INSTRUCTIONS.md` line.
- [x] `.agents/factory/bin/lint.sh`: remove `INSTRUCTIONS.md` from the spec-id
  census pathspec, leaving `-- src README.md`.
- **Verify:** index-and-worktree absence (`git ls-files` census plus
  `test ! -e`), then `uv run pytest -q tests/test_docs_contract.py`, then
  `.agents/factory/bin/lint.sh`, then the absence census over
  `.dockerignore`, `lint.sh`, `src`, `tests`, `README.md` — dying on the
  first unmet clause. Covers R1 (both absence clauses), R3 (pytest file),
  R5 (pathspec census plus lint exit 0).
- **Touches:** `INSTRUCTIONS.md` (deleted), `tests/test_docs_contract.py`,
  `.dockerignore`, `.agents/factory/bin/lint.sh`.

## Phase P2 — Reword the constitution onto SERVER_INSTRUCTIONS
**Satisfies:** R2, R4 · **Depends on:** P1
**Goal:** `AGENTS.md` and `invariants.md` name the served copy correctly, and
`server.py` is provably untouched.

- [x] `AGENTS.md`: reword the five passages (`:36`, `:145`, `:292`, `:299`,
  `:307`) onto `SERVER_INSTRUCTIONS` in `server.py`.
- [x] `.agents/factory/invariants.md`: reword §1 (`:30`) the same way; §12
  (`:171-178`) drops the deleted file from the same-commit list and the
  spec-id rule. Keep the two files in lockstep per `AGENTS.md:135-140`.
- [x] Replacement prose must not contain the literal string `INSTRUCTIONS.md`
  anywhere — no "formerly" aside — or this phase's own gate goes red on the
  files it just edited.
- [x] Touch nothing under `src/`.
- **Verify:** absence census over `AGENTS.md` and `invariants.md`, presence
  anchors for `SERVER_INSTRUCTIONS` in both, then the empty-diff guard on
  `src/rcac_docs_mcp/server.py`. Covers R2 (absence plus presence) and R4
  (diff guard). Whether the replacement sentences read well is
  inspection-only — the gate cannot grade prose, so `proj-review` reads it
  against `server.py` rather than trusting the gate.
- **Touches:** `AGENTS.md`, `.agents/factory/invariants.md`.

Sequential by design: P2 depends on P1 so no committed intermediate state
pairs the deletion with a constitution still asserting the file. Both phases
are `hammerable: false` — P1 is the point of the cycle, P2 touches
`invariants.md`.

---

## How `proj-build` drives this

1. `next_phase.py` prints the next actionable phase. Statuses are authoritative; the `current_phase`
   pointer is reconciled against them.
2. Pre-flight: clean tree, on `branch`, `base` reachable.
3. Execute every `[ ]` in the phase, consulting `PLAN.md` and `research/` for detail.
4. Run the phase's `verify:` command. Never advance on a checkbox alone, and never on exit 0 alone.
5. Amend this file freely if reality diverges — regenerate frontmatter with `set_phase.py` and note
   the amendment in the commit body. STOP and escalate only on a **`GOAL.md` contradiction**.
6. Mark the phase `done`, advance `current_phase`, `--touch`; one `[{category}]` commit; stop and
   report.
