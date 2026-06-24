---
name: release
description: "Ship the wip branch to main for the rcac-docs-mcp Python package — strip WIP: prefixes from commit messages, fast-forward merge, push, return to wip and force-push. With optional arguments: squash commits, bump the version in pyproject.toml (patch/minor/major), create an annotated tag, and publish a GitHub release. Default invocation does merge-and-push only; additional behavior is enabled by free-form instructions after the slash command. WIP: prefixes are rewritten with a modern scripted git rebase (not the deprecated git filter-branch)."
---

# Release (Ship It)

## When to Use

Invoke `/release` when WIP commits on the `wip` branch are ready to ship
to `main`. The default behavior is conservative: rewrite `WIP: ` prefixes,
fast-forward merge into `main`, push, return to `wip`, and force-push.
Anything beyond that (squash, version bump, tag, GitHub release) is opt-in
via free-form instructions passed after the slash command.

This repo is the **`rcac-docs-mcp`** Python package (uv + hatchling,
pytest). The verification gate is the test suite, not a deck build.

## User Instructions

Additional instructions provided with the invocation: $ARGUMENTS

## Argument Parsing

If any text was passed with the invocation, parse it case-insensitively
against the patterns below. If the instruction is ambiguous or contradicts
itself, STOP and ask the user to clarify rather than guess.

- `patch version bump` / `patch bump` → bump patch (`x.y.Z+1`); implies tag
- `minor version bump` / `minor bump` → bump minor (`x.(Y+1).0`); implies tag
- `major version bump` / `major bump` → bump major (`(X+1).0.0`); implies tag
- `tag` → create an annotated version tag (requires a bump or explicit version)
- `release` → publish a GitHub release (implies tag and bump)
- `squash` / `squash commits` → collapse all wip commits into one before merging
- An explicit version like `v0.2.0` overrides bump computation

If no arguments were passed, run the default merge-only path (Steps 1, 3,
4, 6, 8 below; skip 2, 5, 7).

## Safety Principles

- `--force` is used **only** on the `wip` branch. Never on `main`, never
  on tags, never anywhere else.
- Use the default fast-forward merge (`git merge wip`). Never `--no-ff`.
  We want linear history.
