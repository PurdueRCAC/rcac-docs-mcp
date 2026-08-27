---
name: proj-plan
description: >-
  Turn a shaped spec/{slug}/GOAL.md into a design and a phased roadmap. Runs an invariant gate against
  AGENTS.md, fans out read-only research subagents (scaled to appetite; codebase- and
  FTS5/FastMCP-docs-first), synthesizes spec/{slug}/PLAN.md, re-checks invariants, and generates
  spec/{slug}/TECH.md — the phased YAML FSM driven by /proj-build. Second step of the software-factory
  lifecycle (see .agents/factory/methodology.md).
disable-model-invocation: true
argument-hint: "[appetite small|big] [skip research] [status]"
allowed-tools: Read, Write, Edit, Grep, Glob, Agent, AskUserQuestion, WebSearch, WebFetch, Bash(git status *), Bash(git branch *), Bash(git rev-parse *), Bash(git log *), Bash(git grep *), Bash(git submodule *), Bash(git add *), Bash(git commit *), Bash(uv run *), Bash(.agents/factory/bin/*), Bash(sh -c *), Bash(ls *), Bash(head *), Bash(grep *), Bash(test *), Bash(mktemp *), Bash(cp *), Bash(echo *)
---

# proj-plan — research → PLAN → TECH

## When to Use

Invoke `/proj-plan` after `/proj-feature` has landed a quality `GOAL.md` on a feature/fix/docs branch.
It produces the design (`PLAN.md`), optional backing `research/`, and the phased FSM (`TECH.md`), then
stops for your sign-off before `/proj-build` touches code. Depth scales to the GOAL's `appetite`.

Reference: [`methodology.md`](../../factory/methodology.md),
[`invariants.md`](../../factory/invariants.md) (the gate), and the templates
[`PLAN.md`](../../factory/templates/PLAN.md) / [`TECH.md`](../../factory/templates/TECH.md).

**Harness portability.** Runs on any harness — see [`portability.md`](../../factory/portability.md).
Fallbacks: if the *Current state* block is not auto-injected, run those commands yourself in Step 1;
ask in plain text and STOP if `AskUserQuestion` is unavailable; and **if subagents are unavailable or
the session disallows them, do the research fan-out sequentially yourself** (Step 3 gives the
fallback).

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current`
- Tree: !`git status --porcelain | head -n 20`
- Spec artifacts: !`sh -c 'ls -1d spec/*/ 2>/dev/null' | head -n 40 | grep . || echo "(none)"`
- Docs fixture: !`test -d tests/fixtures/RCAC-Docs/docs && echo "present" || echo "ABSENT — temp_site.sh exits 3 and 31 tests skip"`

## Argument Parsing

- `skip research` / `no research` → collapse to a lean plan (no fan-out) regardless of appetite.
- `appetite small|big` → override the GOAL's appetite for this planning run.
- `status` / `report` → summarize what artifacts already exist for this slug and what is missing; no
  work.

## Safety Principles

- **On a feature/fix/docs branch, never `main`.** Derive `{slug}` = branch minus its
  `feature/`|`fix/`|`docs/` prefix. STOP if on the base branch or the tree is dirty.
- **`GOAL.md` must exist, be committed, and carry no unresolved `[NEEDS CLARIFICATION]` markers.** If
  markers remain, STOP and send the human back to `/proj-feature`.
- **Research is strictly read-only.** Bias it to three sources in this order: the code under
  `src/rcac_docs_mcp/`, the retained decision records (`spec/docs-only-refactor/`, `AGENTS.md`,
  [`invariants.md`](../../factory/invariants.md) — where the rejected alternatives are written down),
  and the reference documentation for the layer in question (SQLite FTS5, FastMCP, the upstream
  RCAC-Docs repository). Reach for the web only for genuinely external unknowns — a FastMCP API
  change, an FTS5 semantic, what upstream RCAC-Docs looks like today versus at the pinned submodule.
- **Never build.** No edits to `src/rcac_docs_mcp/**`. That is `/proj-build`. A throwaway copy outside
  the working tree is not a build: it is the sanctioned way to prove a `verify:` gate can go green.
- **The invariant gate is mandatory**, at both checkpoints. Any bend gets recorded in PLAN's deviation
  table, never applied silently.

## Procedure

### Step 1 — Pre-flight & load
1. Confirm feature/fix/docs branch and clean tree; resolve `{slug}`.
2. Read `spec/{slug}/GOAL.md` (appetite, R-IDs, non-goals) and
   [`invariants.md`](../../factory/invariants.md).
3. If the *Docs fixture* line above says ABSENT, initialize it now —
   `git submodule update --init tests/fixtures/RCAC-Docs` — or Step 6 cannot run a single sandbox
   gate and will mistake exit 3 for a red assertion.

### Step 2 — Invariant gate #1 (pre-research sanity)
Given the GOAL's intent, list the invariant sections (§1–§12) this change will touch and confirm the
intent is even sane against them. A change to the render pipeline must respect §6's Jinja2-before-
snippets ordering; a change to query handling must keep §7's guarantee that every normalized query is
valid FTS5 for every input; anything that writes the index must preserve §4's atomic publication onto
a shared PVC. If the GOAL is fundamentally at odds with an invariant, STOP and escalate.

### Step 3 — Research fan-out (appetite-scaled)

Appetite governs the depth; `kind` does not. `/proj-feature` already folded `kind` into it, so a fix
carrying `appetite: big` fans out like any other big change.

- **`appetite: small` / `skip research`:** skip the fan-out. Do at most a couple of targeted reads
  yourself, and proceed to Step 4 with a lean plan; `research/` may be omitted.

  **Exception — diagnostic fixes.** When the GOAL's root cause is *unknown*, or it explicitly requests
  diagnosis, run the full fan-out regardless of `kind`/`appetite`. For such a fix the investigation
  *is* the deliverable, and skipping it yields a guess. `kind` and `appetite` are proxies for "is the
  root cause known?"; when they disagree with the GOAL, the GOAL wins.

  **Exception — high blast radius.** Run the full fan-out whenever the change can alter what a
  high-blast-radius file on `invariants.md`'s list *does* (`index/indexer.py`, `index/database.py`,
  `index/schema.sql`, `tools.py`, `site.py`, `Dockerfile`, `docker-entrypoint.sh`,
  `.github/workflows/build-and-push.yml`), regardless of appetite. A "small" edit there still needs
  the exact contracts pinned before design. The trigger is behavioral, not positional: a pass provably
  confined to comments, docstrings or documentation scales research to appetite instead. Returned text
  is the near miss — the string `doc_search` hands back, a line of `SERVER_INSTRUCTIONS`, an
  `APP_HELP` paragraph is the contract every downstream agent holds, so capture the pre-change output
  as a `research/` baseline even when the fan-out is skipped.

  An explicit `skip research` argument stays a human override and still skips.

