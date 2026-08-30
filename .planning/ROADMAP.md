# Roadmap: Databasise 2.0 — Fully Agnostic System

## Overview

The journey runs the four §BP rungs of SYSTEM-MODEL.md in their binding order, with the product surface fitted around them where dependencies allow. Rung 1 builds the machine that everything else stands on — embedded stores, identity, runner, storage keying — and then puts the verdict's two decisive falsifiers on the table: the computed depth/execution_mode validator (Falsifier 2) and the calibrated A/A noise floor (Falsifier 5). Either one failing halts the ladder. Rung 2 re-cuts LightRAG's query side into primitive parts and proves parity inside that measured floor — the query side first, because spike 005 measured the ingest side as the entangled one. With a real decomposed query path to serve, the §18 seam is locked next: one closed envelope, four selectors, refusals instead of silent fallbacks, reachable in-process and over REST. Rung 3 then admits the two opaque things — LightRAG's ~1,786-line ingest core and codebase-memory-mcp whole-engine — and hangs the ingest, delete, and status surface off them. Rung 4 decomposes HippoRAG 2 with no opaque core left and runs both modalities side by side on one corpus, which is the milestone's actual proof: the caller sees two arms keyed by their own selectors and no envelope field moves. The last phase makes the outcome actionable — an append-only ledger and an operator-invoked promote/rollback path, with the owner's own corpus in the eval bundle before any promotion decision rides on it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Machine Core** - Embedded stores, component identity, runner/scheduler, and storage keying — the §H1 must-decide fence
- [ ] **Phase 2: Falsifier Gate** - Computed depth/execution_mode validator, eval bundle, and A/A calibration — Falsifiers 2 and 5, the rung-1 gate
- [ ] **Phase 3: LightRAG Query Side** - Seventeen §L.1 query positions re-cut as primitive parts with variance-banded parity (§BP rung 2)
- [ ] **Phase 4: The Seam** - §18 closed envelope, four selectors, trace and budget reporting, in-process and REST transports
- [ ] **Phase 5: Opaque-Side Admission** - Ingest core and codebase-memory-mcp admitted under §8's conditions, plus the ingest/corpus surface (§BP rung 3)
- [ ] **Phase 6: HippoRAG 2 & Side-by-Side** - Second modality fully decomposed and both run on one corpus, compared in one call (§BP rung 4 — the proof point)
- [ ] **Phase 7: Promotion & Rollback** - Append-only ledger, operator-asserted promotion path, and the owner's corpus in the bundle

## Phase Details

### Phase 1: Machine Core
**Goal**: The machine executes a wiring graph over embedded stores with stable component identity, inside one local process tree
**Depends on**: Nothing (first phase)
**Requirements**: EMBED-01, MACH-05, MACH-06, MACH-08
**Success Criteria** (what must be TRUE):
  1. Owner installs Databasise as a Python library and it starts with no external database server and no container — Cozo, LanceDB, and SQLite all embedded in the one process tree
  2. Owner submits a wiring graph and the runner executes it to completion under structured concurrency, metering spend at each node's declared boundary, with the intra-node concurrency mechanism decided and written down
  3. The same component wired twice with byte-identical config resolves to one instance identity and one cache partition; changing any config byte yields a different `config_hash` and a separate partition — and a wiring node id is never usable as an identity
  4. A wiring arm containing an `opaque` node writes `quarantined` and cannot reach `shared` KV; per-part graph and vector namespaces are visibly separate after a run
**Plans**: TBD

