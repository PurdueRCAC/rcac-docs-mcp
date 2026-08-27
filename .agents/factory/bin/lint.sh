#!/bin/sh
# SPDX-FileCopyrightText: 2026 Purdue University
# SPDX-License-Identifier: MIT
#
# The static gate: importability, convention, repository-shape, and skill-integrity
# checks that a factory `verify:` command can depend on. The test suite proves the
# server behaves; this proves the repository is still shaped the way every skill
# assumes. It must stay green — a gate with a known failure is not a gate.
#
# Usage:
#   .agents/factory/bin/lint.sh            # all checks
#   .agents/factory/bin/lint.sh --no-net   # skip anything that may resolve dependencies
#
# Exit codes: 0 all checks passed · 1 a check failed · 3 a check could not be run
# (missing tool). 3 is distinct from 1 on purpose: "could not run" must never be
# mistaken for "passed".

set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
repo=$(CDPATH='' cd -- "$here/../../.." && pwd -P)
cd "$repo"

no_net=''
[ "${1:-}" = "--no-net" ] && no_net=1

failed=0
note() { printf 'lint: %s\n' "$*"; }
fail() { printf 'lint: FAIL  %s\n' "$*"; failed=1; }

# ---- 1. importability and collection ---------------------------------------
#
# A syntax error or a broken import surfaces here in a second, rather than after
# the full suite. Collection is the cheaper half of `pytest -q` and catches a
# fixture or conftest fault that plain importability misses.

if [ -n "$no_net" ] && ! command -v uv >/dev/null 2>&1; then
    note "SKIP  import/collect (--no-net, and uv is not on PATH)"
elif ! command -v uv >/dev/null 2>&1; then
    note "CANNOT RUN  uv is not on PATH"
    exit 3
else
    if uv run --quiet python -c 'import rcac_docs_mcp' >/dev/null 2>&1; then
        note "OK    import rcac_docs_mcp"
    else
        fail "the package does not import"
    fi
    if uv run --quiet pytest -q --collect-only >/dev/null 2>&1; then
        note "OK    pytest collects"
    else
        fail "pytest cannot collect the suite"
    fi
fi

# ---- 2. shell syntax --------------------------------------------------------
#
# Almost no shell survives in this repository, but what does is load-bearing: the
# container entrypoint and the two factory scripts. `sh -n` is free.

for f in docker-entrypoint.sh .agents/factory/bin/temp_site.sh .agents/factory/bin/lint.sh; do
    [ -f "$f" ] || continue
    sh -n "$f" || fail "$f does not parse"
done
note "OK    shell scripts parse"

# ---- 3. convention census ---------------------------------------------------
#
# The house style is enforced by prose and by review, not by a formatter (adopting
# one is deferred work — see issues/). These three checks are the mechanical subset:
# each has a single correct answer and each has already drifted once.

# Tracked files plus untracked-but-not-ignored ones. Plain `git ls-files` sees only
# what is already in the index, so a source file created and not yet staged escapes
# every census below — and before the commit is exactly when a gate is worth having.
sources() {
    git ls-files --cached --others --exclude-standard -- src tests .agents/factory/bin \
        | grep -E '\.py$' || true
}

# Every Python source file carries the two-line SPDX header, with one copyright
# entity across the tree. The entity is checked and the year is not: a file added
# in a later year is correct, a file crediting a different holder is not.
spdx_missing=''
for f in $(sources); do
    header=$(head -8 "$f")
    if ! printf '%s\n' "$header" | grep -q 'SPDX-FileCopyrightText:.*Purdue University' ||
       ! printf '%s\n' "$header" | grep -q 'SPDX-License-Identifier: MIT'; then
        spdx_missing="$spdx_missing $f"
    fi
done
if [ -n "$spdx_missing" ]; then
    fail "missing or non-conforming SPDX header:$spdx_missing"
else
    note "OK    SPDX headers uniform (Purdue University / MIT)"
fi

# The version is single-sourced in pyproject.toml and surfaced at runtime through
# importlib.metadata. A second literal anywhere else drifts on the next release.
version=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -1)
if [ -z "$version" ]; then
    fail "cannot find 'version = ' in pyproject.toml"
