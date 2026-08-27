---
name: proj-release
description: >-
  Human-gated cutter of rcac-docs-mcp versions — the operational sibling of proj-harness and
  proj-roadmap. It does NOT ship: `/proj-publish` already shipped the change when it squash-merged to
  `main`, because a merge to `main` is the deploy. This skill only puts a version on what is already
  there — bump `pyproject.toml` (the single source) + `uv lock`, commit `[release] Release v<X.Y.Z>`
  on `main`, run the CI-mirror gate (pytest with the submodule initialized and zero skips → lint.sh →
  a temp_site.sh end-to-end drive → a local `docker build`), annotated tag `v<X.Y.Z>`, then — only
  after an explicit human OK before the first irreversible step — push, `gh release create`, and
  verify the image digest and the live endpoint. Rehearses the whole thing in an isolated detached
  `git worktree` first. Never infers a version. No PyPI, no man pages, no docs site: the artifact is
  the container image. Operational, NOT a lifecycle step — never writes META findings, never
  recurses, never weakens a gate.
disable-model-invocation: true
argument-hint: "<X.Y.Z | patch | minor | major> [--skip-dry-run] | status"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion, Bash(uv run *), Bash(uv sync *), Bash(uv lock *), Bash(git status *), Bash(git branch *), Bash(git rev-parse *), Bash(git rev-list *), Bash(git describe *), Bash(git log *), Bash(git show *), Bash(git diff *), Bash(git fetch *), Bash(git remote *), Bash(git ls-remote *), Bash(git switch *), Bash(git add *), Bash(git commit *), Bash(git push *), Bash(git tag *), Bash(git worktree *), Bash(git submodule *), Bash(gh release *), Bash(gh run *), Bash(gh api *), Bash(gh repo *), Bash(docker build *), Bash(.agents/factory/bin/lint.sh*), Bash(.agents/factory/bin/temp_site.sh*), Bash(curl *), Bash(mktemp *), Bash(head *), Bash(tail *), Bash(grep *), Bash(ls *), Bash(del *), Bash(echo *), Bash(git -C *), Bash(cut *)
---

# proj-release — cut a tagged version, human-gated

## When to Use

Invoke `/proj-release` to put a version number on code that is **already on `main`**. It is an
**operational sibling of `/proj-harness` and `/proj-roadmap`, NOT a lifecycle step**: it touches no
`spec/`, no FSM, no `GOAL/PLAN/TECH/REVIEW`; it moves the version, one commit, a tag, and a GitHub
release.

**This skill does not ship.** `/proj-publish` shipped the change when it squash-merged to `main` —
that push fired `build-and-push.yml`, moved `ghcr.io/purduercac/rcac-docs-mcp:latest`, and the Geddes
poller rolled the pod. By the time you are here, users already have the code. What is missing is a
name for it.

The push in Step 7 is nonetheless **itself a deploy**: the `[release]` commit lands on `main` like any
other and triggers another build and another roll. The tree is one version string different from what
is running, which makes it the lowest-risk deploy this repository has, but it is not a no-op and it is
gated like one.

Reference: [`factory/invariants.md`](../../factory/invariants.md) §10 (the deploy contract, `uv.lock`
tracked, `provenance: false`), §11 (the skipped-test false green) and §12 (version single-sourced),
plus [`AGENTS.md`](../../../AGENTS.md) § *Branch posture and commits*. This file is the ground truth
for the release procedure; it replaces the retired `/release` skill and its `WIP:`-prefix rebase,
which no longer describes anything this repository does.

**Harness portability.** Runs on any harness — see
[`factory/portability.md`](../../factory/portability.md). Fallbacks: run the *Current state* commands
yourself if not auto-injected; ask in plain text and STOP if `AskUserQuestion` is unavailable. `git`,
`gh`, `uv`, `docker` and the `factory/bin` scripts are portable shell, and the rehearsal is plain
`git worktree` — no Claude-specific affordance is load-bearing here.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Current state (injected at load)

