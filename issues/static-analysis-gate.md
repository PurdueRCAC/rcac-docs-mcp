---
status: unshaped
kind: refactor
appetite: small
lane: public
---

# There is no linter, formatter, or type checker

## Problem

`pyproject.toml` configures no `[tool.ruff]`, no `[tool.mypy]`, no `[tool.black]`
and no pre-commit hooks; there is no config file for any of them anywhere in the
tree. The house style described in `AGENTS.md` — labelled import blocks in a
fixed order, `__all__`, double blank lines between module-level definitions,
SPDX headers, a leading newline in multi-line docstrings — is enforced entirely
by prose and by whoever is reading the diff.

`.agents/factory/bin/lint.sh` currently covers the mechanical subset that had
already drifted at least once: SPDX header uniformity, the `pyproject.toml`
version single-source, no feature-scoped spec ids in shipped source, the
`.claude`/`CLAUDE.md` symlinks, and `.dockerignore` completeness. It does not
check anything a real linter would — unused imports, shadowed names, undefined
locals, unreachable branches, or types.

## Why it was deferred

Deliberately excluded from the factory port. Running a formatter across the tree
produces a large mechanical diff that would have swamped the port's own diff and
made the first dogfood cycle unreadable, and choosing the rule set is a design
decision that deserves its own conversation rather than being smuggled in as
harness plumbing.

Pre-existing on `main`; nothing about it changed during the port.

## Outcome / vision

A static gate that catches the class of defect review is worst at — an unused
import, a name that only exists on one branch — without generating a first-run
diff nobody can read, and without fighting a house style that is deliberate.

This is a good candidate for the **first real feature cycle the factory runs on
itself**: it is small, self-contained, has a genuine design question in it, and
demonstrates the lifecycle on something more substantial than a documentation
fix.

## Sketch of the acceptance criteria

Draft R-IDs, to be firmed up at promotion. Prefer EARS phrasing (see
[`ears.md`](../.agents/factory/ears.md)).

- **R1** — The repository SHALL carry a linter configuration whose rule set is
  satisfied by the tree as it stands, so adopting it produces no reformatting
  commit.
- **R2** — `.agents/factory/bin/lint.sh` SHALL run it and fail on a finding.
- **R3** — WHERE a rule conflicts with the `AGENTS.md` house style, the rule
  SHALL be disabled with a comment naming the section it conflicts with, rather
  than the style being changed to suit the tool.

Open for the shaping conversation, and genuinely undecided:

- **Formatting or not.** A formatter is the highest-value and highest-churn
  option. `ruff format` would rewrite most of the tree and does not preserve the
  labelled-import-block convention or the double-blank-line spacing that
  `AGENTS.md` mandates. Linting without formatting (`ruff check`) is the
  low-churn half and probably where this should start.
- **Types.** `mypy` on ten modules is tractable, but the FastMCP decorator turns
  functions into `FunctionTool` objects, which is exactly the sort of thing that
  produces a wall of false positives and a `# type: ignore` habit. Worth
  measuring before committing.
- **Whether R2 is right at all.** Putting the linter inside `lint.sh` couples
  the factory's integrity gate to a code-style tool. The alternative is a
  separate CI job, leaving `lint.sh` about repository shape.

## Notes

- Related: `.agents/factory/bin/lint.sh` is the interim gate; `AGENTS.md`
  § *Code conventions* and § *Prose and comments* are the rules currently
  enforced by reading.
- Found by: the factory port, as an explicit scope exclusion.
