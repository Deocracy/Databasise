---
phase: 15-offline-tooling-packaging
lane: C
iteration: 2
reviewed: 2026-10-21T00:00:00Z
depth: deep
fix_commits: [e808a88, 3bf4704, 72cf2c1, 2c3ec8e, a5a6662]
files_reviewed: 6
files_reviewed_list:
  - databasise/evidence/falsifier2.py
  - databasise/evidence/parity_report.py
  - databasise/evidence/f07_report.py
  - databasise/cli.py
  - docs/gui/CODEBASE-MAP.md
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
findings:
  critical: 1
  warning: 1
  info: 3
  total: 5
status: issues_found
---

# Phase 15: Code Review Report, Lane C, Iteration 2

**Depth:** deep
**Status:** issues_found

## Summary

This review re-checked the seven lane C findings against the fix commits e808a88, 3bf4704, 72cf2c1, 2c3ec8e and a5a6662. The checks ran from scratch scripts that wrote only to the session scratchpad: temp copies of `wirings/`, with `WIRINGS_DIR` and `EVIDENCE_PATH` retargeted, and monkeypatched `load_comparison` and `load_storage_audit`. `tests/evidence` passes (122 passed). Nothing ran with `--spend` or `-m live`, no env file was read, and the working tree is unchanged.

Six of the seven findings are fixed as claimed. C-WR-02 is fixed in the prose it targeted, but it widened `_arm_degraded()` to read inconclusive records without updating that function's callers. After this change, three completed-record prose sites state facts that the records contradict (CR-01 below). One D-03 gap remains in falsifier2 (WR-01). No fix changes D-04: none of the touched paths spends, locks, or writes without the renderer's existing write. No fix contradicts D-01, D-03 or D-16 in 15-CONTEXT.md.

| Finding | Verdict | Evidence |
|---|---|---|
| C-CR-01 | fixed | `falsifier2.py:541-543` `failing_wirings()`; verdict at `:619-638`; exit code at `:667`; violations rendered at `:480-490`; uncomputable guard at `:333-344` and `:394-400`. Probe: adding `writes_artifact` to a w2 node, a self-declared `effective_depth`, and an unknown component each return 1 and render "Falsifier 2 fired". None of them raises `KeyError`. Not firing on cycles is sound: `validator/parse.py:322` treats a cycle as data, and `depth.py` handles cycles through SCC condensation. |
| C-WR-01 | fixed | `parity_report.py:1733-1741` runs `check_results()`, renders both texts, then writes. Named refusals are mapped at `:1703-1710`, and `notes` is read at `:954`. Residual: Info IN-01. |
| C-WR-02 | fixed, but introduced CR-01 | The fixed precondition text is gone (`:1131-1137`, `:1388-1401`, `:1604-1616`). `_inconclusive_causes()` is at `:215-230`. The `_arm_degraded` widening at `:243` is the regression. |
| C-WR-03 | fixed | `cli.py` `write_committed_documents` checks every target before it writes any. `f07_report.py:336-341`, `falsifier2.py:660-664` and `parity_report.py:1741` all route through it. The residual (falsifier2 cannot be imported from a wheel) is recorded and acceptable, because the documents are source-checkout records. |
| C-WR-04 | fixed for the named cases | Named classes: `f07_report.UnreasonedMutableStoreError` (still a `ValueError`, as D-16 requires) and `falsifier2.MalformedBoundaryKnobError`. Probe: `boundary_knobs: ["x"]` returns 1 with one stderr line and writes nothing. Remaining gap: WR-01. |
| C-WR-05 | fixed | `CODEBASE-MAP.md:431`. `databasise/.venv/bin/python -m databasise.evidence.parity_report --help` runs from the repository root. |
| C-WR-06 | fixed | `CODEBASE-MAP.md:202` and the `:451-452` rows are split and now match `f07_report.main()`. |

## Critical Issues

### CR-01: Widening `_arm_degraded()` to inconclusive records makes completed-record prose state false diffs, and hides a real excursion

**File:** `databasise/evidence/parity_report.py:243` (introduced by 72cf2c1). Affected callers: `:701` (`_render_known_design_deviation`), `:912` with `:918-926` (`_render_spotcheck_arm_guidance`), and `:1572-1585` (`_arm_verdict_line`).

**Issue:** D-07 makes `run_comparison` write one record per query (`parity/run_comparison.py:611-618`). A degraded query becomes `status="inconclusive"` with `original_arm_result=None` (`:524`) and no comparison number. A completed record is therefore never degraded after D-07, and one arm can hold completed records next to a degraded inconclusive record.

`_arm_degraded()` now returns True for such an arm. All three callers assume that the degraded record is the completed record they describe, so they misstate what the completed records hold.