- Branch: !`git branch --show-current | grep . || echo "(detached HEAD)"`
- Tree (must be clean): !`git status --porcelain | head -n 20 | grep . || echo "(clean)"`
- Version (pyproject.toml — the only source): !`grep -E '^version = ' pyproject.toml || echo "(no version line)"`
- Recent tags: !`git tag -l --sort=-v:refname | head -n 5 | grep . || echo "(no tags)"`
- Local main: !`git log --oneline -1 main 2>/dev/null || echo "(no local main)"`
- Remote main: !`git log --oneline -1 origin/main 2>/dev/null || echo "(no origin/main — fetch first)"`
- Unreleased commits: !`t=$(git describe --tags --abbrev=0 2>/dev/null); git log --oneline ${t:+$t..}main 2>/dev/null | head -n 15 | grep . || echo "(none)"`
- Submodule fixture (a leading `-` means uninitialized — 31 tests would skip): !`git submodule status tests/fixtures/RCAC-Docs 2>/dev/null || echo "(not registered)"`
- Recent releases: !`gh release list -L 3 2>/dev/null | grep . || echo "(none, or gh unavailable)"`

(The registry and the live endpoint are checked in Step 8, not at load — they are network probes.)

## Argument Parsing

Parse `$ARGUMENTS` case-insensitively for the keywords and flags (an explicit version string is
case-sensitive). If self-contradictory or ambiguous, STOP and ask.

- **Version** (first positional, required): either an explicit `X.Y.Z` (a leading `v` is accepted and
  stripped — `pyproject.toml` holds the bare string, the tag carries the `v`) or one of `patch` /
  `minor` / `major`, which **computes** a bump from the current `pyproject.toml` value. Missing →
  STOP and offer the three computed bumps via `AskUserQuestion`.
- **A computed bump is still confirmed by the human** (Step 6). **Never infer a version and never
  auto-bump silently** — a tag and a GitHub release are permanent, and a version string that named
  the wrong tree can be deleted but never honestly reused.
- Validate: PEP 440 / semver, no hyphen in a prerelease suffix (`0.2.0rc1`, not `0.2.0-rc1`),
  strictly greater than the latest tag by PEP 440 ordering (e.g. via
  `uv run python -c "from packaging.version import Version; ..."`), and not already a tag. A
  prerelease suffix is allowed and adds `--prerelease` to `gh release create`; everything else is a
  final release.
- **`status`** as the sole token → Step 0 fast-path (no work).
- **Flags:** `--skip-dry-run` opts out of Step 2. It must be explicit and it is discouraged; the
  rehearsal is the only thing standing between a bad bump and a permanent tag.
- Any unrecognized token → STOP and ask.

## What a cut touches

| Thing | This skill | Notes |
|---|---|---|
| `pyproject.toml` `version` | bumped | The only source. `__version__` reads it via `importlib.metadata`. |
| `uv.lock` | re-locked | Tracked on purpose — the Dockerfile bind-mounts it (invariants §10). |
| `main` | one `[release]` commit, pushed | The push is a deploy. Never force-pushed. |
| tag `v<X.Y.Z>` | annotated, pushed | Does **not** trigger the workflow by itself; the branch push does. |
| GitHub release | created from the tag | Notes drafted from the log, confirmed by the human. |
| `ghcr.io/purduercac/rcac-docs-mcp:latest` | moved by CI, not by this skill | Verified by digest in Step 8. |
| PyPI, man pages, a docs site | **never** | None exist. The artifact is the container image. |

## Safety Principles

- **Confirm before the first irreversible step.** Steps 1–5 are all reversible in-tree; the single
  Step 6 `AskUserQuestion` gate precedes the push. **Nothing leaves the machine without an explicit
  human OK.** `AskUserQuestion` unavailable → ask in plain text and STOP.
- **Dry-run first (default on).** The whole cut — bump, lock, gate, tag — is rehearsed in an isolated
  detached `git worktree` before a single real ref moves.
- **The gate is non-negotiable.** `uv run pytest -q` **with the submodule initialized**, `lint.sh`, a
  `temp_site.sh` end-to-end drive, and a local `docker build` must all pass. A red gate is a STOP,
  never an override-to-ship.
