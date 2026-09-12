# Phase 7: Promotion & Rollback - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-11
**Phase:** 07-promotion-rollback
**Areas discussed:** Promotion target identity, Verb surface & posture refusal, Owner corpus into the bundle, Doc hardening vs verbatim mirror

---

## Promotion target identity

### What does the operator hand promote() to identify the wiring?

| Option | Description | Selected |
|--------|-------------|----------|
| Derive from the trace ids (Recommended) | Each mandatory trace id resolves via TraceStore to a run naming its wiring; all must agree or refuse by name. Keeps Phase 4 D-11. | ✓ |
| Explicit arm name (operator privilege) | Operator surface accepts the arm name directly; crosses REST/MCP as input, which D-11 forbids. | |
| A selector that must resolve to one wiring | Capability/harness selector; fragile under the smallest-wiring tie-break. | |

**User's choice:** Derive from the trace ids

### How does rollback name the generation it returns to?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit semver, no default (Recommended) | Operator names the semver minted at the target generation; parent set to it; own trace ids. | ✓ |
| Implicit previous generation | rollback(alias) returns to the prior pointer; ambiguous after repeated moves. | |
| Explicit semver, omit means previous | Both behaviours. | |

**User's choice:** Explicit semver, no default

### Who decides the semver bump level?

| Option | Description | Selected |
|--------|-------------|----------|
| Machine derives it (Recommended) | MAJOR on capability/effects surface change vs prior generation, else MINOR; PATCH never on the operator path; first promotion 1.0.0. | ✓ |
| Operator declares the bump | Required argument, recorded as declared. | |
| Operator declares, machine checks | Required argument, refused when inconsistent with the derived surface diff. | |

**User's choice:** Machine derives it

### How does a generation become tombstoned?

| Option | Description | Selected |
|--------|-------------|----------|
| Operator retire verb (Recommended) | Tombstone record appended on the same path; promote/rollback refuse tombstoned targets; §16.2 pin refusal stands. | ✓ |
| No operator tombstone in v1 | Only the artifact-registry tier checked; never-lifted proven against a test-seeded row. | |

**User's choice:** Operator retire verb

---

## Verb surface & posture refusal

### How do promote-next and promote-now exist so they can refuse by name (SC3)?

| Option | Description | Selected |
|--------|-------------|----------|
| One promote entry with a verb argument (Recommended) | Closed verb enum; operator path appends; promote-next/now refuse naming the posture (answer-level, index-side) or the missing floor (retrieval-side); check/preview/run refuse as not built. | ✓ |
| Separate entries | promote_next()/promote_now() as their own always-refusing entries across three transports. | |

**User's choice:** One promote entry with a verb argument

### Who states the mutation class?

| Option | Description | Selected |
|--------|-------------|----------|
| Machine derives, caller may not state it (Recommended) | Derived from the delta vs prior generation: index-recipe node → index-side; generate/keywords/prompt node → answer-level; else retrieval-side. | ✓ |
| Caller declares, required, never defaulted | Recorded as declared; could dodge the posture refusal. | |
| Caller declares, machine checks | Required, refused on disagreement with the derived class. | |

**User's choice:** Machine derives, caller may not state it

### How should the call treat change_origin with no proposer in this milestone?

| Option | Description | Selected |
|--------|-------------|----------|
| Required input, both values accepted (Recommended) | Absent → refuse; machine_mutation accepted since §7 makes the field orthogonal and frozen. | ✓ |
| Required input, machine_mutation refused until a proposer exists | Adds a proposer-existence check nothing can satisfy yet. | |

**User's choice:** Required input, both values accepted

### Where does the measurement posture live?

| Option | Description | Selected |
|--------|-------------|----------|
| Module constant, refusal quotes it (Recommended) | Frozen class → on/off mapping; flip is a source edit and makes MACH-03 due. | ✓ |
| Constructor argument on Databasise | Runtime-constructible posture could reach the floor-less gate path. | |

**User's choice:** Module constant, refusal quotes it

---

## Owner corpus into the bundle

### Which documents are "the owner's own corpus" for HARD-04?

| Option | Description | Selected |
|--------|-------------|----------|
| The documents v1/Sourcerer already indexes | The real working corpus; largest, least curated. | |
| A purpose-built subset the owner curates | Tens of documents chosen for eval. | ✓ (via free text) |

**User's choice:** Free text: "what is hard-04" — HARD-04 explained in plain terms (origin rule, bundle@v1 is public-only, mint_bundle needs gold document ids) — then "smaller subset I pick later to test on".

### What crosses into git?

| Option | Description | Selected |
|--------|-------------|----------|
| Hashes and evidence only (Recommended) | Documents, questions, gold answers stay local-only; git gets bundle hash, snapshot hash, evidence record. | ✓ |
| Questions and gold answers committed, documents not | Bundle JSON committed like bundle@v1. | |
| Everything committed | Redacted subset in the fixture tree. | |

**User's choice:** Hashes and evidence only

### Authoring and binding (interrupted)

Questions on who authors the question set and whether promote() refuses without bundle coverage
were presented and interrupted. **Owner directive:** "Unless this testing is required I wanted to
defer it until the product is built and I do in-depth testing for an entirely different phase."
**Resolution:** not required — the operator-asserted path reads no bundle (CONTRACT §6, RIG §PR.3),
the same argument as 06-GATE-AMENDMENT's MACH-03 deferral. HARD-04 deferred to that later phase;
no coverage check, no authoring tool in Phase 7; deferral to be recorded in a written amendment.

---

## Doc hardening vs verbatim mirror

### Keep HARD-01/HARD-02 in Phase 7 or defer?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to the later hardening phase | Phase 7 becomes MACH-07 + API-09; HARD-01/02/04 move together with one amendment. | ✓ |
| Keep both in Phase 7 | Land now; then decide where edits go given the never-edited mirror. | |
| Keep HARD-01 only | Fix the scripts now, defer the doc reconciliation. | |

**User's choice:** Defer to the later hardening phase
**Notes:** The where-edits-land question (upstream re-mirror vs in-place with recorded divergence vs project-layer copies) was not reached and travels with the deferral.

---

## Claude's Discretion

- Ledger schema additions (change_origin, semver, record kind) as additive columns; atomicity via the single INSERT; async offload at the call site.
- Entry-point names, refusal types, REST paths, MCP tool names, response shape under §18.2's closed set.
- Trace → wiring resolution mechanism; class-derivation node-kind rules; alias lifecycle details.
- Amendment record shape and file name; test scope limited to what the decisions need.

## Deferred Ideas

- HARD-04, HARD-01, HARD-02 → the owner's later in-depth testing / hardening phase (to be added to the roadmap).
- Gate-adjudicated promotion path, batch promotion (§PR.4), MUTPROP, alias retirement, bundle-coverage note on the generation record.
