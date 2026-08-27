---
name: proj-build
description: >-
  Resume and execute an rcac-docs-mcp feature's phased roadmap. Discovers spec/{slug}/TECH.md from the
  current feature/fix/docs branch, reads the FSM via next_phase.py, implements the next phase (one at a
  time by default), runs that phase's verify command in a sandbox, updates state via set_phase.py, and
  makes one atomic code-plus-state commit. May amend TECH.md freely as reality dictates; only a
  GOAL.md contradiction forces a stop. The driver of the software factory (see
  .agents/factory/methodology.md).
disable-model-invocation: true
argument-hint: "[status | dry run | phase P3 | through P5 | next 2 | bundle | no-pause]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git status *), Bash(git branch *), Bash(git rev-parse *), Bash(git log *), Bash(git diff *), Bash(git add *), Bash(git commit *), Bash(git ls-files *), Bash(git rm *), Bash(uv run *), Bash(.agents/factory/bin/*), Bash(grep *), Bash(head *), Bash(ls *), Bash(echo *), Bash(del *), Bash(git grep *), Bash(git submodule *)
---

# proj-build — execute the roadmap (resume-and-implement)

## When to Use

Invoke `/proj-build` on a feature/fix/docs branch whose `spec/{slug}/TECH.md` exists, to execute the
next slice of the roadmap without re-explaining the project. The rhythm is **one-phase-then-stop**:
scale up with arguments when you trust the next chunk, scale down to a dry run when you do not.
`TECH.md` frontmatter is the resume ground truth; `PLAN.md` is the authoritative design; `GOAL.md`
R-IDs are the locked contract; `research/` holds detail. Track progress **only** in `TECH.md`, via the
scripts.

Reference: [`methodology.md`](../../factory/methodology.md),
[`invariants.md`](../../factory/invariants.md), and `AGENTS.md` (the constitution).

