---
name: proj-roadmap
description: >-
  Retire the deferrals whose cycles have landed, and keep ROADMAP.md true. Finds every
  issues/{slug}.md carrying status: adopted:{slug}, confirms the cycle actually reached main, and
  deletes the seed with its ROADMAP entry after a human-gated preview. Also repairs the drift a
  shipped cycle leaves behind: dangling cross-references, stale counts and file:line citations in
  surviving seeds, and adoption markers left by abandoned branches. Operational sibling of
  proj-harness and proj-release — maintenance, NOT a lifecycle step; run between releases (see
  .agents/factory/methodology.md).
disable-model-invocation: true
argument-hint: "[--dry-run] [slug] [--all] [status|report]"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, Bash(git status *), Bash(git branch *), Bash(git log *), Bash(git ls-tree *), Bash(git rev-parse *), Bash(git fetch *), Bash(git pull *), Bash(git add *), Bash(git commit *), Bash(grep *), Bash(del *), Bash(ls *), Bash(head *), Bash(test *), Bash(uv run .agents/factory/bin/meta_status.py *), Bash(.agents/factory/bin/lint.sh *), Bash(echo *), Bash(true)
---

# proj-roadmap — retire what shipped, keep the index true

## When to Use

Invoke `/proj-roadmap` between releases, or any time `ROADMAP.md` has stopped describing the work
that is actually left. Its main job is the one step the lifecycle never had: a cycle seeded from an
`issues/{slug}.md` ships, and nothing retires the seed, so the backlog keeps advertising work that is
already on `main`.

This is **maintenance, not a lifecycle step.** It does not touch `src/rcac_docs_mcp/**`, does not
read or write `GOAL/PLAN/TECH/REVIEW`, and never advances an FSM. It edits `ROADMAP.md`, deletes
seeds under `issues/`, repairs the references a deletion breaks (Step 5), and — in the security lane
only — moves an entry rather than deleting anything.

Deliberately **not** part of `/proj-publish`. Retirement writes outside `spec/`, which is the one
thing publish's staleness gate is built to notice; folding it in would mean excluding `issues/` and
`ROADMAP.md` from that gate, and a cycle legitimately writes there — a review pass that defers a
finding files the seed and its index entry inside the reviewed change set. Publish names an
un-retired seed in its report and stops there.

Reference: [`methodology.md`](../../factory/methodology.md),
[`invariants.md`](../../factory/invariants.md),
[`review-rubric.md`](../../factory/review-rubric.md),
[`templates/ISSUE.md`](../../factory/templates/ISSUE.md) (the `status:` vocabulary), and `AGENTS.md`
§ *Where work is recorded*.