- **`appetite: big`:** identify the *rabbit holes* — the unknowns that could blow the appetite. In this
  project they are usually one of four:

  - **An FTS5 or SQLite semantic that must be verified rather than assumed** — what the
    `porter unicode61 remove_diacritics 1` tokenizer does to a term, how the query parser reads an
    operator or a bare hyphen, what `snippet()` returns at a chunk boundary, when the external-content
    triggers fire, and what `VACUUM INTO` actually guarantees about the seeded temp database.
  - **The upstream RCAC-Docs pipeline** — pymdownx `--8<--` snippet resolution, the docs repo's own
    `main.py` macros, `mkdocs.yml` `extra:` and its `!ENV`, `!relative` and `!!python/name:` tags. The
    fixture is a **pinned submodule**, so it is evidence about that commit and not about today's
    upstream; a brief resting on it says which.
  - **The FastMCP surface** — tool registration and what `mcp_tool` wraps, server `instructions`,
    custom routes, and how `stdio` differs from `http` in what a client sees.
  - **Container and deploy behavior only observable in the Geddes pod** — the shared PVC, the
    `:latest` digest poller, cold-start index time. None of it can be reproduced locally, so a brief
    here states an assumption and **says that it is taken on trust**, and PLAN §5 carries it forward.

  Launch **read-only research subagents in parallel** (`Agent`), one per topic, breadth-first:
  - Each gets the topic, GOAL context, explicit scope boundaries, and the instruction to produce a
    brief of roughly one to two thousand tokens and **write it to
    `spec/{slug}/research/NN-topic.md`** — use `general-purpose` so it can write, and number `01`,
    `02`, … with distinct paths so there are no write conflicts.
  - A research agent **may** drive the server read-only through
    `.agents/factory/bin/temp_site.sh`; that is the cheapest way to answer "what does it actually do".
    It must not edit tracked files, and it must not drive the developer's real site. The MCP tools are
    FastMCP `FunctionTool` objects: `doc_search.fn("slurm")`, never `doc_search("slurm")`.
  - Scale count to appetite. Log what you fan out.
  - **Consume each agent's returned summary; never read its transcript sidecar** — it floods context.
    **No fan-out available?** Whether the harness lacks subagents or the session disallows spawning
    them, do the research yourself, sequentially, writing the same files. The deliverable is the same.