**Confirmed scenario 1 (verdict line):** hybrid has q1 completed with `entity_diff.symmetric_difference=["e1","e2"]` and `chunk_diff=["c9"]`, plus q2 inconclusive and degraded. `_arm_verdict_line("hybrid")` returns:

> `hybrid` completed and measured `chunk_diff`/`entity_diff`/`relation_diff` `symmetric_difference=[]` on `q1` ... The measured zero is both sides retrieving nothing

q1's real excursion is never stated, because the degraded branch runs before the `arm_excursions` branch.

**Confirmed scenario 2 (known design deviation):** hybrid, local and global each have a clean completed q1 with empty diffs, and only hybrid also has a degraded q2. The section then says "the same three arms' decomposed runs degraded ... the zero reflects both the decomposed and original arm retrieving nothing on this run". That throws away a valid clean measurement on local and global.

**Confirmed scenario 3 (spot-check):** for the same hybrid arm, the guidance says "v1's own answer for those query/arm pairs is in `original_arm_result.answer`". That field is `None` on a D-07 inconclusive record. The guidance also names `hybrid` twice (once as blocked, once as unfinished), and it points to "the per-arm degradation notes above". That note filters `status == "completed"` (`:1243-1247`), so it never renders for this case.

This breaks D-16 ("render only states they read") in the committed parity evidence document. It is reachable on the owner's next `--spend` re-run whenever one query of an arm degrades.

**Fix:** Revert the status widening and keep the null guard. The inconclusive cause is already rendered per record, through the reason column and `_inconclusive_causes()`:
```python
for record in load_comparison(arm):
    if record.get("status") != "completed":
        continue
    drr = record.get("decomposed_run_record") or {}
```
If a degraded-inconclusive signal is still wanted, add a separate helper. Use it only where the text describes an unfinished arm, never in `_arm_verdict_line`, `_render_known_design_deviation` or the `blocked` spot-check clause. Add a test for one arm that holds a completed record with a non-empty diff next to a degraded inconclusive record.

## Warnings

### WR-01: A malformed named-wiring JSON still escapes falsifier2.main as a traceback (D-03)

**File:** `databasise/evidence/falsifier2.py:123-125` (`load_wiring`) and `:660-664` (the `except` tuple)

**Issue:** `main()` maps `MalformedBoundaryKnobError`, `InstalledPackageWriteError` and `OSError` only. When `w1` or `w2` holds invalid JSON, `json.JSONDecodeError` (a `ValueError`) propagates out of `render_markdown()`. Probe: `RAISED JSONDecodeError`, a multi-line traceback, no `ClassName: message` line. D-03 requires one stderr line for a refusal. `w3` fails earlier, at import time inside `PROBES`, which is the residual the fixer already recorded.

**Fix:** In `load_wiring`, raise a named `MalformedWiringDocumentError(ValueError)` from `json.JSONDecodeError`, and add it to the `except` tuple at `:663`. Do not catch bare `ValueError` (D-03, aa_run rule).

## Info

### IN-01: `write_committed_documents` can still leave one of two documents written

**File:** `databasise/cli.py` (`write_committed_documents`, second loop); `parity_report.py:1741`
**Issue:** The installed-package check runs on every target first, but the writes run one after another. An `OSError` on `EVIDENCE_PATH` (for example, a full disk or a read-only file) after `DEVIATIONS_PATH` was written leaves the two documents out of sync. The 3bf4704 subject ("writes neither document on a refusal") is true only for refusals raised before the writes.
**Fix:** Write each document to `path.with_suffix(".tmp")` first, then `os.replace` each one, or narrow the claim.

### IN-02: `check_results()` raises on a non-list comparison file instead of refusing

**File:** `databasise/evidence/parity_report.py:354-367`
**Issue:** The render path now goes through `check_results()`, so a comparison file holding an object or a list of non-objects raises `AttributeError` or `TypeError` at `record.get(...)` or `k not in record`. Neither is mapped. This existed before the fix, but 3bf4704 makes this the render path's first step.
**Fix:** Add `if not isinstance(records, list) or not all(isinstance(r, dict) for r in records)` and treat it as a violation.

### IN-03: The CODEBASE-MAP evidence rows cite line ranges that no longer exist

**File:** `docs/gui/CODEBASE-MAP.md:200-201`
**Issue:** The falsifier2 row cites `(558-561)`, but `main()` is now at `falsifier2.py:655`. The parity_report row cites `(1398-1433)`, but `main()` and `_run()` are now at `parity_report.py:1693-1745`.
**Fix:** Cite `main()` by name, as the f07_report row does.

---

_Reviewer: Claude (gsd-code-reviewer), lane C iteration 2_
_Depth: deep_
