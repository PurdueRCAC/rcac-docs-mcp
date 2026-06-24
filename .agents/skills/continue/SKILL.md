---
name: continue
description: Resume rcac-docs-mcp implementation by executing the next incomplete stage from ROADMAP.md. The default behavior is conservative — one stage at a time, with a single WIP commit, then stop and report for review. Free-form arguments can target a specific stage, run several stages in sequence, do a dry run that surfaces the plan without executing, or just report current state. The skill is wired to ROADMAP.md's YAML frontmatter (current_stage, stages_completed), per-stage checklists, the pytest verification gate, and the wip-branch commit workflow.
---

# Continue (Resume Implementation)

## When to Use

Invoke `/continue` when picking up `rcac-docs-mcp` work in a fresh session —
or after a review checkpoint — and you want the next slice of `ROADMAP.md`
executed without re-explaining the whole project. The skill is designed for
the *one-stage-then-stop* rhythm: scale up with arguments when you trust the
next chunk, or scale down to a dry run when you don't.

This is a general stage-based executor for the repo's `ROADMAP.md`. It is not
tied to any single feature — point it at whatever stages the current
`ROADMAP.md` defines. The associated implementation plan (when one exists) is
referenced by `plan_id` in the ROADMAP frontmatter; read it for detail but
treat `ROADMAP.md` as the resume ground truth.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Argument Parsing

If any text was passed with the invocation, parse it case-insensitively
against the patterns below. If the instruction is ambiguous or contradicts
itself, STOP and ask the user to clarify rather than guess.

- `stage N` / `at N` / `from N` / `start at N` → start at stage `N` instead
  of the `current_stage` recorded in `ROADMAP.md` frontmatter
- `through N` / `up to N` / `until N` → execute the next incomplete stage and
  continue forward, stopping after stage `N` completes
- `next N` / `N stages` → execute the next `N` incomplete stages in order
  (each gets its own commit)
- `stages X..Y` → execute all incomplete stages from `X` through `Y`,
  stopping at each stage boundary unless `skip review` is also passed
- `dry run` / `plan only` / `preview` → identify the target stage(s) and read
  all relevant context (ROADMAP, the linked plan, the files to be touched),
  but **do not** edit files, run tools, or commit — just report the plan for
  the user to approve
- `status` / `report` / `review only` → summarize the current ROADMAP state
  (current stage, completed stages, next stage, last commit on `wip`) and
  stop. No implementation, no commits.
- `skip review` / `no checkpoint` → after completing the requested stage(s),
  do NOT stop at the natural checkpoint; continue to the next stage. Use
  sparingly; the default checkpoints exist for a reason.
- `bundle` → collapse the requested run into a single WIP commit instead of
  one-commit-per-stage. Useful only for tightly coupled mechanical stages.

If no arguments were passed, run the default *next-stage-then-stop* path
(Steps 1–6 below; skip Step 0).

## Safety Principles

- **`ROADMAP.md` is the resume ground truth.** Its YAML frontmatter carries
  `current_stage` and `stages_completed`; the body carries one checklist per
  stage. The frontmatter and the checkboxes must agree on what's done. If
  they disagree, STOP and report — do not guess which is right.
- **The linked plan is the detail, the ROADMAP is the tracker.** If
  `ROADMAP.md` frontmatter has a `plan_id`, read that plan for the rationale
  and specifics of a stage, but record progress only in `ROADMAP.md`. If the
  plan and the ROADMAP disagree on what a stage entails, surface the
  discrepancy rather than silently following one.
- **A stage is the unit of work.** Execute every `[ ]` item in the target
  stage, not just the first. A stage is `complete` only when all its items
  are done and the verification gate for that stage passes (or is explicitly,
  documented-as skippable for that stage).
- **Mid-refactor red is expected and documented.** This package is
  intentionally **non-importable between Stage 1 and the end of Stage 3** of
  the refactor (deletions precede the rewire). During those stages the
  `pytest` gate is expected to fail to collect; that is NOT a STOP condition
  by itself — note it in the report and proceed. The gate must be green again
  by the end of Stage 4 and at Stage 6. Outside that window, a red gate IS a
  STOP condition.
