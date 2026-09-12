# Databasise 2.0 — Fully Agnostic System

## What This Is

Databasise 2.0: the RAG engine rebuilt as an **agnostic machine + fitting contract + versioned components**, implementing the v1.0 system model shipped by the RAG Modality Swap project (`docs/system-model/`, verbatim copy of `ServerDestroyer/rag-modality-swap-system-model`). A modality (LightRAG, HippoRAG 2, future paradigms) becomes a wiring of components over machine-owned primitives — databases (graph, vector, KV), LLM/embedding/reranker clients — instead of a monolithic library. Databasise is a **standalone product**: an embeddable, in-process engine whose public voice is its own REST + MCP surface (CONTRACT.md §18); Sourcerer is one consumer among any.

## Core Value

**Modalities are swappable without consumers noticing:** the same corpus, the same seam, N modalities running side-by-side and comparable on the rig — proven by LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope by milestone end.

## Requirements

### Validated

<!-- Inferred from existing code (v1/ — the sourcerer-lightrag fork, mapped in .planning/codebase/). -->

- ✓ v1 engine exists and is the porting source: stock LightRAG 1.5.4 + `v1/lightrag/kg/cozo_impl.py` Cozo plugin — existing
- ✓ Query path already component-shaped: named 4-stage pipeline with plain-data boundaries (`v1/lightrag/operate.py`) — existing (spike 001)
- ✓ Storage/LLM injection seam already exists one level below the modality (storages and model funcs passed in) — existing (spike 001)
- ✓ Parity-harness precedent: `v1/tests/parity/run_substrate_parity.py` (same corpus, isolated dirs, structural diff) — existing
- ✓ Runner, scheduler, and storage-keying designed and built (the §H1 must-decide fence) — Validated in Phase 1: Machine Core
- ✓ Databasise embeddable in-process: Cozo (graph), Faiss (vector), SQLite (KV/lexical/registry/ledger) all in one process tree, no external DB server, no container — Validated in Phase 1: Machine Core
- ✓ Static depth/execution_mode validator (CONTRACT §19) computed from wiring + registry, with self-declaration refused by name at wire time (`self-declared-derivation`) — Validated in Phase 2: Falsifier Gate (evidence: `databasise/evidence/FALSIFIER-2-EVIDENCE.md`)
- ✓ Rung-1→rung-2 gate decision recorded, with a Falsifier 2 failure held as a SELECTION.md-level reversal — Validated in Phase 2: Falsifier Gate (`.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`)
- ✓ Injected-LLM-endpoint survey documented across the five sandbox-candidate engines (Falsifier 8, non-gating) — Validated in Phase 5: Opaque-Side Admission (`databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md`)
- ✓ LightRAG ingest core (~1,786 lines) admitted as opaque node under `quarantined` scope, with an enforced inside-vs-across-boundary change rule and DR-04 decided (§BP rung 3) — Validated in Phase 5: Opaque-Side Admission (`databasise/evidence/DR-04-DECISION.md`)
- ✓ codebase-memory-mcp admitted whole-engine under §17/§8's eleven conditions, run twice (machine chunks / native chunking) — **Falsifier 4** — Validated in Phase 5: Opaque-Side Admission (`databasise/evidence/FALSIFIER-4-EVIDENCE.md`, `databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md`)
- ✓ REST + MCP surface serving the §18 closed envelope: invariance rule, four selectors, tool-surface-growth rule — REST and envelope in Phase 4: The Seam; MCP capability parity completed and Validated in Phase 5: Opaque-Side Admission
- ✓ Operator-asserted promotion and rollback on the append-only ledger: `change_origin` and `promotion_provenance` required on every generation record (never defaulted, never inferable by absence), a semver minted at promotion and only at promotion, tombstoned losers never lifted, the active pointer always a derived query — and all three operator verbs atomic under concurrency (MACH-07, API-09) — Validated in Phase 7: Promotion & Rollback (`databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md`)
- ✓ LightRAG query side re-cut into 17 of 18 §L.1 primitive-part positions, five-arm parity measured on the real corpus (MODAL-01, decomposition and measurement halves) — v1.0, Phase 3; the two CONTRACT §5 owner-only items are in `.planning/TESTING-PLAN.md`
- ✓ HippoRAG 2 fully decomposed (13 positions, no opaque core, whole-graph PPR via bulk export) and run side-by-side with LightRAG on one corpus, compared in one call with no consumer-visible envelope field changing (MODAL-04, MODAL-05, API-08, MACH-10) — v1.0, Phase 6: the core-value proof point
- ✓ Eval bundle minted per RIG §EV.1 with dev/holdout/sealed splits and both §EV.2 target families (MACH-02) — v1.0, Phase 6 (`bundle@v1`, 30-question synthetic fixture)
- ✓ DR-04 decided on `two-covering-rationale` (HARD-03) — v1.0, Phase 5