**Harness portability.** Runs on any harness — see [`portability.md`](../../factory/portability.md).
Run the *Current state* commands yourself if not auto-injected; ask in plain text and STOP if
`AskUserQuestion` is unavailable. `git` and `grep` are portable shell; `del` is this environment's
reversible-trash stand-in for a blocked `rm` (see Safety Principles).

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current`
- Tree: !`git status --porcelain | head -n 20`
- Adopted seeds: !`grep -rl "^status: adopted:" issues .security/issues 2>/dev/null | grep . || echo "(none)"`
- Queued entries: !`grep '^\*\*Seed:\*\*' ROADMAP.md 2>/dev/null | grep -cv '{slug}' || true`
- Hidden entries: !`test -f .security/ROADMAP.md && { grep -c '^\*\*Seed:\*\*' .security/ROADMAP.md || true; } || echo "(no security lane)"`
- Cycles on main: !`git ls-tree --name-only main:spec 2>/dev/null | grep -v '^\.gitkeep$' | grep . || echo "(none)"`

## Argument Parsing

- No argument → consider every adopted seed whose cycle has landed. The default.
- `<slug>` → restrict to the seed adopted by that cycle. This is the **cycle slug**, not a filename;
  Step 2 explains why those need not agree.
- `--all` → widen Step 5's drift sweep to seeds this retirement does not otherwise touch.
- `--dry-run` → run Steps 1–3 and Step 4's *preview only*, then STOP. No `AskUserQuestion`, no edits,
  no deletions, no commit — Step 1's loadability-repair commit and Step 3's "put the missing
  obligation there first" write are both **reported, not performed**, under `--dry-run`.
- `status` / `report` → list adopted seeds with landed/in-flight/stale for each; no work.

## Safety Principles

- **Deleting a seed destroys the only copy outside git history.** Preview every retirement and
  confirm with the human before acting. Never delete on inference alone.
- **`del`, not `rm`.** `rm` is aliased away in this environment and `del` is reversible trash. The
  seed is tracked, so follow with `git add -A` to stage the deletion; that is why this skill does not
  need `git rm`.
- **Landed means on `main`.** A seed is retired only when `git ls-tree main -- spec/{slug}` is
  non-empty. An `adopted:{slug}` marker proves a cycle *started*, never that it finished — a branch
  that bounced at review or was abandoned still carries the marker, and retiring its seed deletes the
  justification for work nobody did.
- **Never delete anything under `.security/`.** That lane is gitignored, so a deletion there leaves
  no commit and no history: the file is gone, and the closed finding is exactly what a later audit
  asks for. Retire it by moving its `.security/ROADMAP.md` entry to that file's § *Terminal records*
  and keeping the `.security/issues/` file. Never `git add` a path under `.security/`, and never name
  one in a commit message.
- **A GOAL is negotiated down from a seed.** Anything the cycle cut and still wants must survive
  retirement. Step 3 checks this against `GOAL.md` § *Non-goals*; it is the one failure here that
  loses work rather than leaving litter.
- **Never edit `spec/{slug}/`.** It is a dated record of what was true when written. A retired seed
  leaves a dangling `Seed:` link in `GOAL.md` § *Related materials*, and that link stays: it is the
  signpost that makes `git log --diff-filter=D -- issues/{slug}.md` a two-step recovery instead of
  archaeology. The one exception is `META.md`, the harness feedback log rather than part of the
  design record; Step 7 says when.
- **One commit per retirement**, `[harness]` category, subject at most 72 characters, **no
  `Co-Authored-By` trailer of any kind** (`AGENTS.md`). Never push.
- **The commit lands on `main`, and pushing `main` is a deploy.** `build-and-push.yml` fires on push,
  moves `ghcr.io/purduercac/rcac-docs-mcp:latest`, and the Geddes poller rolls the pod. A retirement
  changes no source, so the rebuilt image behaves identically — but the pod still restarts, which is
  the human's call to make and not a side effect to spring on them. This skill commits and stops.

## The shape of a ROADMAP entry

Stated here so you do not have to infer it — but **read `ROADMAP.md` before editing.** It evolves,
and if the file disagrees with this description the file wins; say so in the report.

`ROADMAP.md` is **flat and deliberately unnumbered** — the file says why: an ordinal reference
survives a retirement still grammatical and now pointing at the wrong cycle. There are no Parts and
no numbers, so removing an entry renumbers nothing.

```
## Queued

### One sentence saying what is wrong, in the imperative or as a symptom.
*`kind: fix` · `appetite: small` · filed 2026-08-27 by `{slug}` P2*
**Seed:** [`issues/{slug}.md`](issues/{slug}.md)
```

An entry's **block** is the `### ` heading through its `**Seed:**` line inclusive, plus the blank
line that follows, and may carry a paragraph of prose between the two. Only two `## ` sections exist
— *Queued* and *Terminal records* — and neither is ever removed by a retirement. Emptying the queue
leaves the `## Queued` heading, the framing prose above it, and the HTML-comment entry-format example
inside it all standing; note the empty queue in place of the entries.

That commented example is why the injected probe filters `{slug}`: the example carries a literal
`**Seed:**` line, so an unfiltered count reads one entry high on an empty queue. The example is the
format record, not an entry — never retire it.

`.security/ROADMAP.md` mirrors the same convention, gitignored. It may not exist at all; read it
before assuming its section names.

## Procedure