- Read the returned briefs and synthesize **`spec/{slug}/research/00-digest.md`** — the consolidated
  decisions, resolving any cross-brief contradiction with a single recommendation each.

### Step 4 — Write `PLAN.md`
From the template: **Summary**; **Design** at the right altitude, naming the modules under
`src/rcac_docs_mcp/` that change and what the index schema and site layout look like afterwards; the
**requirement → design map** with every R-ID covered; **rabbit holes resolved** (link the briefs);
**risks and open questions**, including anything only the deployed pod can confirm; and the
**verification strategy** that seeds each phase's `verify:` command.

Name which of the five places stating the same contract this change touches — `README.md`,
`INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` in `__init__.py`, `SERVER_INSTRUCTIONS` in `server.py`.
Drift between them ships to every downstream agent.

State explicitly what is being **removed**. A change that only adds is worth a second look in this
repository.

### Step 5 — Invariant gate #2 (post-design)
Re-walk the touched invariant sections against the *drafted design*. Fill PLAN's deviation
justification table for anything that bends an invariant or adds complexity, naming the simpler
alternative and why it was rejected. Empty is the goal. STOP and escalate on an unavoidable conflict
with a §1–§11 invariant.

### Step 6 — Generate `TECH.md` (the FSM)
Copy the template. Author phases as **vertical slices, not horizontal layers** — each independently
verifiable end to end, ordered core-and-novel first.

**Size circuit-breaker (soft):** if the roadmap needs more than about eight phases for a ten-module
server, the scope is probably too big — pause and reconsider with the human before committing a
mega-plan.

For each phase set `id`, `name`, `satisfies` (R-IDs), `depends_on`, `parallel` (**almost always
`false`** — `index/indexer.py`, `index/database.py`, `index/schema.sql` and `tools.py` are one
mechanism wearing four filenames, so two phases touching any of them are not independent; reserve
`true` for documentation-only or CI-only phases), `hammerable` (**false** for anything touching
`invariants.md` §1–§11), `hill: uphill`, and a real `verify:` command.

A `verify:` must name a **post-condition**, not merely exit 0. Build it from the three layers:
`uv run pytest -q`, `.agents/factory/bin/lint.sh`, and a drive under
`.agents/factory/bin/temp_site.sh` (`--empty` for anything touching the clone path). The suite layer
is the weakest of the three and lies by omission: with the docs submodule absent it reports
`76 passed, 31 skipped` and exits 0, so a gate reading only the exit status cannot tell a real pass
from a hollow one — assert the counts, or drive the sandbox, which exits 3 rather than reporting a
pass it cannot support. The canonical drives:

