# The rcac-docs-mcp software factory — methodology

The reference an agent reads when it needs to understand the spec-driven lifecycle the `proj-*` skills
implement. The skills themselves are thin; this is the *why*. When something here disagrees with a
skill, **the skill body is the operating procedure** — fix this file.

## Why a factory for a small, finished server

The obvious objection is that ten source files and two tools do not need a five-stage lifecycle, and
for a one-line change they do not — ceremony scales to appetite, and that is a rule, not an apology.

The factory earns its place for a different reason. This server is **deployed, unauthenticated, and
consumed by other agents**. Its failure modes are quiet: a malformed FTS5 query returns an error an
agent cannot act on and burns a whole research round; a torn index served mid-reindex breaks live
readers; a stale sentence in `INSTRUCTIONS.md` is a system prompt handed to every downstream client
on every call. None of that produces a stack trace anyone will see. The suite is real coverage — 107
tests — but it does not check that the five places stating the tool contract still agree with each
other, and it passes cleanly with its integration tests skipped.

`spec/{slug}/` is the record of what was intended, what was rejected, and what was actually run, for
a change nobody can re-derive from a forty-character diff six months later.

## The lifecycle

One feature (or fix/refactor/docs cycle) flows through five lifecycle skills, on its own branch, with
every artifact committed under `spec/{slug}/`:

```
main ──/proj-feature──▶ feature|fix/{slug}    GOAL.md            (shape: what & why, locked)
          │
          ├──────────/proj-plan──────────▶    research/ PLAN.md TECH.md   (design + phased FSM)
          │
          ├──────────/proj-build─────────▶    src/ + docs                 (execute one phase)
          │            ▲        │
          │            └────────┘  (loop until TECH.md is done)
          │
          ├──────────/proj-review────────▶    REVIEW.md          (adversarial QA, clean context)
          │            │
          │      changes-requested ──▶ back to /proj-build ;  approved ──▶
          │
          └──────────/proj-publish───────▶    squash PR → main
```

The artifact spine — **`GOAL.md → PLAN.md → TECH.md`** — is the standard spec-driven skeleton (Spec
Kit's `spec→plan→tasks`, Kiro's `requirements→design→tasks`). These are committed as an immutable,
dated design record, not as a living source of truth that must be maintained forever. **The code and
`AGENTS.md` remain ground truth; `spec/{slug}/` is a point-in-time record of intent.**

**A merge to `main` is a deploy.** Pushing to `main` fires `build-and-push.yml`, moves
`ghcr.io/purduercac/rcac-docs-mcp:latest`, and the Geddes poller rolls the pod. `proj-publish` is
therefore the moment the change reaches users, and `proj-release` only cuts a version — it does not
ship. Confirm the live endpoint, not the CI run: the poller has taken over 26 minutes to reconcile.

Three operational skills sit outside the lifecycle. **`/proj-harness`** applies the factory's own
self-improvement findings back to `.agents/`. **`/proj-roadmap`** retires the seeds whose cycles have
landed and repairs the drift that leaves in `ROADMAP.md`. **`/proj-release`** bumps the version and
cuts a tagged release. None touches `spec/`, the FSM, or product requirements.

## Load-bearing principles

1. **`AGENTS.md` is the constitution.** There is no separate `constitution.md`; the skills reference
   `AGENTS.md` and the curated [`invariants.md`](invariants.md). The `proj-plan` invariant gate and the
   `proj-review` footgun checklist both draw from it.
2. **Files and git are the durable substrate.** State lives only in the committed `TECH.md`
   frontmatter, re-read fresh each invocation. Never rely on conversation memory to carry lifecycle
   state — `proj-review` runs in a separate context and `proj-build` may run days later.
3. **Parallelism for research, never for building.** `proj-plan` fans out read-only research subagents.
   `proj-build` is strictly single-threaded and linear.
4. **Blind, externally-verified review beats self-review.** The reviewer is denied the author's
   PLAN/TECH rationale and must cite executed commands. Enforced by spawning a fresh subagent, not by
   trusting a human to `/clear`.
5. **Ceremony scales to appetite.** The dominant failure of spec-driven tooling is uniform heavyweight
   process — sixteen acceptance criteria for a one-line fix. `appetite: small` (the default for
   `fix/`) skips the research fan-out and may collapse PLAN and TECH; a one-sentence change skips the
   lifecycle entirely.
6. **Never guess.** Ambiguity gets a `[NEEDS CLARIFICATION: …]` marker and a question to the human,
   recorded into `GOAL.md`.
