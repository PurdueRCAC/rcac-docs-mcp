# Review rubric — `proj-review`

The operating manual for the adversarial QA pass. The correctness reviewer runs in an **isolated
context** (a fresh subagent) and grades the branch diff against `GOAL.md` plus the `AGENTS.md`
invariants **only** — it is denied `PLAN.md` and `TECH.md`, because showing the author's own rationale
produces grading-its-own-homework and plan-sycophancy. Verification is by **executed command**, never
by assertion.

This repository has a real test suite, and that lowers the bar for this pass less than it looks. The
suite proves the server behaves; it does not check that the five places stating the tool contract
still agree, it does not notice prose rotting in `INSTRUCTIONS.md`, and it exits 0 with its
integration tests skipped. The executed-evidence requirement stands.

## What the reviewer sees

- ✅ `GOAL.md` — the locked contract (R-IDs)
- ✅ the branch diff **excluding `spec/`** (`git diff <base>...HEAD -- . ':(exclude)spec/'` — the spec
  artifacts are committed on the branch, so an unfiltered diff would hand the reviewer PLAN/TECH,
  research, and any prior cycle's REVIEW.md) and the full runnable repo. The commit log carries the
  same pathspec, and on a second cycle its **subjects** are dropped as well — they name the prior
  verdict and the finding ids that were remediated
- ✅ [`invariants.md`](invariants.md) and `AGENTS.md`
- ❌ **NOT** `PLAN.md`, `TECH.md`, `research/`, or `META.md` (`META.md` is the harness
  self-improvement log and leaks author intent, same as PLAN/TECH). The ban is on the content reaching
  context, not on opening the file: exclude `spec/` from every repository-wide search too —
  `git grep -n … -- . ':(exclude)spec/'`, `rg --glob '!spec/**' …` — since a sweep returns their
  matching lines without opening anything
- A **separate, later** completeness sub-pass *may* read `TECH.md` to ask "was every planned phase
  shipped? did scope balloon?" — kept isolated so the plan never contaminates the correctness verdict.

**The `spec/` exclusion bounds the artifacts, not the rationale.** A cycle that defers work writes the
evidence into `issues/{slug}.md` and its position into the `ROADMAP.md` entry — outside `spec/`, inside
the graded diff. A correctly filtered pass therefore reads the plan's conclusions in the seeds it is
grading. Excluding `issues/` is the wrong repair, because those files are part of the delta and a
deferral is graded work. Read what the diff's own new prose asserts as a claim to verify, not as a
question already settled.

## Scope — flag ONLY

1. **Correctness bugs** — wrong behavior, a crash, a corrupted or misplaced index.
2. **GOAL-requirement gaps** — an R-ID with no implementing change, or implemented incorrectly.
3. **`AGENTS.md` invariant violations** — auto-CRITICAL (see below).
4. **Scope creep** — changes that map to no R-ID. Report; do not necessarily block.

**Do not** report style nits, speculative hardening, or "you could also…" gold-plating. A gap-hunting
reviewer manufactures gaps, and manufactured gaps drive exactly the bloat this project is trying to
avoid. Silence on a clean diff is a valid and valuable result.

One exception: prose that violates the `AGENTS.md` § *Prose and comments* rules **in a diff hunk** is
in scope as a §12 finding. A comment that restates the code, or a README sentence padded with
marketing adjectives, costs a reader's confidence. In `INSTRUCTIONS.md` and `SERVER_INSTRUCTIONS` it
costs more than confidence — that text is a system prompt held by every downstream agent, so padding
there is billed on every call, forever. Flag it; do not rewrite the surrounding text that the diff did
not touch.

The hunk scoping inverts when the prose *is* the deliverable. On a documentation or prose-pass branch,
or against a `GOAL.md` criterion that is a whole-file census, the graded surface is the file: the work
is defined as the set of lines the pass chose not to change, and grading only what moved cannot see an
omission. Everywhere else the hunk still bounds it — a reviewer sweeping untouched prose on a feature
branch manufactures gaps.

## Reviewer conduct (the subagent)

- **Leave the tree clean.** Make no edits to tracked files. If you must instrument to reproduce a
  finding, revert it before returning — `git status --porcelain` must be empty when you hand back.
- **Drive the server in a sandbox**, always: `.agents/factory/bin/temp_site.sh …`. Never against the
  developer's real site (`$RCAC_DOCS_SITE` or `~/.local/share/rcac-docs-mcp`), which holds a full
  RCAC-Docs checkout and an index that took minutes to build.
- The **Verdict & loop** section below is the *orchestrator's* job, executed after you return. Do not
  write `REVIEW.md`, call `ReportFindings`, or run `set_phase.py` yourself. Your deliverable is the
  structured findings list and the requirement→evidence matrix you were asked for.

## Refutation protocol (mandatory)

For every candidate finding, **try to disprove it first**:

1. Reproduce it — run the exact command, construct the exact state, that triggers it.
2. Name the competing explanation for the same observation and say what in the constructed state
   rules it out. "Indexed nothing" and "indexed everything, then pruned it" both leave an empty
   table, and a one-document fixture cannot tell them apart. When severity or remedy turns on the
   mechanism, build at least two of whatever the mechanism ranges over.
3. Reproduced with the explanation distinguished → **CONFIRMED**. Reproduced with the mechanism
   still open → the observation stays CONFIRMED, narrowed to what the state showed, and the
   mechanism goes out separately as **PLAUSIBLE**; a verdict grades the claim a remediation would
   encode, not the exit code alone.
4. Plausible by reading but not reproduced → **PLAUSIBLE** (human triage; does not auto-loop).
5. Dissolves under scrutiny → drop it silently.

Default to dropping when uncertain. A single-model reviewer has self-preference bias even in a fresh
context, so lean on executed evidence, not opinion.

**What counts as evidence here.** A document or chunk count from the sandbox index; a search result
containing (or missing) a specific path; a captured stderr line; an exit code from a deliberately
malformed query; a second `--index` run proving incrementality; a `doc_search.fn(...)` return value.
"I read the code and it looks wrong" is a PLAUSIBLE at best.

## Verification traps in this repository

Standing knowledge, safe for a blind reviewer: a false green in a gate command is not author intent
and reveals nothing about the plan. A trap found during a review that is not feature-specific belongs
here, added by `/proj-harness` — never in `REVIEW.md`, which the next cycle's reviewer is correctly
forbidden to open, so a technique recorded there is rediscovered or walked into again.

- **The skipped-test false green.** `uv run pytest -q` exits 0 with the RCAC-Docs submodule absent,
  because roughly fourteen integration tests skip. A gate over indexer, tool, or CLI behavior must run
  through `.agents/factory/bin/temp_site.sh` (which exits 3 instead of passing) or assert the passed
  count. Report the skip count in the verification run.
- **The tools are `FunctionTool` objects, not functions.** `doc_search("x")` raises
  `TypeError: 'FunctionTool' object is not callable`. Call `doc_search.fn("x")`, as the suite does.
  A reviewer who reports the TypeError as a defect has found their own probe's bug.
- **`grep` may not be `grep`.** In an interactive agent shell it can be a function wrapping something
  else; under `/bin/sh` it is `/usr/bin/grep`. Run anything load-bearing through `/bin/sh -c` — which
  is exactly what `run_verify.py` does — before believing its exit status.
- **GNU-only regex escapes match nothing.** `\b`, `\?`, `\+`, `\d` and `\s` are GNU extensions. Git's
  POSIX `-E` engine and BSD `sed` silently match nothing with them, so the check reports clean against
  a tree that violates it. Spell boundaries out: `(^|[^A-Za-z0-9_])…([^A-Za-z0-9_]|$)`.
- **`git grep` and `git ls-files` ignore untracked files** unless given `--untracked` /
  `--others --exclude-standard`. A census run before the commit — which is when it matters — cannot
  see the file just written.
- **POSIX `errexit` exempts `!`.** `sh -c 'set -e; ! true; echo REACHED'` prints REACHED and exits 0.
  Write `if cmd; then echo "FAIL: …" >&2; exit 1; fi` instead.
- **An interpolated pathspec collapses under `zsh`.** `git grep -n PATTERN -- $PATHS`, where `$PATHS`
  holds several paths, searches one nonexistent path and exits clean: `zsh` does not word-split an
  unquoted parameter. Write the paths literally.
- **Hard-wrapped prose defeats `git grep`.** `README.md`, `AGENTS.md` and `INSTRUCTIONS.md` wrap near
  80–100 columns, so a unique phrase usually spans two lines and never matches. A gate asserting a
  sentence is gone reads green while the sentence is still there.

## Severity

| Severity | Meaning |
|---|---|
| **CRITICAL** | Index corruption or loss, a torn index served to live readers, a weakening of the read-only/unauthenticated posture, a breaking change to the two-tool contract, or **any** `invariants.md` §1–§11 violation. (A §12 project-conventions violation is **HIGH**.) |
| **HIGH** | A GOAL R-ID unmet or wrong; a real bug on a common path; a §12 violation. |
| **MEDIUM** | A bug on an edge path; a partial or fragile requirement. |
| **LOW** | Minor correctness risk; a documented behavior the diff quietly changed without saying so. |

## Verdict & loop (orchestrator only)

- Emit findings via `ReportFindings` (most severe first) **and** write `REVIEW.md`.
- **CONFIRMED** findings → set `TECH.md` `status: blocked` and `review.verdict: changes-requested`
  (via `set_phase.py`), then loop back to `proj-build`.
- **One exception:** a CONFIRMED finding against behavior that predates the diff *and* that a
  `GOAL.md` criterion requires preserving cannot be repaired this cycle without failing that
  criterion — the recurring shape is a parity criterion demanding the rewritten code reach the old
  code's verdict. Record it in `REVIEW.md` and defer it to `issues/{slug}.md` with a `ROADMAP.md`
  entry, committed *before* `set_phase.py --reviewed-commit`, or `proj-publish`'s staleness gate reads
  the seed as post-review drift. The verdict is otherwise unchanged by it. If either condition
  fails, it blocks.
- **PLAUSIBLE** findings → surface to the human for triage; do not auto-loop.
- Clean pass → `review.verdict: approved`; proceed to `proj-publish`.
- Cycle 2+ **appends** a dated `## Review cycle {n}` section to `REVIEW.md` — never overwrite an
  earlier cycle; the file is the cumulative record.
- **Bounded loop:** at most two or three review↔build cycles, graded against the durable
  `review.cycle` counter in `TECH.md` (auto-incremented by every `set_phase.py --verdict` other than
  `none`). On non-convergence, STOP and escalate — self-correction does not reliably converge.

## Mandatory human sign-off gate

Regardless of auto-loop, a human must approve before `proj-publish` whenever a CONFIRMED finding
touches:

- a high-blast-radius file: `src/rcac_docs_mcp/index/indexer.py`,
  `src/rcac_docs_mcp/index/database.py`, `src/rcac_docs_mcp/index/schema.sql`,
  `src/rcac_docs_mcp/tools.py`, `src/rcac_docs_mcp/site.py`, `Dockerfile`, `docker-entrypoint.sh`,
  or `.github/workflows/build-and-push.yml`; **or**
- a tool-surface, unauthenticated-posture, or index-integrity invariant (§1, §2, §4).

The CI workflow is on that list because a merge to `main` is a deploy: an edit there changes what
reaches production and when, and nothing downstream re-checks it.

A triggered gate is cleared by the human, never by the agent's own reading of the finding. The
sign-off may be given inline and the run continues from there, but the clearance is recorded in
`REVIEW.md` under *Human-gate triggers*: which finding fired it, who cleared it, the date, and the
grounds. Nothing downstream reconstructs that — `proj-publish` gates on the review verdict and the
staleness check, and never asks whether a gate fired.

## Optional debate variant (high-risk diffs)

For a diff touching a high-blast-radius file, run **two** independent fresh reviewers — one
instructed to argue "ship", one to argue "block" — and reconcile. Independent instances beat
single-model introspection. Reserve it for genuinely high-risk changes; it costs twice as much.
