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

### Active

<!-- The four §BP rungs plus the product surface. All hypotheses until shipped. -->

- [ ] Eval bundle stood up (dev/holdout/sealed per RIG §EV.1) and first A/A calibration run per tier — **Falsifier 5 gate**, deferred to its point of first need per `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`; no promotion or parity claim is taken before the A/A floor exists
- [ ] LightRAG query side re-cut into primitive-part nodes (17 of 18 §L.1 positions), parity inside the A/A band (§BP rung 2)
- [ ] HippoRAG 2 fully decomposed (13 node positions, no opaque core) and run side-by-side against LightRAG on the rig (§BP rung 4)
- [ ] Model-doc hardening folded in at the phase that first touches it: gate-script vacuous-pass sites, eight ANATOMY §F closure pointers, DR-04 decision

### Out of Scope

- Any UI (v1 WebUI or new) — API only; standalone means REST + MCP, every UI including Sourcerer is a client
- Docker/k8s deliverables — embeddable-first, local NixOS runtime; v1's docker/k8s material is carried, not maintained
- Re-litigating the architecture — D4 One Machine is **ratified by the owner (2026-08-29)**; SELECTION.md (incl. spike-005 amendment) governs on any disagreement
- Self-improving RAG (automatic modality mutation) — the fitting enables it; building it is a later milestone
- Sourcerer-side applet work — §H2 assigns that to Sourcerer's own planning
- Falsifier 6's foreign-hosted-LightRAG experiment — no ladder rung builds that deployment; accepted risk per §RK
- Trusting published benchmark numbers for decisions — only local measurement on the rig counts

## Context

- **Current state:** Phase 1 (Machine Core) complete — 10 plans across 6 waves, 4/4 ROADMAP success criteria verified, 233 tests passing. The machine executes a wiring graph over embedded stores with stable component identity, metering real spend at each node's declared boundary. Next: Phase 2 (Falsifier Gate) — Falsifiers 2 and 5, the rung-1 gate.

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
| Ratify §VD conditional go; commit build to D4 One Machine | Model's own falsifier discipline held through five phases; the two remaining decisive tests are cheap and gate Phase 1 | — Pending (proves out when Falsifiers 2/5 run) |
| v2.0 milestone covers all four §BP rungs | The goal is demonstrated swappability, which only rung 4's side-by-side run proves | — Pending |
| Standalone product, API only: REST + MCP is Databasise's own voice | Sourcerer is one client; no UI in scope keeps the surface at §18's closed envelope | — Pending |
| Embeddable in-process engine, no Docker | Cozo-style embedding matches actual use; local NixOS is the runtime; containers add surface without value here | — Pending |
| Eval corpus: public set bootstraps, own corpus before promotions | A/A calibration needs data on day one; promotion decisions need representative local data | — Pending |
| Hardening items folded into the build at first-touch | Avoids a stalled doc-only phase; each item has a natural rung (gate scripts → rung 1, DR-04 → rung 3) | — Pending |

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
*Last updated: 2026-09-08 after Phase 5 completion*