### Active

<!-- Carried out of v1.0. Not a phase: worked from .planning/TESTING-PLAN.md at the owner's pace, or picked up by the next milestone's requirements. -->

- [ ] First A/A calibration run and bootstrap p95 floor keyed `(bundle@v, tier, metric)` — **Falsifier 5 / MACH-03**, deferred four times, due at the first gate-adjudicated promotion (`06-GATE-AMENDMENT.md`); driver `databasise/eval/aa_run.py` is built and tested, only real judge spend is missing
- [ ] MODAL-01 owner items: human-authored causes for the 20 hybrid/local/global excursions and the q1/q2 answer spot-check (CONTRACT §5; `03-UAT.md` tests 2 and 3)
- [ ] Owner's own corpus layered into the eval bundle before any promotion decision that rides on a measured number (HARD-04)
- [ ] Doc hardening: gate-script vacuous-pass sites (HARD-01) and ANATOMY §F / PARTS Appendix A reconciliation (HARD-02); landing location for the repairs still undecided (upstream, in-place with recorded divergence, or project-layer copies)
- [ ] Nyquist validation reconciled for phases 1, 2, 4, 5, 6 (`/gsd-validate-phase N`)
- [ ] Gate-adjudicated promotion path (measured, with verdict and tier-of-decision) — the next milestone's natural centre, since v1.0 ships only the operator-asserted path

### Out of Scope

- Any UI (v1 WebUI or new) — API only; standalone means REST + MCP, every UI including Sourcerer is a client
- Docker/k8s deliverables — embeddable-first, local NixOS runtime; v1's docker/k8s material is carried, not maintained
- Re-litigating the architecture — D4 One Machine is **ratified by the owner (2026-08-29)**; SELECTION.md (incl. spike-005 amendment) governs on any disagreement
- Self-improving RAG (automatic modality mutation) — the fitting enables it; building it is a later milestone
- Sourcerer-side applet work — §H2 assigns that to Sourcerer's own planning
- Falsifier 6's foreign-hosted-LightRAG experiment — no ladder rung builds that deployment; accepted risk per §RK
- Trusting published benchmark numbers for decisions — only local measurement on the rig counts

## Context

- **Current state:** v1.0 shipped 2026-09-12 — 7 phases, 64 plans, 163 tasks, 569 commits over 15 days. `databasise/` is 48,485 lines of Python with 105 test modules; the full suite is 1068 passed / 1 skipped and needs no external service. Both modalities (LightRAG, HippoRAG 2) run behind the §18 seam in-process, over REST and over MCP; promotion is operator-asserted only. Every promotion in v1.0 is provisional and unmeasured: no A/A floor exists (MACH-03) and the eval bundle holds a synthetic fixture, not the owner's corpus (HARD-04). Milestone audit: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`. Owner testing outside any phase: `.planning/TESTING-PLAN.md`.
- **Known technical debt (from the v1.0 audit):** ledger-wide write lock contended by read-only alias lookups with no timeout tuning (Phase 7 WR-03); Faiss flush race, dormant until Faiss is wired into a live node (Phase 1 CR-01); unchecked tool-name forwarding in the codebase-memory-mcp part, unreachable until a wiring declares a config block (Phase 5 WR-02); `IngestDocument` validation errors lose their refusal shape on both transports (Phase 5 IN-02); MCP has no streaming analog for REST SSE (documented protocol exception).

- **Governing documents:** `docs/system-model/` — SYSTEM-MODEL.md (entry point; §VD verdict, §BP ladder, §H1 handoff), CONTRACT.md (20 sections), ANATOMY.md (44 entries), PARTS.md (3 worked wirings), CATALOG.md (72-system roster + porting protocol), RIG.md (comparison rig, versioning, §F3 affordability), MODEL-RED-TEAM.md, D-VARIANTS/SELECTION.md (governs on disagreement). Frozen at model v1.0; contract repairs during the build are recorded, not silent.
- **Verdict status:** §VD conditional go **ratified 2026-08-29**. Conditions: Falsifiers 2 and 5 run and pass at or within Phase 1; the ladder halts if either fires (that is a SELECTION.md-level reversal, not a repairable defect).
- **Binding order (spike 005):** query side decomposes first; the entangled ingest side stays opaque longest. Any plan assuming a clean ingest lane arrives first is falsified reasoning.
- **Spike findings skill:** `.claude/skills/spike-findings-rag-graph-vector-raw/` — load at the start of design/build work; `references/selected-architecture.md` is the entry point.
- **Codebase map:** `.planning/codebase/` (7 documents, mapped 2026-08-29) covers the v1 fork's stack, architecture, conventions, and concerns.
- **Eval corpus:** public benchmark corpus bootstraps Phase 1's A/A calibration; the owner's own document corpus is layered in before any promotion decision (the model's own rule: papers' numbers disagree 6× — only local measurement counts).
- **Repo:** `Deocracy/Databasise` (public). v1 tree was sanitized for public release (root `.env` removed, credential values blanked; exposed keys rotated by owner 2026-08-29). The unsanitized archive stays local-only.
- **LightRAG evidence pin:** upstream commit `b93f7c31f` — code-verified claims in the model are pinned there.
- **Known open items inherited (§H1 must-decide):** runner/scheduler/storage-keying; intra-node concurrency scheduling; measurement-posture switches for answer-level/index-side classes (default off per RIG §F3.2); cost-model validation (A1–A4); DR-04 per-chunk provenance stamp (first faced at rung 3); N1/N3 design handovers; F-07 snapshot/reset protocol; F-08 seam-level trace shape.