### Phase 2: Falsifier Gate
**Goal**: Depth and execution mode are computed rather than declared, and the rig's own noise floor is measured — the two conditions the ratified verdict rides on
**Depends on**: Phase 1
**Requirements**: GATE-01, MACH-01, MACH-02, MACH-03, MACH-09, HARD-01, HARD-02
**Success Criteria** (what must be TRUE):
  1. Owner runs the validator over the three named wirings (decomposed lightrag-local query side, opaque codebase-memory-mcp, half-decomposed full LightRAG) and reads `effective_depth` as the minimum over transitive deps and `execution_mode` derived from `effects[]`, with a self-declared value never standing in for the computation and the §19.10 boundary enumeration recorded alongside the node set — Falsifier 2
  2. Owner mints an eval bundle with dev/holdout/sealed splits carrying questions, gold answers, judge instance, judge prompt hash, corpus snapshot hash, determinism/concurrency setting, and both §EV.2 target families — and cannot edit a minted version in place; opening `sealed` mints a new version and every holdout consultation is logged before any decomposition work reads it
  3. Owner runs one A/A calibration and reads a bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)` inseparable from the run's declared determinism/concurrency setting, with T1's null width materially narrower than T0's — Falsifier 5
  4. Answer-level and index-side measurement is off by default and stays off, and any fallback-ladder run is labelled `degraded` with its `degradation_reason`
  5. The gate is real, not decorative: the gate scripts fail on missing extraction instead of passing vacuously, every ANATOMY §F row points at its landed repair with stale cross-document rows reconciled, and the rung-1→rung-2 decision is recorded — a Falsifier 2 or 5 failure halts the ladder as a SELECTION.md-level reversal
**Plans**: TBD

### Phase 3: LightRAG Query Side
**Goal**: LightRAG's query path runs as fitted primitive parts and its parity against the original is measured, not asserted (§BP rung 2)
**Depends on**: Phase 2 (rung-1 gate: Falsifiers 2 and 5 both passed)
**Requirements**: MODAL-01
**Success Criteria** (what must be TRUE):
  1. Seventeen of the eighteen §L.1 query-side positions run as fitted primitive-part nodes, with the eighteenth (`embedder-index`) authored by the port and identified as its one index-recipe node
  2. Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band rather than a single diff — the band sits inside Phase 2's A/A floor, or every excursion outside it is a named declared deviation under CONTRACT §5's parity-not-gain rule
  3. Every fitted node reaches storage through a machine primitive only — no node holds a direct reference to v1's singleton store or a process-wide lock, and the per-node ownership audit ships as part of the parity evidence
**Plans**: TBD

### Phase 4: The Seam
**Goal**: Callers reach the engine through one closed envelope that tells them nothing about which modality answered
**Depends on**: Phase 3
**Requirements**: API-03, API-04, API-05, API-10, API-11, EMBED-02, MACH-11
**Success Criteria** (what must be TRUE):
  1. Caller submits a §18.1 query object (never a query string) and selects via one of §18.4's four selectors; an unsatisfiable selector or an unconsumable query-object member returns an explicit refusal naming what was missing, never a silent fallback, and opaque nodes are excluded from the default selector
  2. Caller receives the §18.2 closed envelope with evidence references on every answer and can stream it; a `mutates_store`-outside-`deps` participant surfaces as a seam-level event (`name@version`, spend, outcome) instead of vanishing
  3. Every token number in the envelope carries `counted_by`; any `unbudgetable` participant produces an explicit refusal rather than a substituted or estimated number, and spend is never reported as capacity
  4. Caller sets the debug flag and retrieves the node-by-node execution trace through the envelope's trace reference — internal node identities stay behind the reference and never enter the envelope itself
  5. The same seam is reachable two ways with identical behavior: `import databasise` in-process, and the optional REST layer over the same call path
**Plans**: TBD

### Phase 5: Opaque-Side Admission
**Goal**: The entangled ingest side is admitted under the contract's opaque conditions rather than smuggled in, and callers can feed and inspect the corpus (§BP rung 3)
**Depends on**: Phase 4 (and Phase 3's rung-2 parity gate)
**Requirements**: MODAL-02, MODAL-03, MACH-04, API-01, API-02, API-06, API-07, HARD-03
**Success Criteria** (what must be TRUE):
  1. LightRAG's ~1,786-line ingest core runs as an admitted opaque node whose output artifacts land in `quarantined` scope, with a written inside-vs-across-boundary change rule that a compat test enforces, and the DR-04 decision recorded either way — the per-chunk chunker/embedder provenance stamp adopted, or the two-covering rationale written down as sufficient
  2. codebase-memory-mcp is admitted whole-engine with a verdict recorded against each of the eleven §17/§8 conditions — the three PARTS §X records logged as not-clean-yeses, network namespace denied with the machine acting as injected LLM provider, wall-clock ceiling measured and never self-declared, evidence normalized to §4's ItemKind union at the adapter, code-inspected admission manifest — backed by the injected-LLM-endpoint survey across the five sandbox-candidate engines, and run twice (machine chunks / native chunking) with the machine-chunks leg's disposition recorded whether or not it proves runnable
  3. Caller uploads a document (raw or structured payload), polls the job to completion, then deletes it — and entities and edges it shared with surviving documents are cleaned up without orphaning the survivors
  4. Caller reads health, corpus status, and document counts in bounded paginated form; a full corpus or index dump is never returned
  5. The MCP surface exposes the same capabilities as REST as intention-level tools; a capability expressible as a §18.4 selector never becomes a new tool, and adding a modality adds no tool
**Plans**: TBD

### Phase 6: HippoRAG 2 & Side-by-Side
**Goal**: Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Depends on**: Phase 5 (rung-3 admission complete)
**Requirements**: MODAL-04, MODAL-05, API-08, MACH-10
**Success Criteria** (what must be TRUE):
  1. HippoRAG 2 runs as thirteen fitted node positions with no opaque core left behind, whole-graph PPR reached through §14.2's Graph bulk-export declared capability into the native igraph/prpack call, with OpenIE and reset-vector-join scaling carried as node internals and index-side effective depth staying `opaque` under the taint rule until its parity is shown
  2. LightRAG and HippoRAG 2 run on one corpus under RIG §RUN — KV shared only where scope admits it, graph and vector stores isolated per arm — and their outputs are structurally comparable
  3. Caller sends one query against two or more modalities and receives per-arm results keyed by the selectors they supplied, never by arm id, wiring name, node id, or modality name; comparison returns per-arm outputs, traces, and scores with no verdict, and a single arm comes back as a run rather than a comparison
  4. The first genuine seam call records F-14's outcome either way: no consumer-visible envelope field changed across the modality swap, or the field that did is named
  5. Mutable-store components either have a defined snapshot/reset protocol or are recorded as permanently excluded from A/B — F-07 discharged rather than left open
**Plans**: TBD

### Phase 7: Promotion & Rollback
**Goal**: The owner can promote a wiring and roll it back on recorded evidence, with nothing inferable by absence
**Depends on**: Phase 6
**Requirements**: MACH-07, API-09, HARD-04
**Success Criteria** (what must be TRUE):
  1. Every generation record in the append-only ledger carries both `change_origin` and `promotion_provenance` — never defaulted, never inferable by absence — a semver is minted at promotion and only at promotion, tombstoned losers are never lifted, and the active pointer answers as a derived query over the ledger rather than a written field
  2. Owner promotes a wiring by explicit call with `operator_asserted` provenance and non-empty `promotion_trace_ids`, carrying no verdict and no tier-of-decision; the ledger append is the decision and the alias repoint is atomic; rollback follows the same path
  3. Promote-next and promote-now stay unavailable for answer-level and index-side mutation classes under the default measurement posture, and the refusal names the posture rather than failing silently
  4. The owner's own document corpus is layered into the eval bundle before any promotion decision is taken on it
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Machine Core | 0/TBD | Not started | - |
| 2. Falsifier Gate | 0/TBD | Not started | - |
| 3. LightRAG Query Side | 0/TBD | Not started | - |
| 4. The Seam | 0/TBD | Not started | - |
| 5. Opaque-Side Admission | 0/TBD | Not started | - |
| 6. HippoRAG 2 & Side-by-Side | 0/TBD | Not started | - |
| 7. Promotion & Rollback | 0/TBD | Not started | - |

## Requirement Coverage

Every v1 requirement maps to exactly one phase. 34/34 mapped.

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1. Machine Core | EMBED-01, MACH-05, MACH-06, MACH-08 | 4 |
| 2. Falsifier Gate | GATE-01, MACH-01, MACH-02, MACH-03, MACH-09, HARD-01, HARD-02 | 7 |
| 3. LightRAG Query Side | MODAL-01 | 1 |
| 4. The Seam | API-03, API-04, API-05, API-10, API-11, EMBED-02, MACH-11 | 7 |
| 5. Opaque-Side Admission | MODAL-02, MODAL-03, MACH-04, API-01, API-02, API-06, API-07, HARD-03 | 8 |
| 6. HippoRAG 2 & Side-by-Side | MODAL-04, MODAL-05, API-08, MACH-10 | 4 |
| 7. Promotion & Rollback | MACH-07, API-09, HARD-04 | 3 |

## Ordering Constraints

These are binding, not preferences:

- **GATE-01 rung ordering**: Phase 3 (rung 2) does not start until Phase 2's Falsifiers 2 and 5 both pass. Phase 5 (rung 3) does not start until Phase 3's parity gate passes. Phase 6 (rung 4) does not start until Phase 5's admission completes. A Falsifier 2 or 5 failure halts the ladder — a SELECTION.md-level reversal, not a repairable defect.
- **Spike-005 decomposition order**: the query side decomposes first (Phase 3), the ingest side stays opaque longest (Phase 5). Any plan assuming a clean ingest lane arrives first is falsified reasoning.
- **Envelope before endpoints**: Phase 4 locks the §18.2 envelope shape (including MACH-11's seam-level event extension) before Phase 5 ships ingest, delete, and status endpoints.
- **Rig before comparison surface**: API-08's comparison endpoint lands in Phase 6 with the side-by-side rig, not earlier. API-09's promotion path lands in Phase 7 with the ledger, not earlier.
- **Eval infrastructure before decomposition**: the bundle and A/A floor (Phase 2) exist before any node boundary is moved (Phase 3), per the spike-findings requirement.
- **HARD-04 before promotion**: the owner's corpus is in the bundle before any promotion decision rides on it (Phase 7).
