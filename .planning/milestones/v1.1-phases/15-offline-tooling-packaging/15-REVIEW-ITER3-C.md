---
phase: 15-offline-tooling-packaging
lane: C
iteration: 3
reviewed: 2026-10-21T00:00:00Z
depth: deep
fix_commits: [4a57dca, e6e381f]
files_reviewed: 2
files_reviewed_list:
  - databasise/evidence/parity_report.py
  - databasise/evidence/falsifier2.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 15: Code Review Report, Lane C, Iteration 3

**Depth:** deep
**Status:** issues_found

## Summary

This review re-checked the two lane C iteration-2 findings against commits 4a57dca and e6e381f. The probes ran from scratch scripts that wrote only to the session scratchpad, using temp copies of `parity_results/`, `human_findings.json` and `wirings/`, with the module paths retargeted. `databasise/tests/evidence` passes (125 passed). A fresh `render_markdown()` for both `PARITY-EVIDENCE.md` and `FALSIFIER-2-EVIDENCE.md` is byte-identical to the committed file. Nothing ran with `--spend` or `-m live`, no env file was read, and no source or test file changed.

Both findings are fixed as scoped. Neither fix changes D-04: neither touched path spends, locks, or writes outside the existing `write_committed_documents` call. Neither fix contradicts 15-CONTEXT.md D-03 or D-16. Two Warnings remain. The fixer's reason for adding no degraded-inconclusive signal ("no section needs one") is wrong for the Verdict section (WR-01). WR-01's iteration-2 fix catches `JSONDecodeError` only, so other malformed wiring documents still escape as tracebacks (WR-02).

| Finding | Verdict | Evidence |
|---|---|---|
| C-ITER2-CR-01 | fixed | `parity_report.py:245` filters `status != "completed"` again, and `:247` keeps the `or {}` null guard. The three scenarios from iteration 2 no longer reproduce: the verdict line states q1's excursion, the design-deviation section states the measured excursion, and the spot-check names `hybrid` once and does not cite `original_arm_result.answer`. The covering test is `test_a_degraded_inconclusive_record_does_not_rewrite_the_arm_s_completed_excursion`. Residual: WR-01. |
| C-ITER2-WR-01 | fixed for `JSONDecodeError` | `falsifier2.py:123-134` defines `MalformedWiringDocumentError(ValueError)`, and `:674-679` adds it to the named tuple. No bare `ValueError` is caught. Probe: `{not json` in w1 or w2 returns 1 with one stderr line and writes nothing. Residual: WR-02. The recorded w3 import-time residual is IN-01. |

## Warnings

### WR-01: The Verdict section says an arm "completed ... with no decomposed-run degradation" when one of its queries degraded into an inconclusive record

**File:** `databasise/evidence/parity_report.py:1592`, `:1600` (`_arm_verdict_line`); `:1626` and `:1641` (`_render_verdict`)

**Issue:** `_render_verdict()` calls `_arm_verdict_line()` for every arm, including an arm whose state is `mixed`. That function filters to completed records, then uses `_arm_degraded()` (now completed-only) to choose its wording. Under D-07, an arm can hold a clean completed q1 next to a degraded `inconclusive` q2. For that arm the Verdict section prints the following. The probe set hybrid q2 to D-07 degraded-inconclusive and gave q1 empty diffs:

> **Mixed run state ...** An arm that did not complete has no retrieval-level outcome at all; the lines below state an outcome only for the arms that completed.
>
> `hybrid` completed and measured `chunk_diff`/`entity_diff`/`relation_diff` `symmetric_difference=[]` on `q1`, with no decomposed-run degradation — a validated exact retrieval-level agreement.

Two statements here are false:

- The opening says lines are given only for arms that completed, yet hybrid (state `mixed`) gets a line.
- That line says hybrid "completed" with "no decomposed-run degradation", but hybrid's q2 degraded.

The excursion branch at `:1592` has the same "completed with no decomposed-run degradation" wording. This breaks D-16 ("render only states they read") in the committed parity evidence. The path is reachable on the next `--spend` re-run whenever one query of an arm degrades.

This is not a regression from 4a57dca: the wording behaved the same way before 72cf2c1. But the iteration-2 review said to keep a degraded-inconclusive signal for text about unfinished arms. The fixer declined it because "an arm with an inconclusive record is already named as unfinished by `_arm_state`", and that reason does not hold here: `_render_verdict` never checks `_arm_state` before it prints an arm's line.

