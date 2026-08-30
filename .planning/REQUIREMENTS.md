# Requirements — Databasise 2.0

Requirements are grouped by category with stable REQ-IDs. v1 (this milestone) = the four §BP rungs plus the full standalone product surface. Traceability is filled by the roadmap.

Audited 2026-08-29 against SYSTEM-MODEL.md, CONTRACT.md, RIG.md, PARTS.md, ANATOMY.md, SELECTION.md by three independent reviewers; all findings applied below.

## v1 Requirements

### Build Gates (GATE)

- [ ] **GATE-01**: Rung ordering is enforced: the phase implementing §BP rung N+1 never starts before rung N's gate passes. A Falsifier 2 or Falsifier 5 failure **halts the ladder** — it is a SELECTION.md-level reversal, not a repairable defect (SYSTEM-MODEL §BP Phase 1 gate)

### Machine Core (MACH)

- [ ] **MACH-01**: Static validator implements CONTRACT §19's depth/execution_mode derivations from wiring + registry — `effective_depth` computed as the minimum over transitive deps, `execution_mode` derived from declared `effects[]`, with no self-declaration standing in for the computation — demonstrated on the three named wirings (decomposed lightrag-local query side, opaque codebase-memory-mcp, half-decomposed full LightRAG); the §19.10 boundary enumeration is recorded with the node set — **Falsifier 2 gate**
- [ ] **MACH-02**: Eval bundle stood up per RIG §EV.1 with dev/holdout/sealed splits, containing questions, gold answers, a judge instance, a judge prompt hash, a corpus snapshot hash, and the determinism/concurrency setting; both §EV.2 target families are mandatory bundle content; versions are minted, never edited in place (opening `sealed` mints a new version); holdout-usage logging policy in force before decomposition work consults dev/holdout. Bootstrapped from a public benchmark corpus
- [ ] **MACH-03**: First A/A calibration per RIG §AA.1: one A/A run at n questions producing n paired per-question differences, bootstrap-resampled, the resampled distribution's p95 taken as the calibrated floor at `(bundle@v, tier, metric)` inseparable from the run's declared determinism/concurrency setting; §AA.2 precondition holds (a null with unknown bypass status is not usable as a floor). **Pass criterion: per-tier null width at T1 materially narrower than T0** (SELECTION Falsifier 5) — **Falsifier 5 gate**
- [ ] **MACH-04**: Injected-LLM-endpoint survey documented across the five sandbox-candidate engines named in the lineup (Falsifier 8, non-gating documentation pass)
- [ ] **MACH-05**: Runner/scheduler executes wiring graphs with structured concurrency, metering spend at each node's declared boundary; the intra-node concurrency scheduling mechanism (§H1 handover, contract-settled at V-7) is decided as part of this design; **and the runner stamps the full RIG §TR.1 run-record field set the gate later reads — `determinism_setting`, `concurrency_setting`, `arm_execution_order`, per-node `cache_hit`, `realised_budget_share`, and `guards_fired` — validated against `docs/system-model/rig-trace.schema.json`**. *Run-record clause added 2026-08-30 per CONTEXT.md D-10: without these fields CONTRACT §5 can never evaluate refusal conditions 8, 10 or 11, and a confounded comparison then returns a normal verdict that looks settled rather than unsettled.*
- [ ] **MACH-06**: Component and artifact identity per CONTRACT §0/§1: `name@version`, RFC 8785 + SHA-256 `config_hash`, content-addressed artifact registry with `upstream_ref` lineage; instance identity is `(name@version, config_hash, resolved_dependency_ids)`, never a wiring node id
- [ ] **MACH-07**: Append-only promote/rollback ledger per CONTRACT §7 + RIG §PR: the §7 field set with both `change_origin` (`human_edit` | `machine_mutation` — who authored the change) and `promotion_provenance` (`gate_adjudicated` | `operator_asserted` — who adjudicated it) required on every generation record, never defaulted, never inferable by absence (the two are orthogonal per CONTRACT §7), plus non-empty `promotion_trace_ids` on operator promotions; the ledger append is the decision; alias repoint is atomic; a semver is minted at promotion and only at promotion; tombstoned losers are never lifted; the active pointer is always a derived query, never a written field
- [ ] **MACH-08**: Storage keying per RIG §RUN: KV shared only where CONTRACT §3's `shared` scope admits it (effective depth `stage`); an arm containing an `opaque` node writes `quarantined`, never `shared`; per-part graph/vector namespaces; artifact sharing iff index-recipe hashes are identical
- [ ] **MACH-09**: Measurement posture for answer-level and index-side mutation classes defaults **off** per RIG §F3.2 and stays off in v1 unless §CM.3's A1–A4 cost-model inputs are replaced by measurements; fallback-ladder (degraded) runs are labelled via RIG §TR's `degraded`/`degradation_reason`
- [ ] **MACH-10**: F-07 discharged: the snapshot/reset protocol CONTRACT §14.4 point 3 names for `mutable-store` components is defined, or the A/B exclusion is recorded as permanent
- [ ] **MACH-11**: F-08 discharged: CONTRACT §18.2's envelope extended with the minimum seam-level event shape (`name@version`, spend, outcome) for the `mutates_store`-outside-`deps` exception class

