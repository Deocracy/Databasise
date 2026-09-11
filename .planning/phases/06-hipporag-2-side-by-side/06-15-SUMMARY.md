---
phase: 06-hipporag-2-side-by-side
plan: 15
subsystem: rag-modality-fitting
tags: [hipporag, lightrag, cross-modality, parity, evidence]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    provides: "06-14's fact-score root-cause fix (corpus-ingest wiring variant, EmptyEmbeddingInputError guard)"
provides:
  - "The first real-corpus cross-modality comparison record: databasise/evidence/CROSS-MODALITY-EVIDENCE.md's `## Real run — 2026-09-10` section"
  - "A built, verified HippoRAG index at v1/.parity_v2_store/shared-4fab18fef508b7bc3dda1cc2d8f12e36 (hipporag-chunks/hipporag-entities/hipporag-facts namespaces, hipporag-graph store) — reusable by future real runs against this corpus"
  - "MODAL-05 discharged in .planning/REQUIREMENTS.md"
affects: ["any future plan re-running or extending the real cross-modality comparison", "Falsifier 5/MACH-03 (the owner's own stated sequencing reason for declining that spend has now resolved cleanly for this one)"]

actuals:
  tokens: 3733
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Checkpoint resolution for a re-attempted spend: re-verify all three preconditions live (env, prior LightRAG index, wiring-variant fix) before running, rather than trusting the prior plan's own precondition record"

key-files:
  created: []
  modified:
    - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Ran the build in the background (uv run python -m databasise.parity.build_hipporag_index) rather than foreground, since a real 20-document OpenIE extraction pass exceeded the 600s foreground command timeout; polled the background process by PID rather than retrying or interrupting it"
  - "Treated the pandas ModuleNotFoundError traceback pycozo prints at store construction as non-fatal noise (an optional pycozo feature probe, not a raised exception reaching the harness) rather than a new-shape failure, since the process continued running and both harnesses exited 0 with real, verified values afterward"

requirements-completed: [MODAL-05]

coverage:
  - id: D1
    description: "The real HippoRAG index build (databasise.parity.build_hipporag_index) completes end to end against the live 20-document Phase 3 parity corpus and live v1/.env.parity credentials, verified non-zero graph/vector counts, partial=False, degraded=False"
    requirement: "MODAL-05"
    verification:
      - kind: other
        ref: "uv run python -m databasise.parity.build_hipporag_index (live invocation, exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The real cross-modality comparison (databasise.parity.run_cross_modality) runs both of the corpus's 2 queries through Databasise.compare() against both arms, isolated stores, structurally comparable envelopes, no partial/degraded arm"
    requirement: "MODAL-05"
    verification:
      - kind: other
        ref: "uv run python -m databasise.parity.run_cross_modality (live invocation, exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "CROSS-MODALITY-EVIDENCE.md gains exactly one new dated section appended below both prior sections, carrying only harness-returned values; MODAL-05 flips to Complete"
    requirement: "MODAL-05"
    verification:
      - kind: other
        ref: "grep -c '^## Real run attempted — refused — 2026-09-10' + grep -c '^\\*\\*Date:\\*\\* 2026-09-09' both = 1 (byte-for-byte preserved); grep -c '| MODAL-05 | Phase 6 | Complete |' .planning/REQUIREMENTS.md = 1"
        status: pass
    human_judgment: false
---

# Phase 06 Plan 15: Real Cross-Modality Run — Re-Attempted and Completed Summary

