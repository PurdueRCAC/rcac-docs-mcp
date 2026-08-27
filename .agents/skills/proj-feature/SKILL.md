---
name: proj-feature
description: >-
  Start a new rcac-docs-mcp feature/fix/refactor/docs cycle from a clean main branch. Safety-checks
  the tree, derives a {slug}, creates feature/{slug}, fix/{slug} or docs/{slug}, ingests an inline
  prompt, an untracked GOAL.md, or an issues/{slug}.md deferral, and refines it into
  spec/{slug}/GOAL.md — appetite, non-goals, EARS acceptance criteria with stable R-IDs, resolved
  clarifications. Shaping only: no deep research, no big code reads. First step of the spec-driven
  software factory (see .agents/factory/methodology.md).
disable-model-invocation: true
argument-hint: "<inline feature description> | spec/<slug>/GOAL.md | issues/<slug>.md [fix|refactor|docs] [appetite small|big]"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, Bash(git status *), Bash(git branch *), Bash(git switch *), Bash(git rev-parse *), Bash(git fetch *), Bash(git add *), Bash(git commit *), Bash(git log *), Bash(git ls-files *), Bash(git ls-tree *), Bash(head *), Bash(grep *), Bash(echo *), Bash(true)
---

# proj-feature — shape the goal

## When to Use

Invoke `/proj-feature` on a clean `main` to begin a new unit of work. It produces exactly one
artifact — a refined `spec/{slug}/GOAL.md` on a fresh branch — and stops for your sign-off before the
expensive `/proj-plan` step. This is **shaping** in the Shape Up sense: make the goal coherent,
bounded and unambiguous, but leave design freedom for the plan. Do **not** research or read a lot of
code here.

Reference, loaded only if needed: [`methodology.md`](../../factory/methodology.md),
[`ears.md`](../../factory/ears.md), [`invariants.md`](../../factory/invariants.md), and the template
[`templates/GOAL.md`](../../factory/templates/GOAL.md).

