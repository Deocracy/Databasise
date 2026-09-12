# API Coverage — Phase 7: Promotion & Rollback

This phase carries its own §18.5 operations-table record rather than only amending Phase 5's
(`.planning/phases/05-opaque-side-admission/COVERAGE.md`), following the precedent Phase 6 set:
the phase that actually lands a new operation is the phase whose own coverage record states it
landed there.

**Which file is canonical.** `databasise/tests/mcp/test_tool_growth_invariant.py` parses Phase 5's
COVERAGE.md and cross-checks its §18.5 table against `TOOL_NAMES` in code. 07-03 amended that file
with the three rows below and moved `promote`/`rollback`/`retire` out of its deliberately-absent
table as `DISCHARGED`. Phase 5's file therefore remains the test-coupled record; this one is the
provenance record for the phase that landed them. The two must state the same thing — if they ever
diverge, Phase 5's is the one the test enforces and this one is the one that is wrong.

**No external API integration** — this phase consumes no third-party API. It adds three operator
verbs over the machine's own append-only ledger and exposes them across the existing §18 seam. The
one external API this system integrates — the OpenAI-compatible model endpoint — is Phase 3's and
is untouched here; `.planning/phases/03-lightrag-query-side/COVERAGE.md` stays authoritative for it.
No provider row is restated and none is fabricated.

## The §18.5 surface record

CONTRACT §18.5: *"The tool surface MAY grow per part and MUST NOT grow per modality."* This phase
adds exactly three new operations — the MACH-07/API-09 operator path — each reachable the same way
in-process, over REST and over MCP. `TOOL_NAMES` grows from six entries to nine
(`databasise/mcp/tools.py`), and the growth is **per part, not per modality**: the same three verbs
serve every fitted modality, and no modality-named tool was added.

| operation | transports | plan | why an operation and not a selector |
|---|---|---|---|
| promote | in-process, REST (`POST /promote`), MCP (`promote` tool) | 07-01, 07-03 | MACH-07/API-09's operator-asserted promotion. A §18.4 selector picks which fitted modality answers a query; `promote` writes one generation record to the append-only ledger and repoints an alias, which no selector value can express. Its own operation under Phase 4 D-03's one-entry-per-operation rule and §19.6's precedent that a differently-effecting mutation is its own port. |
| rollback | in-process, REST (`POST /rollback`), MCP (`rollback` tool) | 07-02, 07-03 | RIG §PR.2's rollback path. Writes a new generation record naming an **explicit** prior semver target — no default "previous" (D-05) — and repoints the alias to it. Not a selector value; not a parameter on `promote`, because the effect differs. |
| retire | in-process, REST (`POST /retire`), MCP (`retire` tool) | 07-02, 07-03 | D-07's tombstone verb. Writes a tombstone record for a named generation on the same append-only path, guarded against retiring the active generation and against double-tombstoning. A third effect, so a third operation. |

Every other operation (`query`, `compare`, `ingest`, `delete`, `status`, `resolve`) is unchanged by
this phase. No route body carries logic: the three REST routes
(`databasise/seam/rest.py`) and the three MCP tools are thin passes over the identical
`Databasise.promote()` / `.rollback()` / `.retire()` methods, and 07-03 proves field-for-field
parity across all three transports on success **and** on refusal.

### The refusal ladder is part of the surface

Ten named `SeamRefusalError` subclasses cover the operator path (`databasise/seam/refusals.py`):
`EmptyPromotionTraceIdsError`, `DisagreeingPromotionTraceIdsError`, `InvalidChangeOriginError`,
`UnrecognisedPromotionVerbError`, `GateVerbNotBuiltError`, `MeasurementPostureRefusalError`,
`UncalibratedFloorRefusalError`, `UnknownGenerationVersionError`, `TombstonedGenerationError`,
`ActiveGenerationRetirementError`.

These are surface, not implementation detail: a refusal is what a caller observes, so each one
surfaces under the **identical name** in-process, over REST (422) and over MCP (`ToolError`). A
refusal that named a modality, an arm id or a wiring name would breach §18.3 as surely as a
modality-named tool would.

### Operations still deliberately absent

| operation | decision | reason |
|---|---|---|
| comparison-rig operations | OPT-OUT | Unchanged from Phase 4/5/6. The rig is a peer client of this seam (§18.3), not an operation on it — it reaches the machine through the same surface every other consumer does. |
| `delete` for non-LightRAG modalities | OPT-OUT | Unchanged from Phase 6's write-surface record: only LightRAG ships a `corpus-delete.json`, and any other fitted modality raises `NoWritePathForModalityError` **by name** rather than writing into LightRAG's index. Not this phase's scope; tracked for whichever phase builds the retracting node. |
| a per-modality tool of any kind | FORBIDDEN | §18.5. A consumer calling a modality-named tool has, by construction, named the modality, which §18.3's invariance rule forbids. Not an opt-out a later phase may revisit — a contract prohibition, recorded so the growth rule is enforced against a written surface rather than from memory. |

### Authentication and transport hardening

Unchanged and not silently omitted. The three new routes inherit the REST layer's existing posture
exactly: no authentication, authorization, TLS termination or rate limiting, with binding and access
control the operator's boundary (Phase 4's threats T-04-25/T-04-26, disposition `transfer`). This is
worth restating here only because these three verbs *mutate* where every prior route only read — an
operator surface on an unauthenticated transport is a deliberate inherited position, not an
oversight of this phase.

## Evidence

`databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` records which ROADMAP Phase 7 success criteria
hold and by which committed test.