- **A skipped test is a red gate.** With `tests/fixtures/RCAC-Docs` absent the suite reports
  `76 passed, 31 skipped` and still **exits 0** — 29% of the suite vanishing without changing the
  exit status (invariants §11). Read the counts, not the exit code. Any nonzero skip count fails the
  gate.
- **Never infer a version.** The human states it or confirms the computed bump.
- **Version is single-sourced.** Bump `pyproject.toml` only; the tag is `v` + that exact string, and
  the runtime reports it through `importlib.metadata.version('rcac-docs-mcp')`. Never hardcode a
  version anywhere else.
- **`main` discipline.** One `[release]` commit directly on `main` — a mechanical version bump has no
  review surface a PR would examine. Never force-push `main`, never rewrite a published tag.
- **Release notes are drafted, then confirmed.** Auto-draft from `git log <lasttag>..HEAD` grouped by
  `[category]`; present for human edit at Step 6; never publish unreviewed notes.
- **Commit convention.** Subject `[release] Release v<X.Y.Z>`, at most 72 characters. **No
  `Co-Authored-By` trailer** of any kind. A body only if it records something the diff does not show.
- **Never `rm`.** Use `del` (and `git rm` for tracked files); `git worktree remove` cleans the
  rehearsal.
- **Operational, not meta.** This skill never writes `META.md` findings and never recurses; harness
  friction here goes to `/proj-harness`.

## Procedure

### Step 0 — status fast-path (when requested)
`status` (or no meaningful args): report the current `pyproject.toml` version, the latest tags,
whether `main` and `origin/main` agree, the commits since the last tag, whether the submodule fixture
is initialized, and whether a release looks in-flight (an unpushed local tag, or a tag with no GitHub
release). Stop.

### Step 1 — Parse + pre-flight
Parse `$ARGUMENTS` → resolve the target version. Then, all of:

- **Clean tree** — `git status --porcelain` empty, else STOP (commit or stash first).
- **On `main`** — `git branch --show-current` is `main`, else STOP. This skill releases what shipped;
  it does not release a branch.
- **`main` == `origin/main`** — `git fetch origin --tags`, then compare `git rev-parse main
  origin/main`. Diverged or behind → STOP: `/proj-publish` lands work, not this skill.
- **Something to release** — `git log <lasttag>..main` is non-empty. Nothing since the last tag →
  STOP and ask; a version that names no change is noise.
- **Submodule initialized** — `git submodule status tests/fixtures/RCAC-Docs` must not begin with
  `-`. If it does, run `git submodule update --init tests/fixtures/RCAC-Docs` before going further;
  the gate is worthless without it.
- **Version legal** — not already a tag, strictly greater than the latest, suffix rules per
  *Argument Parsing*.

### Step 2 — Worktree rehearsal (default ON; `--skip-dry-run` opt-out, discouraged)
Rehearse the entire cut in isolation before any real ref moves:

1. `dir=$(mktemp -d)` — **outside the repository**. Claude Code refuses to create a worktree beneath a
   symlinked `.claude`, and `.claude` here is a symlink to `.agents`, so a path inside the repo fails.
   `$TMPDIR` also keeps the rehearsal from dirtying the working tree, mirroring `temp_site.sh`.
2. `git worktree add --detach "$dir/rel" main`. **`--detach`** because `main` is already checked out
   in the main tree and git refuses to check out the same branch twice; a detached worktree at the
   same commit sidesteps that and needs no branch of its own.
3. `git -C "$dir/rel" submodule update --init tests/fixtures/RCAC-Docs`. **A fresh worktree does not
   populate submodules**, so without this the rehearsal's `pytest` reports 31 skips and its
   `temp_site.sh` exits 3 — a gate that proves nothing while looking green.
4. In that worktree, replay Step 3 (bump + `uv lock`, no commit needed) and the **full Step 4 gate**.
5. Tear down, in this order: `git -C "$dir/rel" status --porcelain` to see what the rehearsal left,
   then `git worktree remove --force "$dir/rel"` (a plain `remove` exits 128 on the uncommitted bump),
   then `del -rf "$dir"` — the `mktemp` parent outlives the worktree. Without `del`, leave `$dir`
   alone; it is under `$TMPDIR` and the system reaps it.