### Step 0 — status / report / dry-run (when requested)
`status` (alias `report`): classify each adopted seed and report; no work. `--dry-run`: Steps 1–3
plus Step 4's preview, then STOP — no confirmation prompt, no deletion, no commit.

### Step 1 — Pre-flight
Clean tree; non-empty → STOP. Confirm you are on `main`; this skill does not run on a
`feature/`|`fix/`|`docs/`|`harness/` branch, because a seed retired on a branch that never merges
takes the backlog entry with it.

`git fetch origin || true`. `/proj-publish` lands cycles by squash PR, so a merge can exist on
`origin/main` before local `main` has it: if local `main` is behind, `git pull --ff-only`, or
classify against `origin/main` and say which ref you used in the report.

One exception to the clean-tree STOP, because the alternative is circular: when the tree is dirty
*only* with the repair that made this skill loadable, commit that as its own `[harness]` commit and
continue. The STOP is there to keep a retirement from being tangled with unrelated work; a fix to the
factory is not unrelated work, it is the reason the sweep can run at all. Anything else in the tree
still STOPs, and the repair is never folded into a retirement commit.

### Step 2 — Find the adopted seeds and classify each
```
grep -rl "^status: adopted:" issues .security/issues 2>/dev/null || true
```
Plain `grep`, not `git grep`: `.security/` is gitignored, and `git grep` searches tracked files only,
so it would skip that lane while appearing to work. The `|| true` is load-bearing — with `.security/`
absent `grep` exits 2 while still printing its matches, so anything branching on the exit status
reads "no adopted seeds" off a list of them.

**Match on the frontmatter, never on the filename.** Nothing constrains a seed's filename and its
cycle slug to agree, because `/proj-feature` derives the slug in the shaping conversation rather than
copying it off the file it promotes. A filename guess deletes nothing, or deletes the wrong thing.

Read the `{slug}` out of each `status: adopted:{slug}` value and classify:

| `git ls-tree main -- spec/{slug}` | Meaning | Action |
|---|---|---|
| non-empty | the cycle landed | retire (Steps 3–4) |
| empty, branch exists | in flight | leave alone |
| empty, no branch | abandoned; the marker is stale | offer to reset `status:` to `shaped` or `unshaped`, never delete |

"Branch exists" means local **or** remote — after a `git fetch` it may be only the latter, and
`/proj-feature` maps `kind: fix` → `fix/{slug}`, `kind: docs` → `docs/{slug}`, everything else →
`feature/{slug}`:
```
for b in feature fix docs; do
    git rev-parse --verify --quiet "$b/{slug}" || git rev-parse --verify --quiet "origin/$b/{slug}"
done
```

The stale case matters because `/proj-feature` STOPs on an adoption marker as already-promoted. Left
alone, an abandoned cycle permanently bricks its own seed: it can never be promoted and its ROADMAP
entry can never be worked.

### Step 3 — Check the seed shipped whole
Read `spec/{slug}/GOAL.md` § *Non-goals* against the seed's problem statement and its sketch of the
acceptance criteria. Non-goals are the written record of what the promotion negotiated away.

Anything cut and still wanted does not die with the seed. Either rewrite the seed down to the
remainder and reset `status:` to `unshaped`, re-wording its ROADMAP entry to match, or file a fresh
seed for it from [`templates/ISSUE.md`](../../factory/templates/ISSUE.md). Only a seed with no live
remainder is deleted.

**A non-goal that discharges itself by pointing elsewhere is conditional, and the condition is what
you verify.** "Record it there", "the harness cycle must cover this", "that is a seed for `issues/`"
— each of those is the reason the cycle was allowed to ship without the work. Open the file it names
and confirm the obligation is *in* it: `issues/{slug}.md` plus a `ROADMAP.md` entry for code work,
`.security/` for anything unremediated, `spec/{slug}/META.md` for harness friction — the homes in
`AGENTS.md`, one rule each. An intention stated in `GOAL.md`, in `PLAN.md`, or in the ROADMAP entry
is not the record; the named destination is. Where it is missing, put it there first, in the
retirement's own commit.