**Fix:** In `_arm_verdict_line`, scope the claim when the arm is not fully completed, and leave `_arm_degraded` completed-only:
```python
unfinished = [r for r in load_comparison(arm) if r.get("status") != "completed"]
scope = (
    f" (its other record(s) did not complete: {_inconclusive_causes((arm,))})"
    if unfinished or _arm_state(arm) != "completed" else ""
)
```
Append `scope` to all three branches, and say "its completed records ran with no decomposed-run degradation" instead of "no decomposed-run degradation". Also reword the `:1626` opening to "the lines below state an outcome only for each arm's completed records". Add a test with the probe's data that asserts "a validated exact retrieval-level agreement" does not appear without the scope clause.

### WR-02: Other malformed wiring documents still escape falsifier2.main as tracebacks (D-03)

**File:** `databasise/evidence/falsifier2.py:132-134` (`load_wiring`), `:383` (`doc.get("wiring_id", ...)`), `:437` (`enumerate(doc.get("boundary_knobs", []))`), `:674-679`

**Issue:** The fix converts only `json.JSONDecodeError`. These probes each replaced `w2-codebase-memory-mcp.json` in a temp copy and called `falsifier2.main([])`:

| w2 content | Result |
|---|---|
| `[]` (valid JSON, not an object) | `AttributeError: 'list' object has no attribute 'get'` traceback, from `:383` |
| `"x"` | `AttributeError` traceback |
| `"boundary_knobs": 5` | `TypeError: 'int' object is not iterable` traceback, from `:437` |
| bytes that are not valid UTF-8 | `UnicodeDecodeError` traceback, from `read_text` at `:132` (a `ValueError`, but not `JSONDecodeError`) |

None of these prints the D-03 single `ClassName: message` line. `evaluate_wiring` already guards `raw_nodes` against a non-dict document (`:340`), so the author expected non-object documents. Only `load_wiring` and the knob loop lack that guard. The new class's own docstring ("not valid JSON") and the iteration-2 finding cover this whole category of malformed named-wiring document.

**Fix:** Make `load_wiring` reject anything that is not a JSON object, and have the knob loop reject a non-list:
```python
try:
    doc = json.loads(path.read_text(encoding="utf-8"))
except (json.JSONDecodeError, UnicodeDecodeError) as exc:
    raise MalformedWiringDocumentError(f"{path}: {exc}") from exc
if not isinstance(doc, dict):
    raise MalformedWiringDocumentError(f"{path}: top level must be a JSON object")
return doc
```
At `:437`, read `knobs = doc.get("boundary_knobs", [])`, and raise `MalformedBoundaryKnobError` when `not isinstance(knobs, list)`. Add the `[]` and invalid-UTF-8 cases to `test_falsifier2_refuses_a_named_wiring_that_is_not_json_by_name`.

## Info

### IN-01: A malformed w3 still fails at import time, outside main()

**File:** `databasise/evidence/falsifier2.py:198`, `:315` (`PROBES` built at module load)
**Issue:** The fixer's recorded residual is accurate: `python -m databasise.evidence.falsifier2` with a malformed w3 raises `MalformedWiringDocumentError` while the module is being imported, so it prints a traceback instead of one line. This was accepted in iterations 1 and 2 because the documents are committed source-checkout files. That reason is sound, but it still conflicts with D-03.
**Fix:** If this is ever addressed, build `PROBES` lazily (a cached function) so that `main()` catches the error.

### IN-02: The per-arm degradation note dereferences `decomposed_run_record` without a null guard

**File:** `databasise/evidence/parity_report.py:1250` (`record.get("decomposed_run_record", {}).get("degraded")`)
**Issue:** A completed record that holds `"decomposed_run_record": null` raises `AttributeError`. `_arm_degraded` (`:247`) already uses `or {}` for the same field. This predates this fix and is not reachable from current `run_comparison` output.
**Fix:** `(record.get("decomposed_run_record") or {}).get("degraded")`.

### IN-03: Legacy completed-and-degraded records still hide an excursion in the same arm

**File:** `databasise/evidence/parity_report.py:1575-1589`
**Issue:** The degraded branch runs before the excursion branch, so suppose one completed record is degraded (the pre-D-07 shape) and another completed record in the same arm has a non-empty diff. The line then states `symmetric_difference=[]` for every query. After D-07 this arises only from legacy committed records, and the current committed records do not contain it (the render is byte-identical).
**Fix:** Test `arm_excursions` together with `degraded`, or render both clauses.

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer), lane C iteration 3_
_Depth: deep_
