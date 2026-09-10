---
phase: 06-hipporag-2-side-by-side
plan: 13
subsystem: eval
tags: [hipporag, cross-modality, a-a-calibration, falsifier-5, spend-decision, evidence]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    provides: "06-10's HippoRAG ingest path through the public seam, 06-12's judge-identity resolver and cost-bounded corpus ingest — both spend-decision preconditions this plan's two checkpoints needed to be answerable at all"
provides:
  - "A real, spend-incurring attempt at the MODAL-05 cross-modality run — refused before completion by build_hipporag_index's own post-run verification, surfacing a genuine fact-score empty-string defect never exercised by fixture tests"
  - "A second, informed decline of the MACH-03 A/A calibration spend, recorded with the owner's reasoning and both named preconditions now closed in code"
  - "A dated WINDOWS.md ledger entry for the fact-score defect, so it is discoverable as future work rather than lost in an evidence-document paragraph"
affects: ["phase-7-promotion-rollback", "any future plan re-attempting the real HippoRAG cross-modality run or the A/A calibration"]

# Actuals (#2632)
actuals:
  tokens: 5400
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Spend checkpoints append a dated house-sectioned entry to the plan's named evidence document rather than rewriting it — history of every deferral/attempt stays intact and readable in one place"
    - "A harness's own refusal (non-zero exit, no verified result) is recorded as 'attempted and refused,' distinct from both a clean success and an undecided deferral"

key-files:
  created: []
  modified:
    - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
    - databasise/evidence/FALSIFIER-5-EVIDENCE.md
    - .planning/REQUIREMENTS.md
    - .planning/WINDOWS.md

key-decisions:
  - "Owner approved the MODAL-05 real cross-modality run; the harness itself refused (fact-score node 400 on empty-string input) before completion — real spend incurred, no comparison produced, MODAL-05 stays Pending against the concrete defect instead of the prior 'unauthorized' blocker."
  - "Owner declined the MACH-03 A/A calibration a second time, reasoning that Task 1's live failure in this same session on an untested edge case makes fixing fact-score first the cheaper path before risking the far larger T0-leg spend."

patterns-established: []

requirements-completed: []  # Neither MODAL-05 nor MACH-03 flipped to Complete this plan — both stay Pending per their own prohibitions against rounding a declined/refused spend up to done.

coverage:
  - id: D1
    description: "MODAL-05 spend checkpoint: owner authorized the real cross-modality run; build_hipporag_index invoked for real against live v1/.env.parity credentials, refused by its own post-run verification (fact-score node 400 on empty-string input) before run_cross_modality could be reached"
    requirement: "MODAL-05"
    verification:
      - kind: other
        ref: "grep -c '^\\*\\*Date:\\*\\* 2026-09-09' + grep -c '^## .*2026-09-10' over CROSS-MODALITY-EVIDENCE.md; grep -c '| MODAL-05 | Phase 6 | (Complete|Pending) |' over REQUIREMENTS.md"
        status: pass
    human_judgment: true
    rationale: "The spend authorization itself and the correctness of 'attempted and refused, not rounded up to success' as the recorded verdict are owner-facing judgment calls this document reports honestly, not something a script can adjudicate."
  - id: D2
    description: "MACH-03 spend checkpoint: owner declined the A/A calibration a second time; FALSIFIER-5-EVIDENCE.md gained a dated deferral entry naming both preconditions closed by 06-12 and the spend as the sole remaining blocker"
    requirement: "MACH-03"
    verification:
      - kind: other
        ref: "grep -c '^\\*\\*Date:\\*\\* 2026-09-09' + grep -c '^## .*2026-09-10' over FALSIFIER-5-EVIDENCE.md; grep -c '| MACH-02 | Phase 6 | Complete |' + grep -c '| MACH-03 | Phase 6 | (Complete|Pending) |' over REQUIREMENTS.md; bundle@v1 digest check; pytest tests/evidence/test_falsifier5_record.py tests/eval/ -x"
        status: pass
    human_judgment: true
    rationale: "A recorded decline is this task's success state per the plan's own text — whether the owner's stated reason and the deferral record honestly capture that decision is a judgment call, not something an automated check settles."

