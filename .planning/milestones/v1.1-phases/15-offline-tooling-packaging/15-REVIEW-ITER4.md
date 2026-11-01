---
phase: 15-offline-tooling-packaging
iteration: 4
reviewed: 2026-10-21T00:00:00Z
depth: standard
scope: iteration-3 fix commits 057da4a 5c5a1d6 17ce530 afdf521, against 15-REVIEW-ITER3-A.md WR-01, 15-REVIEW-ITER3-B.md WR-01, 15-REVIEW-ITER3-C.md WR-01 and WR-02, and 15-REVIEW-FIX.md "## Iteration 3"
files_reviewed: 4
files_reviewed_list:
  - databasise/parity/import_index.py
  - docs/gui/API-INVENTORY.md
  - databasise/evidence/parity_report.py
  - databasise/evidence/falsifier2.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 15: Code Review Report, Iteration 4

**Reviewed:** 2026-10-21
**Depth:** standard. I read every product diff and the code around it at HEAD. I traced `_arm_state`, `_inconclusive_causes`, `_arm_degraded` and `_arm_excursion_summary` in `parity_report.py`; `load_wiring`, `evaluate_wiring`, `enumerate_boundaries` and `main` in `falsifier2.py`; the `StoreFault` raises in `seam/engine.py` (`:2390`, `:2475`) and the REST 502 mapping in `seam/rest.py:153-154`; and the `mint_bundle` refusal at `eval/bundle.py:472`.
**Files Reviewed:** 4
**Status:** issues_found

Tests run: `tests/parity`, `tests/evidence`, `test_docstring_currency.py` and `test_cli_refusals.py` gave 437 passed and 3 deselected. This matches the fix log. I also ran two probes. Both used temp copies of `parity_results/` and `wirings/` in the session scratchpad, with the module paths retargeted. A fresh `parity_report.render_markdown()` is byte-identical to the committed `PARITY-EVIDENCE.md`. I read no test file. No CLI ran with `--spend`, no `-m live` test ran, and I read no env file.

## Summary

All four in-scope findings are fixed. No fix breaks D-03 or D-04, and none contradicts 15-CONTEXT D-01 to D-24. Each new refusal is a class that already maps to one stderr line and exit 1, or to a `refused` result. No fix adds a lock, a write or a provider call.

Each code fix leaves one sibling case of the same defect:
- The parity Verdict line still says a `mixed` arm "completed" on its no-retrieval branch (WR-01).
- A knob whose `between` or `rationale` is not a string still escapes `falsifier2.main` as a traceback (WR-02).

| Finding | Verdict | Evidence |
|---|---|---|
| ITER3-A-WR-01 | fixed | `import_index.py:678` catches `sqlite3.DatabaseError`, which is the parent class of `OperationalError`. It returns `refused` with a `precondition` violation (`:679-683`) and writes nothing (D-04, D-06). `import_index.main` turns `refused` into one `ImportPreconditionError` stderr line and exit 1 (D-03). See IN-01. |
| ITER3-B-WR-01 | fixed | `API-INVENTORY.md:586` now states the 502 `ForeignEngineRefusalError {operation: "promote", failure_class: "StoreFault"}` for stages 1 and 2, which matches `engine.py:2390` and `:2475` and `rest.py:154`. Rows `:868` and `:869` state the fresh-mint `SealedPartitionOpenedError`, which matches `bundle.py:467-472`. Row `:867` states the own-definition rule. No other `docs/` file names `floors.db` or `SealedPartitionOpenedError`. The MCP `promote` row (`:678`) is a list of examples, not a complete list, so it does not contradict the change. |
| ITER3-C-WR-01 | fixed for the three named branches; a fourth branch remains (WR-01) | `parity_report.py:1578-1616`. Probe 1 set hybrid q2 to D-07 inconclusive and q1 to clean. The output was "`hybrid`'s completed record(s) measured ... an exact retrieval-level agreement on those records only, not for the arm. Its other record(s) or storage audit did not complete: `hybrid`/`q2`: ...". Probe 2 set the storage audit alone to inconclusive. The excursion branch then carried the scope clause. The opening at `:1645` reads "for each arm's completed records". Fully completed arms render unchanged (D-16). |
| ITER3-C-WR-02 | fixed for the four reported cases; a sibling case remains (WR-02) | `falsifier2.py:133-139` and `:442-444`. Probes on w2: `[]` and non-UTF-8 bytes each gave `MalformedWiringDocumentError`, and `boundary_knobs: 5` and `null` each gave `MalformedBoundaryKnobError`. All four printed one stderr line and returned 1 (D-03). A `nodes` value that is not an object returns 1 as a validator violation, with no traceback. |

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: A `mixed` arm whose completed records carry no diff is still called "completed", with no scope clause (residual of ITER3-C-WR-01)