Check this before deleting, not after. The obligation is frequently written in exactly one place —
the roadmap entry the retirement removes — so the deletion is what makes the loss irreversible, and
this is the one failure in the sweep that costs work rather than leaving litter.

### Step 4 — Preview, confirm, retire
Present per seed: the file to delete, the ROADMAP entry to remove, any remainder being preserved, and
the cross-references Step 5 will repair. Confirm with `AskUserQuestion`. On `--dry-run`, stop here.

Then, for each confirmed public-lane seed:
```
del {seed-path}     # the path Step 2 printed, never a name reconstructed from {slug}
```
Remove its block from `ROADMAP.md` — the `### ` heading through the `**Seed:**` line inclusive, plus
the trailing blank line.

Security-lane seeds are **moved, not deleted**, per the safety rule above: rewrite the
`.security/ROADMAP.md` entry under § *Terminal records* with a one-line note of what closed it, and
keep the `.security/issues/` file. None of this is committable, so the run report is the only place
these edits are visible; name them there.

### Step 5 — Repair what the removal broke
Find the references; do not recall them. Both strings matter, and Step 2 already says they need not
be the same:

```
grep -rn '{seed-filename}\|{slug}' \
    --include='*.md' --include='*.py' --include='*.toml' --include='*.sh' . \
    | grep -v '^\./\.git/'

# The harness `Grep` tool is ripgrep-backed and honours .gitignore, so a `.`-rooted search returns
# nothing from the security lane. Name it as an explicit path argument, the way Step 2 does, or the
# cross-lane row of the table below is dead:
grep -rn '{seed-filename}\|{slug}' --include='*.md' .security 2>/dev/null || true
```

A short generic slug matches ordinary prose — `index`, `search` or `site` alone return well over a
hundred lines in this tree. When that happens, split the sweep: run the *filename* pattern
(`issues/{seed-filename}`) unfiltered, since that is the authoritative set of index references, and
run the bare slug only inside the files the filename pass already flagged, plus `ROADMAP.md`,
`.security/ROADMAP.md`, and `issues/`.

Triage every hit by where it lands, because three of these destinations are deliberately left alone:

| Where the hit is | Action |
|---|---|
| `ROADMAP.md`, other `issues/*.md` | Repair. This is the work described below. |
| `.security/ROADMAP.md`, `.security/issues/*.md` | Repair — the cross-lane references are real, since the hidden lane cites public seeds by path. **Never stage it**; name the edit in the report instead, since no commit will show it. |
| `.agents/` skills, templates, factory docs | Repair — with one carve-out: a slug used as an **illustrative example** (this skill's Examples, `/proj-feature`'s Examples) is a placeholder, not a cite. Repair a real cite; repair an instruction the promotion falsified. |
| `AGENTS.md`, `README.md`, `INSTRUCTIONS.md` | **Repair, but conservatively.** These are ground truth about the code, not an index of pending work: a genuine cite of a deleted seed is drift, while a description of behavior the cycle shipped is now documentation and stays. `INSTRUCTIONS.md` is a system prompt held by every downstream client — do not pad it. Flag anything ambiguous in the report. |
| `spec/**` | **Leave.** Never edit `spec/{slug}/`. The dangling `Seed:` link is the signpost that makes recovery two steps instead of archaeology. |
| `.agents/factory/harness-log.md` | **Leave.** A dated record of what was decided, not an index of what exists. |
| `src/rcac_docs_mcp/**` | **Report, do not edit.** Source is never supposed to cite a seed or a feature-scoped id (`AGENTS.md`, enforced by `lint.sh`); a hit here is a finding for the human, not a fix for this sweep. |

Entries carry no numbers, so removing one renumbers nothing. What still breaks is prose:

- A cross-reference to the retired cycle by name (`Follows the rename`, `the same line as …`). The
  dependency is discharged, so say so rather than deleting the sentence — a reader needs to know the
  ordering constraint existed and cleared. Where surviving text cites the retired seed's R-IDs,
  repoint it at the shipped thing by name: R-IDs are renegotiated at promotion, so `R3` in a seed and
  `R3` in `spec/{slug}/GOAL.md` are not guaranteed to be the same requirement.
