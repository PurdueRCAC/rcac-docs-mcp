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

*(No seeds yet. The factory landed 2026-08-27; the first deferrals will be
filed by the cycles that find them.)*

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