- **`wip` branch only.** All commits land on `wip` with `WIP: ` prefixes (per
  the user's wip-workflow rule). Never commit to `main` from this skill.
  Never squash or force-push from this skill — that is `/release`'s job.
- **Co-author every commit** with `Co-Authored-By: Oz <oz-agent@warp.dev>` on
  its own line at the end of the commit message body.
- **The user has aliased `rm` away — use `del`** for any file removals. When
  a stage calls for removing tracked files, prefer `git rm`; for untracked
  files use `del`.
- **Honor the project's code conventions** (from the user's rules): SPDX
  headers, the structured import blocks with section comments
  (`# Standard libs`, `# External libs`, `# Internal libs`), the
  `# Public interface` + `__all__` label, double blank lines between
  module-level definitions, and CmdKit-style CLI layout. Match the
  surrounding code.
- **If something doesn't fit the plan, STOP and ask.** Do not improvise
  around missing context, ambiguous stage definitions, unexpected test
  failures outside the documented mid-refactor window, or ROADMAP ↔ plan
  divergence.

## Procedure

### Step 0 — Status / dry-run only (when requested)

Skip entirely unless `status`, `report`, `review only`, `dry run`,
`plan only`, or `preview` was passed.

When `status` / `report` / `review only`:

1. Read `ROADMAP.md` frontmatter (`current_stage`, `stages_completed`,
   `last_updated`, `plan_id`).
2. Identify the next incomplete stage by scanning `[ ]` checkboxes in
   document order AND cross-check against `current_stage`.
3. Report a compact summary: current stage, stages completed, next stage
   title and goal, and the timestamp/subject of the last commit on `wip`.
4. Stop. No file edits. No commits.

When `dry run` / `plan only` / `preview`:

1. Do everything in Steps 1 and 2 below (identify the target and load
   context), then report the plan that *would* be executed — checklist
   items, files that will be touched, the verification gate, and the expected
   commit message — and stop.
2. Do not edit files. Do not run `uv`, `pytest`, `git commit`, or any other
   side-effecting tool.

### Step 1 — Pre-flight checks (always)

1. Working directory must be clean:
   ```bash
   git status --porcelain
   ```
   Non-empty output → STOP and report (commit, stash, or discard first).
2. Current branch must be `wip`:
   ```bash
   git branch --show-current
   ```
   If not on `wip`, STOP and report. Do not auto-switch.
3. Sync with origin (read-only), if a remote exists:
   ```bash
   git remote -v && git fetch origin || true
   ```
   A missing origin is not an error; proceed.

### Step 2 — Identify the target stage and load context

1. Read `ROADMAP.md` to determine the target stage:
   - Default: the first stage whose checklist still has `[ ]` items, starting
     from `current_stage`. Confirm it agrees with the frontmatter; if not,
     STOP.
   - `stage N` / `at N`: that stage, regardless of `current_stage`.
   - `through N` / `next N` / `stages X..Y`: the first incomplete stage; track
     the stop condition for Step 6.
2. If frontmatter has a `plan_id`, read the linked plan's section for the
   target stage so you implement against the real intent, not just the
   checklist shorthand.
3. Read the actual files the stage will touch before editing them — do not
   edit blind. For this refactor the load-bearing files recur across stages
   (`pyproject.toml`, `src/` package modules, `server.py`, the CLI
   `__init__.py`, `tests/`); know their current state first.

### Step 3 — Implement the stage

1. Execute every unchecked item in the target stage's checklist. Do not stop
   at the first one — the stage is the unit of work.
2. Apply the project code conventions (SPDX headers, structured import
   blocks, `__all__`, spacing) to any new or moved modules.
3. After substantive changes, sanity-check import/collection where it is
   *expected* to be green:
   ```bash
   uv run python -c "import rcac_docs_mcp" 2>&1 | tail -5   # post-rename stages
   ```
   Skip this check (with a note) during the documented non-importable window
   (Stage 1 → end of Stage 3), or when the package has not yet been renamed.
4. If implementation surfaces a real correction to the linked plan (a stale
   path, a missed dependency), STOP and surface it for confirmation before
   editing the authoritative plan document.
5. If implementation reveals a blocker not covered by the plan or the
   documented mid-refactor red window, STOP and report.

### Step 4 — Update `ROADMAP.md` (the resume contract)

1. Check off every completed `[ ]` item under the stage, turning them into
   `[x]`.
