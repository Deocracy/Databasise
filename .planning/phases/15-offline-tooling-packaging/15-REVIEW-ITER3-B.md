---
phase: 15-offline-tooling-packaging
lane: B
iteration: 3
reviewed: 2026-10-21T00:00:00Z
depth: deep
scope: fix commits 7806e4e 13ecfa8 2d3138b (B-ITER2-WR-01..03), against 15-REVIEW-ITER2-B.md and 15-REVIEW-FIX.md "Iteration 2 — Lane B"
files_reviewed: 6
files_reviewed_list:
  - databasise/eval/aa_run.py
  - databasise/seam/engine.py
  - databasise/eval/bundle.py
  - databasise/eval/remint.py
  - databasise/seam/floors_store.py
  - databasise/tests/eval/test_review_fix_15_iter2_lane_b.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 15: Code Review Iteration 3, Lane B

**Reviewed:** 2026-10-21
**Depth:** deep. I traced the fixes into `seam/refusals.py` (`ForeignEngineRefusalError`), `seam/floors_store.py` (read paths), `eval/remint.py` (`main`'s refusal `try`), `cli.offline_refusals`, the committed `judge-prompt-v1.txt` and `docs/gui/API-INVENTORY.md`. I ran the verdict parser against 13 sample replies using a fake client. The new test file passes (15 passed). Nothing ran with `--spend` or `-m live`.
**Status:** issues_found

## Summary

All three iteration-2 findings are fixed in code. None of the fixes introduces a correctness bug. None breaks D-03: every new refusal is a class already in `cli.offline_refusals` (`cli.py:58`, `:80`) or a `SeamRefusalError`, so each exits 1 with one line, and REST and MCP map them. None breaks D-04: `mint_bundle` is reached only after the `--spend` branch in `remint.main` (`remint.py:156-171`), and `promote` is not a CLI. None contradicts D-13: no new refusal class is added, the existing `StoreFault` is reused, and no `ledger.db` is created on the stage-1 path. Nor does any contradict D-14.

The fixer's not-adopted reason for WR-01 holds. The review's line-leading rule would have scored `"CORRECT. Actually it is INCORRECT."` as CORRECT, and the current parser refuses it (confirmed). One Warning remains. None of the three commits updated the GUI contract document (`docs/gui/API-INVENTORY.md`), which B-WR-08 had brought up to date. The document now misstates promote's refusals, remint's refusals and the verdict rule.

| Finding | Verdict | Evidence |
|---|---|---|
| B-ITER2-WR-01 | Fixed | `aa_run.py:140`, `:378-385`. Confirmed with the committed prompt: PARTIAL followed by its own definition scores 0.5 (also with `-` in place of `—`, and with line breaks inside the definition). The echoed three-option list, `"CORRECT. Actually it is INCORRECT."`, and own-definition followed by `INCORRECT` or `Not correct.` are all refused. A truncated or paraphrased definition is still refused, which is acceptable because the prompt says "Respond with exactly one of the following verdicts, and nothing else". |
| B-ITER2-WR-02 | Fixed | `engine.py:2386-2390` (stage 2) and `:2471-2477` (stage 1) wrap `lookup`/`any_floor` in `sqlite3.Error` and raise `_foreign_fault("promote", exc, failure_class="StoreFault")`. That is a `ForeignEngineRefusalError` (`refusals.py:810`), which REST answers with 502. `sqlite3` is imported (`engine.py:190`). The self-raised `OperationalError` at `floors_store.py:81` and a `DatabaseError` ("not a database") are both covered. |
| B-ITER2-WR-03 | Fixed | `bundle.py:467-472`. The check runs on the fresh-mint path only, after the dedup return (`:450-452`) and before `_write_version` (`:502`), so a refusal writes nothing. `open_sealed` calls `_write_version` directly (`:603`), so the check does not block it. `_find_version_by_content_hash` (`:301-307`) already loads every version, so the loop adds no new failure mode. |

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: API-INVENTORY was not updated for any of the three fixes, so the GUI contract misstates promote, remint and the verdict rule

**File:** `docs/gui/API-INVENTORY.md:586`, `:867`, `:868`, `:869`
**Issue:** B-WR-08 rewrote these rows to "state the current code". The three iteration-2 commits change that code but touch only source and the new test file (`git show --stat 7806e4e 13ecfa8 2d3138b`). The document is now wrong in four places:
- `:586`, the promote **Refusals** paragraph. It still lists only `GateNotCalibratedError` for the floors stages, and gives only one non-422 status: "500: `sqlite3.OperationalError` under ledger write contention". Since 13ecfa8, a `floors.db` fault in stage 1 or stage 2 answers 502 `ForeignEngineRefusalError {operation: "promote", failure_class: "StoreFault"}`. A GUI written against this paragraph will not expect a 502 from `/promote` with `promote-next`/`promote-now`.
- `:868`, the `eval.remint` row. It says the only sealed refusal is "a mint whose unchanged input matches a version whose sealed partition was opened". Since 2d3138b, a fresh mint (changed judge, prompt, corpus or settings) whose sealed split shares an id with an opened version is also refused as `SealedPartitionOpenedError`, exit 1.
- `:869`, the `eval.bundle` row. It does not mention the new `mint_bundle` refusal.
- `:867`, the `eval.aa_run` row. It says the reply must "name no second one, or it is refused". Since 7806e4e, a verdict followed by its own option-line definition parses, even though PARTIAL's definition contains "correct".

**Fix:** Update these four places:
- `:586`: add "502 `ForeignEngineRefusalError {operation: "promote", failure_class: "StoreFault"}` when `floors.db` cannot be read in stage 1 or stage 2 (never read as no floor)".
- `:868`/`:869`: add "a fresh mint whose sealed split holds a question id that an opened version's sealed split holds is refused the same way (splits depend on the id alone)".
- `:867`: add "a verdict followed by its own definition from the prompt's option list parses".

## Info

### IN-01: A verdict followed by a different verdict's definition still scores as the leading verdict

**File:** `databasise/eval/aa_run.py:378-385`
**Issue:** Confirmed: `"CORRECT — the candidate answer is factually correct but incomplete relative to the gold answer."` (CORRECT followed by PARTIAL's definition) scores 1.0. The fixer disclosed this, and the earlier parser behaved the same way. It is a wrong score, not a refusal, but the prompt forbids extra text, and a judge would rarely produce this reply.
**Fix:** Inside the same loop, also refuse when the definition of a different verdict appears in `text_upper`. This is a one-line `elif ... in text_upper: raise UnparseableJudgeVerdictError(result.text)`.

### IN-02: The fresh-mint refusal text does not give the only remedy

**File:** `databasise/eval/bundle.py:119-123`, `:471-472`
**Issue:** On the new path the error names the prior opened version and says "a sealed bundle needs sealed question ids that no opened version holds". Because `_assign_split` depends only on the id (`:316-322`), the only remedy is to remove or re-id the opened sealed questions in the corpus snapshot. Without that, every future mint is refused after a judge change, including the one a judge-model update forces. The message is accurate, but it does not tell the operator what to do.
**Fix:** Add "(remove or re-id those questions in the corpus snapshot)" to the message.

### IN-03: One refused-case test does not exercise the rule it names

**File:** `databasise/tests/eval/test_review_fix_15_iter2_lane_b.py:56`
**Issue:** `"PARTIAL — ...factually correct but incomplete. Actually INCORRECT."` truncates the definition, so it is refused because of the leftover "CORRECT", whether or not "Actually INCORRECT" is present. The "full own-definition, then a second verdict" case is not pinned. I checked it by hand and it is refused.
**Fix:** Add the full-definition variant ending in `" INCORRECT"` to the refused parametrize list.

### IN-04: The ITER2-B Info items IN-01 to IN-03 are still open (out of scope by the fix log)

**File:** `databasise/eval/bundle.py:105` ("repair or remove that line"); `databasise/eval/aa_run.py:89`, `:561`, `:571` (private `_verify_cache_bypassed` import); `databasise/seam/floors_store.py:9` (docstring names only `record` as the creator).
**Fix:** As given in 15-REVIEW-ITER2-B.md.

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
