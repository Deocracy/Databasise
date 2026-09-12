# Milestones

## v1.0 Fully Agnostic System (Shipped: 2026-09-12)

**Phases completed:** 7 phases, 64 plans, 163 tasks
**Timeline:** 2026-08-29 → 2026-09-12 (15 days, 569 commits)
**Codebase:** `databasise/` 48,485 lines of Python, 105 test modules, suite 1068 passed / 1 skipped at close
**Closeout type:** override_closeout (see Known Gaps)

**Delivered:** An embeddable, in-process RAG machine (Cozo, Faiss, SQLite; no server, no container) that runs any modality as a wiring of versioned parts behind one closed §18 envelope, reachable identically in-process, over REST and over MCP. LightRAG's query side is decomposed into 17 primitive parts; its ingest core and codebase-memory-mcp are admitted opaque under §8; HippoRAG 2 is fully decomposed into 13 parts; both modalities run side-by-side on one corpus and are compared in one call with no consumer-visible field changing (MODAL-05, the core-value proof point). Promotion and rollback ride an append-only ledger with atomic operator verbs.

**Key accomplishments:**

- Machine core: structured-concurrency runner metering spend at each node's declared boundary, RFC 8785 + SHA-256 component identity, content-addressed artifact registry, KV shared/quarantined scope rule enforced at load time (Phase 1).
- Falsifier 2 passed: `effective_depth` and `execution_mode` computed from wiring + registry, self-declaration refused by name; measurement posture pinned off by default (Phase 2).
- LightRAG query side re-cut into 17 of 18 §L.1 positions with a five-arm parity harness that refuses rather than fabricates verdicts; hybrid/local/global excursions disclosed, not hidden (Phase 3).
- The §18 seam: query object, four selectors, explicit refusals, citations, budget tokens with `counted_by`, trace reference, single event-shaping path shared by REST streaming and in-process streaming (Phase 4).
- Opaque admission of LightRAG ingest/delete (subprocess-hosted, quarantined) and codebase-memory-mcp (whole-engine, Falsifier 4 run twice), plus MCP tool set with proven REST parity (Phase 5).
- HippoRAG 2 fully decomposed (13 positions, whole-graph PPR via bulk export), eval bundle minted, and the first real LightRAG-vs-HippoRAG side-by-side run on the 20-document parity corpus (Phase 6).
- Append-only promote/rollback/retire ledger with `BEGIN IMMEDIATE` spans and a `UNIQUE(alias, minted_version)` backstop, identical over in-process, REST and MCP (Phase 7).

### Known Gaps

Carried out of v1.0 under written, owner-originated gate amendments. Tracked in `.planning/TESTING-PLAN.md`, not in a phase.

- **MACH-03** (Phase 6): first A/A calibration / Falsifier 5 never run; no p95 floor exists. Driver `databasise/eval/aa_run.py` and all preconditions are built and tested; only real judge spend is missing. Deferred a fourth time by `06-GATE-AMENDMENT.md` to the first gate-adjudicated promotion.
- **MODAL-01** (Phase 3): decomposition and measurement complete; two owner-only CONTRACT §5 items open (human-authored causes for 20 excursions, q1/q2 answer spot-check). Deferred by `06-GATE-AMENDMENT.md`.
- **HARD-01, HARD-02, HARD-04** (Phase 7): deferred out of the milestone by `07-GATE-AMENDMENT.md` to the owner's hardening pass or the first gate-adjudicated promotion.

Known verification overrides: 5 newly acknowledged, 0 carried forward from a prior close (see STATE.md Deferred Items). Phases 3 and 6 closed at `human_needed` / `gaps_found`; phases 4, 5 and 7 read stale in the projection but their VERIFICATION.md reports are `passed`.

**Audit:** `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — 29/34 requirements satisfied, 7/7 integration points wired, 4/4 end-to-end flows complete.

---
