# Baseline — served text and pre-change census

Recorded 2026-09-03 on `main` (shape commit `b56a2d5` adds only
`spec/`, `issues/`, `ROADMAP.md`). The served instructions text must be
identical after the build; this file is the fingerprint to compare against.

## Served text

- Source: `SERVER_INSTRUCTIONS` in `src/rcac_docs_mcp/server.py:62-90`,
  passed as `instructions=` at `create_mcp_server()` (`server.py:102`).
- sha256: `fd2dd5cd6d79a57ab2f77ee03677c081b731e8d8fda7b7fd14e04bf1a96dd575`
- Length: 1566 chars.
- Nothing outside `server.py` feeds the `initialize` response: `src/` holds no
  other `INSTRUCTIONS` reference, and `Dockerfile`, `docker-entrypoint.sh`,
  `.github/`, `pyproject.toml`, and `uv.lock` hold none either.

## Pre-change census

Tracked files naming `INSTRUCTIONS.md` (from `git grep -l`):

- Live contract (change): `INSTRUCTIONS.md` itself,
  `tests/test_docs_contract.py`, `AGENTS.md`,
  `.agents/factory/invariants.md`, `.dockerignore`,
  `.agents/factory/bin/lint.sh` (pathspec at lines 117-118).
- Seed and index (adopt, do not edit the seed's evidence):
  `issues/instructions-md-is-a-runtime-no-op.md`, `ROADMAP.md`.
- Retained history (do not touch): `spec/docs-only-refactor/STAGES.md`.
- Wider factory prose (out of scope per GOAL non-goals): `methodology.md`,
  `review-rubric.md`, skill `SKILL.md` files, factory templates.

## Gate baselines (pre-change, all green)

- `uv run pytest -q tests/test_docs_contract.py` → 3 passed.
- `.agents/factory/bin/lint.sh` → all checks passed.
- The phase gates in `TECH.md` are red against this tree: P1 dies on
  `INSTRUCTIONS.md` still tracked, P2 dies on the constitution references.
