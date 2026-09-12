# Roadmap: Databasise 2.0 — Fully Agnostic System

## Overview

The journey runs the four §BP rungs of SYSTEM-MODEL.md in their binding order, with the product surface fitted around them where dependencies allow. Rung 1 builds the machine that everything else stands on — embedded stores, identity, runner, storage keying — and then puts the verdict's decisive falsifier on the table: the computed depth/execution_mode validator (Falsifier 2). Failing it halts the ladder. The calibrated A/A noise floor (Falsifier 5) stands up at its point of first need, Phase 6's cross-modality run, per the GATE-01 waiver record (`.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`) and its second deferral in `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`. Rung 2 re-cuts LightRAG's query side into primitive parts and proves parity inside that measured floor — the query side first, because spike 005 measured the ingest side as the entangled one. With a real decomposed query path to serve, the §18 seam is locked next: one closed envelope, four selectors, refusals instead of silent fallbacks, reachable in-process and over REST. Rung 3 then admits the two opaque things — LightRAG's ~1,786-line ingest core and codebase-memory-mcp whole-engine — and hangs the ingest, delete, and status surface off them. Rung 4 decomposes HippoRAG 2 with no opaque core left and runs both modalities side by side on one corpus, which is the milestone's actual proof: the caller sees two arms keyed by their own selectors and no envelope field moves. The last phase makes the outcome actionable — an append-only ledger and an operator-invoked promote/rollback path, with the owner's own corpus in the eval bundle before any promotion decision rides on it.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Machine Core** - Embedded stores, component identity, runner/scheduler, and storage keying — the §H1 must-decide fence (completed 2026-08-31)
- [x] **Phase 2: Falsifier Gate** - Computed depth/execution_mode validator, eval bundle, and A/A calibration — Falsifiers 2 and 5, the rung-1 gate (completed 2026-08-31)
- [ ] **Phase 3: LightRAG Query Side** - Seventeen §L.1 query positions re-cut as primitive parts with variance-banded parity (§BP rung 2)
- [x] **Phase 4: The Seam** - §18 closed envelope, four selectors, trace and budget reporting, in-process and REST transports (completed 2026-09-06)
- [x] **Phase 5: Opaque-Side Admission** - Ingest core and codebase-memory-mcp admitted under §8's conditions, plus the ingest/corpus surface (§BP rung 3) (completed 2026-09-08)
- [ ] **Phase 6: HippoRAG 2 & Side-by-Side** - Second modality fully decomposed and both run on one corpus, compared in one call (§BP rung 4 — the proof point)
- [x] **Phase 7: Promotion & Rollback** - Append-only ledger, operator-asserted promotion path, and the owner's corpus in the bundle (completed 2026-09-12)

## Phase Details

### Phase 1: Machine Core

**Goal**: The machine executes a wiring graph over embedded stores with stable component identity, inside one local process tree
**Depends on**: Nothing (first phase)
**Requirements**: EMBED-01, MACH-05, MACH-06, MACH-08
**Success Criteria** (what must be TRUE):

  1. Owner installs Databasise as a Python library and it starts with no external database server and no container — Cozo (graph), Faiss (vector), and SQLite (KV/lexical/registry/ledger) all embedded in the one process tree *(amended 2026-08-30 per CONTEXT.md D-05; the prior text said LanceDB)*
  2. Owner submits a wiring graph and the runner executes it to completion under structured concurrency, metering spend at each node's declared boundary, with the intra-node concurrency mechanism decided and written down
  3. The same component wired twice with byte-identical config resolves to one instance identity and one cache partition; changing any config byte yields a different `config_hash` and a separate partition — and a wiring node id is never usable as an identity
  4. A wiring arm containing an `opaque` node writes `quarantined` and cannot reach `shared` KV; per-part graph and vector namespaces are visibly separate after a run

