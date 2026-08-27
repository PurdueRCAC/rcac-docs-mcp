---
name: proj-publish
description: >-
  Land an approved rcac-docs-mcp branch on main — which is the production deploy. Default: push the
  branch and open a squash PR with a rich, artifact-linked body (Summary/Goal/Design/Research/Phases/
  Verification/Deploy). Alternative (local): squash-merge into main locally and leave it unpushed.
  Confirms before any irreversible or outward step, then watches the image build, confirms the
  ghcr.io/purduercac/rcac-docs-mcp:latest digest moved, and probes the live endpoint at
  docs.rcac.purdue.edu/mcp before claiming the change is live. Final step of the software factory.
disable-model-invocation: true
argument-hint: "[pr (default) | local] [merge]"
allowed-tools: Read, Grep, Glob, AskUserQuestion, Bash(uv run *), Bash(.agents/factory/bin/*), Bash(git status *), Bash(git branch *), Bash(git log *), Bash(git diff *), Bash(git rev-parse *), Bash(git fetch *), Bash(git pull *), Bash(git push *), Bash(git switch *), Bash(git merge *), Bash(git add *), Bash(git commit *), Bash(git submodule *), Bash(gh pr *), Bash(gh run *), Bash(gh repo *), Bash(curl *), Bash(grep *), Bash(sed *), Bash(head *), Bash(sleep *), Bash(echo *), Bash(true), Bash(mktemp *)
---

# proj-publish — ship the branch to main, and confirm it deployed

## When to Use

Invoke `/proj-publish` once `/proj-review` has approved the branch (`TECH.md` `review.verdict:
approved`). This is the **one irreversible step** — remote pushes and PRs cannot be checkpointed — so
it always confirms with you before acting. The default is a PR to `main`; `local` does a local
squash-merge.

**A merge to `main` is the production deploy.** `.github/workflows/build-and-push.yml` fires on push
to `main`, moves `ghcr.io/purduercac/rcac-docs-mcp:latest`, and the Geddes Kubernetes poller rolls
the pod behind `docs.rcac.purdue.edu/mcp`. There is no separate ship step: `/proj-release` only cuts
a version (bump, tag, GitHub release) and reaches no user. Everything downstream of the squash button
in this skill is production, which is why Step 1 re-runs the gates and Step 4c refuses to report
success on a green CI run alone.

**Harness portability.** Runs on any harness — see [`portability.md`](../../factory/portability.md).
Run the *Current state* commands yourself if not auto-injected; ask in plain text and STOP if
`AskUserQuestion` is unavailable. `gh`, `git` and `curl` are portable shell.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current`
- Verdict / kind / slug: resolved in **Step 1** from `spec/{slug}/TECH.md` (a load-time injection cannot strip the branch prefix to form `{slug}`).
- Commits vs main: !`git log --oneline main..HEAD 2>/dev/null | head -n 30 | grep . || echo "(none)"`
- Working tree: !`git status --porcelain 2>/dev/null | head -n 20 || true`
- Default remote branch: !`gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo "(gh unavailable)"`

## Argument Parsing

- `local` / `no fuss` → squash-merge into `main` locally, delete the branch, no remote PR and no push.
- `pr` (default) → push the branch and open a PR to `main`.
- `merge` → after opening the PR, also `gh pr merge --squash`. Only with explicit confirmation, and
  that confirmation is a confirmation to deploy.

## Safety Principles

- **Base is `main`.** There is no `develop` and no `wip` branch in this repository. Branches are
  `feature/{slug}`, `fix/{slug}` or `docs/{slug}`, and they land by squash. Never force-push `main`.
- **Merging deploys.** Say so out loud in the confirmation. A PR left open deploys nothing; a squash
  merge reaches users within minutes to tens of minutes and cannot be un-served, only rolled forward.
- **Require a *current* approved review.** If `TECH.md` `review.verdict` is not `approved`, STOP and
  report; proceed only on explicit human override. Approval is pinned to
  `review.last_reviewed_commit`: any later commit touching anything **outside `spec/`** invalidates it
  (the review's own artifact commit and meta-notes do not). The Step 1 staleness gate checks this
  mechanically.
- **Confirm before irreversible or outward actions.** Always confirm the mode, PR title and body with
  the human before `git push`, `gh pr create`, or a local merge.
- **Squash, always.** The PR title becomes the squash commit subject on `main`, so the **PR title is
  `[category] Imperative summary`** (at most 72 characters) — **never Conventional Commits**
  (`feat:`/`fix:`). `{category}` is the `AGENTS.md` category of this branch's **shape commit** — the
  oldest entry in the *Commits on branch* injection — which is what `proj-build` and `proj-review`
  use too. It is **not** `TECH.md`'s `kind`: the two are different taxonomies, and `kind` has no
  `harness` or `release` member, so a `.agents/` cycle would land on `main` mislabelled.
- **Link, do not quote.** The PR body references artifacts via SHA-pinned blob permalinks, not pasted
  copies.
- **No `Co-Authored-By` trailer of any kind**, on any commit this skill makes. PR **bodies** end with
  the Claude Code generation line.
- **This skill deletes nothing.** It carries no `Edit` tool and no deletion verb, for the reason given
  in Step 5.

## Procedure

### Step 0 — status (when requested)
Report the verdict, commits vs `main`, whether a PR already exists (`gh pr status`), and the digest
`:latest` currently points at (Step 4c has the two commands). Stop.

### Step 1 — Pre-flight
1. On a `feature/`, `fix/` or `docs/` branch, clean tree. Resolve `{slug}` from the branch, then read
   `kind`, the review `verdict`, and `review.last_reviewed_commit` from `spec/{slug}/TECH.md`. STOP if
   the verdict is not `approved`, unless the human overrides.
2. **Staleness gate:** `git diff --stat {last_reviewed_commit}..HEAD -- . ':(exclude)spec/'` must be
   empty. Non-empty means code changed after the approved review — STOP and send back to
   `/proj-review`. Proceed only on an explicit human override, recorded in the PR body.
3. **Final gate.** Run both on the head commit. They take seconds, and they are the last chance to
   catch a break before a squash lands on `main` and a pod starts serving it.
   ```
   .agents/factory/bin/lint.sh
   uv run pytest -q
   ```
   `lint.sh` exits 0 pass / 1 fail / 3 could-not-run; treat 3 as red here, not as a pass. **Read the
   pytest counts, not the exit status.** The suite is 107 tests, and with the RCAC-Docs submodule
   absent it reports `76 passed, 31 skipped` and still exits 0 — twenty-nine percent of the coverage
   gone with a green exit. Anything short of `107 passed` before a deploy means initializing the
   fixture and running again:
   ```
   git submodule update --init tests/fixtures/RCAC-Docs
   ```
   Red → STOP.
4. `git fetch origin`. Confirm `main` is reachable and note if the branch is behind it; squash-merge
   tolerates drift, but flag a large one.

### Step 2 — Compose the PR title and body
- **Title:** `[{category}] {imperative summary}`, at most 72 characters, synthesized from `GOAL.md` —
  not a copy of it. `{category}` is resolved in Step 1 from the shape commit, never from `kind`.
- **Body** (sectioned; link artifacts as
  `https://github.com/PurdueRCAC/rcac-docs-mcp/blob/{head_sha}/spec/{slug}/<file>`, using the current
  `git rev-parse HEAD`):
  - **Summary** — a high-level description of the whole change. Say what was **removed** as well as
    added; the standing bias in this repository is to delete, and a deletion is the part a reader
    cannot reconstruct from the file list.
  - **Goal** → link `GOAL.md`.
  - **Design** → link `PLAN.md`.
  - **Research** → links to `research/*.md`, if present.
  - **Phases completed** → rendered from the `TECH.md` FSM (id · name · satisfies).
  - **Verification** → the gates and sandbox drives actually run, with the post-conditions observed,
    taken from `REVIEW.md`. Give the pytest counts, not "tests pass". Name anything taken on trust
    because it needs the live deployment or today's upstream RCAC-Docs — the fixture is a pinned
    submodule and is not evidence about upstream.
  - **Contract surface** → confirm the same-commit rule was honored across the five places that state
    the same contract: `README.md`, `INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` in `__init__.py`, and
    `SERVER_INSTRUCTIONS` in `server.py`. Say "none affected" when that is true.
  - **Deploy** → one line stating that merging this PR moves `:latest` and rolls the pod, plus
    anything an operator must do by hand (none, normally — the entrypoint re-runs `--update-site` and
    `--index` on every pod start).
  - **Harness feedback** — surface the self-improvement loop *only when substantial*, per the rule
    below; omit the section entirely otherwise.
  - Issue: `Closes #NN` when there is one. This PR targets `main`, which is the default branch, so
    GitHub closes the issue on merge.
  - Trailing line: `Generated with [Claude Code](https://claude.com/claude-code)`.

**Harness-feedback surfacing rule.** Before finalizing the body, read this feature's harness notes:
```
uv run .agents/factory/bin/meta_status.py spec/{slug}/META.md --status open
```
Add a terse, factual, **toolchain-only** `## Harness feedback` section when there is something
substantial: `counts.open > 0` (list each open finding as a one-liner `F# · {severity} · {title}`),
**or** `spec/{slug}/META.md` has a non-empty "What worked well" section — read the file directly for
that, since the parser only enumerates `F#` findings; list those bullets. Keep it short and
process-focused; it is reviewed alongside the code, so it must not editorialize about the feature. No
emoji in the heading or the body. If there are no open findings and nothing worked-well of note, or
the file is absent (`exists: false`), **omit the section**. `proj-publish` never *writes* `META.md`
findings; it is the loop's surfacer, and `/proj-harness` is where fixes get applied.

### Step 3 — Confirm with the human
Present the mode (PR or local), the title, and the body via `AskUserQuestion`. State plainly which
option deploys: `pr` alone does not, `pr merge` and a pushed `local` do. Do not proceed without a
choice.

Once confirmed, stamp the FSM terminal so the retained record does not read `in_review` forever:
```
uv run .agents/factory/bin/set_phase.py spec/{slug}/TECH.md --top-status done --touch
git add spec/{slug}/TECH.md && git commit -m "[{category}] Mark {slug} roadmap done"
```
A spec-only commit; the Step 1 staleness gate ignores it by design.

### Step 4a — PR (default)
```
git push -u origin {branch}
gh pr create --base main --head {branch} --title "{title}" --body-file - <<'PR_BODY'
… the Step 2 body …
PR_BODY
```
Report the PR URL. If `merge` was requested and confirmed, first record the digest `:latest` points at
*now* — it is the baseline Step 4c compares against, and after the merge it is unrecoverable:
```
curl -fsS "https://ghcr.io/token?scope=repository:purduercac/rcac-docs-mcp:pull"
curl -fsSI -H "Authorization: Bearer {token}" -H "Accept: application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json" https://ghcr.io/v2/purduercac/rcac-docs-mcp/manifests/latest | grep -i '^docker-content-digest'
```
Then squash with an **explicit** subject and body so none of the intermediate branch commit subjects
leak into the `main` commit — a bare `gh pr merge --squash` concatenates every branch commit message
into the squash body:
```
gh pr merge {N} --squash --subject "{title}" --body "{one-line summary, or empty}" --delete-branch
```
Then `git switch main && git pull --ff-only`, so the local tree matches what is deploying, and
continue to Step 4c.

### Step 4b — local (`local`)
```
git switch main && git pull --ff-only
git merge --squash {branch}
git commit -m "{title}"     # no co-author trailer
git branch -D {branch}
```
Do **not** push `main` unless the human explicitly asks. An unpushed local merge is the only way to
land a change here without deploying it, so the push is a second, separate confirmation — and once it
happens, Step 4c applies unchanged.

### Step 4c — watch the deploy (only when a merge actually landed on `main`)
A green CI run is **not** evidence the change is live. The build and the registry are fast; the
Geddes poller is not, and it has been observed taking over 26 minutes to reconcile while both
`:latest` and `sha-<short>` resolved correctly at the registry the whole time. Three checks, in order,
and stop at the first that fails.

1. **The build.** `gh run list --workflow build-and-push.yml --branch main --limit 3`, then
   `gh run watch {id} --exit-status`. A failed build means nothing shipped; report it and stop.
2. **The digest moved.** Re-run the two `curl` commands from Step 4a and compare against the baseline.
   Unchanged after a successful build means the workflow published something other than what you
   think it did.
3. **The endpoint serves it.** The MCP `initialize` handshake needs
   `Accept: application/json, text/event-stream` — a bare `curl` gets HTTP 406 — and returns an
   `mcp-session-id` header:
   ```
   curl -si -X POST https://docs.rcac.purdue.edu/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"proj-publish","version":"0"}}}'
   ```
   Then send `notifications/initialized` with `Mcp-Session-Id: {id}`, then a `tools/call` that
   exercises **this change specifically**. `serverInfo.version` in the handshake is FastMCP's version,
   not this project's, so it identifies nothing about the build — a probe that only reads it proves
   the pod is up and nothing else. Choose a query or a `doc_load` path whose result differs before and
   after.

**Report honestly.** If the digest moved and the probe still shows the old behavior, the pod has not
rolled. Say exactly that, with the clock time of the probe, and hand back the re-probe command. Do not
claim the fix is live, and do not sit in a polling loop for half an hour: one or two re-probes spaced
a few minutes apart (`sleep 300`) is the budget, then it is the human's to watch.

### Step 5 — Report
The PR URL or local merge result, the squash subject that landed, the retained `spec/{slug}/`
artifacts, and the deploy state as three separate facts — workflow conclusion, digest before → after,
and the endpoint probe with its timestamp — never collapsed into one word. Then whether a release is
warranted (`/proj-release`): a user-visible behavior change usually is, but note the ordering, because
it is the reverse of most projects. The change is *already* deployed; `/proj-release` bumps
`pyproject.toml`, tags `v<X.Y.Z>` and cuts a GitHub release, which labels what shipped rather than
shipping it. There is no PyPI publish, no docs site and no man pages — the artifact is the container
image.

If `meta_status.py` reported open findings in Step 2, name **`/proj-harness {slug}`** as a follow-on
too, to be run once the merge has landed. `proj-harness` is the only thing that applies a `META.md`
finding, and nothing else in the lifecycle recommends it — surfacing findings into a PR body that
no one acts on is the observe half of the loop running without the act half.

If this cycle was seeded from a deferral — find it with plain Bash, not the `Grep` tool:
`grep -rl "^status: adopted:{slug}$" issues .security/issues 2>/dev/null || true`. The harness `Grep`
tool is ripgrep-backed and honours `.gitignore`, so it silently returns nothing from the security
lane, which is both gitignored and a dot-directory. A sweep that cannot see `.security/` reports
"no hidden-lane seed" every time, which is indistinguishable from the truth. Then name the seed and flag what the landed cycle leaves behind: its
entry under `## Queued` in `ROADMAP.md` now advertises work that has shipped. **Report it; never
retire it here.** Deleting or editing the seed would put this skill's own commit outside `spec/`,
where the Step 1 staleness gate reads it as post-review drift and STOPs the next invocation — which is
why publish carries neither an `Edit` tool nor a deletion verb. Retirement is `/proj-roadmap`'s job,
run once the merge lands on `main`, and only when the cycle shipped the seed *whole*: scope cut to a
non-goal leaves a live remainder that must stay on the index. A match under `.security/` is never
named in a PR body or a report — say only that a hidden-lane seed is affected. `.security/` is
gitignored and absent in a fresh clone; finding nothing there is the normal case, not a fault.

## Notes

- `spec/{slug}/` is **retained** on merge: the immutable dated design record. The PR body may label
  PLAN and research as historical.
- This skill does not bump the version or tag. That is `/proj-release`, and `/proj-release` does not
  ship.
- The deployed pod runs `--update-site` → `--index` → serve under `set -eu` on every start, so a
  change that breaks either step means the pod never becomes ready and the previous one keeps serving.
  That is the designed failure mode; a rollback is a revert commit on `main`, which is another deploy.
- The user has aliased `rm` away — `del`, and `git rm` for tracked files. This skill removes nothing,
  so it should never come up.