duration: 42min
completed: 2026-09-10
status: complete
---

# Phase 6 Plan 13: Spend Decisions — Cross-Modality Run and A/A Calibration Summary

**Owner authorized the real HippoRAG cross-modality run; the harness itself refused on a genuine fact-score empty-string defect before producing a comparison, and the owner then declined the A/A calibration spend a second time, citing that same live failure as the reason to fix the defect before risking a larger spend.**

## Performance

- **Duration:** 42 min (spans a `gate="blocking-human"` checkpoint pause between Task 1 and Task 2)
- **Started:** 2026-09-10T17:01:55Z (Task 1 commit)
- **Completed:** 2026-09-10T17:44:33Z
- **Tasks:** 2 (both `checkpoint:human-action`, `gate="blocking-human"`)
- **Files modified:** 4 (`CROSS-MODALITY-EVIDENCE.md`, `FALSIFIER-5-EVIDENCE.md`, `REQUIREMENTS.md`, `WINDOWS.md`)

## Accomplishments

- **Task 1 (MODAL-05):** owner replied `approve`. `databasise.parity.build_hipporag_index` ran for real against the 20-document Phase 3 parity corpus using live `v1/.env.parity` credentials (`qwen/qwen3.7-flash` extraction, `qwen/qwen3-embedding-8b` embedding). The harness's own post-run verification refused to report success — `partial=True degraded=True`, `stop_reason` naming a `NodeExecutionError` at the `fact-score` node, a provider `400` over an empty-length string in the input batch. Real, non-zero spend was incurred (chunk/entity/fact-embedding nodes ran to completion ahead of the refusal) but its exact size is unknown — the harness's own token accounting is only assembled on a completed run. `run_cross_modality` was never invoked, per the plan's stop-on-refusal rule. `CROSS-MODALITY-EVIDENCE.md` gained a `## Real run attempted — refused — 2026-09-10` section below its 2026-09-09 record; MODAL-05 stays Pending, its outstanding item now naming the `fact-score` defect as the concrete next blocker instead of "unauthorized."
- **Task 2 (MACH-03 / Falsifier 5):** owner replied `decline`. `FALSIFIER-5-EVIDENCE.md` gained a `## Deferred again — 2026-09-10` section below its 2026-09-09 record, carrying the owner's reason verbatim: Task 1's real run had just died on an untested edge case in this same session, and the same defect class could waste the far more expensive T0 leg, so fixing `fact-score` first makes both spends cheaper to attempt. The entry also records what changed since 2026-09-09 — 06-12 closed both of Falsifier 5's named preconditions (`databasise/eval/remint.py` resolves a real judge identity; `databasise/eval/corpus_ingest.py` gives a cost-bounded, dry-run-by-default ingest path) — so the spend itself is now the sole outstanding blocker. MACH-03 stays Pending with a dated annotation naming that blocker; MACH-02 and `bundle@v1`'s committed digest are both undisturbed.
- **`fact-score` defect filed as future work.** Appended to `.planning/WINDOWS.md` (`kind: deviation`, entry id 3, `databasise/parts_core/hipporag/fact_score.py`) — a real code defect surfaced by the first-ever real HippoRAG index build in this project, uncaught by any fixture test, now discoverable at ship time rather than buried in an evidence-document paragraph.

## Task Commits

1. **Task 1: Spend decision — real cross-modality run (MODAL-05)** — `fa2aade` (docs) — completed by a prior agent before this continuation; verified present via `git log` per resume instructions, not redone.
2. **Task 2: Spend decision — real A/A calibration decline (MACH-03, Falsifier 5)** — `a45bfd4` (docs)

**Plan metadata:** committed separately below (STATE.md/ROADMAP.md/SUMMARY.md).

## Files Created/Modified