7. **Observe cheaply, act deliberately.** The factory improves *itself* through an asymmetric loop:
   every lifecycle skill records harness friction into `spec/{slug}/META.md` at near-zero cost (silence
   by default), but fixes are applied only by the human-gated `proj-harness`, with fresh eyes and
   guardrails that forbid quietly weakening a gate.

## What we take from Shape Up, and what we drop

Shape Up (Singer, 2019) is a team methodology; we take its cognitive tools and drop its org rituals.

**Adopt:**

- **Appetite** — fixed budget, variable scope. Expressed as a phase cap, since calendar weeks are
  meaningless at machine tempo.
- **Shaping** — `GOAL.md` is rough, solved, and bounded: concrete enough to de-risk, abstract enough to
  leave design freedom.
- **No-gos** — explicit exclusions in `GOAL.md`. Especially valuable here, where the docs-only refactor
  deliberately removed auth, `sse`, and all cluster operations, and the standing bias is to delete.
- **Rabbit holes** — each `research/{topic}.md` investigates one unknown that could blow the appetite.
- **Hill state** — `hill: uphill|crest|downhill` per phase encodes risk and confidence. A phase stuck
  uphill across builds is a raised hand.
- **Scope hammering** — nice-to-haves are cuttable; `proj-review` scope-checks against the appetite.
- **Circuit breaker** — cap build iterations and review bounce-backs; on trip, stop and re-shape.

**Discard:** the betting table, the six-week cadence, cool-down, two-track pipelining, dedicated QA
roles. All exist to synchronize and shield a human team, and dissolve for a serial solo-plus-agent
pipeline.

**Quality is not negotiable for the data path.** Shape Up assumes scope is cuttable and most bugs can
wait. That is false for index integrity and the tool contract. An index published non-atomically
breaks live readers on a shared PVC; a normalizer that emits invalid FTS5 fails the exact
natural-language queries the tool exists to serve; a renamed tool silently breaks every downstream
agent holding `INSTRUCTIONS.md` as a system prompt. The `hammerable: false` phase flag operationalizes
this: `proj-review` must never scope-hammer a correctness phase to fit the appetite.

## Where things live

```
.agents/
  skills/proj-{feature,plan,build,review,publish}/SKILL.md   # the five lifecycle skills
  skills/proj-harness/SKILL.md                               # meta/maintenance: apply the loop
  skills/proj-roadmap/SKILL.md                               # operational: retire landed seeds
  skills/proj-release/SKILL.md                               # operational: cut a tagged version
  factory/
    methodology.md        # this file
    invariants.md         # curated AGENTS.md footgun checklist (plan gate + review rubric)
    ears.md               # EARS requirement templates
    review-rubric.md      # severity scale, refutation protocol, human-gate triggers
    portability.md        # non-Claude / smaller-model harness compatibility contract
    templates/            # GOAL PLAN TECH REVIEW META ISSUE skeletons
    bin/                  # next_phase.py, set_phase.py, _fsm.py (FSM); run_verify.py;
                          # meta_status.py; temp_site.sh (sandbox), lint.sh (static gate)
    harness-log.md        # proj-harness decision ledger (cross-job anti-thrash memory)
spec/{slug}/              # per-feature artifacts incl. META.md (committed, retained on merge)
issues/{slug}.md          # deferred code work, pre-shaped — /proj-feature promotes one into a GOAL
ROADMAP.md                # the ordered index; each entry's **Seed:** points at an issues/ file
.security/                # the same two, for unremediated findings — gitignored, never published
AGENTS.md                 # the constitution (CLAUDE.md is a symlink to it)
```

**Where a deferral goes.** Work a pass decides *not* to do is not an artifact of that feature, so it
does not live in `spec/{slug}/`. It becomes an `issues/{slug}.md` — pre-shaped from
[`templates/ISSUE.md`](templates/ISSUE.md) — plus an ordered `ROADMAP.md` entry pointing at it.
`META.md` is **never** the destination: that file is harness feedback, and the boundary is stated once
in `AGENTS.md`. The `status:` field keeps a deferral a candidate: `/proj-feature` promotes it into a
real `GOAL.md`, and that promotion is where a human negotiates appetite, non-goals and R-IDs. When the
cycle lands, `/proj-roadmap` retires the seed and its index entry, so the backlog stops advertising work
that is already on `main`.

Security-sensitive deferrals take the hidden lane: `.security/issues/` plus `.security/ROADMAP.md`,
same convention, gitignored. A public roadmap of unremediated weaknesses is an attacker's work plan,
and this service is unauthenticated and on the public internet; fixes are public when they ship, the
standing inventory is not.

