# REVIEW — `INSTRUCTIONS.md` ships to nobody

> Adversarial QA by `proj-review`, run in an isolated context. The correctness pass grades the branch
> diff against [`GOAL.md`](GOAL.md) plus the `AGENTS.md` invariants **only** — it does not see
> `PLAN.md` or `TECH.md`, which would invite grading-its-own-homework. Every finding cites an
> **executed** command, not an assertion.

- **Reviewed commit:** 1270e6c322e04bccb20ecc68cbbe90fad83c20a3  ·  **Base:** main  ·  **Date:** 2026-09-04
- **Verdict:** approved
- **Cycle:** 1 of ≤3 — mirrors `review.cycle` in `TECH.md` (escalate on non-convergence)
- **Mode:** full blind pass over the spec-excluded diff (cycle 1, no scoping)

## Verification run

Commands actually executed and their outcomes. This is the spine of the review.

- `uv run pytest -q` → 110 passed, 0 skipped in 9.47s (orchestrator re-run; blind reviewer observed 110 passed in 10.81s). Fixture initialized; not the hollow 76/31 shape.
- `uv run pytest -q tests/test_docs_contract.py` → 3 passed.
- `.agents/factory/bin/lint.sh` → exit 0, `all checks passed`.
- R1: `git ls-files | grep -x INSTRUCTIONS.md` → no output, exit 1; `test ! -e INSTRUCTIONS.md` → exit 0. Diff shows the 32-line file mode-deleted.
- R2: `git grep -n "INSTRUCTIONS\.md" -- AGENTS.md .agents/factory/invariants.md` → no output, exit 1. Replacement prose graded against `server.py:62-90` — names the served literal correctly.
- R4: `git diff main -- src/rcac_docs_mcp/server.py` → empty; `git diff main...HEAD -- src/` → empty. No `src/` hunk at all.
- R5: `git grep -n "INSTRUCTIONS\.md" -- .dockerignore .agents/factory/bin/lint.sh src tests README.md` → exit 1.
- `git status --porcelain` → clean on reviewer hand-back and at orchestration.
- `temp_site.sh` drive skipped with recorded rationale: zero `src/` change means no behavioral surface to drive; the real site was never touched.

## Requirement → evidence matrix

| R-ID | Implemented by (module/function) | Verified how (command + post-condition) | Status |
|------|----------------------------------|------------------------------------------|--------|
| R1 | Deletion of `INSTRUCTIONS.md` | `git ls-files` census empty + `test ! -e` exit 0 + mode-deleted hunk in diff | ✅ |
| R2 | `AGENTS.md` (4 passages), `.agents/factory/invariants.md` (§1, §12) reworded onto `SERVER_INSTRUCTIONS` | Absence census exit 1 + prose read against `server.py:62-90`; §12 list is exactly `README.md`, `AGENTS.md`, `APP_HELP`, `SERVER_INSTRUCTIONS` | ✅ |
| R3 | `tests/test_docs_contract.py` (dropped `INSTRUCTIONS.md` from `_sources()`, two-copy docstring) | `pytest -q tests/test_docs_contract.py` → 3 passed; retired-advice absence holds (only the test's own `RETIRED_ADVICE` list names it) | ✅ |
| R4 | No change (served text untouched) | Empty `git diff main -- src/rcac_docs_mcp/server.py`; literal at `server.py:62-90` still passed as `instructions=` | ✅ |
| R5 | `.dockerignore` entry deleted; `lint.sh` pathspec narrowed to `-- src README.md` | Absence census exit 1 + `lint.sh` exit 0 | ✅ |

Unmapped changes (possible scope creep): none. `ROADMAP.md` (adopted-marker + body summary) and `issues/instructions-md-is-a-runtime-no-op.md` (`unshaped` → `adopted:…`) hunks are expected lifecycle bookkeeping, assert no behavior.

Requirements taken on trust: none. Every R-ID was observed from the sandbox.

## Findings

No CONFIRMED findings. No PLAUSIBLE findings. Two candidates were investigated under the refutation protocol and dropped: wider `.agents/factory/**` prose still naming the file (explicitly out of scope per GOAL non-goals; R2/R5 censuses are path-scoped and clean), and the `ROADMAP.md:26` / seed-issue mentions (retained historical record + lifecycle bookkeeping, exempt by the same non-goals).

## Human-gate triggers

Not triggered. No CONFIRMED finding; the diff touches none of the high-blast-radius files and violates no §1/§2/§4 invariant. Tool surface byte-identical, read-only posture and index pipeline untouched.

## Optional completeness sub-pass (separate reviewer; may see TECH.md)

Not run (not requested; `completeness` argument absent).
