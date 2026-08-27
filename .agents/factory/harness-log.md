# Harness change log (`proj-harness`)

The cross-job ledger of every harness self-improvement **decision** — the *act* side of the factory's
self-improvement loop. `/proj-harness` appends one entry per **applied** and **rejected** decision (and
notable **deferred** ones), and **reads this file before applying**: a proposed fix that reverts a
recent change, or repeats a previously-rejected one, is flagged to the human rather than silently
re-applied. This is the loop's anti-thrash memory.

Findings themselves live in each feature's `spec/{slug}/META.md`; this file is the durable record of
what was *done* about them.

Entry format — one section per decision, newest at the bottom:

```markdown
## {YYYY-MM-DD} — {slug} {F#}: {one-line title}
`decision=applied|rejected|deferred commit={sha|—} target={file}`
- **Rationale:** what was changed and why it generalizes / why rejected (overfit, stale,
  would-weaken-a-gate) / why deferred.
```

Read `origin`, `severity` and `category` from the finding in `META.md`; this ledger records the
*outcome*.

---

<!-- Decisions are appended below this line by /proj-harness. -->

## 2026-08-27 — bootstrap: factory ported from uv-manager and HyperShell
`decision=applied commit=— target=.agents/`
- **Rationale:** initial import. uv-manager is the second-generation factory and is the source for
  almost everything: the FSM scripts, `run_verify.py`, `lint.sh`'s tri-state exit and
  skill-injection check, the five-step refutation protocol, the four blind-review leak closures, the
  flat `ROADMAP.md`, the "§12 is HIGH, not CRITICAL" clause, and the *Prose and comments* directive,
  which HyperShell lacks entirely. Taken from HyperShell instead: no `Co-Authored-By` trailer, the
  richer `ISSUE.md` (uv-manager dropped `kind: docs`, which this project needs — five files state the
  same contract, so a behavior change routinely strands one), and the `UV_PROJECT` pin plus `cd` in
  the sandbox, which uv-manager has no use for because it has no `pyproject.toml`.
- **Adapted, not copied:** skills are `proj-*` rather than a per-project prefix, so the naming holds
  across future ports. `base` is `main` and there is no develop-equivalent, which means a merge is a
  deploy — `proj-publish` ships and `proj-release` only cuts a version. `temp_root.sh` became
  `temp_site.sh` over the `RCAC_DOCS_SITE` model. `lint.sh`'s shellcheck and `bash -n` groups were
  replaced by Python equivalents; `invariants.md` was written from scratch.
- **Three hardenings uv-manager does not have**, each fixing a real defect: `set_phase.py` writes
  `TECH.md` atomically through `os.replace`; `_fsm.validate()` detects dependency cycles, which
  previously reported `all_done: true` on an unbuildable FSM; `next_phase.py --all` resolves `spec/`
  from the git root and errors on a missing directory instead of printing the same empty list an
  empty backlog produces. `--verdict none` also no longer counts as a completed review pass.

## 2026-08-27 — bootstrap: every lint.sh check observed failing before being trusted
`decision=applied commit=20b4d40 target=.agents/factory/bin/lint.sh`
- **Rationale:** the factory requires a `verify:` gate to be seen red before green, and uv-manager
  extends that to the offline fixture's assertions, but neither applies it to `lint.sh`'s own checks —
  editing `lint.sh` there requires only that it still pass on a clean tree, which a check that can
  never fail satisfies perfectly. Running all nine against a deliberately broken tree found two that
  could not fire: the convention census walked `git ls-files`, which lists only tracked files, so a
  source file created and not yet staged was invisible to it; and the spec-id pattern used `\b`, a
  GNU extension git's POSIX `-E` engine matches nothing with, so it reported clean against a file
  containing `R1`. Both fixed and re-observed failing. The general finding was written up as a
  portable seed and filed into uv-manager and HyperShell.
