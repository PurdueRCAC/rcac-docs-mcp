---
slug: example-slug
title: "One-line human title for this feature"
kind: feature
appetite: big
status: planned
branch: feature/example-slug
base: main
current_phase: P1
last_updated: "2026-01-01"
phases:
  - id: P1
    name: "First vertical slice (core + small + novel)"
    status: pending
    satisfies: [R1]
    depends_on: []
    parallel: false
    hammerable: false
    hill: uphill
    verify: "uv run pytest -q -k normalize"
  - id: P2
    name: "Second slice"
    status: pending
    satisfies: [R2, R3]
    depends_on: [P1]
    parallel: false
    hammerable: true
    hill: uphill
    verify: ".agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index | grep -qE \"Indexed: +[1-9][0-9]* documents\"'"
review:
  last_reviewed_commit: ""
  verdict: none
  blocked_reason: ""
  cycle: 0
---

# TECH.md — {title}

The **context engine and finite-state machine** for building this feature. The YAML frontmatter above
is the resume ground truth (read it with
`uv run .agents/factory/bin/next_phase.py spec/{slug}/TECH.md`); the per-phase checklists below are the
work. `proj-build` executes the next actionable phase, runs its `verify:` command, updates state via
`uv run .agents/factory/bin/set_phase.py …`, and makes one atomic code-plus-state commit.

- **Vision / requirements (locked):** [`GOAL.md`](GOAL.md) — R-IDs are the contract.
- **Authoritative design:** [`PLAN.md`](PLAN.md).
- **Backing research:** [`research/00-digest.md`](research/00-digest.md) plus briefs, if `appetite: big`.

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

## Phase P1 — First vertical slice
**Satisfies:** R1 · **Depends on:** —
**Goal:** <what this slice delivers, end to end and independently verifiable>.

- [ ] <concrete step>
- [ ] <concrete step>
- **Verify:** `uv run pytest -q -k …` — and name the post-condition asserted.
- **Touches:** `src/rcac_docs_mcp/tools.py`, `tests/test_tools.py`, …

## Phase P2 — Second slice
**Satisfies:** R2, R3 · **Depends on:** P1
**Goal:** <…>.

- [ ] <concrete step>
- **Verify:** `.agents/factory/bin/temp_site.sh …` asserting <post-condition>.
- **Touches:** `src/rcac_docs_mcp/index/indexer.py`.

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