```
.agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index'
.agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index >/dev/null &&
  uv run python -c "from rcac_docs_mcp.tools import doc_search; print(doc_search.fn(\"slurm\"))"'
```

Any change to the user-facing surface gets a phase item for the same-commit rule — `README.md`,
`INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` in `__init__.py`, `SERVER_INSTRUCTIONS` in `server.py`. A
design that overturns an invariant gets one for `AGENTS.md` § *Invariants* and
`.agents/factory/invariants.md`: Step 5's deviation row records the bend, and the phase that lands the
code has to make those records true, or `/proj-review` grades correct code against the decision it
reversed.

Then read each phase's `verify:` back against that phase's own checklist and against the *Checked by*
clause of every R-ID in `satisfies`, both directions. A clause naming two checks is not covered by a
gate asserting one, and where the phase satisfies a criterion in two places — a returned tool string
and the `INSTRUCTIONS.md` sentence describing it — the gate names each. A gate can **contradict** an
item: `! git grep -q OLD_NAME` goes red the moment the same phase adds the design note that has to
name `OLD_NAME` to explain itself. A gate can also be **blind** to one, which is the quieter failure —
a phase mixing mechanical items with judgment items gets a gate shaped by the mechanical ones, goes
green, and the judgment item ships unchecked. An enumerated pathspec against a universally-quantified
criterion — "wherever it is stated", "every", "no file" — is that same failure wearing a scope: the
gate carries the criterion's quantifier, repository-wide with literal exclusions, and each exclusion
earns its reason in the phase body. Reconcile at plan time: narrow the gate's pathspec, extend it, or
state in the phase body that an item — or the part of a *Checked by* clause no command can decide — is
inspection-only so `/proj-review` reads it rather than trusting the gate.

Then run every `verify:` against the current tree before committing the plan, and run it through
`uv run .agents/factory/bin/run_verify.py spec/{slug}/TECH.md --phase P<n>` rather than by hand.
Copying a gate out of folded YAML means reflowing it, and reflowing is where a quoting error
enters; `/bin/sh -c ''` exits 0, so a hand-copy that silently produced nothing satisfies the
red check while proving nothing. A gate asserting a
post-condition the phase has not yet delivered must exit **non-zero**; one that exits 0 here is inert
until proven otherwise, and will still be inert when `/proj-build` reads its green as done. The failure
that motivates this is silent: a census gate whose pathspec is interpolated from a variable searches
one nonexistent path under `zsh`, which does not word-split, and reports a clean tree with thirteen
hits in it. Write the paths literally. A prose anchor fails the same way: `git grep` matches within
a line, and `README.md`, `AGENTS.md` and `INSTRUCTIONS.md` hard-wrap near 100 columns, so a phrase long
enough to be unique often spans two of them and never matches — the gate asserting a sentence is gone
reads green while the sentence is still there. Confirm the anchor matches the file as it stands before
gating on its absence.

Under `set -e`, POSIX exempts `! cmd` from errexit: `sh -c 'set -e; ! true; echo REACHED'` prints
`REACHED` and exits 0. A `! cmd` that is the gate's last command, or a link in an `&&` chain, still
reports its status — most committed gates use it that way and are correct. Appending a drive after
one silently disables it, and the gate then goes green with the assertion unmet. There, write
`if cmd; then echo "FAIL: …" >&2; exit 1; fi`, which also names the post-condition that failed.