Any red → STOP and report; **nothing in the real tree moved.** A few permission prompts may appear
for commands run against the `$TMPDIR` path; that is expected and harmless.

### Step 3 — Bump + lock + commit (real tree, on `main`)
1. Edit the `version = "…"` line in `pyproject.toml` → `X.Y.Z` (the ONLY source).
2. `uv lock` — updates the `rcac-docs-mcp` entry in `uv.lock`.
3. Confirm `git diff --stat` shows **exactly two files**, `pyproject.toml` and `uv.lock`. Anything
   else means the tree was not what Step 1 said it was → STOP.
4. Commit, staging exactly those two files:
   ```bash
   git commit -m "[release] Release v<X.Y.Z>"
   ```

### Step 4 — Gate (mirrors CI; non-negotiable)
Run all of, in order, against the commit from Step 3:

```bash
uv sync --quiet
uv run pytest -q                       # assert the counts: 107 passed, 0 skipped
.agents/factory/bin/lint.sh            # 0 pass · 1 fail · 3 could-not-run
.agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index >/dev/null && uv run python -c "
from rcac_docs_mcp.tools import doc_search
print(doc_search.fn(\"slurm\"))"'
docker build -t rcac-docs-mcp:release-gate .
```

- **`pytest`**: read the summary line. `107 passed` is today's full-suite count; if the suite has
  legitimately grown the number changes, but **any skip count above zero is a red gate**, not a pass.
- **`lint.sh`**: exit 3 is "could not run", which is a STOP — it is not a pass.
- **`temp_site.sh`**: exits 3 when the fixture is absent, for the same reason. The drive must both
  index and return a search hit; the tools are FastMCP `FunctionTool` objects, so it is
  `doc_search.fn(...)`, never `doc_search(...)`.
- **`docker build`**: the image is what production runs; CI must not be the first place it is built.
  Docker unavailable is a could-not-run → STOP, or an explicit human waiver recorded in the Step 9
  report.

Any failure → STOP (never override-to-ship). Nothing has been pushed, so the cut is undone by
`git reset --hard origin/main` — deliberately outside this skill's allowlist, because a silent
working-tree discard is a human's call, not an agent's.

### Step 5 — Annotated tag
```bash
git tag -a v<X.Y.Z> -m "rcac-docs-mcp v<X.Y.Z>"
```
Tag the Step 3 commit, so the tag, `pyproject.toml`, and
`importlib.metadata.version('rcac-docs-mcp')` all agree. If the maintainer has tag signing configured
(`user.signingkey` / `tag.gpgSign`), use `git tag -s` instead and verify with `git tag -v v<X.Y.Z>`
**before** anything is pushed; a signing or verification failure is a STOP. Do not invent a key.

### Step 6 — PAUSE: confirm before anything irreversible
Everything so far is local and reversible. Draft the release notes from `git log <lasttag>..HEAD`
grouped by `[category]` (`feature`, `fix`, `docs`, `refactor`, `harness`), linking `#NN` where a PR or
issue number appears; write them to a file outside the repo (`$dir/NOTES.md` or a fresh `mktemp`) so
the tree stays clean. Then present via `AskUserQuestion`:

- the version, and that it was **stated** or **computed** (say which);
- the tag and the commit it points at;
- the drafted notes, human-editable;
- the exact push and publish commands;
- and the consequence in plain words: **pushing `main` fires `build-and-push.yml`, moves `:latest`,
  and Geddes will roll the pod.**

**Nothing is pushed until an explicit OK.**

### Step 7 — Push + publish
Push the branch first, then the tag — `--verify-tag` requires the tag to be on the remote:

```bash
git push origin main
git push origin v<X.Y.Z>
gh release create v<X.Y.Z> --verify-tag --title "v<X.Y.Z>" --notes-file <file>
```

Add `--prerelease` only for a prerelease suffix. Use `--notes-file`, not `--generate-notes`: the notes
were confirmed at Step 6 and regenerating them here discards that review.

If `origin` does not exist (a detached fork or a bare local clone), do the local work and STOP with a
clear note that the push and the release were skipped. Never invent or add a remote.

