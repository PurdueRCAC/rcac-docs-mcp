#!/bin/sh
# SPDX-FileCopyrightText: 2026 Purdue University
# SPDX-License-Identifier: MIT
#
# Run a command against a throwaway site, so factory verify commands and review
# drives never touch the developer's real site — the one under $RCAC_DOCS_SITE or
# ~/.local/share/rcac-docs-mcp, which holds a full RCAC-Docs checkout and a built
# index that took minutes to produce.
#
# A site is one container directory holding the docs checkout at <site>/repo and
# the search index at <site>/index.db. This script builds one from the pinned
# RCAC-Docs submodule fixture, so a drive never clones from the network and never
# depends on what upstream happens to look like today.
#
# Usage:
#   .agents/factory/bin/temp_site.sh uv run rcac-docs-mcp --index
#   .agents/factory/bin/temp_site.sh sh -c 'uv run rcac-docs-mcp --index && uv run rcac-docs-mcp --index'
#   .agents/factory/bin/temp_site.sh --empty uv run rcac-docs-mcp --update-site
#   .agents/factory/bin/temp_site.sh --keep sh -c 'uv run rcac-docs-mcp --index'
#
# Options:
#   --empty   Leave <site>/repo absent, so --update-site exercises the clone path
#             against the file:// fixture instead of the pull path.
#   --keep    Leave the sandbox in place and print its path. For inspection.
#
# Variables the command sees: RCAC_DOCS_SITE (the sandbox), RCAC_DOCS_URL (a
# file:// URL at the fixture, so --update-site never reaches the network), and
# RCAC_DOCS_SANDBOX. Everything else RCAC_* the developer had exported is scrubbed.
#
# Exit codes: the command's own status · 2 usage error · 3 the RCAC-Docs submodule
# fixture is not initialized. 3 is distinct from 1 on purpose: without the fixture
# this script cannot prove anything, and "could not run" must never be mistaken for
# "passed". That is the single most likely false green in this repository — the
# submodule-gated tests skip silently and `pytest -q` still exits 0.

set -eu

# Repo root from this script's own location, not from $PWD, so the wrapper works
# when invoked from anywhere.
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
repo=$(CDPATH='' cd -- "$here/../../.." && pwd -P)

empty=''
keep=''

while [ $# -gt 0 ]; do
    case "$1" in
        --empty) empty=1; shift ;;
        --keep)  keep=1; shift ;;
        --)      shift; break ;;
        -*)      echo "temp_site.sh: unknown option: $1" >&2; exit 2 ;;
        *)       break ;;
    esac
done

[ $# -gt 0 ] || { echo "usage: temp_site.sh [--empty] [--keep] COMMAND [ARG...]" >&2; exit 2; }

fixture="$repo/tests/fixtures/RCAC-Docs"
if [ ! -d "$fixture/docs" ]; then
    echo "temp_site.sh: the RCAC-Docs submodule fixture is not initialized at" >&2
    echo "  $fixture" >&2
    echo "Run: git submodule update --init tests/fixtures/RCAC-Docs" >&2
    exit 3
fi

sandbox=$(mktemp -d "${TMPDIR:-/tmp}/rcac-docs-temp-site.XXXXXX")
if [ -n "$keep" ]; then
    echo "temp_site.sh: keeping sandbox at $sandbox" >&2
else
    trap 'rm -rf "$sandbox"' EXIT INT TERM
fi

# Scrub every inherited RCAC_* variable. Without this, a developer with
# RCAC_DOCS_SITE exported gets a drive that reads their real site and a green
# verify that proves nothing. The sandbox's own variables are set below, after
# this runs. The interval form [A-Za-z0-9_]* avoids GNU-only sed extensions, which
# match nothing under BSD sed and would silently disable the whole scrub on macOS.
for name in $(env | sed -n 's/^\(RCAC_[A-Za-z0-9_]*\)=.*/\1/p'); do
    unset "$name"
done

# A copy, not a symlink: --update-site runs git against <site>/repo and --index
# writes index.db beside it, so the fixture must be writable and disposable.
if [ -z "$empty" ]; then
    mkdir -p "$sandbox/repo"
    cp -R "$fixture/." "$sandbox/repo/"
fi

RCAC_DOCS_SITE="$sandbox"
RCAC_DOCS_URL="file://$fixture"
RCAC_DOCS_SANDBOX="$sandbox"
export RCAC_DOCS_SITE RCAC_DOCS_URL RCAC_DOCS_SANDBOX

# `uv run` discovers the project by walking up from the working directory, so once
# cwd is the /tmp sandbox it can no longer find pyproject.toml. UV_PROJECT pins
# discovery back to the repo.
UV_PROJECT="$repo"
export UV_PROJECT

# Run inside the sandbox so a drive's relative write (`sh -c '… > out.txt'`) stays
# contained instead of leaking into the working tree, where proj-build's atomic
# `git add -A` would sweep it into the commit.
cd "$sandbox"

set +e
"$@"
rc=$?
set -e
exit "$rc"
