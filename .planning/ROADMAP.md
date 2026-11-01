# Roadmap: Databasise 2.0 — Fully Agnostic System

## Milestones

- ✅ **v1.0 Fully Agnostic System** — Phases 1-7 (shipped 2026-09-12) — archive: `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 Engine Fixes + Operator Console** — Phases 8-18 (shipped 2026-11-01) — archive: `.planning/milestones/v1.1-ROADMAP.md`

Owner testing carried out of v1.0 and v1.1 (A/A calibration, MODAL-01 owner items, RUN-11 live embedder runs, parity-env check, optional live rerank) is tracked in `.planning/TESTING-PLAN.md`, not as a phase.

## Phases

<details>
<summary>✅ v1.0 Fully Agnostic System (Phases 1-7) — SHIPPED 2026-09-12</summary>

- [x] Phase 1: Machine Core (10/10 plans) — completed 2026-08-31
- [x] Phase 2: Falsifier Gate (4/4 plans) — completed 2026-08-31
- [x] Phase 3: LightRAG Query Side (13/13 plans) — executed 2026-09-06; MODAL-01 owner items deferred (06-GATE-AMENDMENT.md)
- [x] Phase 4: The Seam (5/5 plans) — completed 2026-09-06
- [x] Phase 5: Opaque-Side Admission (9/9 plans) — completed 2026-09-08
- [x] Phase 6: HippoRAG 2 & Side-by-Side (18/18 plans) — executed 2026-09-12; MACH-03 A/A run deferred (06-GATE-AMENDMENT.md)
- [x] Phase 7: Promotion & Rollback (5/5 plans) — completed 2026-09-12; HARD-01/02/04 deferred (07-GATE-AMENDMENT.md)

Full phase details, success criteria and ordering constraints: `.planning/milestones/v1.0-ROADMAP.md`.
Audit: `.planning/milestones/v1.0-MILESTONE-AUDIT.md` (29/34 requirements, 7/7 integration, 4/4 flows).

</details>

<details>
<summary>✅ v1.1 Engine Fixes + Operator Console (Phases 8-18) — SHIPPED 2026-11-01</summary>

- [x] Phase 8: Run the Engine (10/10 plans) — completed 2026-10-16
- [x] Phase 9: Inputs, Errors & Security (10/10 plans) — completed 2026-10-17
- [x] Phase 10: Stores, Locking & Data Integrity (12/12 plans) — completed 2026-10-17
- [x] Phase 11: LightRAG Corpus Path (11/11 plans) — completed 2026-10-19
- [x] Phase 12: HippoRAG Fixes (14/14 plans) — completed 2026-10-19
- [x] Phase 13: Selectors, Wiring & Runner (13/13 plans) — completed 2026-10-20
- [x] Phase 14: Promotion & Ledger (11/11 plans) — completed 2026-10-21
- [x] Phase 15: Offline Tooling & Packaging (19/19 plans) — completed 2026-10-22
- [x] Phase 16: GUI Connectors (12/12 plans) — completed 2026-10-22
- [x] Phase 17: GUI Mockup (13/13 plans) — completed 2026-10-31; owner re-froze console-a 2026-11-01
- [x] Phase 18: GUI Live (11/11 plans) — completed 2026-11-01; owner click-through approved

Full phase details, success criteria and cross-phase decisions: `.planning/milestones/v1.1-ROADMAP.md`.
Audit: `.planning/milestones/v1.1-MILESTONE-AUDIT.md` (tech_debt: 168/169 requirements, RUN-11 owner-deferred; 11/11 phases; 5/5 integration; 5/5 flows).
Debugging and security battery: `.planning/v1.1-DEBUG-SECURITY-BATTERY.md`.

</details>

## Next milestone

Not yet defined. Start it with `/gsd-new-milestone`. Carried candidates: RUN-11 live runs (TESTING-PLAN.md §2); per-request RocksDB open/close and Faiss reload on the event loop; REST `raw` vs MCP `raw_base64` encoding; installed-wheel default `--store-root`; the namespace-wide socket count in `test_phase_success_criteria.py`.

---
*Last updated: 2026-11-01 after v1.1 milestone*