Red is necessary, not sufficient. Read the failure output and confirm the gate died on the asserted
post-condition rather than on itself — a typo, a missing flag, an uninitialized submodule reported as
exit 3, a string the YAML layer mangled. In a multi-clause gate, confirm it died on the *first* unmet
clause: output from a later clause means an earlier assertion ran without aborting — usually a bare
`! cmd` with something after it — and the gate turns green the day those later clauses pass. A gate red
for its own reasons stays red through the build, walking `--record-attempt` toward the circuit breaker
at 3 while the code is correct. When the output does not settle it, prove the gate can go green: copy
the repository outside the working tree (`cp -R . "$(mktemp -d)/probe"`), apply the phase's change to
the copy, and run the gate from inside it.

Set top `status: planned`, `current_phase` to the first phase, and `last_updated` to today. The plan is
written but not signed off; `/proj-build` flips the top status to `in_progress` when it completes the
first phase. Then **validate**: `uv run .agents/factory/bin/next_phase.py spec/{slug}/TECH.md` must
exit 0 and report the first phase.

### Step 7 — Meta-note (self-improvement loop · silence by default)
Before committing, reflect on the **skillset itself** — not the task, not the code. Write nothing
unless the bar is met.

**The bar (one test):** *was this the skill's fault — not mine, not the task's?* **Qualifies:** you
hand-fixed a command this skill gave (wrong flag or path, unquoted `verify:` YAML); a genuinely
ambiguous instruction; a `[NEEDS CLARIFICATION]` better guidance could have pre-empted; an
allowed-tools/step mismatch; a gate that passed or failed misleadingly. **Stay silent for:** a merely
hard task; your own error against clear guidance; a one-off content or code issue (that goes in
`PLAN.md`/`GOAL.md`); a vague preference.

If, and only if, the bar is met, record it in `spec/{slug}/META.md` — create from
[`templates/META.md`](../../factory/templates/META.md) if absent, else append. You may also add a
one-line **What worked well** note. Caps: at most three findings, terse; append "· seen again" rather
than duplicating an equivalent finding; a fix that would weaken a non-negotiable gate (the invariant
gate, the `verify:` design, an `invariants.md` item) is `severity=high` and must say so. **Records
only.** Use the next unused `F#`, always `status=open`, appended **outside** any code fence:

```markdown
## F<n> — <one-line title>
`origin=proj-plan:<step> severity=<high|medium|low> category=<instruction|steering|tooling|template|missing-guidance> status=open target=<best-guess file>`
- **What happened:** <what the skill made you do, or fail to do>.
- **Skill cause:** <why it's the instructions' fault — not yours, not the task's>.
- **Recommended fix:** <the change to the skill/template/script>.
- **Confidence:** <high|med|low> · **Effort:** <small|medium|large>
```

Likely sources here: the research fan-out mechanics (Step 3), the invariant-gate steps, or `TECH.md`
YAML authoring.

### Step 8 — Commit
```
git add -A spec/{slug}      # PLAN.md + TECH.md, plus research/ and META.md when present
git commit -m "[{category}] Plan {slug}: design + phased roadmap"
```
`{category}` is the same category as the shape commit. Subject at most 72 characters, and **no
`Co-Authored-By:` trailer**. Do not push.

### Step 9 — Report & hand off
Report the design summary, the phase list (id · name · satisfies · verify), any deviations recorded,
and open risks — especially anything that can only be confirmed in the deployed Geddes pod. Sign-off
gate: the human reviews `PLAN.md` and `TECH.md`, then `/proj-build` executes phase one. Stop.

## Examples

- `/proj-plan` — full appetite-scaled run for the current branch's slug.
- `/proj-plan skip research` — lean plan for a small change, no fan-out.
- `/proj-plan status` — list existing GOAL/research/PLAN/TECH for this slug and what is missing.

## Notes

- Keep `research/` lean. Reviewers and future readers pay a tax for sprawl; keep only what informs the
  design.
- `TECH.md` is the resume ground truth for `/proj-build`. If `next_phase.py` reports it invalid, fix it
  before committing.
- A research brief that concludes "this is only observable in the deployed pod" is a useful brief.
  Record the assumption in PLAN §5 rather than inventing a verification that does not verify anything.