`.claude` is a symlink to `.agents`, so Claude Code discovers the skills and settings through it. The
skills reference bundled scripts and shared reference material by **repo-relative path**
(`.agents/factory/…`), which keeps them portable across harnesses — see
[`portability.md`](portability.md).

## Verification: three layers

Every `verify:` command should use at least one, and the layers are ordered by how much they prove:

- **Static.** `.agents/factory/bin/lint.sh` — importability, pytest collection, SPDX uniformity, the
  version single-source, no feature-scoped spec ids in shipped source, the `.claude`/`CLAUDE.md`
  symlinks, `.dockerignore` completeness, and that every skill's `` !`cmd` `` state injection exits 0.
- **The suite.** `uv run pytest -q` — 107 tests. **Necessary, not sufficient.** With the RCAC-Docs
  submodule uninitialized 31 of the 107 tests skip and the suite still exits 0. A gate
  that only reads the exit status cannot tell a green run from a skipped one, so assert the counts or
  use the layer below.
- **Behavioral, sandboxed.** `.agents/factory/bin/temp_site.sh` builds a throwaway site from the
  pinned submodule fixture, scrubs every inherited `RCAC_*` variable, points `RCAC_DOCS_URL` at a
  `file://` copy so `--update-site` never reaches the network, and runs from inside the sandbox so a
  relative write cannot leak into the working tree. It **exits 3** when the fixture is absent, rather
  than reporting a pass it cannot support.

A `verify:` command that only asserts exit 0 is not a gate. Assert the post-condition: a document
count, a path in the search results, a specific line on stderr, the second run reporting zero
reindexed.

## The self-improvement loop (META.md + `proj-harness`)

The five lifecycle skills improve the *product*; this loop improves the *factory*. Skill friction is
otherwise invisible and forgotten between sessions, so each lifecycle skill ends with a
silence-by-default meta-note step that appends a finding to `spec/{slug}/META.md` **only** when the
skillset itself cost something. The single gate is one test: *was this the skill's fault — not mine,
not the task's?* A merely hard task, a self-inflicted error, or a one-off code issue that belongs in
`GOAL.md` or `REVIEW.md` is not a finding.

```
proj-feature ─┐
proj-plan     ├─ meta-note (silence by default) ─► spec/{slug}/META.md
proj-build    │                                          │  (kept OUT of the blind reviewer's context)
proj-review  ─┘  (orchestrator only)                     │
                                                         ▼
proj-publish ──► reads open findings (meta_status.py) ─► "Harness feedback" block in the PR
                                                         ▼
proj-harness ──► human-gated: shape → preview → apply to .agents/ ─► flip status + log harness-log.md
```

The design is deliberately asymmetric — cheap to observe, deliberate to act — so it cannot become a
token sink or quietly loosen its own guardrails:

- **Producers** (`proj-feature`/`proj-plan`/`proj-build`/`proj-review`) only record, never fix, at most
  three terse findings each. `proj-build` is the richest source, because it runs per phase across
  separate invocations and appending to a file preserves signal a context reset erases.
  `proj-review`'s finding is written by the *orchestrator*, never by the blind reviewer, which must not
  read `META.md` at all — it leaks author intent.
- **The applier is separated from the observer.** `proj-harness` is human-gated always and bound by
  hard guardrails: it never auto-weakens a non-negotiable gate without an explicit typed override — *a
  finding arguing to loosen a guardrail is itself a warning sign* — prefers an example over a new hard
  rule, keeps per-finding atomic revertable commits with post-apply verification, writes no `META.md`
  findings (no recursion), and reads [`harness-log.md`](harness-log.md) first so a fix that reverts a
  recent change or repeats a rejected one is flagged rather than silently re-applied.

**Observe earns act.** The cheap half should prove it produces real signal over the first few features
before the applier is leaned on hard. A finding that recurs across features (via `proj-harness --all`
and the ledger) escalates itself. As with the FSM, the fragile parsing is owned by a script —
`meta_status.py` — not the model.

## Traceability chain

`GOAL.md` R-IDs → `PLAN.md` requirement→design map → `TECH.md` phase `satisfies:` → commits →
`REVIEW.md` requirement→evidence matrix → PR body. Because merges are squashed, the committed
`spec/{slug}/` folder *is* the retained trace.

Provenance lives in that chain, **not in source comments**. Comments explain the invariant or the
*why* on their own terms and never embed R-IDs or phase ids: those restart per feature, collide across
branches, and mean nothing to a later reader of `tools.py`. `git blame → commit → PR → spec/{slug}/`
recovers the requirement behind any line when you need it. `lint.sh` enforces the ban.