### Modality Ports (MODAL)

- [ ] **MODAL-01**: LightRAG query side re-cut into primitive-part nodes — seventeen of the eighteen §L.1 positions (the eighteenth, `embedder-index`, is the one index-recipe node the port authors) — with N-run, variance-banded parity against the pre-decomposition original inside the A/A band, or named declared deviations (CONTRACT §5's parity-not-gain rule)
- [ ] **MODAL-02**: LightRAG's ~1,786-line ingest core admitted opaque under CONTRACT §8's conditions, its output artifacts under `quarantined` scope per PARTS §L.2's `embedder-index` treatment; at admission time an explicit inside-vs-across-boundary change rule is written (build-added discipline per PITFALLS research — not a model clause; prevents contract erosion at the opaque boundary)
- [ ] **MODAL-03**: codebase-memory-mcp admitted whole-engine under §17/§8's eleven admission conditions verdict-by-verdict — including the three PARTS §X records as not-clean-yeses (machine-side obligations), network namespace denied with the machine acting as injected LLM provider (§8 condition 3), the wall-clock ceiling never self-declared (§8 condition 4), evidence normalized to §4's ItemKind union at the adapter (§17), and a code-inspected admission manifest. Run twice per Falsifier 4 — once consuming machine chunks, once chunking natively — carrying PARTS §X.5's finding that the machine-chunks leg may be unrunnable as worded (record the disposition either way; **Falsifier 4** calibrates the contract, it does not halt the ladder)
- [ ] **MODAL-04**: HippoRAG 2 fully decomposed — thirteen node positions, no opaque core left behind — with whole-graph PPR reached via §14.2's Graph bulk-export declared capability and the native igraph/prpack call plus OpenIE/reset-vector-join scaling formulas carried over as node internals; index-side effective depth remains `opaque` under the taint rule until its parity is shown
- [ ] **MODAL-05**: LightRAG and HippoRAG 2 run side-by-side on one corpus under RIG §RUN (KV sharing per MACH-08's scope rules, isolated graph/vector stores), outputs structurally comparable — the milestone proof point. The first genuine seam call records F-14's outcome (the §18.3 seam-invariance falsifier) either way

### Product Surface (API)

- [ ] **API-01**: Caller can ingest documents (raw upload and structured payload) with async job status polling
- [ ] **API-02**: Caller can delete a document with graph-aware cleanup of entities/edges shared across documents
- [ ] **API-03**: Caller queries with CONTRACT §18.1's query **object** (never a query string); selection via §18.4's four selectors (alias, capability, harness, default) with an unsatisfiable selector returning an explicit refusal naming what was missing, never a silent fallback; an unconsumable query-object member is refused by name; opaque nodes are excluded from the default selector (§8 condition 7); the response is the §18.2 closed envelope, invariant across modality swap
- [ ] **API-04**: Caller can stream query responses
- [ ] **API-05**: Every answer carries citations/provenance (evidence references per §18.2)
- [ ] **API-06**: Caller can introspect health, corpus status, and document counts (bounded/paginated, never full dumps)
- [ ] **API-07**: MCP surface exposes a curated intention-level tool set (ingest, query, delete, status, compare) with capability parity to REST; admission rule per §18.5 — a capability expressible as a §18.4 selector is never a new tool, and the surface never grows per-modality
- [ ] **API-08**: Caller can run one query against two or more modalities on the same corpus in one call and receive per-arm results side-by-side, **keyed by the caller-supplied selectors** — never by arm_id, wiring name, node id, or modality name (§18.2/§18.3); comparison is inspection-only (per-arm outputs, traces, scores — no verdict) and is unaffected by §F3's default posture (RIG §RUN.4); one arm is a run, never a comparison (§RUN.3)
- [ ] **API-09**: Caller can promote and roll back a wiring via RIG §PR.3's operator path: `promotion_provenance: operator_asserted` with non-empty `promotion_trace_ids`, no `verdict` and no `tier-of-decision`; explicit caller-invoked action only; promote-next/promote-now remain unavailable for answer-level and index-side classes under the default posture (MACH-09)
- [ ] **API-10**: Caller can retrieve the node-by-node execution trace for a query per RIG §TR's schema, reached through §18.2's trace reference (debug-flagged; trace content lives behind the reference — internal identities never enter the envelope itself)
- [ ] **API-11**: Response envelope carries per-query budget-token spend with `counted_by` on every token number, an explicit refusal — never a substituted or estimated number — for any `unbudgetable` participant §8 admits, and spend never conflated with capacity (§9)

### Embeddable Product (EMBED)

- [ ] **EMBED-01**: Databasise installs and runs as a single self-contained process tree on the local machine — importable as a Python library, embedded stores (Cozo pinned/vendored for graph, Faiss for vector, SQLite stdlib for KV/lexical/artifact-registry-index/ledger, filesystem for blob), no external DB servers, no Docker; node `execution_mode` remains derived per CONTRACT §3 (subprocess/confined-unit placements are legal inside the tree — only pure, non-iterative nodes may be hosted in-process). *Amended 2026-08-30 per CONTEXT.md D-05: the prior text named LanceDB, which was adopted from `.planning/research/STACK.md:26`'s factually wrong description of the incumbent. Cozo + Faiss are the fork's actual defaults (`v1/lightrag/lightrag.py:275-284`, `v1/lightrag/api/config.py:64-68`) and are owner-locked.*
- [ ] **EMBED-02**: The REST + MCP server is a thin optional layer over the same seam the embedded library exposes — one seam, two transports

### Model Hardening (HARD) — folded in at first-touch

- [ ] **HARD-01**: Gate-script vacuous-pass sites fixed (parts-check.sh: 5 extraction sites guarding ~6 checks; anatomy-check.sh: 1 site guarding 3 checks) — first touched at rung 1
- [ ] **HARD-02**: The eight ANATOMY §F rows lacking landed-repair pointers linked to their PARTS Appendix A dispositions, **reconciling stale cross-document rows in the same pass** (e.g. DR-06: ANATOMY reads "Answered", PARTS Appendix A still reads "not reached") — doc pass alongside rung 1
- [ ] **HARD-03**: DR-04 decided (per-chunk chunker/embedder provenance stamp on the stored chunk artifact: adopt the stamp, or record the two-covering rationale as sufficient) — first faced at rung 3
- [ ] **HARD-04**: Owner's own corpus layered into the eval bundle before any promotion decision is made on it

## v2 Requirements (Deferred)

- Self-improving/auto-promotion loop — the fitting enables it; explicit caller-invoked promotion only this milestone
- Third-modality port from the CATALOG protocol by a non-author (the porting-protocol generality test)
- Measured cost-model validation replacing RIG §CM.3's A1–A4 inference bands (build-or-later-spike per §H1); prerequisite for ever switching MACH-09's posture on
- DR-05 graph-store `validity` sub-capability (bi-temporal time-shift) — no v1 modality declares `temporal`; kept buildable per §14.4, deliberately deferred

## Out of Scope

- Any UI (v1 WebUI or new) — API only; every UI including Sourcerer is a client
- Docker/k8s deliverables — embeddable-first, local NixOS runtime
- Re-litigating the architecture — D4 One Machine ratified 2026-08-29; SELECTION.md governs
- Sourcerer-side applet work — §H2 assigns it to Sourcerer's own planning
- Falsifier 6's foreign-hosted-LightRAG experiment — no rung builds that deployment; accepted risk per §RK
- Full corpus/index dumps via API — bounded responses only (MCP anti-pattern and exfiltration risk)
- N1 (store kinds as NodeKind members) and N3 (`writes_artifact` differentiation) — inherited and left as stated per §H1's repair directions; each reopens only on its named forcing case, not by choice

## Traceability

Maps REQ-IDs to phases (see .planning/ROADMAP.md). Every v1 requirement maps to exactly one phase. Coverage: 34/34.

| REQ-ID | Phase | Status |
|--------|-------|--------|
| GATE-01 | Phase 2 | Pending |
| MACH-01 | Phase 2 | Pending |
| MACH-02 | Phase 2 | Pending |
| MACH-03 | Phase 2 | Pending |
| MACH-04 | Phase 5 | Pending |
| MACH-05 | Phase 1 | Pending |
| MACH-06 | Phase 1 | Pending |
| MACH-07 | Phase 7 | Pending |
| MACH-08 | Phase 1 | Pending |
| MACH-09 | Phase 2 | Pending |
| MACH-10 | Phase 6 | Pending |
| MACH-11 | Phase 4 | Pending |
| MODAL-01 | Phase 3 | Pending |
| MODAL-02 | Phase 5 | Pending |
| MODAL-03 | Phase 5 | Pending |
| MODAL-04 | Phase 6 | Pending |
| MODAL-05 | Phase 6 | Pending |
| API-01 | Phase 5 | Pending |
| API-02 | Phase 5 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| API-06 | Phase 5 | Pending |
| API-07 | Phase 5 | Pending |
| API-08 | Phase 6 | Pending |
| API-09 | Phase 7 | Pending |
| API-10 | Phase 4 | Pending |
| API-11 | Phase 4 | Pending |
| EMBED-01 | Phase 1 | Pending |
| EMBED-02 | Phase 4 | Pending |
| HARD-01 | Phase 2 | Pending |
| HARD-02 | Phase 2 | Pending |
| HARD-03 | Phase 5 | Pending |
| HARD-04 | Phase 7 | Pending |

---
*Last updated: 2026-08-29 after roadmap creation (traceability filled)*