**LightRAG and HippoRAG 2 ran side-by-side on the real 20-document Phase 3 parity corpus for the first time — both harnesses exited 0, MODAL-05 (the milestone's core-value proof point) is discharged.**

## Performance

- **Duration:** ~55 min (mostly the ~20.3-minute live HippoRAG index build plus a shorter cross-modality comparison pass)
- **Tasks:** 1 (the plan's single checkpoint task, resolved `approve`)
- **Files modified:** 2

## Accomplishments

- Re-verified all three of the plan's own `<precondition>` checks live before asking anything: `v1/.env.parity` resolves a real `llm`/`embedding` client pair; the Phase 3 v1-built LightRAG index is present at `v1/.parity_v2_store/shared-4fab18fef508b7bc3dda1cc2d8f12e36`; `load_wiring("hipporag", variant="corpus-ingest")` resolves to 7 nodes (vs. the 13-node base wiring) — 06-14's fix confirmed in place. Full suite green (960 passed, 3 skipped) before running.
- Ran `databasise.parity.build_hipporag_index` for real against live `v1/.env.parity` credentials — exited 0. `graph_node_count=229`, `graph_edge_count=460`, `chunk_vector_count=20`, `entity_vector_count=209`, `fact_vector_count=226`, `duration_seconds=1218.03`, `partial=False`, `degraded=False`.
- Ran `databasise.parity.run_cross_modality` — exited 0. Both of the corpus's 2 queries (`q1`, `q2`) ran through one `Databasise.compare()` call each against both arms; `directories_disjoint=True`, `artifacts_overlap=False`; every arm on every query `partial=False`/`degraded=False` with identical envelope field sets.
- Appended `## Real run — 2026-09-10` to `databasise/evidence/CROSS-MODALITY-EVIDENCE.md`, below both prior dated sections, carrying only the two harnesses' own returned values.
- Flipped MODAL-05 to `- [x]` / `| MODAL-05 | Phase 6 | Complete |` in `.planning/REQUIREMENTS.md`, appending a new dated `[Measured 2026-09-10 (06-15-PLAN.md): ...]` annotation without touching the two prior annotations.

## Task Commits

1. **Task 1: Spend decision — re-attempt the real cross-modality run now that the fact-score blocker is fixed (MODAL-05)** - `b8eb8f2` (docs)

_Ledger: `plan_head_before` `59443bb` → `HEAD` `b8eb8f2`, 1 commit measured via `git rev-list --count 59443bb..HEAD`._

## Files Created/Modified
- `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` - appended `## Real run — 2026-09-10` (claim/method/findings/verdict/limits), below both pre-existing dated sections, unchanged
- `.planning/REQUIREMENTS.md` - MODAL-05 checkbox and traceability-table row flipped to Complete; new dated annotation appended, both prior annotations intact

## Decisions Made

- **Ran the live build in the background** rather than foreground, since a real 20-document OpenIE extraction pass (40 LLM calls, 109,341 completion tokens) exceeded the 600-second foreground command timeout. Polled the backgrounded process by PID at ~10-second intervals until it exited, rather than interrupting or retrying it.
- **Treated the `pandas` `ModuleNotFoundError` traceback pycozo prints at every store construction as non-fatal noise**, not a new-shape failure worth halting over — it comes from `pycozo.client`'s own optional-feature probe (`import pandas` inside a `try`), printed but caught internally; both harnesses continued and exited 0 with real, verified values immediately afterward. The plan's own "record honestly if a run fails in a new way" instruction was evaluated against this and did not apply, since neither harness ever raised or reported a failure — the traceback is printed noise from a library dependency, not a harness-level outcome.

## Deviations from Plan

None - plan executed exactly as written. Both harnesses were invoked in the order the plan specifies (`build_hipporag_index` first, `run_cross_modality` only after it exited 0), no guard was weakened or bypassed, and the evidence section was appended rather than rewriting prior history.

## Issues Encountered

None - both harnesses exited 0 on the first attempt. No retry, no third harness, no broader scope than the two authorized invocations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **MODAL-05 is Complete.** The milestone's own core-value statement — "the same corpus, the same seam, N modalities running side-by-side and comparable on the rig" — is now observed for LightRAG vs. HippoRAG 2, not just asserted.
- **A real, verified HippoRAG index now exists** at `v1/.parity_v2_store/shared-4fab18fef508b7bc3dda1cc2d8f12e36` (namespaces `hipporag-chunks`/`hipporag-entities`/`hipporag-facts`, store `hipporag-graph`) — reusable by any future real run against this same corpus without re-incurring the index-build spend.
- **MACH-03 (Falsifier 5/A/A calibration) remains Pending**, unaffected by this plan. The owner's own stated reason for declining that spend on 2026-09-10 (uncertainty about whether the same class of live-data defect that hit `fact-score` could waste the far larger T0-leg spend) is now partially addressed for this specific corpus/wiring pair — this run completed cleanly — but MACH-03's own spend decision was not part of this plan's authorized scope and was not asked again, per this plan's own prohibition against broadening the question.
- No further code is needed against MODAL-05; a future plan could extend the comparison (more queries, more corpora) but that is new scope, not a gap in what this plan closes.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*