- A count (`Highest-value cycle of the three`, `Three are already queued`) that the retirement makes
  wrong, in `ROADMAP.md` and inside surviving seeds. The framing prose above `## Queued` states facts
  about the index itself — re-read it whenever the queue empties or the last entry of a theme goes.
- A figure the shipped cycle falsified — a count, a `file:line` citation, a quoted output — anywhere
  in a file this retirement already edits. Read those whole: a stale figure standing beside a freshly
  repaired link is worse than one in a file nobody opened, because the repair is what tells a later
  reader the file was reviewed. The counts most likely to be stale here are the test totals
  (`107 passed`, `76 passed, 31 skipped`) and the module inventory under *Architecture*.
- With `--all`: the same figures in seeds this retirement never touches — a line count, an occurrence
  table, a file inventory. A stale baseline in a seed whose own acceptance criterion is a count guard
  is the one number in it that has to be right.

Do not rewrite a `Found by:` line. Those ordinals are provenance, not queue position.

### Step 6 — Commit
```
git add -A
git commit -m "[harness] Retire the {slug} seed and its roadmap entry"
```
One commit per retirement; fold Step 5's repairs into the commit that caused them. `git add -A`
stages the `del` as a deletion — that is why no `git rm` is needed — and `.security/` is gitignored
so `-A` cannot reach it; still check `git status --porcelain` before committing that no `.security/`
path appears and that the message names none. For this sweep the category is always `[harness]` because the sweep maintains
the factory's bookkeeping, never the product; do not coin a new one. **No `Co-Authored-By` trailer.**
Do not push — see the deploy note in Safety Principles.

For a stale marker reset with no deletion: `[harness] Reset the stale adoption marker on {slug}`.

### Step 7 — Report
Seeds retired, seeds left in flight, stale markers found and what was done about them, remainders
preserved, cross-references repaired, and every uncommittable `.security/` edit (the report is their
only record). Name anything you chose not to touch, and say which ref you classified against if it
was not local `main`. Say plainly that nothing was pushed and that pushing `main` deploys.

Name any **harness friction** this sweep exposed — a skill instruction that was wrong or ambiguous, a
command that had to be hand-fixed — and offer to record it, on the same rule `/proj-release` carries:
`/proj-harness` reads only `spec/*/META.md`, so on the human's OK it goes to the retired cycle's
`spec/{slug}/META.md` with `origin=proj-roadmap:<step>` and `status=open`, as its own `[harness]`
commit. Read it back with
`uv run .agents/factory/bin/meta_status.py spec/{slug}/META.md` to confirm the append parsed.

## Examples

- `/proj-roadmap` — retire every landed seed, one commit each.
- `/proj-roadmap --dry-run` — preview the whole sweep; change nothing.
- `/proj-roadmap fts5-normalizer` — retire just that cycle's seed.
- `/proj-roadmap status` — classify every adopted seed; no work.

## Notes

- `/proj-publish` detects an un-retired seed and names it in its final report. It does not act: this
  skill is where deletion lives, so publish keeps neither an `Edit` tool nor a deletion verb.
- A **public** seed that shipped leaves no terminal record. `ROADMAP.md` § *Terminal records* is for
  deferrals closed **without** shipping — the `declined` and `accepted-behaviour` stances — where
  nothing else in the repository shows the question was asked. For shipped public work the refutation
  is free: someone re-filing it greps the code and finds it already done, and `spec/{slug}/` holds the
  account. **The hidden lane inverts this:** a remediated finding *does* get a terminal record in
  `.security/ROADMAP.md`, because a gitignored lane has no git history to refute a re-filing with.
- This sweep has no test gate. It touches no source, so `uv run pytest -q` proves nothing about it;
  if a repair reaches outside markdown, that is the signal the edit is out of scope. Run
  `.agents/factory/bin/lint.sh --no-net` only when the sweep edited a skill's state injections.
- This skill never touches `src/rcac_docs_mcp/**`, never advances an FSM, never tags a version
  (`/proj-release` does that), and never ships (`/proj-publish` does that).