2. Update the YAML frontmatter:
   - `current_stage`: advance to the next incomplete stage number.
   - `stages_completed`: append the just-completed stage number (as a string,
     e.g. `"2"`) only if every item in that stage is now `[x]`. Partial
     completion earns nothing.
   - `last_updated`: set to the current ISO-8601 UTC date.

### Step 5 — Commit

Compose a single `WIP:` commit per stage (default) or per run (when `bundle`
was passed). The commit message should:

- **First line names the stage**: `WIP: Stage 2 — restructure & rename package`.
- Optional body: 1–3 short lines describing decisions made and any deferred
  items, only when those decisions aren't obvious from the diff.
- Final line of the body: `Co-Authored-By: Oz <oz-agent@warp.dev>`.

```bash
git add -A
git commit -m "WIP: <stage summary>

<optional body explaining decisions>

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

Do **not** push by default. Pushing/shipping is `/release`'s job. (Narrow
exception: if the user explicitly invokes `/continue ... and push wip` *and* a
remote exists, run `git push origin wip` after the final commit — never
`--force` from this skill.)

### Step 6 — Continue or stop

- Default (no arguments): stop and report.
- `through N` / `next N` / `stages X..Y`: loop back to Step 2 with the next
  incomplete stage. Stop when:
  1. The stop condition is reached (stage `N` completed, or `N` stages done,
     or stage `Y` reached).
  2. A natural checkpoint is hit (a stage boundary). Stop here unless
     `skip review` was passed.
  3. Step 3 surfaces a STOP condition (blocker, plan divergence, or an
     unexpected red gate outside the documented mid-refactor window).

### Step 7 — Verification gate + final report

Run the verification gate for the stage(s) touched this run:

```bash
uv sync --quiet
uv run pytest -q
```

Interpreting the gate:
- **Stages 1–3 (non-importable window):** collection/import failure is
  expected — record it and continue. Do not treat it as a regression.
- **Stage 4 onward:** the suite must collect and pass (submodule-dependent
  tests skip cleanly when `tests/fixtures/RCAC-Docs` is not initialized;
  that's fine).
- **Stage 6:** also smoke-test the CLI and an index build, per the ROADMAP
  Stage 6 checklist (`rcac-docs-mcp --help`, `--index-docs --docs-path
  tests/fixtures/RCAC-Docs`).

Then produce a compact report:

- What was completed (stage IDs and one-line summaries).
- Any `[ ]` items intentionally deferred and why.
- Updated `current_stage` and `stages_completed`.
- Verification-gate results (or why they were expected-red / skipped).
- Any open questions or blockers for Geoffrey.

## Examples

### Default — execute the next stage and stop

```
/continue
```

Reads `current_stage` from `ROADMAP.md`, executes every `[ ]` item in that
stage honoring the project conventions, updates the checklist + frontmatter,
commits with a `WIP:` prefix naming the stage and the Oz co-author line, runs
the pytest gate (noting expected-red during the mid-refactor window), then
stops and reports.

### Status check (no work)

```
/continue status
```

Reports current stage, completed stages, next stage, and last commit on
`wip`. No edits. No commits.

### Dry run before approving a chunk of work

```
/continue dry run stage 3
```

Reads the linked plan's Stage 3 section and the files Stage 3 touches
(`server.py`, the CLI `__init__.py`, the new `site.py`), and reports the plan
it *would* execute — files, commit message, frontmatter deltas. No edits. No
commits.

### Drive several stages, stopping at a target

```
/continue through 4
```

Executes the next incomplete stage and each one after it, one `WIP:` commit
per stage, stopping after Stage 4 (the point where the suite is green again).
Stops at each stage boundary for review unless `skip review` is passed.

### Bundle tightly-coupled stages into one commit

```
/continue stages 2..3 bundle skip review
```

Runs the rename/restructure and the server/CLI rewire as one continuous
change and lands a single `WIP:` commit. Use only when the stages are
mechanically coupled and you don't want an intermediate non-importable commit.

## Notes

- `current_stage` and `stages_completed` are the agent's resume markers. Keep
  both accurate even when stopping mid-stage due to a STOP condition; in that
  case do **not** advance `current_stage` past the partially-completed stage.
- Commit message bodies should explain *why* a decision was made, not what the
  diff shows.
- This skill never ships to `main`, squashes, or force-pushes — that's
  `/release`. If the user's instruction includes something out of scope (e.g.
  `merge to main`, `squash`, `cherry-pick`, `bump version`), STOP and point
  them at `/release`.