- After a successful ship, `main` and `wip` point to the **same** commit.
- Author all new commits with `Co-Authored-By: Oz <oz-agent@warp.dev>`
  (per the user's wip-workflow rule).
- If pre-flight checks fail (dirty tree, wrong branch, test failure,
  divergent main), STOP and report. Do not attempt remediation without
  confirmation.
- Confirm the computed version and the release notes with the user
  **before** tagging or publishing.
- The version source of truth is the `version = "X.Y.Z"` line in
  `pyproject.toml`. A tag is `v` + that version (e.g. `v0.2.0`). Keep the
  two in lockstep — bump the file, then tag.
- This repo **has** a git remote (`origin`,
  `git@github.com:PurdueRCAC/rcac-docs-mcp.git`). Push paths are active. If
  a future checkout has no `origin`, treat all `origin` operations as
  conditional: do the local merge/tag work and STOP with a clear note that
  pushing was skipped — do not invent or add a remote.
- The user has aliased `rm` away — use `del` for any file removals
  (e.g. clearing a stray `*.bak`).

## Procedure

### Step 1 — Pre-flight checks (always)

1. Working directory must be clean:
   ```bash
   git status --porcelain
   ```
   Non-empty output → abort.
2. Current branch must be `wip`:
   ```bash
   git branch --show-current
   ```
3. Sync with origin **only if a remote exists**:
   ```bash
   if git remote | grep -q .; then git fetch origin && git fetch --tags; fi
   ```
4. `wip` must be ahead of `main`:
   ```bash
   git rev-list --count main..HEAD
   ```
   `0` → nothing to ship; abort.
5. Tests must pass (the ship gate):
   ```bash
   uv sync --quiet && uv run pytest -q
   ```
   Non-zero exit → abort. **Refactor-tolerance:** during the documented
   package refactor the tree can be intentionally non-importable between
   Stage 1 and the end of Stage 3 (see `ROADMAP.md`). Do **not** ship from
   a known-red mid-refactor state — `/release` is for shipping a coherent,
   green `wip`. If the user insists on shipping a WIP checkpoint anyway,
   STOP and make them confirm explicitly before bypassing the gate.

### Step 2 — Squash (only if `squash` was requested)

Skip entirely unless the user asked to squash. When squashing:

1. Compute the merge-base and soft-reset to it (keeps all changes staged):
   ```bash
   BASE=$(git merge-base main wip)
   git reset --soft "$BASE"
   ```
2. Propose a commit message synthesized from the prior `WIP: `-prefixed
   messages, **without** the `WIP: ` prefix. Confirm with the user, then
   commit:
   ```bash
   git commit -m "<proposed message>" -m "Co-Authored-By: Oz <oz-agent@warp.dev>"
   ```
3. After squashing, **skip Step 3** (there are no `WIP: ` prefixes left to
   rewrite).

### Step 3 — Rewrite `WIP: ` prefixes (skip if squashed)

Strip the `WIP: ` prefix from every commit in `main..HEAD` using a **modern,
non-deprecated scripted rebase** (we no longer use `git filter-branch`, which
is deprecated and noisy). The rebase replays `main..HEAD` onto `main`,
marking each commit for `reword` and applying a `sed` rewrite
non-interactively via scripted sequence/commit editors:

```bash
GIT_SEQUENCE_EDITOR='sed -i.bak -E "s/^pick/reword/"' \
GIT_EDITOR='sed -i.bak -E "1 s/^WIP: //"' \
git rebase -i main
```

Notes:
- `GIT_SEQUENCE_EDITOR` turns every `pick` in the rebase todo into `reword`,
  so each commit's message is opened for editing.
- `GIT_EDITOR` then strips a leading `WIP: ` from the first line of each
  message. Commits that don't start with `WIP: ` are left unchanged.
- The `sed -i.bak` form is portable on macOS (BSD sed); the `.bak` temp
  files are inside git's transient rebase dir and are discarded with the
  rebase. If any step leaves a stray `*.bak`, remove it (use `del`, not
  `rm`, per the user's alias preference).
- If the rebase stops (e.g. an unexpected conflict — should not happen for a
  pure message rewrite replaying onto its own base), STOP and report; do not
  improvise. `git rebase --abort` returns to the pre-rewrite state.

### Step 4 — Fast-forward merge into `main`

```bash
git checkout main
git merge wip
```

Do **not** pass `--no-ff`. If git refuses the merge (non-fast-forward,
conflicts), STOP and report — `main` has diverged and human intervention is
needed.

### Step 5 — Version bump and tag (only if requested)

Skip entirely unless a bump, explicit version, or `tag` was requested. When
tagging:

1. Read the current version from `pyproject.toml` (the `version = "X.Y.Z"`
   line) and cross-check the latest tag:
   ```bash
   grep -E '^version = ' pyproject.toml
   git describe --tags --abbrev=0 2>/dev/null || echo "(no tags yet)"
   ```
2. Compute the new version per semver from the `pyproject.toml` value, or
   use the explicit version provided. (If no tag exists yet, this is likely
   the first tagged release — `v0.1.0` is the current baseline in
   `pyproject.toml`.)
3. Confirm the computed version with the user.
4. Edit `pyproject.toml` to the new version, commit on `main` (the merged
   HEAD) with the Oz co-author trailer, then create an **annotated** tag:
   ```bash
   git commit -am "Release v<version>" -m "Co-Authored-By: Oz <oz-agent@warp.dev>"
   git tag -a v<version> -m "Release v<version>"
   ```
   Keeping the bump commit on `main` before tagging ensures the tag, the
   `pyproject.toml` version, and `importlib.metadata.version('rcac-docs-mcp')`
   all agree. (Step 8 fast-forwards `wip` back to this `main`, so the bump
   is not lost.)

### Step 6 — Push `main` (and tag if any) — only if a remote exists

```bash
if git remote | grep -q .; then
  git push origin main
  git push origin v<version>   # only if a tag was created in Step 5
else
  echo "No remote configured — skipped push of main (and tag). Local refs updated."
fi
```

### Step 7 — GitHub release (only if `release` was requested)

Skip entirely unless the user asked for a release. Requires a remote +
`gh`. When releasing:

1. Review prior release style for tone and structure, if any prior release
   exists:
   ```bash
   gh release list -L 5
   gh release view <previous-tag> --json tagName,name,body
   ```
2. Draft comprehensive notes consistent with the prior style. Either:
   - Use `--generate-notes` for an auto-generated changelog, then review
     with the user before publishing; **or**
   - Hand-curate notes in a file and pass `--notes-file <file>`.
3. Confirm the notes with the user, then publish:
   ```bash
   gh release create v<version> --title "v<version>" --generate-notes
   ```
   (or `--notes-file` instead of `--generate-notes`).

### Step 8 — Return to `wip` and force-push (always; push only if remote)

```bash
git checkout wip
git merge --ff-only main   # pull the release/bump commit back onto wip
if git remote | grep -q .; then
  git push --force origin wip
else
  echo "No remote configured — local wip updated; skipped force-push."
fi
```

After this (with a remote), `origin/main` and `origin/wip` point to the same
commit. The wip branch is ready for the next iteration.

## Examples

### Default — just merge

```
/release
```

Runs the test gate, strips `WIP: ` prefixes on `main..HEAD` (scripted
rebase), fast-forward merges into `main`, pushes `main`, returns to `wip`,
force-pushes `wip`. No version bump, no tag, no GitHub release.

### Minor version bump with tag and release

```
/release Let's do a minor version bump with tag and release
```

Default path plus: compute next minor version, confirm with user, bump
`pyproject.toml`, annotated tag on merged main, push tag, draft release
notes, publish GitHub release.

### Squash with patch bump, no release

```
/release squash and patch bump
```

Soft-reset `wip` to merge-base, propose+confirm a single combined commit
message, commit with Oz co-author. Skip prefix rewrite (no `WIP: ` left).
Merge to main, bump `pyproject.toml` patch version, tag, push tag. **No**
GitHub release. Force-push wip.

### Explicit version

```
/release tag as v1.0.0 and release
```

Use `v1.0.0` directly instead of computing a bump (writing `1.0.0` to
`pyproject.toml`). Same flow as a bump-with-release otherwise.

## Notes

- The `WIP: ` prefix convention and the force-push-on-wip allowance are per
  the user's wip-workflow rule.
- **Modernized rewrite.** This skill uses a scripted `git rebase -i` (via
  `GIT_SEQUENCE_EDITOR` + `GIT_EDITOR`) to strip `WIP: ` prefixes — a
  deliberate departure from the deprecated `git filter-branch`. If you ever
  need to verify the result, check that the merged history shows no
  remaining `WIP: ` first lines (`git log main -n 50 --format=%s`).
- The version lives in `pyproject.toml` and is surfaced at runtime via
  `importlib.metadata.version('rcac-docs-mcp')` in `rcac_docs_mcp/__init__.py`.
  Always bump the file (not just the tag) so the installed package reports
  the right version.
- If the user's instruction includes something not covered above (e.g.
  `dry run`, `skip tests`, `publish to PyPI`, `add a remote`), STOP and ask
  before deviating from the documented procedure. PyPI publishing is **not**
  part of this skill.
