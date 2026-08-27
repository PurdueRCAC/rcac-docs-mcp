# REVIEW — {Title}

> Adversarial QA by `proj-review`, run in an isolated context. The correctness pass grades the branch
> diff against [`GOAL.md`](GOAL.md) plus the `AGENTS.md` invariants **only** — it does not see
> `PLAN.md` or `TECH.md`, which would invite grading-its-own-homework. Every finding cites an
> **executed** command, not an assertion.

- **Reviewed commit:** {sha}  ·  **Base:** {base}  ·  **Date:** {YYYY-MM-DD}
- **Verdict:** approved | changes-requested
- **Cycle:** {n} of ≤3 — mirrors `review.cycle` in `TECH.md` (escalate on non-convergence)

## Verification run

Commands actually executed and their outcomes. This is the spine of the review.

- `uv run pytest -q` → <result — **state the passed and skipped counts**, not just the exit status>
- `.agents/factory/bin/lint.sh` → <result>
- `.agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index'` → <observed behavior>
- <further drives: incremental reindex, a `doc_search.fn(...)` / `doc_load.fn(...)` call against the
  sandbox index, failure paths, the specific post-conditions asserted>

A suite that exits 0 with the RCAC-Docs submodule uninitialized has skipped its integration tests.
Report the skip count; a green run that proved nothing is a finding about this review, not a pass.

## Requirement → evidence matrix

Bidirectional traceability. Flag requirements with no implementing change **and** changes that map to
no requirement (scope creep).

| R-ID | Implemented by (module/function) | Verified how (command + post-condition) | Status |
|------|----------------------------------|------------------------------------------|--------|
| R1   | <…>                              | <…>                                      | ✅ / ❌ |

Unmapped changes (possible scope creep): <list or "none">.

Requirements taken on trust (cannot be observed from the sandbox — typically anything that only
happens in the deployed pod): <list or "none">. Anything here must already be named in `GOAL.md` or
`PLAN.md` §5; a criterion silently downgraded to trust during review is itself a finding.

## Findings

Severity: **CRITICAL** (any `invariants.md` §1–§11 violation is auto-CRITICAL) · **HIGH** ·
**MEDIUM** · **LOW**. Verdict: **CONFIRMED** (reproduced) versus **PLAUSIBLE** (suspected, needs human
triage). Only CONFIRMED findings auto-loop to `proj-build`.

### [CRITICAL/CONFIRMED] <one-line defect>
- **Where:** `src/rcac_docs_mcp/<module>.py:NNN` (`function_name`)
- **Failure scenario:** <concrete state and inputs → wrong output, wrong exit code, wrong index>
- **Evidence:** <the command run and what it showed>
- **Touches invariant / requirement:** <§n or R-ID>

### Correction to cycle {n}

Written only when this cycle's measurements overturn or narrow an earlier cycle's finding: what that
cycle claimed, what was measured here, which account supersedes. The earlier section stays as
written; without this note its claim reads as current to whoever arrives later.

## Human-gate triggers

Set if any CONFIRMED finding touches a high-blast-radius file (`index/indexer.py`,
`index/database.py`, `index/schema.sql`, `tools.py`, `site.py`, `Dockerfile`,
`docker-entrypoint.sh`, `.github/workflows/build-and-push.yml`) or a data-integrity, tool-surface or
unauthenticated-posture invariant (§1, §2, §4). These always require human sign-off before
`proj-publish`, regardless of auto-loop.

- <triggered? which finding? — if triggered: cleared by whom, on what date, on what grounds>

## Optional completeness sub-pass (separate reviewer; may see TECH.md)

- Was every planned phase actually shipped? Did scope balloon beyond the appetite? <notes>
