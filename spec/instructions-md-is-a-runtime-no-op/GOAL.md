# GOAL — `INSTRUCTIONS.md` ships to nobody

> **Origin spec.** The *what* and *why* — the locked contract `proj-review` grades against.
> The *how* lives in [`PLAN.md`](PLAN.md) and [`TECH.md`](TECH.md), written by `proj-plan`.
> Keep this at the right altitude: solved and bounded, but not over-specified — leave design freedom
> for the plan. Edit requirements here; do not silently drift them during build.

- **slug:** instructions-md-is-a-runtime-no-op
- **kind:** refactor
- **appetite:** small

## Problem

Nothing reads `INSTRUCTIONS.md` at runtime. The text FastMCP serves in the
`initialize` response is `SERVER_INSTRUCTIONS`, the literal in
`src/rcac_docs_mcp/server.py:62-90` passed at `create_mcp_server()`. The
markdown file is a near-copy no code path opens.

The sufferer is the maintainer first, the downstream agent second. Four
load-bearing passages assert the reverse — `AGENTS.md:145`, `AGENTS.md:36`,
`.agents/factory/invariants.md:30`, `.agents/factory/invariants.md:175` — so a
maintainer correcting guidance edits the file the constitution names. That is
what happened in `c2c943a`: the wildcard fix went to `README.md` and
`INSTRUCTIONS.md`, `SERVER_INSTRUCTIONS` stayed stale, the change deployed, and
the live handshake served the old advice until the endpoint was probed
directly. Commit `7f8d98c` records that instance. An agent holding the stale
system prompt cannot ask a follow-up question; it pays a wasted round trip for
every query shaped by advice the engine contradicts.

`7f8d98c` added `tests/test_docs_contract.py`, which fails when the copies
disagree. The drift is now loud instead of silent. The copy it enforces is a
file nothing reads, kept in step forever — the wrong end of the problem.

## Outcome / vision

One place holds the agent-facing instructions, and the constitution names it.
`SERVER_INSTRUCTIONS` in `server.py` is the only editable source;
`INSTRUCTIONS.md` does not exist; `AGENTS.md` and `invariants.md` state the
served copy correctly. Drift is impossible by construction rather than caught
by a three-way comparison.

## Acceptance criteria (the contract)

- **R1** — The repository SHALL hold exactly one editable source for the
  served instructions text, and `INSTRUCTIONS.md` SHALL NOT exist as a tracked
  file. Checked by `git ls-files | grep -x INSTRUCTIONS.md` returning nothing
  and `test ! -e INSTRUCTIONS.md`.
- **R2** — `AGENTS.md` and `.agents/factory/invariants.md` SHALL name
  `SERVER_INSTRUCTIONS` in `server.py` as the text served to downstream
  agents, and the §12 same-commit list SHALL contain the surviving set only
  (`README.md`, `AGENTS.md`, `APP_HELP`, `SERVER_INSTRUCTIONS`). Checked by
  `git grep -n "INSTRUCTIONS\.md" -- AGENTS.md .agents/factory/invariants.md`
  returning nothing, with the reviewer grading the replacement prose against
  `server.py`.
- **R3** — `tests/test_docs_contract.py` SHALL NOT read `INSTRUCTIONS.md` and
  SHALL still prove `README.md` agrees with `SERVER_INSTRUCTIONS`, including
  the absence of the retired wildcard advice. Checked by
  `uv run pytest -q tests/test_docs_contract.py`.
- **R4** — The served instructions text itself SHALL NOT change in this cycle:
  no wording change rides along with the deletion. Checked by
  `git diff main -- src/rcac_docs_mcp/server.py` showing no hunk inside the
  `SERVER_INSTRUCTIONS` literal, confirmed by the reviewer.
- **R5** — The mechanical stragglers SHALL follow the deletion: the
  `.dockerignore` entry goes, and `.agents/factory/bin/lint.sh` no longer
  names the deleted file in its pathspec. Checked by
  `git grep -n "INSTRUCTIONS\.md" -- .dockerignore
  .agents/factory/bin/lint.sh src tests README.md` returning nothing, and
  `lint.sh` still exiting 0.

## Non-goals (no-gos)

- No rewrite of the served guidance. A prompt that reads differently to an
  agent is a behavior change with its own cycle.
- No `importlib.resources` / package-data alternative. That fork was offered
  in the seed and refused at shaping; the literal stays.
- No change to the tool surface, the transports, the site layout, or the
  index pipeline.
- No refresh of retained historical records (`spec/docs-only-refactor/`,
  commit bodies) or of wider factory prose beyond the constitution and the
  mechanical references R2 and R5 name. History describes what was true when
  written.
- `APP_HELP` in `__init__.py` is unaffected. Rechecked at promotion: it
  carries no search guidance.

## Clarifications

- **Q:** Delete `INSTRUCTIONS.md`, or make it the runtime source via
  `importlib.resources`? — **A:** Delete. The cheapest answer removes the
  packaging failure mode R3 of the seed was written to catch
  (resolved 2026-09-03 with the human).
- **Q:** Do `kind: refactor` / `appetite: small` from the seed still hold? —
  **A:** Yes. No packaging change, no behavior change; the diff is a deletion
  plus constitution and test edits (resolved 2026-09-03 at shaping).

## Related materials

- Seed: `issues/instructions-md-is-a-runtime-no-op.md`
- Instance: commits `c2c943a` (fixed the wrong files) and `7f8d98c` (the
  contract test that made the drift loud)
- Constitution: `AGENTS.md:36`, `AGENTS.md:145`, `AGENTS.md:292-309`,
  `.agents/factory/invariants.md:30`, `.agents/factory/invariants.md:171-178`
- Code: `src/rcac_docs_mcp/server.py:62-90` (`SERVER_INSTRUCTIONS`),
  `tests/test_docs_contract.py`, `.agents/factory/bin/lint.sh:117-118`,
  `.dockerignore:39`
