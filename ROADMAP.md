# Roadmap

The ordered index of **deferred code work**. One entry per `issues/{slug}.md`
seed, each pointing at the file that holds the evidence. This is an index of
*work*, not a design document and not a progress tracker — the `spec/{slug}/`
records are the account of what was actually done.

Entries are deliberately **unnumbered**. An ordinal reference survives a
retirement still grammatical and now pointing at the wrong cycle; order is the
order they appear in.

**A seed is a candidate, not a contract.** `/proj-feature` promotes one into a
`GOAL.md`, and that promotion is where appetite, non-goals and the R-IDs get
negotiated. When the adopting cycle lands on `main`, `/proj-roadmap` deletes
the seed and its entry here: `spec/{slug}/` is the retained account and git
history holds the file.

Unremediated **security** findings do not appear here. They live in
`.security/ROADMAP.md` and `.security/issues/`, which are gitignored — see the
deferral table in [`AGENTS.md`](AGENTS.md).

---

## Queued

### `INSTRUCTIONS.md` ships to nobody, and the constitution says it ships to everybody.
*`kind: refactor` · `appetite: small` · filed 2026-09-03 by the wildcard-drift cycle*
Delete `INSTRUCTIONS.md`; `SERVER_INSTRUCTIONS` in `server.py` stands as the
only editable source, with the constitution, the contract test, and the
mechanical references following the deletion. No prompt rewrite, no
`importlib.resources` path.
**Seed:** [`issues/instructions-md-is-a-runtime-no-op.md`](issues/instructions-md-is-a-runtime-no-op.md) · **adopted** as
[`spec/instructions-md-is-a-runtime-no-op/`](spec/instructions-md-is-a-runtime-no-op/GOAL.md)

### `--site` is honored when indexing and silently ignored when serving.
*`kind: fix` · `appetite: small` · filed 2026-08-27 by the factory port*
Reproduced. Production is unaffected, because the container relies on
`RCAC_DOCS_SITE`, which both halves honor.
**Seed:** [`issues/site-flag-ignored-when-serving.md`](issues/site-flag-ignored-when-serving.md)

### There is no linter, formatter, or type checker.
*`kind: refactor` · `appetite: small` · filed 2026-08-27 by the factory port*
Deliberately excluded from the port so its reformatting diff would not swamp
the port's own. A good first substantial cycle.
**Seed:** [`issues/static-analysis-gate.md`](issues/static-analysis-gate.md)

<!--
Entry format:

### One sentence saying what is wrong, in the imperative or as a symptom.
*`kind: fix` · `appetite: small` · filed 2026-08-27 by `{slug}` P2*
**Seed:** [`issues/{slug}.md`](issues/{slug}.md)
-->

## Terminal records

Deferrals that were closed **without shipping** — `declined`, or
`accepted-behaviour`. They keep their files, because nothing else in the
repository records that the question was ever asked. A deferral that *shipped*
is deleted instead: the code refutes a re-filing on its own.

*(None yet.)*
