# GOAL — {Title}

> **Origin spec.** The *what* and *why* — the locked contract `proj-review` grades against.
> The *how* lives in [`PLAN.md`](PLAN.md) and [`TECH.md`](TECH.md), written by `proj-plan`.
> Keep this at the right altitude: solved and bounded, but not over-specified — leave design freedom
> for the plan. Edit requirements here; do not silently drift them during build.

- **slug:** {slug}
- **kind:** feature | fix | refactor | docs
- **appetite:** small | big  ·  *small caps research and phase count; a one-sentence change may skip
  the lifecycle entirely.*

## Problem

<The raw need, in plain language. What hurts today, for whom, and why it matters. One or two
paragraphs. Motivate the work; do not describe the solution yet. For this project, "for whom" is
usually an **AI agent** consuming `doc_search` / `doc_load`, or an **operator** running the container
— say which. An agent cannot ask a follow-up question and pays for every wasted round trip; an
operator can read a stack trace. The two have very different tolerances for a vague failure.>

## Outcome / vision

<What "good" looks like when this ships. The shared picture we are agreeing on.>

## Acceptance criteria (the contract)

Stable IDs (`R1`, `R2`, …) that survive squash-merge and anchor traceability. Prefer **EARS** phrasing
(see [`ears.md`](../../.agents/factory/ears.md)) — it makes each line directly testable — but plain,
unambiguous prose is acceptable where EARS would be forced.

Every criterion declares how it is checked. The default is a test (`uv run pytest -q -k …`) or a
sandbox drive (`.agents/factory/bin/temp_site.sh …`) asserting something observable — an exit status,
an indexed-document count, a path in the results, a specific line on stderr, the shape of a tool's
returned string. One a drive cannot reach names its substitute where it is written: the command that
stands in (`git grep -n …` for a documentation sweep, or a rename's eradication of the old name); or,
where no command can decide it, the reviewer who grades it and the text they grade against; or the
deployed pod, which means the criterion is taken on trust. Prose quality is the third kind — no grep
detects a comment that restates the line below it.

- **R1** — WHEN <trigger>, the <component> SHALL <observable response>.
- **R2** — WHILE <state>, the <component> SHALL <response>.
- **R3** — IF <unwanted condition>, THEN the <component> SHALL <response>.
- **R4** — The <component> SHALL <ubiquitous requirement>.

## Non-goals (no-gos)

Explicit exclusions that keep scope bounded to the appetite. Naming what we are **not** doing matters
as much as what we are — this server is finished, small, and deployed, so the standing bias is to
delete rather than add, and a non-goal is how that bias gets recorded.

- <thing deliberately out of scope>

## Clarifications

Questions resolved with the human during shaping. Unresolved ones stay marked
`[NEEDS CLARIFICATION: …]` and **block** `proj-plan`. Never guess.

- **Q:** <question> — **A:** <answer> (resolved YYYY-MM-DD).

## Related materials

- Issue: <https://github.com/PurdueRCAC/rcac-docs-mcp/issues/NN>
- Seed: <`issues/{slug}.md`, when this was promoted from a deferral>
- <`README.md` / `INSTRUCTIONS.md` sections, FastMCP or SQLite FTS5 documentation, the upstream
  RCAC-Docs repository, prior art in `spec/`>