else
    stray=$(git grep --untracked -n -E '__version__[[:space:]]*=[[:space:]]*.[0-9]+\.[0-9]+' -- src || true)
    if [ -n "$stray" ]; then
        fail "a hardcoded version literal shadows the pyproject.toml single source: $stray"
    else
        note "OK    version single-source reads $version"
    fi
fi

# Feature-scoped spec ids restart per feature and collide across branches, so they
# mean nothing to a later reader of the source. Provenance lives in the commit and
# the retained spec/{slug}/ record. The boundaries are spelled out rather than
# written \b, which is a GNU extension that git's POSIX -E engine matches nothing
# with — the check reported clean against a file containing "R1" for exactly that
# reason.
ids=$(git grep --untracked -n -E '(^|[^A-Za-z0-9_])[RP][0-9]+([^A-Za-z0-9_]|$)' \
        -- src README.md INSTRUCTIONS.md || true)
if [ -n "$ids" ]; then
    fail "feature-scoped spec id in source or user-facing docs: $ids"
else
    note "OK    no feature-scoped spec ids in src/ or the user-facing docs"
fi

# ---- 4. repository shape ----------------------------------------------------
#
# `.claude` and `CLAUDE.md` are symlinks (git mode 120000). Materialized into real
# files they still work today and drift apart on the next edit, which is the failure
# this check exists to catch — an agent editing CLAUDE.md while a human edits
# AGENTS.md, with no conflict to reveal it.

for pair in ".claude .agents" "CLAUDE.md AGENTS.md"; do
    link=${pair% *}
    want=${pair#* }
    mode=$(git ls-files -s "$link" | awk '{print $1}')
    target=$(git cat-file -p ":$link" 2>/dev/null || echo '?')
    if [ "$mode" != "120000" ]; then
        fail "$link is not a symlink in the index (mode ${mode:-absent})"
    elif [ "$target" != "$want" ]; then
        fail "$link points at '$target', expected '$want'"
    fi
done
note "OK    .claude and CLAUDE.md are symlinks"

# The image build context excludes agent and lifecycle material. .dockerignore names
# paths individually, so a new top-level directory is not covered by anything and
# silently inflates every build until someone notices the transfer size.
missing_ignores=''
for path in .agents .claude spec issues .security docs tests; do
    grep -qx "$path" .dockerignore || missing_ignores="$missing_ignores $path"
done
if [ -n "$missing_ignores" ]; then
    fail ".dockerignore does not exclude:$missing_ignores"
else
    note "OK    .dockerignore excludes the agent and lifecycle trees"
fi

# ---- 5. skill state injections ----------------------------------------------
#
# A `!`cmd`` line under "Current state" runs when the skill loads, and the harness
# aborts the entire skill when one exits non-zero — rendering the failure with that
# command's own output inside it, so a correct answer arrives looking like a fault.
# `grep -r` over an absent .security/issues exits 2 while still listing every match,
# and that alone is enough to make a skill unrunnable.
#
# The commands execute at every skill load regardless; running them here only moves
# the discovery to a developer who is watching. Empty state is the case that breaks
# them, and it is reachable only from a repository in that state, which is why this
# is a gate rather than a rule someone remembers. portability.md carries the rule.

inject_tmp="${TMPDIR:-/tmp}/rcac-lint-inject.$$"
trap 'rm -f "$inject_tmp"' EXIT INT TERM

inject_ok=1
inject_n=0
for f in .agents/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    # One injection per line: between the first !` and the last ` on that line.
    # The backticks are the markdown delimiter being matched, not a substitution.
    # shellcheck disable=SC2016
    sed -n 's/^[^!]*!`\(.*\)`.*$/\1/p' "$f" > "$inject_tmp"
    while IFS= read -r cmd; do
        [ -n "$cmd" ] || continue
        inject_n=$(( inject_n + 1 ))
        if ! ( eval "$cmd" ) >/dev/null 2>&1; then
            fail "$f: injected state command exits non-zero, so the skill cannot load: $cmd"
            inject_ok=0
        fi
    done < "$inject_tmp"
done

if [ "$inject_ok" -eq 1 ]; then
    note "OK    $inject_n skill state injections all exit 0"
fi

# ---- report ------------------------------------------------------------------

if [ "$failed" -eq 0 ]; then
    note "all checks passed"
    exit 0
fi
note "one or more checks failed"
exit 1