**Plans**: 10/10 plans executed across 6 waves — 9/10 executed; wave 6 is gap closure for the two BLOCKER gaps in `01-VERIFICATION.md`

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Wave 1 · package scaffold, build config, test harness, and the two one-way identity gates

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Wave 2 · end-to-end tracer slice: wiring in, schema-valid run record out (runs alone, before expansion)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Wave 3 · validator: SCC-condensation depth, blast-radius at load time, execution_mode refusals, spike-005 conformance set
- [x] 01-04-PLAN.md — Wave 3 · identity hardening, explicit part registry, four reference parts + three declaration-only entries
- [x] 01-05-PLAN.md — Wave 3 · namespace derivation and the SQLite KV / lexical FTS5 / content-addressed blob stores
- [x] 01-06-PLAN.md — Wave 3 · Cozo graph and Faiss vector adapters ported by copy, with the frozen-bug regression suite

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-07-PLAN.md — Wave 4 · artifact registry, the non-bypassable write-path blast-radius check, and the append-only ledger
- [x] 01-08-PLAN.md — Wave 4 · runner completion: per-node semaphore, exact budget metering, full RIG §TR.1 run record

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-09-PLAN.md — Wave 5 · EMBED-01 smoke test, v1 import-boundary checker, four-criteria acceptance suite

**Wave 6** *(gap closure — the two BLOCKER gaps in `01-VERIFICATION.md`; Phase 2's Falsifier 2/5 gate is blocked on this)*

- [x] 01-10-PLAN.md — Wave 6 · wire real budget metering and guards into the live runner path (MACH-05 / Gap 2, still open), and close Gap 1's missing under-declaring blast-radius regression plus an AST pin on the registry-as-trusted-source invariant (MACH-08 / Gap 1, re-verified closed in source)

### Phase 2: Falsifier Gate

**Goal**: Depth and execution mode are computed rather than declared, and the rung-1→rung-2 gate decision is recorded — the condition the ratified verdict rides on now, with the calibrated A/A noise floor deferred to its point of first need per the GATE-01 waiver record
**Depends on**: Phase 1
**Requirements**: GATE-01, MACH-01, MACH-09
**Success Criteria** (what must be TRUE):

  1. Owner runs the validator over the three named wirings (decomposed lightrag-local query side, opaque codebase-memory-mcp, half-decomposed full LightRAG) and reads `effective_depth` as the minimum over transitive deps and `execution_mode` derived from `effects[]`, with a self-declared value never standing in for the computation and the §19.10 boundary enumeration recorded alongside the node set — Falsifier 2
  2. Answer-level and index-side measurement is off by default and stays off, and any fallback-ladder run is labelled `degraded` with its `degradation_reason`
  3. The gate decision is recorded: the rung-1→rung-2 decision is written down, and a Falsifier 2 failure halts the ladder as a SELECTION.md-level reversal (`.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`)

**Plans**: 4/4 plans executed across 3 waves

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Falsifier 2 evidence: three named wirings as committed JSON, computed depth and execution_mode rendered into a re-runnable evidence document with the §19.10 boundary enumeration
- [x] 02-02-PLAN.md — MACH-09 default measurement posture recorded, with a structural guard pinning the unbuilt promotion path

**Wave 2** *(blocked on 02-01)*

- [x] 02-03-PLAN.md — self-declaration refused by name at wire time, plus the seven-probe suite with paired controls recorded in the evidence document

**Wave 3** *(blocked on Wave 2)*

- [x] 02-04-PLAN.md — GATE-01 waiver record amending the ratified §VD condition, and the ROADMAP/REQUIREMENTS re-scope it authorises

### Phase 3: LightRAG Query Side

**Goal**: LightRAG's query path runs as fitted primitive parts and its parity against the original is measured, not asserted (§BP rung 2)
**Depends on**: Phase 2 (rung-1 gate: Falsifier 2 passed, Falsifier 5 deferred per `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`)
**Requirements**: MODAL-01
**Success Criteria** (what must be TRUE):

  1. Seventeen of the eighteen §L.1 query-side positions run as fitted primitive-part nodes, with the eighteenth (`embedder-index`) authored by the port and identified as its one index-recipe node
  2. Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band rather than a single diff — the band sits inside criterion 6's deterministic retrieval-level substitute gate (the A/A floor itself is deferred to Phase 6, per criteria 4/5's amendment below), or every excursion outside it is a named declared deviation under CONTRACT §5's parity-not-gain rule
  3. Every fitted node reaches storage through a machine primitive only — no node holds a direct reference to v1's singleton store or a process-wide lock, and the per-node ownership audit ships as part of the parity evidence
  4. Owner mints an eval bundle with dev/holdout/sealed splits carrying questions, gold answers, judge instance, judge prompt hash, corpus snapshot hash, determinism/concurrency setting, and both §EV.2 target families — and cannot edit a minted version in place; opening `sealed` mints a new version and every holdout consultation is logged before any decomposition work reads it *(amended 2026-08-31 per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`: deferred to Phase 6's cross-modality run — the point of first need where no retrieval-level identity exists to lean on)*
  5. Owner runs one A/A calibration and reads a bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)` inseparable from the run's declared determinism/concurrency setting, with T1's null width materially narrower than T0's — Falsifier 5 *(amended 2026-08-31 per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`: deferred to Phase 6's cross-modality run, same reason as criterion 4)*
  6. Until the A/A floor exists, parity is checked at the retrieval level with deterministic, zero-token comparisons of retrieved chunk sets and rankings between the original and the decomposed query side, plus human spot-checks of answers (D-05 substitute gate)

