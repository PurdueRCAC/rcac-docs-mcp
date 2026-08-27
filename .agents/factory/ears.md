# EARS — Easy Approach to Requirements Syntax

A lightweight controlled-natural-language convention for acceptance criteria that are **testable and
low-ambiguity**. Used by `proj-feature` to shape `GOAL.md` criteria (R-IDs).

**Nudge, do not hard-enforce.** EARS reduces ambiguity; it does not eliminate it, and forcing it onto
genuinely exploratory requirements stilts them. Prefer EARS where it clarifies; fall back to plain,
unambiguous prose where it would be contrived. Every criterion still gets a stable R-ID.

## Generic template

> **While** \<optional precondition/state>, **when** \<optional trigger>, the \<component> **shall**
> \<observable response>.

Keep `<component>` a real part of this project — `doc_search`, `doc_load`, the indexer, the query
normalizer, `resolve_db_path`, the container entrypoint — and keep `<response>` **observable**: an
exit status, an indexed-document count, a path present in the results, a line on stderr, the shape of
the string a tool returns. `proj-review` has to check it by running the suite or driving the server
under `.agents/factory/bin/temp_site.sh`, so a criterion it cannot observe is a criterion it cannot
grade.

## The six patterns

| Pattern | Keyword | Form |
|---|---|---|
| **Ubiquitous** | *(none)* | The \<component> shall \<response>. |
| **State-driven** | `While` | While \<state>, the \<component> shall \<response>. |
| **Event-driven** | `When` | When \<trigger>, the \<component> shall \<response>. |
| **Optional-feature** | `Where` | Where \<feature is included>, the \<component> shall \<response>. |
| **Unwanted-behavior** | `If … Then` | If \<unwanted condition>, then the \<component> shall \<response>. |
| **Complex** | combo | While \<state>, when \<trigger>, the \<component> shall \<response>. |

## Examples in this project's terms

- **R1 (event):** *When* `--index` runs against a site whose documents are unchanged, the indexer
  *shall* report `Indexed: 0 documents` and leave the existing index in place.
- **R2 (unwanted):** *If* a caller's query normalizes to a string FTS5 cannot parse, *then*
  `doc_search` *shall* return the engine's own error text plus a way forward, and *shall not* raise.
- **R3 (state):** *While* no index exists at `<site>/index.db`, `doc_search` *shall* return the
  build instructions rather than an empty result set.
- **R4 (ubiquitous):** The indexer *shall* publish a rebuilt index atomically, so a concurrent reader
  never observes a partial database.

## Anti-patterns

- Untestable adjectives — "fast", "robust", "safe". Replace with an observable threshold or a named
  post-condition.
- Several requirements on one line. Split so each has its own R-ID and its own pass/fail.
- Specifying the *how*. Implementation belongs in `PLAN.md`.
- Encoding a **suspected cause** in a *fix's* criterion ("the fix must not use the stale term
  splitter"). The root cause is unverified until `/proj-plan` diagnoses it; state the observable
  broken→fixed behavior instead.
- A criterion satisfied by a test that skips. "`pytest` passes" is met by a suite whose integration
  tests all skipped for want of the submodule. Name the assertion, not the exit status.
- A criterion that can only be observed against the live upstream RCAC-Docs repository or the
  deployed Geddes pod. If it genuinely cannot be reduced to a sandbox drive, say so explicitly in the
  criterion and in `PLAN.md`'s verification strategy, so the reviewer knows it is being taken on
  trust rather than silently assuming it was checked.
