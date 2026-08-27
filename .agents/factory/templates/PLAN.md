# PLAN — {Title}

> **Status:** Draft for review · **Last updated:** {YYYY-MM-DD}
> **Authoritative technical design.** The *how*. The contract is [`GOAL.md`](GOAL.md); the phased
> executable roadmap is [`TECH.md`](TECH.md). Backing detail is in [`research/`](research/) when
> `appetite: big`. Every design element traces to a GOAL R-ID.

## 1. Summary

<Two to four sentences: the approach in a nutshell and why it fits the appetite.>

## 2. Design

<The technical design at the right altitude. For this project that means: which modules under
`src/rcac_docs_mcp/` change and how, what the index schema and the site layout look like afterwards,
which environment variables and CLI flags are read, what the failure paths return to the caller
(a tool returns a string — it does not raise at an agent), and what the user-facing surface has to
say. Be specific enough to build from, not so specific it duplicates the diff.

Name the five places that state the same contract and say which this change touches: `README.md`,
`INSTRUCTIONS.md`, `AGENTS.md`, `APP_HELP` in `__init__.py`, and `SERVER_INSTRUCTIONS` in
`server.py`. Drift between them is what ships to every downstream agent.

State explicitly what is being *removed*. A change that only adds is worth a second look.>

### Requirement → design map

| R-ID | Design element(s) that satisfy it |
|------|-----------------------------------|
| R1   | <module / function / behavior / documented text> |
| R2   | <…> |

## 3. Invariant gate (AGENTS.md constitution check)

Checked against [`invariants.md`](../../.agents/factory/invariants.md) **before** research and
**again** after this design was drafted. List every load-bearing invariant this change touches and
confirm compliance.

- <§n invariant> — <how this design honors it>.

### Deviation justifications

Any place this design bends an invariant or adds complexity, with the simpler alternative and why it
was rejected. Empty is the goal.

| Deviation | Why needed | Simpler alternative rejected because |
|-----------|-----------|--------------------------------------|
| —         | —         | — |

## 4. Rabbit holes (resolved)

Unknowns that could have blown the appetite, and how research settled them. Link the relevant
`research/NN-*.md`. This is where risk was bought down before committing to phases.

Typical shapes here: an FTS5 or SQLite semantic that has to be verified rather than assumed
(tokenizer behavior, Porter stemming, operator parsing, `snippet()`, external-content triggers,
what `VACUUM INTO` actually guarantees); an upstream RCAC-Docs pipeline detail (pymdownx `--8<--`
snippets, the docs repo's `main.py` macros, `mkdocs.yml` `extra:` and its `!ENV` tag) where the
fixture is a *pinned* submodule and upstream can drift; a FastMCP surface question; or container
behavior only observable in the deployed pod.

- <unknown> → <resolution> ([`research/NN-topic.md`](research/NN-topic.md)).

## 5. Risks & open questions

- <residual risk, its mitigation, or a question that needs a human before or during build>.
- <anything only observable in the deployed pod — the shared PVC, the `:latest` digest poller,
  cold-start index time — named explicitly so it is not mistaken for something the review covered>.

## 6. Verification strategy

How we will *prove* this works. This seeds each phase's `verify:` command in `TECH.md`.

Start from the three layers in [`methodology.md`](../../.agents/factory/methodology.md):
`uv run pytest -q`, `.agents/factory/bin/lint.sh`, and a sandbox drive under
`.agents/factory/bin/temp_site.sh`. For each R-ID, name the **post-condition** the drive asserts —
not just the command. A `verify:` that only checks exit 0 is not a gate.

`pytest -q` exiting 0 is the weakest of the three: with the RCAC-Docs submodule uninitialized the
integration tests skip and the suite still passes. A gate over indexer, tool, or CLI behavior runs
through `temp_site.sh`, which exits 3 rather than reporting a pass it cannot support.

---

*Backing research (if present): [`research/00-digest.md`](research/00-digest.md).*