### Step 8 — Verify after publish
1. **CI** — `gh run list --workflow "Build and push image" -L 3`, then `gh run watch <id>`. The run
   comes from the **branch push**; the tag push triggers nothing on its own.
2. **Registry, both tags, same digest** — fetch an anonymous pull token and compare manifests:
   ```bash
   tok=$(curl -s "https://ghcr.io/token?scope=repository:purduercac/rcac-docs-mcp:pull" \
         | grep -o '"token":"[^"]*' | cut -d'"' -f4)
   for ref in latest "sha-$(git rev-parse --short=7 HEAD)"; do
     curl -sI -H "Authorization: Bearer $tok" \
          -H "Accept: application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
          "https://ghcr.io/v2/purduercac/rcac-docs-mcp/manifests/$ref" | grep -i docker-content-digest
   done
   ```
   Both must resolve to the **same new digest**. That the *anonymous* token works at all is the second
   half of this check: the package published **private** the first time (GitHub's default for a
   first-time Actions publish, even from a public repo), and Geddes pulls unauthenticated. A 401 here
   means the package went private again, not that the release failed.
3. **The live endpoint** — probe `https://docs.rcac.purdue.edu/mcp` with an MCP `initialize` (it needs
   `Accept: application/json, text/event-stream`; a bare `curl` gets HTTP 406), then a `tools/call`
   with the returned `mcp-session-id`. The endpoint exposes **no version string**, so this proves the
   pod is alive and serving after the roll, not which image it runs — correlate with the digest above.
4. **Standing caveat, always reported:** the Geddes poller has taken **over 26 minutes** to reconcile
   (observed 2026-08-27, with the registry side correct throughout). A green CI run and a moved digest
   are **not** evidence the release is live. If the probe still answers from the old image, that is
   expected lag, not a failure — say so and say when it was last checked.
5. Confirm `main`, `origin/main` and the tag all point at the same commit.

### Step 9 — Report
Version and whether it was stated or computed; the tag SHA and signature status; the release URL; the
CI run URL and result; the two digests and whether they match; the anonymous-pull result; the endpoint
probe result **with a timestamp**; any waiver taken at Step 4; and the poller caveat.

## Examples

- `/proj-release 0.2.0` — cut `v0.2.0` from `main` at the stated version.
- `/proj-release minor` — compute `0.2.0` from `pyproject.toml`, confirm it with the human, cut it.
- `/proj-release patch` — the usual shape after a `fix/{slug}` cycle has landed.
- `/proj-release status` — version, tags, `main` vs `origin/main`, unreleased commits, submodule
  state, in-flight check; no changes.
- `/proj-release 0.1.1 --skip-dry-run` — skip the worktree rehearsal (discouraged).

## Notes

- **Reference `invariants.md`, don't duplicate it** — §10 (the deploy contract, tracked `uv.lock`,
  `provenance: false` and the `latest` + `sha-<short>` tags), §11 (the skipped-test false green), §12
  (single-sourced version, no co-author trailer). This skill introduces no new numbered invariant.
- **The retired `/release` skill.** Its `WIP:` prefix, its `GIT_SEQUENCE_EDITOR` rebase and its
  `wip → main` fast-forward describe a workflow that no longer exists. Factory commits already carry
  `[category]` subjects and are squashed by `/proj-publish`. If any of that resurfaces in a prompt,
  it is stale; this file is the procedure.
- **Worktree caveat.** Claude Code refuses to create a worktree under a symlinked `.claude`, and
  `.claude` here is a symlink to `.agents`. Create the rehearsal under `mktemp -d` outside the repo,
  and tear it down in the Step 2 order — `status` first, then `worktree remove --force`, then the
  parent.
- **A worktree has no submodules and no `.venv`.** The first is a false green waiting to happen (Step
  2.3 fixes it); the second is harmless, since `uv run` and the PEP 723 factory scripts resolve their
  own environments.
- **Deleting a tag is not undoing a release.** A pushed tag can be removed, but anyone who fetched it
  keeps it and the version number is spent. Reuse a version string only if it never left the machine.