## Constraints

- **Architecture**: D4 One Machine per SELECTION.md — settled, not re-litigated; contract vocabulary (NodeKind tagged sum, 17-member effects[], three artifact scopes, budget tokens, promote/rollback ledger) is frozen input
- **Language**: Python — all candidate modalities are Python; the fitting contract assumes Python parts
- **Runtime**: local NixOS (host legion), embeddable in-process; no external DB servers, no Docker
- **Gate discipline**: Phase 1 → 2 gate is Falsifiers 2 and 5 passing; rung N+1 never starts before rung N's gate
- **Evidence standard**: every promotion claim priced against RIG §F3's per-mutation-class affordability; no benchmark number settles a decision
- **Compatibility**: the §18 seam must stay modality-agnostic — swapping the fitted modality changes no field a consumer sees

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Ratify §VD conditional go; commit build to D4 One Machine | Model's own falsifier discipline held through five phases; the two remaining decisive tests are cheap and gate Phase 1 | ✓ Good — Falsifier 2 passed (Phase 2); Falsifier 5 never fired because it never ran (MACH-03 deferred), so the go stands on one of two falsifiers |
| v1.0 milestone covers all four §BP rungs | The goal is demonstrated swappability, which only rung 4's side-by-side run proves | ✓ Good — MODAL-05 discharged by the real LightRAG-vs-HippoRAG side-by-side run (06-15) |
| Standalone product, API only: REST + MCP is Databasise's own voice | Sourcerer is one client; no UI in scope keeps the surface at §18's closed envelope | ✓ Good — one engine instance under REST and MCP, parity proven per operation |
| Embeddable in-process engine, no Docker | Cozo-style embedding matches actual use; local NixOS is the runtime; containers add surface without value here | ✓ Good — EMBED-01 discharged by the kernel-interface smoke test; the whole suite runs with no external service |
| Eval corpus: public set bootstraps, own corpus before promotions | A/A calibration needs data on day one; promotion decisions need representative local data | ⚠️ Revisit — the public fixture was minted (`bundle@v1`) but the A/A run was declined four times and the owner corpus never layered in; the rule now reads "before any promotion that rides on a measured number" |
| Hardening items folded into the build at first-touch | Avoids a stalled doc-only phase; each item has a natural rung (gate scripts → rung 1, DR-04 → rung 3) | ⚠️ Revisit — only DR-04 (HARD-03) landed at its rung; HARD-01/02 were moved twice and never reached, so first-touch did not hold for doc-only items |
| Defer HARD-01/HARD-02/HARD-04 out of Phase 7 to their point of first need | The operator-asserted path consumes no eval bundle, no floor and no verdict, so none of the three is reached by anything Phase 7 builds (`07-GATE-AMENDMENT.md`) | — Pending (in `.planning/TESTING-PLAN.md`; due at the hardening pass or the first gate-adjudicated promotion) |
| Close v1.0 with MACH-03 and MODAL-01 open under the gate amendments rather than insert a closure phase | Both gaps are owner decisions (spend, human judgment), not code; a phase would only re-record the decline. Owner testing tracked outside phases in `TESTING-PLAN.md` | — Pending (resolves when the owner runs the A/A calibration or records the §5 causes) |
| Close the operator verbs' check-then-act races with one `BEGIN IMMEDIATE` span per verb plus a UNIQUE `(alias, minted_version)` index | A guard read and the append it gates must commit together or the guard goes stale under concurrency; the schema constraint backstops it independently of any Python read path | ✓ Held (G-07-1 closed; 40/40 concurrency runs, full suite green) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-12 after v1.0 milestone*