**Plans**: 13/13 plans executed — 10/10 executed across 8 waves, plus 3 gap-closure plans (03-11..03-13) for the four `03-VERIFICATION.md` gaps

Plans:

**Wave 1**

- [x] 03-01-PLAN.md — machine-owned LLM/embedding/rerank client primitive, `NodeContext.clients`, scheduler threading, and the two gated package installs
- [x] 03-03-PLAN.md — MACH-02/MACH-03 amendment record, ROADMAP/REQUIREMENTS propagation, and the external model API coverage matrix

**Wave 2** *(blocked on Wave 1)*

- [x] 03-02-PLAN.md — v1's pinned environment, the hashed corpus snapshot, the one v1-built index, and its verified import into the v2 stores

**Wave 3** *(blocked on Wave 2)*

- [x] 03-04-PLAN.md — tracer: the `naive` arm end to end — committed wirings, RFC 6902 arm resolution, seven ported parts, one run record

**Wave 4** *(blocked on Wave 3)*

- [x] 03-05-PLAN.md — the graph half: `get_node_edges` plus keyword extraction and the entity/relation lookup and hydrate-expand positions

**Wave 5** *(blocked on Wave 4)*

- [x] 03-06-PLAN.md — the transform half: round-robin joins, token-budget truncators, the KG chunk selector; base and all five arms parse and conform

**Wave 6** *(blocked on Wave 5)*

- [x] 03-07-PLAN.md — the parity harness: pinned-subprocess original arm, keyword pinning, N-run variance band, deterministic retrieval-level diff
- [x] 03-08-PLAN.md — per-node storage-ownership audit, extended import-boundary proof, stub retirement with Falsifier 2's verdict intact

**Wave 7** *(blocked on Wave 6)*

- [x] 03-09-PLAN.md — the recorded parity evidence, the declared-deviation record, the filled-in validation map, and the owner's spot-check

**Gap closure** *(G-03-1, from 03-UAT.md test 1)*

- [x] 03-10-PLAN.md — the human-authored declared-deviation cause mechanism, derived (no longer hardcoded) evidence prose, a landing place for the pending answer spot-check, and a reconciled MODAL-01 entry

**Gap closure** *(the four `03-VERIFICATION.md` gaps; sequential — each wave depends on the one before)*

- [x] 03-11-PLAN.md — wave 1 · the corpus index has no knowledge graph: the unquoted `OPENAI_LLM_EXTRA_BODY` that failed every extraction, the guards that stop it recurring, the re-ingest and re-import, and the D-07 provider pin on the decomposed arm
- [x] 03-12-PLAN.md — wave 2 · the graph-half nodes read the chunks index: a multi-namespace vector handle, each §L.1 vector position pointed at its own namespace, proven against the real imported index, then one graph arm run end to end
- [x] 03-13-PLAN.md — wave 3 · one consistent evidence set from one post-fix run, named defects instead of vacuous zeros, a MODAL-01 annotation that matches, and the two owner-only asks made exact

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

**Plans**: 5/5 plans executed

**Wave 1**

- [x] 04-01-PLAN.md — the seam tracer: the async `Databasise` object, the §18.1 query object, the §18.2 closed envelope frozen at every nesting depth, the refusal hierarchy, and `run_wiring` demoted to machine-internal