**Harness portability.** Runs on any harness — see [`portability.md`](../../factory/portability.md).
If the *Current state* block is not auto-injected, run those commands yourself in Step 1, which
already re-runs `next_phase.py`. Nothing else here is Claude-specific.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current | grep . || echo "(detached HEAD)"`
- Tree: !`git status --porcelain | head -n 20 | grep . || echo "(clean)"`
- Commits on branch (vs main): !`git log --oneline main..HEAD 2>/dev/null | head -n 15 | grep . || echo "(none)"`
- FSM: resolved in **Step 1** by running `uv run .agents/factory/bin/next_phase.py spec/{slug}/TECH.md` (a load-time injection cannot strip the branch prefix to form `{slug}`).

## Argument Parsing

Parse `$ARGUMENTS` case-insensitively; if ambiguous, STOP and ask.

- `status` / `report` → summarize FSM state (via `next_phase.py`, Step 1) plus the last commit; no
  work.
- `dry run` / `plan only` / `preview` → identify the target phase and load context, but make **no**
  edits or commits. Report the plan: checklist items, files, verify command, expected commit.
- `phase P<n>` / `at P<n>` → execute that phase regardless of `current_phase`.
- `through P<n>` / `up to P<n>` → execute forward, stopping after `P<n>` completes.
- `next N` / `N phases` → execute the next `N` incomplete phases, each its own commit.
- `bundle` → collapse the run into a single commit. Only for tightly coupled phases.
- `no-pause` → continue past the natural phase-boundary stop. Use sparingly.
- No arguments → default next-phase-then-stop.

## Safety Principles

- **`next_phase.py` is the resume ground truth**, re-run fresh every invocation in Step 1. If it
  reports the FSM invalid, or warns of pointer/status drift, **reconcile before acting** — do not
  guess.
- **On a feature/fix/docs branch only** — never `main`. A merge to `main` is a deploy, and this skill
  does not deploy. Clean tree required; non-empty → STOP (commit, stash, or discard first).
- **A phase is the unit of work.** Execute every `[ ]` item in the target phase, not just the first. A
  phase is `done` only when all items are satisfied **and** its `verify:` command passes.
- **Verify by driving the server, in a sandbox.** Run the phase's `verify:` command. Anything
  behavioral goes through `.agents/factory/bin/temp_site.sh` — never a bare `uv run rcac-docs-mcp
  --index`, which writes into the developer's real site and can clone the docs repo from the network.
  **Exit 0 is necessary but not sufficient:** assert the concrete post-condition (a document count, a
  path present in the search results, a second `--index` reporting `Indexed: 0 documents`, a specific
  line on stderr). `uv run pytest -q` alone is the weakest gate in this repository — with the
  RCAC-Docs submodule absent it reports `76 passed, 31 skipped` and still exits 0, so assert the
  counts or drive through the sandbox, which **exits 3** rather than reporting a pass it cannot
  support. An exit 3 is *could not run*, never a pass. A drive that "completed" but left the wrong
  index is a FAIL. A still-red gate is a STOP — do not mark the phase done or advance state.
- **Amend `TECH.md` freely; the GOAL is locked.** When reality diverges from the plan — a phase is
  wrong, needs splitting, or a new one is required — rewrite `TECH.md` (regenerate frontmatter with
  `set_phase.py`, edit phase bodies as needed) and **note the amendment in the commit body**. But if
  the work contradicts a `GOAL.md` R-ID, **STOP and escalate** — never silently drift the contract.
- **Honor `AGENTS.md`.** The invariants for the region you are touching (consult `invariants.md`,
  where a §1–§11 violation is auto-CRITICAL and §12 is HIGH), the same-commit rule (`README.md`,
  `INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` in `__init__.py`, `SERVER_INSTRUCTIONS` in `server.py`),
  the single version source in `pyproject.toml`, and the **prose and comment voice** — declarative
  statements of the *why*, no filler or marketing adjectives, no emoji, and **no feature-scoped spec
  ids (`R1`, `P3`) in `src/rcac_docs_mcp/**`, `README.md`, or `INSTRUCTIONS.md`**.
- **Prefer deleting to adding.** If a phase can be satisfied by removing a special case rather than
  adding one, do that and say so in the commit body. `rm` is aliased away — use `del`, or `git rm` for
  tracked files.
- **Circuit breaker (durable).** Every gate that stays red is recorded on file via
  `set_phase.py spec/{slug}/TECH.md --phase {id} --record-attempt` — the counter, not session memory, trips the breaker.
  When a phase's `attempts` reaches about 3 (`next_phase.py` warns), or it stays `hill: uphill` across
  builds, **stop and re-shape**: STOP and recommend `/proj-plan` or human input rather than looping.
- **`main` is off-limits; never push, squash, force-push, or open PRs** — that is `/proj-publish`.
  **No `Co-Authored-By:` trailer** of any kind.

## Procedure

### Step 0 — status / dry-run (when requested)
`status`: run `next_phase.py` (Step 1), report the FSM plus the last commit, and stop. `dry run`: do
Steps 1–2, then report the plan that *would* run and stop — no edits, no commits.

### Step 1 — Pre-flight
1. Clean tree on a feature/fix/docs branch, from the injection. STOP otherwise.
2. Resolve `{slug}` from the branch (strip the `feature/`, `fix/` or `docs/` prefix), then run
   `uv run .agents/factory/bin/next_phase.py spec/{slug}/TECH.md` and read its output. If it errored or
   warned of drift, reconcile (`uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md --current …`) or STOP and report.
3. **Remediation mode.** If the FSM shows `top_status: blocked` or
   `review.verdict: changes-requested`, a prior `/proj-review` requested changes. Read
   `spec/{slug}/REVIEW.md`, then make the fixes actionable by amending `TECH.md`. **Prefer reopening**
   the existing phase whose `satisfies` covers the failing R-IDs
   (`uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md --phase P<n>
   --phase-status in_progress`). A reopened phase's gate is retuned the
   same script-safe way — tighten a too-weak `verify:` with `uv run .agents/factory/bin/set_phase.py
   spec/{slug}/TECH.md --phase P<n> --verify "…"`,
   never by hand-editing the YAML. Only if a fix maps to no existing phase, add one **through the
   script**: `uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md --add-phase P<next>
   --name "F# remediation: …" --satisfies R<n>
   --depends-on P<m> --verify "…"`, then write its checklist body and re-validate with
   `next_phase.py`. Set `--top-status in_progress` and proceed. If a finding contradicts a `GOAL.md`
   R-ID rather than just the plan, STOP and escalate instead.

   A remediation edit is not local to its phase. After making it, re-run the `verify:` of every `done`
   phase that lists the reopened phase in `depends_on`, and reopen any that goes red. `next_phase.py`
   never re-runs a gate, so a `done` phase whose assertion the fix invalidated is invisible to the FSM
   and ships green. The shape that breaks is a reconciliation phase whose gate hardcodes a count the
   fix just moved.

### Step 2 — Identify target phase + load context
1. Target = the `next_phase` output from Step 1, or the argument-selected phase. Confirm its
   `depends_on` are `done`; if not, STOP.
2. Read `spec/{slug}/PLAN.md` and the relevant `research/` for the detail behind the phase's checklist.
   **Read the region of `src/rcac_docs_mcp/` the phase will touch before editing it**, including the
   module docstring and the comments above it — they carry the constraints that are not visible from
   the code, such as why Jinja2 renders before snippets and why the index is swapped rather than
   written in place.

### Step 3 — Implement the phase
Execute every `[ ]` item to `AGENTS.md` conventions. Sanity-check as you go: `uv run python -c "import
rcac_docs_mcp"` after any non-trivial edit is nearly free and catches the class of error that
otherwise surfaces at pod start, when the entrypoint's `set -eu` turns it into a pod that never
becomes ready. If implementation reveals a real correction to `TECH.md`/`PLAN.md`, amend `TECH.md` per
Step 5. If it reveals a `GOAL.md` contradiction, STOP and escalate.

### Step 4 — Verify gate
Run the phase's `verify:` command, plus any additional drive the change warrants. "Green" means **the
asserted post-condition held** — the observed document count, search result, exit code or stderr line
is correct — not merely that the command exited 0. When the drive calls a tool from Python, remember
the MCP tools are FastMCP `FunctionTool` objects: `doc_search.fn("slurm")`, not `doc_search("slurm")`,
which raises `TypeError: 'FunctionTool' object is not callable`.

A **new or retuned** `verify:` gets one step before you trust it: run it under `/bin/sh`, and confirm
it is red before the fix and green after.
```
uv run .agents/factory/bin/run_verify.py spec/{slug}/TECH.md --phase {id}
```
That reads the gate out of the folded YAML and execs it as `/bin/sh -c '…'`, erroring rather than
exiting 0 when the string is empty. Copying a wrapped gate by hand means reflowing it, and reflowing is
where a quoting error enters; `/bin/sh -c ''` exits 0, so a reader that silently produced nothing
satisfies the red check while proving nothing. The string is authored in this session's interactive
shell and executed later by `lint.sh`, by CI, and by anyone reading `TECH.md` under plain `sh`, where
aliases, shell functions and GNU-versus-BSD utilities all diverge — a `grep` that is a shell function
here is `/usr/bin/grep` there. A gate never observed failing is not a gate.

Green → proceed. A red you can name the correction for is the inner loop of implementation: make the
fix, re-run, and record what it took in the commit body, not as an attempt — the counter catches a
phase that will not converge, and one converging exactly as planned would trip it in three reds. A
gate that stays red — no correction left to try, or the one you predicted would clear it did not —
says the phase is mis-shaped → STOP; do not mark done or advance state. Record the failure:
```
uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md --phase {id} --record-attempt --touch
```
and commit at least that `TECH.md` change before handing back, so the circuit breaker counts across
sessions.

### Step 5 — Update `TECH.md` (the resume contract)
1. Check off the phase's `[ ]` items in the body.
2. Advance state with the script — regenerate, never hand-edit the YAML:
   ```
   uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md \
       --phase {id} --phase-status done --current {next_id_or_done} --touch
   ```
   For a mid-phase amendment, edit phase bodies and use `set_phase.py` for any status, pointer or hill
   change. If all phases are now done, also pass `--top-status in_review`; otherwise, if the top status
   is still `planned`, this is the branch's first completed phase — pass `--top-status in_progress`.
3. `set_phase.py` re-serializes the whole frontmatter block canonically and **drops any YAML comments
   in it**. An enum or a caveat worth writing down belongs in the body of `TECH.md`, where it survives
   the next state change.

### Step 6 — Meta-note (self-improvement loop · silence by default)
Before committing, reflect on the **skillset itself** — not the task, not the code. Write nothing
unless the bar is met.

**The bar (one test):** *was this the skill's fault — not mine, not the task's?* **Qualifies:** you
hand-fixed a command this skill gave (a wrong flag or path, a bare `python` that should be `uv run`,
a drive that should have gone through `temp_site.sh`, a bare `doc_search(…)` that needed `.fn`,
unquoted YAML); a genuinely ambiguous instruction; a verify gate that passed or failed misleadingly
(exit 0 hid a skipped test suite); an allowed-tools/step mismatch. **Stay silent for:** a merely hard
task; your own error against clear guidance; a one-off code issue (that goes in `REVIEW.md` at review
time); a vague preference.

If, and only if, the bar is met, record it in `spec/{slug}/META.md` — create from
[`templates/META.md`](../../factory/templates/META.md) if absent, else append. You may also add a
one-line **What worked well** note. Caps: at most three findings, terse; append "· seen again" rather
than duplicating (recurrence across phases is exactly the signal `/proj-harness` acts on); a fix that
would weaken a non-negotiable gate (`lint.sh`, the sandbox drive, an `invariants.md` item) is
`severity=high` and must say so. **Records only.** Next unused `F#`, always `status=open`, appended
**outside** any code fence:

```markdown
## F<n> — <one-line title>
`origin=proj-build:{id} severity=<high|medium|low> category=<instruction|steering|tooling|template|missing-guidance> status=open target=<best-guess file>`
- **What happened:** <what the skill made you do, or fail to do>.
- **Skill cause:** <why it's the instructions' fault — not yours, not the task's>.
- **Recommended fix:** <the change to the skill/template/script>.
- **Confidence:** <high|med|low> · **Effort:** <small|medium|large>
```

`proj-build` is **the richest source** and runs **per phase across separate invocations** — appending
to the file, not to memory, is exactly how you preserve a finding a context reset would erase. The note
rides in this phase's atomic commit below.

### Step 7 — Commit (atomic code + state)
```
git add -A
git commit -m "[{category}] Build {slug} {id}: {phase name}"
```
`{category}` is the `AGENTS.md` category of this branch's **shape commit** — the oldest entry in the
*Commits on branch* injection — which is what `/proj-plan` follows too. Fall back to `kind` only when
no prior branch commit exists. The two are different taxonomies: `kind` is
`feature | fix | refactor | docs` and has no `harness` or `release` member, and a `.agents/` cycle,
which the factory's own self-improvement loop produces, is exactly where they diverge. There is **no
`WIP:` prefix**: every branch commit is squashed into the single PR-title commit at `/proj-publish`,
so subjects only need to read well in the PR's commits tab. Keep the subject inside 72 characters. For
a remediation commit, keep the `{id}` and describe the fix, e.g.
`[fix] Build {slug} P1: F1 — keep hyphens out of FTS5 prefix terms`. Use the body for non-obvious
decisions, for a `TECH.md` amendment, or to record what was removed; a body records a decision, a
rejected alternative, or a consequence the diff does not show, and never narrates the diff. **No
`Co-Authored-By:` trailer.** Do not push. `bundle` → one commit for the whole run.

### Step 8 — Continue or stop
Default, or at a phase boundary: stop and report. `through`/`next`/multi: loop to Step 2 with the next
phase until the stop condition, a phase boundary (unless `no-pause`), or a STOP from Steps 3–4.

### Final report
Phases completed (ids plus one-line summaries), any `TECH.md` amendments and why, any `[ ]` deferred,
the new `current_phase` and statuses, verify-gate results with the post-conditions actually observed,
and open questions or blockers. When the FSM is fully done (`status: in_review`), recommend a
**clean-session** `/proj-review`.

## Examples

- `/proj-build` — next incomplete phase, run its verify, one clean commit, stop and report.
- `/proj-build status` — FSM state plus last commit; no work.
- `/proj-build dry run phase P3` — report what P3 would do; no edits.
- `/proj-build through P3` — run each incomplete phase up to P3, one commit each.

## Notes

- Never advance state on a checkbox alone, and never on exit 0 alone. The asserted post-condition is
  the gate.
- Keep `current_phase` accurate even when stopping mid-phase on a STOP condition; do not advance past
  a partially done phase.
- This skill never ships to `main`, squashes, or force-pushes — that is `/proj-publish`, and because a
  push to `main` fires the image build and the Geddes poller, it is also the deploy. Out of scope
  (`merge`, `push`, `open PR`, `bump version`) → STOP and point at `/proj-publish` or `/proj-release`.