- `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` — Task 1: appended `## Real run attempted — refused — 2026-09-10` (by the prior agent; verified intact)
- `databasise/evidence/FALSIFIER-5-EVIDENCE.md` — Task 2: appended `## Deferred again — 2026-09-10`
- `.planning/REQUIREMENTS.md` — MODAL-05 annotation appended (Task 1, prior agent); MACH-03 annotation appended (Task 2, this continuation); both rows remain in their pre-plan checked state (`[ ]`/Pending)
- `.planning/WINDOWS.md` — new `deviation` entry (id 3) for the `fact-score` empty-string defect

## Decisions Made

- **Owner: `approve` (Task 1).** Authorized the real cross-modality run. The harness's own refusal (not a second deferral, not a decline) is the recorded outcome — a genuine spend-incurring attempt that surfaced a concrete code defect instead of a comparison result.
- **Owner: `decline` (Task 2).** Declined the A/A calibration a second time (first at 06-06). Reason recorded verbatim in `FALSIFIER-5-EVIDENCE.md` and in `.planning/REQUIREMENTS.md`'s MACH-03 annotation: fixing the `fact-score` defect Task 1 just surfaced makes both spends cheaper to attempt, since the same defect class could waste the much larger T0-leg spend.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — pre-existing, not fixed this plan] `fact-score` node fails a real HippoRAG index build on empty-string input**
- **Found during:** Task 1 (prior agent's real run attempt)
- **Issue:** `databasise.parity.build_hipporag_index`, invoked for real for the first time in this project against a live corpus, failed at the `fact-score` node with a provider `400` ("too_small — expected string to have >=1 characters") — an empty-length string reached the scoring provider's batch input. No fixture test ever exercised this input shape.
- **Fix:** Not fixed in this plan — Rule 3's blocking-issue auto-fix does not apply here because the failure surfaced inside a `checkpoint:human-action` task whose own action text is explicit: "A non-zero exit from either is a refusal, not a result: record the refusal's own message and stop — never retry with a weakened guard." Fixing the node would be new engineering work outside this plan's own scope (which "contains no code," per its objective), and the owner's own Task 2 decline treats fixing `fact-score` first as the deliberate next step, not something to patch silently mid-checkpoint.
- **Files modified:** none (documented, not patched)
- **Filed as:** `.planning/WINDOWS.md` entry id 3 (`kind: deviation`, `databasise/parts_core/hipporag/fact_score.py`), open
- **Impact:** MODAL-05 stays Pending against this concrete defect instead of the prior "unauthorized" blocker; MACH-03 stays Pending, with the owner explicitly sequencing the defect fix ahead of the next spend attempt.

**2. [Deviation from prompt paraphrase — projection method] Task 2's projection was computed read-only rather than via the plan's own CLI invocation**
- **Found during:** Task 2 (prior context, per continuation prompt)
- **Issue:** The plan's Task 2 action text calls for running `corpus_ingest --limit 291 --arm lightrag` and showing the owner its printed output as the projection. That invocation was blocked by the session's command classifier.
- **Fix:** The projection was derived read-only via `wc -c` over `databasise/tests/fixtures/eval-corpus/documents/`, and the resulting figures matched `estimate()`'s own arithmetic exactly — the owner was shown the same numbers the CLI would have printed, computed by a different, non-blocked path.
- **Files modified:** none
- **Verification:** figures cross-checked against `corpus_ingest.estimate()`'s formula
- **Impact:** No effect on the decision's substance — the owner saw the real, computed projection either way.

**3. [Rule 1-adjacent — measurement, not a code bug] Task 1's `<read_first>` cited a stale, overstated corpus size**
- **Found during:** this continuation, re-checking Task 1's prose against the canonical reader before writing this Summary
- **Issue:** Task 1's `<read_first>` and the checkpoint text presented to the owner both cite the Phase 3 parity corpus as "20 documents, 15,711 bytes, 2,119 words." `MANIFEST.json` itself does not state a byte or word count at all (only per-document SHA-256 digests and a corpus-level hash) — that figure was carried in from somewhere else and is wrong. Independent measurement via `databasise.parity.corpus.load_snapshot()` (the canonical drift-checked reader — verified 20/20 documents, no `CorpusDriftError`) found **9,597 bytes, 1,590 words** across the same 20 documents; a raw `wc -c`/`wc -w` over `tests/fixtures/corpus/documents/*.txt` independently confirms the identical totals. The cited figure overstates the corpus by roughly 6,100 bytes (64%) and 530 words (33%).
- **Fix:** Not corrected in the evidence documents or the plan text — the owner was shown and approved against the plan's stated (overstated) figure at Task 1's checkpoint, so rewriting it after the fact would misrepresent what the owner actually saw when approving the spend. Recorded here instead so a future plan citing this corpus's size uses the measured figure, not the plan's stale one.
- **Files modified:** none
- **Verification:** `load_snapshot()` output cross-checked against raw `wc -c`/`wc -w` over the same 20 files — both give 9,597 bytes / 1,590 words
- **Impact:** The projection's *conclusion* ("well under 1M tokens") is unaffected — even the overstated figure is off by less than 1% of the projection's own headroom. What matters going forward: any future plan computing a fresh projection from this corpus should call `load_snapshot()` or `wc`, not reuse the "15,711 bytes" figure this plan's Task 1 carried forward uncorrected.

---

**Total deviations:** 3 documented (1 pre-existing defect filed as future work, 1 tooling-path substitution with no substantive effect, 1 stale/overstated corpus-size figure found and measured but left uncorrected in the already-approved checkpoint text)
**Impact on plan:** No scope creep. The `fact-score` defect is real, valuable, and deliberately left unfixed per this plan's own explicit prohibition against silently expanding a checkpoint's scope into new engineering work. The corpus-size discrepancy does not change the projection's conclusion and does not require re-asking the owner.

## Issues Encountered

None beyond the `fact-score` defect documented above, which is the plan's single most valuable finding, not an unresolved problem with the plan's own execution.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **MODAL-05 and MACH-03 both remain Pending.** Neither is rounded up to Complete — both evidence documents and both `REQUIREMENTS.md` rows say so plainly, per this plan's own prohibitions.
- **The concrete next blocker for both is now the same defect:** `fact-score`'s empty-string-input handling (`databasise/parts_core/hipporag/fact_score.py`, `.planning/WINDOWS.md` entry id 3). Fixing it is prerequisite work for both a future MODAL-05 re-attempt and a future MACH-03 spend authorization, per the owner's own stated reasoning in the Task 2 decline.
- **Phase 7 (Promotion & Rollback)** is the eventual consumer of the MACH-03 A/A floor; `.planning/ROADMAP.md`'s Ordering Constraints already state no promotion or parity claim may ride on a measured number until that floor exists. Nothing in Phase 7 is unblocked by this plan; nothing in Phase 7 newly depends on work this plan skipped.
- **`bundle@v1` and MACH-02 are untouched** — verified by digest check in Task 2's verification.
- This is the last plan in Phase 6's gap-closure wave (06-13, depends on 06-11/06-12). Phase 6 is otherwise complete; MODAL-05 and MACH-03 are its two remaining open items, both spend-gated and both now blocked on the same named defect.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*

## Self-Check: PASSED

- `.planning/phases/06-hipporag-2-side-by-side/06-13-SUMMARY.md` exists on disk.
- Both task commits (`fa2aade`, `a45bfd4`) found in `git log --oneline --all`.
- All four modified files (`CROSS-MODALITY-EVIDENCE.md`, `FALSIFIER-5-EVIDENCE.md`, `REQUIREMENTS.md`, `WINDOWS.md`) exist on disk.
- Both tasks' full acceptance-criteria grep suites re-run: all eight checks return `1` (original 2026-09-09 dates intact, exactly one new dated section per evidence document, MODAL-05/MACH-02/MACH-03 rows each in exactly one state).
- `tests/evidence/test_cross_modality_record.py tests/evidence/test_falsifier5_record.py`: 22 passed.
- `bundle@v1` digest re-verified intact (`v1-intact`).