**Wave 2** *(blocked on Wave 1; the two plans run in parallel — no shared files)*

- [x] 04-02-PLAN.md — evidence references that resolve back to the store, and a per-`counted_by` token breakdown with an explicit refusal for an `unbudgetable` participant
- [x] 04-03-PLAN.md — all four §18.4 selectors, the closed selector input set, refusals that name what was missing without naming what the machine holds, and the §18.5 falsifier check

**Wave 3** *(blocked on Wave 2)*

- [x] 04-04-PLAN.md — run-record persistence behind an opaque trace token, MACH-11's out-of-`deps` mutation event, and the two-tier leak gate over a complete real envelope

**Wave 4** *(blocked on Wave 3)*

- [x] 04-05-PLAN.md — the optional REST transport with SSE streaming over the same seam object, the dual-transport conformance test, and this phase's COVERAGE.md

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

**Plans**: 9/9 plans executed — 7/7 executed, plus 2 gap-closure plans pending (05-VERIFICATION.md found 2 BLOCKER gaps)

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Tracer: LightRAG's ingest core admitted opaque and running end-to-end through the machine as a subprocess-placed node (wave 1)
- [x] 05-02-PLAN.md — MACH-04's injected-LLM-endpoint survey across five engines, and DR-04 decided (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-03-PLAN.md — The delete port: a separate §19.6 registration, MACH-11's first real correlation, graph-aware cleanup proved (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 05-04-PLAN.md — Bounded job status, health, counts and paginated corpus reads, plus the corpus-side REST routes (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 05-06-PLAN.md — codebase-memory-mcp admitted whole-engine, Falsifier 4 run twice, and the phase COVERAGE record (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 05-05-PLAN.md — The inside-vs-across-boundary change rule and the compat test that enforces it (wave 5)
- [x] 05-07-PLAN.md — The MCP transport: five intention-level tools with the §18.5 growth rule under test (wave 5)

**Gap closure** *(from 05-VERIFICATION.md; both plans wave 1, no dependencies, run in parallel)*

- [x] 05-08-PLAN.md — G-05-1: ingest()/delete_document() refuse on any node failure instead of fabricating a job (wave 1)
- [x] 05-09-PLAN.md — G-05-2: the MCP transport refuses a page-cap violation and a malformed base64 payload where it used to crash (wave 1)

### Phase 6: HippoRAG 2 & Side-by-Side

**Goal**: Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Depends on**: Phase 5 (rung-3 admission complete)
**Requirements**: MODAL-04, MODAL-05, API-08, MACH-10, MACH-02, MACH-03
**Success Criteria** (what must be TRUE):

  1. HippoRAG 2 runs as thirteen fitted node positions with no opaque core left behind, whole-graph PPR reached through §14.2's Graph bulk-export declared capability into the native igraph/prpack call, with OpenIE and reset-vector-join scaling carried as node internals and index-side effective depth staying `opaque` under the taint rule until its parity is shown
  2. LightRAG and HippoRAG 2 run on one corpus under RIG §RUN — KV shared only where scope admits it, graph and vector stores isolated per arm — and their outputs are structurally comparable
  3. Caller sends one query against two or more modalities and receives per-arm results keyed by the selectors they supplied, never by arm id, wiring name, node id, or modality name; comparison returns per-arm outputs, traces, and scores with no verdict, and a single arm comes back as a run rather than a comparison
  4. The first genuine seam call records F-14's outcome either way: no consumer-visible envelope field changed across the modality swap, or the field that did is named
  5. Mutable-store components either have a defined snapshot/reset protocol or are recorded as permanently excluded from A/B — F-07 discharged rather than left open
  6. Owner mints an eval bundle with dev/holdout/sealed splits carrying questions, gold answers, judge instance, judge prompt hash, corpus snapshot hash, determinism/concurrency setting, and both §EV.2 target families (MACH-02), then runs one A/A calibration and reads a bootstrap-resampled p95 floor keyed to `(bundle@v, tier, metric)` with T1's null width materially narrower than T0's — Falsifier 5, MACH-03, carried forward from Phase 3 per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` *(deferred 2026-09-11 per `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md`: MACH-03 is re-timed a fourth time — from this phase's cross-modality run to the first gate-adjudicated promotion, which lies outside this milestone under MACH-09's default posture, since RIG §PR.3 and CONTRACT §7's operator-asserted path carries no verdict and consumes no floor for the gate's floor to serve. The criterion's substance — no measured claim rides on an unmeasured comparison — is re-timed, not withdrawn: MACH-03 stays Pending, Falsifier 5 stays open rather than failed, and the milestone cannot close until a real A/A run computes both floors. This annotation completes the tracking change that amendment's `## What this authorises` section named alongside the two that did land — Phase 7's `**Depends on**` line and REQUIREMENTS.md's MACH-03 and MODAL-01 rows.)*

**Plans**: 18/18 plans executed — 9 executed across 6 waves, plus 4 gap-closure plans (06-10..06-13) across 3 further waves, plus 4 more gap-closure plans (06-14..06-17) added 2026-09-10 across 3 further waves, plus 1 more (06-18) added 2026-09-12 (06-VERIFICATION.md re-verified at 5/6; SC2 is VERIFIED — 06-15's real cross-modality run completed against live credentials and MODAL-05 is Complete — and WINDOWS.md entry id 3 is closed as `fixed` with `open_count: 0` per 06-14; SC6 alone remains FAILED, deferred a fourth time per `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md`)

Plans:
**Wave 1** *(tracer — runs alone, before any expansion)*

- [x] 06-01-PLAN.md — Tracer: HippoRAG's five-node query-side chain answers a query end to end through the §18 seam, over isolated stores, via §14.2 bulk-export into the native igraph/prpack call

**Wave 2** *(blocked on Wave 1; three plans run in parallel — no shared files)*

- [x] 06-02-PLAN.md — HippoRAG index side, part 1: `chunk-embed`, `openie`, `entity-fact-embed`
- [x] 06-03-PLAN.md — API-08's comparison surface across all three transports, and F-14's first recorded outcome
- [x] 06-04-PLAN.md — MACH-02's eval bundle: a 30-question corpus snapshot, both §EV.2 target families, `bundle@v1` minted

**Wave 3** *(blocked on Wave 2; two plans run in parallel)*

- [x] 06-05-PLAN.md — HippoRAG index side, part 2: the three edge builders, §14.2 batched self-KNN, and the quarantined graph materialiser
- [x] 06-06-PLAN.md — MACH-03's first A/A calibration and Falsifier 5's verdict against a pre-registered threshold

**Wave 4** *(blocked on Wave 3)*

- [x] 06-07-PLAN.md — `dpr-fallback`, the §19.8 guard, and the thirteen-position conformance pin with every divergence from `## §H` recorded

**Wave 5** *(blocked on Wave 4)*

- [x] 06-08-PLAN.md — MODAL-05: both modalities indexed and answering one corpus, with isolation and comparability observed

**Wave 6** *(blocked on Wave 5)*

- [x] 06-09-PLAN.md — MACH-10 / F-07 discharged with an enforcing refusal, plus the phase's record and requirement reconciliation

**Gap-closure Wave 1** *(added 2026-09-10; two plans run in parallel — no shared files)*

- [x] 06-10-PLAN.md — Gap 1(a): HippoRAG gets a real ingest path through the §18 seam, delete refuses by name, and COVERAGE.md states the write surface the seam actually has
- [x] 06-11-PLAN.md — MACH-10 flips to Complete on the owner's confirmation recorded in 06-UAT.md Test 1

**Gap-closure Wave 2** *(blocked on 06-10)*

- [x] 06-12-PLAN.md — Falsifier 5's two named preconditions, closed spend-free: a judge-identity resolver and a cost-bounded, document-count-capped eval-corpus ingest path

**Gap-closure Wave 3** *(blocked on 06-11 and 06-12; not autonomous — two blocking spend checkpoints)*

- [x] 06-13-PLAN.md — the two real-corpus spend decisions (MODAL-05's cross-modality run; MACH-03's A/A calibration), each asked once with a costed projection and each recorded honestly either way

**Gap-closure Wave 4** *(added 2026-09-10, second round; tracer — runs alone, before any expansion)*

- [x] 06-14-PLAN.md — the fact-score defect fixed at its root: index builds resolve HippoRAG's seven-position corpus-ingest wiring, and an empty or blank embedding batch refuses by name at the one method every caller routes through

**Gap-closure Wave 5** *(blocked on 06-14; two plans run in parallel — no shared files; not autonomous: 06-15 holds a blocking spend checkpoint)*

- [x] 06-15-PLAN.md — MODAL-05's real cross-modality run, re-attempted once with the previous wasted authorization named honestly
- [x] 06-16-PLAN.md — the missing A/A run driver: two per-question scorers and a dry-run-by-default paired-calibration command line, without which MACH-03 was not runnable at any price

**Gap-closure Wave 6** *(blocked on 06-15 and 06-16; not autonomous — one blocking spend checkpoint)*

- [x] 06-17-PLAN.md — MACH-03's A/A calibration spend, asked with the threshold pre-registered first, plus a dated correction note making 06-VERIFICATION.md honest about what later commits closed

**Gap-closure Wave 7** *(added 2026-09-12; runs alone, depends on nothing — a three-item paperwork closeout, autonomous with no checkpoint)*

- [x] 06-18-PLAN.md — the deferral annotation Phase 6's own success criterion 6 never received, the stale status line above it, and the blanket asyncio mark warning on every suite run

### Phase 7: Promotion & Rollback

**Goal**: The owner can promote a wiring and roll it back on recorded evidence, with nothing inferable by absence
**Depends on**: Phase 6 (code complete; SC6/MACH-03 and Phase 3's MODAL-01 owner items deferred per `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md`)
**Requirements**: MACH-07, API-09 *(amended 2026-09-11 per `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`: HARD-04, HARD-01 and HARD-02 deferred out of this phase — the operator-asserted path consumes no eval bundle, no floor and no verdict, so none of the three is reached by anything Phase 7 builds)*
**Success Criteria** (what must be TRUE):

  1. Every generation record in the append-only ledger carries both `change_origin` and `promotion_provenance` — never defaulted, never inferable by absence — a semver is minted at promotion and only at promotion, tombstoned losers are never lifted, and the active pointer answers as a derived query over the ledger rather than a written field
  2. Owner promotes a wiring by explicit call with `operator_asserted` provenance and non-empty `promotion_trace_ids`, carrying no verdict and no tier-of-decision; the ledger append is the decision and the alias repoint is atomic; rollback follows the same path
  3. Promote-next and promote-now stay unavailable for answer-level and index-side mutation classes under the default measurement posture, and the refusal names the posture rather than failing silently
  4. ~~The owner's own document corpus is layered into the eval bundle before any promotion decision is taken on it~~ — **STRUCK 2026-09-11** *(deferred per `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`: HARD-04 moves to the owner's in-depth testing / hardening phase, or the first gate-adjudicated promotion, whichever comes first — an operator-asserted promotion reads no eval bundle, so nothing in this phase consumes the owner-corpus layer. HARD-04 stays Pending.)*
  5. ~~The gate scripts fail on missing extraction instead of passing vacuously, and every ANATOMY §F row points at its landed repair with stale cross-document rows reconciled~~ — **STRUCK 2026-09-11** *(deferred per `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`: HARD-01 and HARD-02 move to the same phase, same point of first need — neither is consumed by the promote path, and where the repairs land relative to the never-edited `docs/system-model/` mirror travels with the deferral, unresolved. Both stay Pending.)*

**Plans**: 5 plans across 5 sequential waves (each plan modifies files the previous one created, so no two run in parallel)

Plans:
**Wave 1** *(tracer — runs alone, before any expansion)*

- [x] 07-01-PLAN.md — Tracer: an operator promotes a wiring in-process, one row lands in the append-only ledger, and the alias selector resolves to it through the unchanged Phase 4 read path — plus the four additive columns, the derived semver and mutation class, and SC3's posture refusal

**Wave 2** *(blocked on 07-01 — shares `engine.py`, `promotion.py`, `refusals.py`)*

- [x] 07-02-PLAN.md — `rollback()` to an explicitly named semver and `retire()` as a tombstone on the same append-only path, with the never-lifted rule proven against the real write path

**Wave 3** *(blocked on 07-02 — the three verbs must exist before the transports wrap them)*

- [x] 07-03-PLAN.md — API-09 across all three transports: three REST routes, three MCP tools, conformance parity, the §18.5 coverage record, and the phase's evidence document

**Wave 4** *(gap closure — blocked on 07-03; closes `07-VERIFICATION.md`'s one scored gap / `07-REVIEW.md` CR-01)*

- [x] 07-04-PLAN.md — An out-of-enum promotion `verb` refuses by a named `SeamRefusalError` subclass checked before trace-id resolution, and surfaces under that same name on all three transports (422 over REST, `ToolError` over MCP) instead of crashing

**Wave 5** *(gap closure — blocked on 07-04; closes `07-UAT.md`'s sole gap G-07-1 / `07-REVIEW.md` WR-01, carried unaddressed through two review rounds)*

- [x] 07-05-PLAN.md — A `BEGIN IMMEDIATE` transaction spans each operator verb's guard read and its append, and `(alias, minted_version)` becomes UNIQUE, so concurrent promote/rollback/retire on one alias either serialize or refuse the loser by an already-shipped name — with a committed concurrency regression test for both reproduced races and no change to the §18 envelope

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Machine Core | 10/10 | Complete    | 2026-08-31 |
| 2. Falsifier Gate | 4/4 | Complete    | 2026-08-31 |
| 3. LightRAG Query Side | 13/13 | In Progress|  |
| 4. The Seam | 5/5 | Complete    | 2026-09-06 |
| 5. Opaque-Side Admission | 9/9 | Complete    | 2026-09-08 |
| 6. HippoRAG 2 & Side-by-Side | 17/17 | In Progress|  |
| 7. Promotion & Rollback | 5/5 | Complete    | 2026-09-12 |

## Requirement Coverage

Every v1 requirement maps to exactly one phase. 34/34 mapped.

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1. Machine Core | EMBED-01, MACH-05, MACH-06, MACH-08 | 4 |
| 2. Falsifier Gate | GATE-01, MACH-01, MACH-09 | 3 |
| 3. LightRAG Query Side | MODAL-01 | 1 |
| 4. The Seam | API-03, API-04, API-05, API-10, API-11, EMBED-02, MACH-11 | 7 |
| 5. Opaque-Side Admission | MODAL-02, MODAL-03, MACH-04, API-01, API-02, API-06, API-07, HARD-03 | 8 |
| 6. HippoRAG 2 & Side-by-Side | MODAL-04, MODAL-05, API-08, MACH-10, MACH-02, MACH-03 | 6 |
| 7. Promotion & Rollback | MACH-07, API-09 (+ HARD-04, HARD-01, HARD-02 deferred — see `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`) | 2 built / 3 deferred |

## Ordering Constraints

These are binding, not preferences:

- **GATE-01 rung ordering**: Phase 3 (rung 2) does not start until Phase 2's Falsifier 2 passes, per `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`. Phase 5 (rung 3) does not start until Phase 3's parity gate passes. Phase 6 (rung 4) does not start until Phase 5's admission completes. A Falsifier 2 failure halts the ladder — a SELECTION.md-level reversal, not a repairable defect.
- **Spike-005 decomposition order**: the query side decomposes first (Phase 3), the ingest side stays opaque longest (Phase 5). Any plan assuming a clean ingest lane arrives first is falsified reasoning.
- **Envelope before endpoints**: Phase 4 locks the §18.2 envelope shape (including MACH-11's seam-level event extension) before Phase 5 ships ingest, delete, and status endpoints.
- **Rig before comparison surface**: API-08's comparison endpoint lands in Phase 6 with the side-by-side rig, not earlier. API-09's promotion path lands in Phase 7 with the ledger, not earlier.
- **Eval infrastructure at point of need**: the bundle and A/A floor stand up at Phase 6's cross-modality run, before any promotion or parity claim rides on a measured number, per `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` and its second deferral in `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`. Phase 3's parity comparison uses the deterministic retrieval-level substitute gate instead (D-05).
- **HARD-04 before promotion**: the owner's corpus is in the bundle before any promotion decision rides on it *(amended 2026-09-11 per `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`: this constraint now reads "before any promotion decision that rides on a measured number" — the class it was written for. Phase 7 builds only the operator-asserted path, which carries no verdict and reads no bundle, so HARD-04 moves to the owner's hardening phase or the first gate-adjudicated promotion, whichever comes first.)*