**File:** `databasise/evidence/parity_report.py:1568-1572`
**Issue:** The `if not measured_fields` branch returns before the new `unfinished` and `scope` logic at `:1577-1589`. For a `mixed` arm it therefore still prints "`<arm>` completed with no retrieval to compare ...". It also leaves out the arm's unfinished causes.

This branch is reachable. `run_comparison.py:648-656` writes `chunk_diff`, `entity_diff` and `relation_diff` as `None` for every `bypass` record, because bypass is a single `generate` node with no retrieval. Suppose one bypass query degrades into a D-07 `inconclusive` record, or the bypass storage audit is inconclusive. The Verdict section then says bypass "completed", under an opening that says the lines speak only for completed records.

Probe 3 reproduced this. It made the hybrid records diff-less with q2 inconclusive, and the output was "`hybrid` completed with no retrieval to compare (it has no chunk, entity or relation diff), so there is no retrieval-level outcome to state for it." This is the same D-16 break that ITER3-C-WR-01 named. Commit 17ce530's subject says "never 'completed ...'", but this branch still says it.
**Fix:** Compute `unfinished` and `scope` before the `measured_fields` check, and use them in this branch too:
```python
if not measured_fields:
    subject = f"`{arm}`'s completed record(s) have" if unfinished else f"`{arm}` completed with"
    return (
        f"{subject} no retrieval to compare (no chunk, entity or relation diff), so there is "
        f"no retrieval-level outcome to state for it.{scope}\n"
    )
```
Add a test that combines a diff-less completed record with an inconclusive sibling record.

### WR-02: A boundary knob whose `between` or `rationale` is not a string still escapes `falsifier2.main` as a traceback (residual of ITER3-C-WR-02, D-03)

**File:** `databasise/evidence/falsifier2.py:451-458`, `:529-530`
**Issue:** The knob check rejects only `None` values for `between` and `rationale`. A non-string value passes the check and reaches `_escape_cell(row.between)` at `:529`, which calls `.replace`. Probe: `boundary_knobs: [{"between": 5, "rationale": "x"}]` in w2 made `falsifier2.main([])` raise `AttributeError: 'int' object has no attribute 'replace'` as a traceback. It did not print one `ClassName: message` line. Like ITER3-C-WR-02, this is a malformed named-wiring document. `MalformedBoundaryKnobError` is already in `main`'s named tuple.
**Fix:** In the knob loop, after the `None` check, add:
```python
if not isinstance(between, str) or not isinstance(rationale, str):
    raise MalformedBoundaryKnobError(
        f"{evidence.stem}'s boundary_knobs[{i}] 'between' and 'rationale' must be strings"
    )
```
Also check `boundary_id` when it is present, because `:529` renders it without `_escape_cell` but still interpolates it. Add the `between: 5` case to the lane C knob test.

## Info

### IN-01: The widened catch also reports sqlite programming errors as an operator precondition

**File:** `databasise/parity/import_index.py:678`
**Issue:** `sqlite3.DatabaseError` is also the parent of `ProgrammingError`, `IntegrityError`, `DataError` and `NotSupportedError`. A code defect in `list_kv_prefix`, such as malformed SQL, would print "v2 text_chunks KV is unreadable read-only" and look like store damage. A read-only listing does not raise these classes on a real store, so the risk is only a misleading diagnosis.
**Fix:** Add `except sqlite3.ProgrammingError: raise` before the `except sqlite3.DatabaseError` branch.

### IN-02: The `falsifier2.main` docstring still names only "not valid JSON"

**File:** `databasise/evidence/falsifier2.py:672-677`
**Issue:** The docstring lists "a wiring document that is not valid JSON". After afdf521 the class also covers non-UTF-8 bytes and a top level that is not an object, and `MalformedBoundaryKnobError` also covers a `boundary_knobs` value that is not a list. The class docstring at `:124-125` was updated, but this one was not.
**Fix:** Change it to "a wiring document that is not a UTF-8 JSON object".

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer), iteration 4_
_Depth: standard_
_Not checked: the content of the new and edited test files (I ran them but did not read them); live or `--spend` behaviour; the parity sections other than Verdict (design-deviation, per-arm, spot-check) for a mixed arm whose records carry no diff; ITER3 Info items and the owner-gated A-WR-02, which are out of scope._