**Harness portability.** These skills run on any harness, not only Claude Code — see
[`portability.md`](../../factory/portability.md). Here the Claude-specific affordances degrade
gracefully: if the *Current state* block below is not auto-injected, run those commands yourself in
Step 1; if `AskUserQuestion` is unavailable, ask in plain text and STOP. Everything else is portable
shell.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current`
- Tree: !`git status --porcelain | head -n 20`
- Untracked GOAL.md files: !`git ls-files --others --exclude-standard 'spec/**/GOAL.md' | grep . || echo "(none)"`
- Open issues: !`git ls-files 'issues/*.md' | grep . || echo "(none)"`
- Landed cycles on main: !`git ls-tree main --name-only spec/ 2>/dev/null | grep . || echo "(none)"`

## Argument Parsing

Parse `$ARGUMENTS` case-insensitively. If self-contradictory, STOP and ask.

- A path matching `spec/<slug>/GOAL.md` → **adopt that file** as the seed; `{slug}` comes from the
  path. This is the "I hand-wrote a GOAL.md" flow.
- A path matching `issues/<slug>.md` (or `.security/issues/<slug>.md`) → **promote that issue**.
  `{slug}` is the file stem; its frontmatter supplies `kind` and `appetite` unless the invocation
  overrides them. A bare `{slug}` naming an existing `issues/{slug}.md` resolves the same way. See
  "Promoting an issue" in Step 4.
- `fix` / `bug` / `refactor` / `docs` → set `kind`; otherwise infer from the wording, defaulting to
  `feature`. The `kind:` set is open — it is the `AGENTS.md` commit category — so a promoted seed
  carrying an unusual kind still has a defined branch.
- `appetite small` / `appetite big` → set appetite; else default `small` for `kind: fix` and
  `kind: docs`, `big` for `feature`/`refactor`. Those two values are the whole vocabulary; a seed
  whose frontmatter still reads `medium` rounds **up** to `big`, because rounding up costs a research
  fan-out while rounding down fails `proj-review`'s scope check
  ([`review-rubric.md`](../../factory/review-rubric.md)) against a contract a human already accepted.
  Record the round-up as a dated Clarification in the GOAL; leave the seed's own frontmatter alone.
- Everything else → the inline feature description (the seed prompt). Alongside a path it is not the
  seed: prose accompanying a promoted issue is shaping input for that seed, never an automatic scope
  extension. Check it against the injected *Open issues* list — a remark owned by a different seed is
  recorded there and named as a non-goal here (Step 4), and where it is unclear which seed owns it,
  ask. Merging two cycles is an appetite decision, not a parsing one.
- No arguments **and** no untracked `spec/*/GOAL.md` present → STOP and ask for a description or a
  GOAL.md path.

## Safety Principles

- **On `main`, otherwise-clean tree.** If the injected branch is not `main`, STOP — do not auto-switch
  or stash. The tree must be clean **except** the untracked `spec/{slug}/GOAL.md` you are adopting
  when a path was given; any *other* modified or untracked file → STOP.
- **Never overwrite a tracked GOAL.** If `spec/{slug}/` already exists **in git**, or the target branch
  already exists, STOP and report a collision. Adopting an *untracked* hand-written
  `spec/{slug}/GOAL.md` at an explicit path is the intended flow, not a collision.
- **Branch mapping:** `kind: fix` → `fix/{slug}`; `kind: docs` → `docs/{slug}`; every other kind →
  `feature/{slug}`. A docs-only cycle is ordinary here rather than exceptional: `AGENTS.md`,
  `invariants.md`, `README.md`, `INSTRUCTIONS.md` and the tool docstrings in
  `src/rcac_docs_mcp/tools.py` all state the same contract, so a behavior change routinely strands
  one of them and the repair is its own cycle.
- **Never guess.** On any ambiguity in scope or requirements, emit a literal
  `[NEEDS CLARIFICATION: …]` marker in GOAL.md and ask the human. Record answers in the Clarifications
  section. Do not invent behavior.
- **Shaping only.** No research fan-out, no broad code exploration, no implementation. If you feel the
  urge to research, that is `/proj-plan`'s job.
- **Size circuit-breaker (soft).** If shaping produces more than roughly 8–10 acceptance criteria, or
  several distinct deliverables, the appetite is probably too big — pause and offer the human a pilot
  plus follow-ups split, recording the deferred scope in Non-goals. A prompt, not a hard limit.
- **Bias toward the smallest surface.** This server is finished, small, and deployed — ten source
  files, two tools, one job. Before shaping anything additive, check `README.md` and `AGENTS.md` for
  whether the capability was deliberately scoped out: the docs-only refactor removed auth, `sse` and
  all cluster operations on purpose, and `spec/docs-only-refactor/STAGES.md` records those decisions.
  A change that adds a third MCP tool needs an explicit GOAL criterion saying why two are not enough.
  If the GOAL is re-proposing something already rejected, say so and make the human confirm.
- **No `Co-Authored-By` trailer** on the commit, of any kind (repo convention).

## Procedure

### Step 1 — Pre-flight
1. Confirm on `main` with an otherwise-clean tree. The **only** permitted pending change is the
   untracked `spec/{slug}/GOAL.md` being adopted in the path-given flow. Any other dirty or untracked
   file → STOP (commit, stash, or discard first).
2. `git fetch origin || true`; if `main` is behind, note it. Not fatal.

### Step 2 — Resolve slug, kind, appetite
1. If a `spec/<slug>/GOAL.md` path was given, use it. Otherwise derive a concise kebab `{slug}` of
   about five words or fewer from the description; if it is not obviously good, propose it and
   confirm.
2. Resolve `kind` and `appetite` per Argument Parsing.
3. Check collisions: `git rev-parse --verify {branch}` must fail (branch absent), and `spec/{slug}/`
   must not be tracked. STOP on collision.

### Step 3 — Create the branch
`git switch -c {branch} main`, where `{branch}` is `fix/{slug}`, `docs/{slug}` or `feature/{slug}`.

### Step 4 — Write / refine `spec/{slug}/GOAL.md`
Start from the template. Fill **Problem** (the raw need — motivate, do not design), **Outcome**,
**Acceptance criteria** as R-IDs (`R1`, `R2`, …) nudged toward EARS, **Non-goals**, **Clarifications**
(with any `[NEEDS CLARIFICATION]` markers resolved), and **Related materials**. Record `slug`, `kind`
and `appetite` in the header. Say in **Problem** whether the sufferer is an AI agent consuming
`doc_search` / `doc_load` or an operator running the container: an agent cannot ask a follow-up
question and pays for every wasted round trip, and the two have very different tolerances for a vague
failure.

Every criterion declares how it is checked. The default is a test (`uv run pytest -q -k …`) or a
sandbox drive under `.agents/factory/bin/temp_site.sh` asserting something observable — an exit
status, an indexed-document count, a path present in the results, a line on stderr, the shape of the
string a tool returns. The MCP tools are FastMCP `FunctionTool` objects, so a criterion naming a drive
calls `doc_search.fn(…)`, never `doc_search(…)`. One a drive cannot reach names its substitute in the
criterion itself: the command that stands in for the drive, the reviewer who grades it and against
what, or the deployed pod, which tells the reviewer it is taken on trust rather than leaving it to
assume the criterion was checked.

**A criterion that reads "`pytest` passes" is not a criterion.** With the RCAC-Docs submodule absent
the suite reports `76 passed, 31 skipped` and still exits 0, so 29% of the coverage can vanish behind
a green gate. Name the assertion, not the exit status.

**A non-goal that defers work by naming another file is a promise, and the promise is only real in
that file.** "No regression test for the pull path — `issues/test-site-clone.md` owns it" is what lets
the cycle ship without the work, and `spec/{slug}/GOAL.md` is a dated record the named cycle never
opens. Land the obligation in that seed — an acceptance criterion, not a sentence in this GOAL — in
the same commit, or do not write the non-goal that way. `/proj-roadmap` deletes the seed when the
cycle lands, and a promise recorded only in `GOAL.md` goes with it; Step 3 there is the backstop,
not the control.

If adopting a hand-written GOAL.md, refine it **in place**: preserve the author's intent, and only
disambiguate, structure, and add R-IDs, appetite and non-goals. Do not expand scope.

**For `kind: fix`, phrase criteria as the observable broken→fixed behavior the user sees** — never the
suspected cause or mechanism, which is unverified until `/proj-plan` root-causes it. A criterion pinned
to a wrong diagnosis has to be reinterpreted mid-lifecycle.

**Promoting an issue.** A deferral recorded earlier arrives pre-shaped — Problem, why it was deferred,
draft R-IDs — and its body mirrors [`templates/ISSUE.md`](../../factory/templates/ISSUE.md), which in
turn mirrors this template, so promotion is a move-and-fill. It is still a *candidate*: **do not copy
it into `GOAL.md` verbatim.** Read its `status:` first.

- **`unshaped`** — nobody has agreed an appetite, non-goals, or a final contract. That negotiation is
  this step's job, and skipping it hands `proj-review` a contract no human ever accepted. Carry the
  evidence (`src/rcac_docs_mcp/index/indexer.py:NNN`, the mechanism, whether the defect is
  **pre-existing**) into **Problem**, and treat the draft R-IDs as input, not as the contract.
- **`shaped`** — the shaping conversation already happened with a human. Do **not** re-litigate it.
  Re-confirm the scope still holds against current `main`, cite anything that has drifted since it was
  written, surface that for sign-off, and adopt it largely as written. What this step performs is
  *acceptance into a cycle*.
- **`adopted:{other-slug}`** — already promoted. STOP and report the collision. If
  `git ls-tree main -- spec/{other-slug}` is empty and no branch carries it, the adoption is stale from
  an abandoned cycle rather than a real collision: show the human and offer to reset the status instead.
- **`declined` / `accepted-behaviour`** — terminal records, not candidates: the first was considered
  and refused as debt, the second was reported as a defect and judged intended. They sit under
  `ROADMAP.md` § *Terminal records* rather than in the queue. STOP and show the human the recorded
  reasoning before doing anything.

Read the seed's `ROADMAP.md` entry too. The two halves of a deferral hold different information: the
issue holds the evidence, the entry holds the position and the reasoning for that position. An entry
recording a sequencing dependency — "after the index-publication work, so the fix lands against the
atomic swap" — is a decision a human made, and promoting out of order overrides it. The injected
*Landed cycles on main* list shows which cycles are done; if the named ones have not landed, surface
the reordering for sign-off before shaping, and record what was decided as a Clarification and a
Non-goal.

When the GOAL lands, leave the `issues/` file in place, set its `status:` to `adopted:{slug}`, and
update that seed's `ROADMAP.md` entry in the same commit. The seed stays accurate until the branch
actually lands, so a cycle that bounces at review or is abandoned still has the evidence that
justified it; `/proj-roadmap` retires both once the work reaches `main`. The roadmap entry has two
halves — extend its **Seed:** line with the adoption marker, and rewrite the entry body to the scope
shaping settled, since an entry still posing the question the human just answered sends the next
reader to a stale index. `kind` and `appetite` already sit on the entry's metadata line, so the marker
adds only the adoption:

    **Seed:** [`issues/{slug}.md`](issues/{slug}.md) · **adopted** as
    [`spec/{slug}/`](spec/{slug}/GOAL.md)

Commit both edits alongside the GOAL.

An issue promoted out of `.security/issues/` keeps its evidence in the hidden lane: the public
`GOAL.md` states the **observable hardening outcome** and points at `.security/` for detail. It never
republishes an attack mechanism for a weakness that is still live. This server is unauthenticated and
on the public internet, so that lane is the default when the answer is unclear.

### Step 5 — Coherence self-check
Re-read the GOAL. Is it solved, bounded to the appetite, and free of unresolved markers? Is every
requirement testable and observable? If not, iterate with the human before committing.

### Step 6 — Meta-note (self-improvement loop · silence by default)
Before committing, reflect on the **skillset itself** — not the task, not the code. Write nothing
unless the bar is met.

**The bar (one test):** *was this the skill's fault — not mine, not the task's?* **Qualifies:** you
hand-fixed a command this skill gave (wrong flag or path, unquoted YAML); a genuinely ambiguous
instruction; a `[NEEDS CLARIFICATION]` better guidance could have pre-empted; an allowed-tools/step
mismatch; a gate that passed or failed misleadingly. **Stay silent for:** a merely hard task; your own
error against clear guidance; a one-off content or code issue (that goes in `GOAL.md`, not here); a
vague preference.

If, and only if, the bar is met, record it in `spec/{slug}/META.md` — create it from
[`templates/META.md`](../../factory/templates/META.md) if absent, else append. You may also add a
one-line **What worked well** note when part of this skill materially helped. Caps: **at most three
findings**, terse; if an equivalent finding already exists, append "· seen again" rather than
duplicating; a fix that would weaken a non-negotiable gate (`lint.sh`, the `temp_site.sh` drive, an
`invariants.md` item) is `severity=high` and must say so. **Records only** — `/proj-harness` applies
fixes later, human-reviewed. Use the next unused `F#`, always write `status=open`, and append the
finding as a section **outside** any code fence:

```markdown
## F<n> — <one-line title>
`origin=proj-feature:<step> severity=<high|medium|low> category=<instruction|steering|tooling|template|missing-guidance> status=open target=<best-guess file>`
- **What happened:** <what the skill made you do, or fail to do>.
- **Skill cause:** <why it's the instructions' fault — not yours, not the task's>.
- **Recommended fix:** <the change to the skill/template/script>.
- **Confidence:** <high|med|low> · **Effort:** <small|medium|large>
```

`proj-feature` is shaping-only, so findings here are usually about ambiguous shaping guidance or the
`GOAL.md` template.

### Step 7 — Commit
```
git add spec/{slug}/GOAL.md          # add spec/{slug}/META.md too if you recorded a meta-note
git add issues/{slug}.md ROADMAP.md  # only when promoting: the two Step 4 edits
git add issues/{other-slug}.md       # a sibling seed this GOAL wrote into
git commit -m "[{category}] Shape {slug} goal"
```
`{category}` is the `AGENTS.md` commit category matching the work — normally `{kind}` itself
(`fix`|`feature`|`refactor`|`docs`). Never collapse everything non-`fix` to `feature`. The subject is
at most 72 characters, and a body earns its place only by recording a decision the diff does not show.
**No co-author trailer.** Do not push.

### Step 8 — Report & hand off
Report the branch, slug, kind, appetite, the R-ID list, and any open clarifications. Tell the human
the sign-off gate: review `spec/{slug}/GOAL.md`, then run **`/proj-plan`**. Stop.

## Examples

- `/proj-feature let doc_search take a limit argument so an agent can ask for one hit` — infer
  `feature`, derive slug `doc-search-limit`, create the branch, shape the GOAL.
- `/proj-feature issues/site-flag-ignored-when-serving.md` — promote the recorded deferral: shape its
  draft R-IDs into a contract, then flip the issue to `status: adopted:{slug}`.
- `/proj-feature fix the indexer crashes on a snippet containing a brace sequence` — `kind: fix`,
  appetite small, branch `fix/{slug}`.
- `/proj-feature docs INSTRUCTIONS.md still tells callers to add prefix wildcards` — `kind: docs`,
  appetite small, branch `docs/{slug}`.
- `/proj-feature spec/query-normalizer-audit/GOAL.md` — adopt the hand-written GOAL and refine in
  place.

## Notes

- This skill never researches, edits source, or pushes. That is `/proj-plan`, `/proj-build`,
  `/proj-publish`.
- If a requirement cannot be made unambiguous with the human right now, leave the
  `[NEEDS CLARIFICATION]` marker in place and STOP — an ambiguous GOAL blocks `/proj-plan`.
- Some `git` mutations may prompt for permission depending on your `settings.local.json`. That is
  expected and safe.
