# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Fully Agnostic System

**Shipped:** 2026-09-12
**Phases:** 7 | **Plans:** 64 | **Sessions:** not tracked (569 commits over 15 days)

### What Was Built
- An embeddable machine (runner, identity, registry, embedded Cozo/Faiss/SQLite stores) that executes wiring graphs of versioned parts under structured concurrency with metered spend.
- The §18 seam: one closed envelope, four selectors, named refusals, reachable in-process, over REST and over MCP with proven parity.
- Two modalities behind that seam: LightRAG (query side decomposed, ingest admitted opaque) and HippoRAG 2 (fully decomposed), run side-by-side on one corpus and compared in one call.
- Append-only promotion ledger with atomic operator verbs; eval bundle and A/A driver ready for the first measured promotion.

### What Worked
- Verification that re-reproduces claims live instead of trusting SUMMARY.md caught every real gap (Phase 1 unmetered spend, Phase 3 silently-empty extraction, Phase 5 fabricated ingest success, Phase 7 check-then-act race).
- Refuse-don't-fabricate as a house rule: parity harness, evidence renderers and the A/A driver all record `inconclusive` or refuse rather than emit a number. No fabricated verdict shipped.
- Written gate amendments (02-GATE-01-WAIVER, 03/06/07-GATE-AMENDMENT) kept deferrals explicit and dated instead of silent.
- Cross-transport parity tests (in-process / REST / MCP, fixed-trace-token isolation) made every new surface cheap to prove equal.

### What Was Inefficient
- MACH-03 was re-timed four times. The decision to not spend on A/A calibration should have been taken once, early, and recorded as a milestone-level posture instead of re-litigated per phase.
- Mass requirement-status reverts on `gaps_found` (Phase 5, `7c5b9f1`) flipped requirements that were never defective and were only partly restored; the audit had to correct HARD-01/02/04 and the Phase 5 rows.
- Phase 3 needed three review-fix iterations plus a gap-closure wave (03-11..13) because the first parity run was measured against an index with no knowledge graph; an ingest sanity guard earlier would have saved the rework.
- Phase 6 grew to 18 plans, several of them paperwork-only (06-11, 06-17, 06-18) recording declined spend.
- VALIDATION.md was seeded for six phases but reconciled for only two; Nyquist coverage stayed a TODO through the whole milestone.

### Patterns Established
- Every store write goes through a machine primitive; opaque parts write `quarantined`, never `shared`.
- One event-shaping implementation per surface (streaming), one refusal mapper per transport, one shared engine instance under REST and MCP.
- Gate amendments live in the phase directory, cite `docs/system-model/` rather than editing the upstream mirror, and name the point of first need.
- Real-spend runs are dry-run by default and require an explicit flag.

### Key Lessons
1. Record spend posture once per milestone. A recurring "decline" costs a plan each time it recurs.
2. Never mass-revert requirement statuses; revert only the rows the verification actually names.
3. Guard ingest outputs for emptiness before any measurement rides on them.
4. Keep human-only items (CONTRACT §5 causes, spot-checks) out of phase gates; route them to a standing testing plan the owner works at their own pace.

### Cost Observations
- Model mix: not tracked this milestone (adaptive profile).
- Sessions: not tracked.
- Notable: the full suite grew from 233 tests (Phase 1) to 1068 passing at close with a 205 s runtime; no external services are needed to run it.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | n/a | 7 | Gate amendments as first-class records; owner testing moved out of phases into TESTING-PLAN.md |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 1068 passed / 1 skipped | not measured | FTS5 lexical store, blob store, namespace derivation, budget token arithmetic |

### Top Lessons (Verified Across Milestones)

1. Live re-reproduction beats summary trust (one milestone so far).
2. Refuse rather than fabricate (one milestone so far).
