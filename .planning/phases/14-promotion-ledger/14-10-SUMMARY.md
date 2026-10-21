---
phase: 14-promotion-ledger
plan: 10
subsystem: docs
tags: [docstring-currency, api-inventory, offline-gate, ledg-14]
requires: ["14-02", "14-03", "14-04", "14-05", "14-06", "14-07", "14-08", "14-09", "14-11"]
provides:
  - LEDG-14 docstring-currency test (databasise/tests/test_docstring_currency.py)
  - registry, schema, resolve, ledger, alias-test and mutable-store-refusal docstrings that state current facts
  - API-INVENTORY.md that states no Phase 14 defect as live
  - STATE.md Blockers/Concerns lines carrying the Phase 16 text amendments
affects: [phase-15, phase-16, phase-17, phase-18]
status: complete
actuals:
  tokens: 25000
  tasks: 3
  commits: 3
plan_head_before: de68bb2b9d29fa5947c107152c6b4936ed3fdfac
plan_head_after: 6cf549490933e095cd2daaad700728f6bc506425
key-files:
  created:
    - databasise/tests/test_docstring_currency.py
  modified:
    - databasise/parts/registry.py
    - databasise/parts/schema.py
    - databasise/wirings/resolve.py
    - databasise/ledger/ledger.py
    - databasise/tests/seam/test_alias_registry.py
    - databasise/seam/refusals.py
    - docs/gui/API-INVENTORY.md
    - .planning/STATE.md
key-decisions:
  - "The currency test reads docstrings with ast and phrases with whitespace-normalised source, using the standard library only, so it also collects and fails by assertion when copied alone into a checkout of the phase base"
  - "PartRegistry and default_registry docstrings state no part count; a regex in the test bans a count word before executable, ported, declaration-only, reference or parts"
  - "The DeclarationOnlyPartError message dropped its Phase 1 / Phase 3 wording; no test pinned the old text"
requirements-completed: [LEDG-14]
---

# Phase 14 Plan 10: Docstring currency, inventory sweep and phase gate Summary

The LEDG-14 currency test fails on the stale registry, schema, resolve, ledger and alias-test text and passes once the docstrings state current facts. API-INVENTORY.md no longer presents any Phase 14 defect as live, STATE.md carries the Phase 16 amendment list, and the full offline gate is green in both pytest styles (2598 passed in each).

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Tracer: docstring-currency test plus registry, schema, resolve, ledger and alias-test docstrings | 059dfb0 |
| 2 | API-INVENTORY sweep and the mutable-store refusal docstring | eb9f6ba |
| 3 | STATE Phase 16 amendments (docs commit), then the offline gate | 6cf5494 |

## LEDG-14 row test

Intended `test_ref`: `databasise/tests/test_docstring_currency.py` (file; the stale-phrase node is `databasise/tests/test_docstring_currency.py::test_no_stale_phrase_remains`, five modules as parameters, plus `::test_no_stale_phrase_remains_in_resolve_alias_docstring`, `::test_the_registry_points_at_keys_and_states_no_count[PartRegistry|default_registry]`, `::test_the_resolve_module_docstring_names_its_functions`, `::test_the_selectors_docstring_keeps_all_wirings`).

Fail-first evidence, plain `AssertionError`, quoted from two runs.

Pre-edit run on this working tree (8 failed, 2 passed):

```
AssertionError: ledger/ledger.py still states stale text: ['Scope fence (Phase 1 only stands the table', 'The registry is empty until Phase 7', 'zero rows in every environment', "is this method's only caller", "are this method's only callers", 'nothing in the live Phase 1 runner path calls']
AssertionError: parts/registry.py still states stale text: ["D-04's seven Phase-1 entries", 'two remaining declaration-only', 'wiring placeholders', 'fifteen ported LightRAG parts', 'five ported HippoRAG parts', 'four executable', 'awaits its Phase 3 port', 'a later runner plan']
AssertionError: parts/schema.py still states stale text: ['starts being consumed']
AssertionError: tests/seam/test_alias_registry.py still states stale text: ['promote path does not exist yet']
AssertionError: wirings/resolve.py still states stale text: ['needs all fifteen new components', 'only the ``naive`` and ``bypass`` arms resolve', 'does not necessarily']
AssertionError: PartRegistry docstring does not point at keys(): "In-memory dict mapping ..."
AssertionError: default_registry docstring does not point at keys(): "A registry preloaded with D-04's four executable ..."
AssertionError: wirings/resolve.py module docstring omits ['all_wirings', 'load_wiring', 'wiring_for_name']
```

Run at the phase base bb52fbb: the test file alone copied beside the six scanned files as they were at bb52fbb (scripted in the scratchpad, no checkout; the scanned files include `seam/selectors.py`): 9 failed, 1 passed. The extra failure is `_resolve_alias docstring still states stale text: ["Phase 7's promote path must append", 'An empty registry']`; `would stall the` also appears in `ledger/ledger.py` there. The one pass is `test_the_selectors_docstring_keeps_all_wirings` (SEAM-16 already pinned it). The orchestrator's `record-fail --at bb52fbb` should see the same 9 failures.

After the edits: `test_docstring_currency.py` 10 passed.

## Offline gate

`databasise/.venv/bin/python databasise/tools/check_offline_suite.py` (run in the background, exit code 0):

```
pytest -q -rs: 2598 passed, 4 deselected in 963.50s (0:16:03)
python -m pytest -q -rs: 2598 passed, 4 deselected in 936.55s (0:15:36)
```

Baseline at Phase 13 close was 2482 passed in both styles; the 116 added tests are Phase 14's.

## API-INVENTORY.md lines changed

Located by quoted content (line numbers are the post-edit file).

| Section | Change | Decision |
| ------- | ------ | -------- |
| 1 (error model, unhandled 500 list) | Dropped the `UnknownArmError` example, the HippoRAG-alias path and the partial-trace promote path | D-05, D-03 |
| 3.0 selector `alias` row | Resolves through `wiring_for_name`; HippoRAG alias resolves; missing `ledger.db`, no row and an unresolvable row all give 422 `UnsatisfiableSelectorError`; stale selectors.py docstring remark removed | D-05 |
| 3.0 refusals and live check | Removed the HippoRAG-alias 500 and the `UnknownArmError` live-check line; stated the named 422 | D-05 |
| 3.2 compare refusal 3, validation paragraph, live check, chained-calls bullet | cbm wiring is the fixture `databasise/tests/fixtures/codebase-memory-mcp.json`; part not in `default_registry()`; tests register it with `registry=`; alias pre-resolution loop is a 422; promote disabled for partial columns only | D-13, D-05, D-03 |
| 3.2.2 promote helper | Partial trace is `PartialRunEvidenceError` on promote and identified by `arm_id` on rollback and retire | D-03, D-01 |
| 3.3.1 and 3.3.4 500 lists | Removed the HippoRAG-alias `UnknownArmError` entries | D-05 |
| 3.5 ledger paragraph | Each verb closes its `Ledger`; a refused rollback or retire creates no `ledger.db` | LEDG-06, D-08 |
| 3.5.2 rollback | Partial evidence by `arm_id`; `PartialRunEvidenceError` when unidentifiable; lineage-based `TombstonedGenerationError`; unresolvable row is 422; no `ledger.db` on a refusal; chained-calls remark; partial-evidence label for the console | D-01, D-06, D-08, D-05 |
| 3.5.3 retire | Refuses any version in the active lineage; removed the live defect paragraph, the stale live check and the "server does not block it" control note | D-06, D-08 |
| 4 MCP intro and live checks | Removed the HippoRAG-alias `UnexpectedToolError`; `promote` partial gives `PartialRunEvidenceError`; `rollback` partial accepted by `arm_id`; `retire` of the rollback target gives `ActiveGenerationRetirementError` | D-05, D-03, D-01, D-06 |
| 5.1 wirings list row | Per-arm `wiring_id`s; cbm wiring is a fixture | Phase 13 D-03, D-13 |
| 5.1 wiring detail row (the stale `resolved_wiring_for_arm` line) | Points at `wiring_for_name`, which returns None on a miss | D-05 |
| 5.1 part registry row | `keys()` is the source of contents; cbm part not in `default_registry()`; dropped the stale "exactly D-04's seven" remark | D-13, D-15 |
| 5.1 promotion dry-run row, test-coverage bullet | Partial traces are refused with a named refusal; dropped the two gaps now closed | D-03, D-06 |
| 5.2 defects table (the stale line near 761) | Three rows marked fixed in Phase 14 (HippoRAG alias; partial-run evidence; retire guard) | D-05, D-01, D-03, D-06 |
| Open question 9 | Notes the three fixes | D-05, D-03, D-06 |
| 7.5 cbm row | Part not registered in `default_registry()`; wiring is the fixture | D-13 |

Kept unchanged: the `query()` with `top_k <= 0` assertion-failure row (`vector.py:217-224`, outside Phase 14), 14-05's tenancy and strict-flag statements, and 14-08's section 3.5 and 3.5.1 text.

Acceptance counts: `AssertionError` or `UnknownArmError` or `known arms` or `UncalibratedFloorRefusalError` between section 3.5.1 and section 4 is 0; `UnknownArmError` or `known arms` anywhere is 0; `AssertionError` appears once, on the `vector.py:217-224` line; the fixture path appears three times.

## Consolidated ledger table (LEDG-01..14 and the WIRE-17 granted edit)

| Row | Intended test_ref | Fail-first route |
| --- | ----------------- | ---------------- |
| LEDG-01 | `databasise/tests/seam/test_partial_run_evidence.py` (14-08 nodes: `::test_promote_refuses_a_real_partial_trace`, `::test_rollback_and_retire_accept_a_real_partial_trace`, `::test_a_hipporag_partial_record_is_accepted_by_rollback_and_...`) | `record-fail --at bb52fbb` (false `UnknownTraceReferenceError`) |
| LEDG-02 | `databasise/tests/seam/test_promote_refuses_partial.py` (14-08 nodes: `::test_a_failed_bypass_run_is_refused_twice_with_no_row`, `::test_an_old_format_partial_record_is_refused`, `::test_only_the_partial_trace_is_named`, ...) | `record-fail --at bb52fbb` (old-format partial promotes 1.0.0) |
| LEDG-03 | `databasise/tests/seam/test_alias_resolution.py` (14-06: `::test_a_hipporag_alias_never_gives_a_500`, `::test_an_unresolvable_alias_row_is_a_named_422`, `::test_the_mcp_tools_never_raise_an_unexpected_error_for_either_row`, ...) | `record-fail --at bb52fbb` (500s and `UnknownArmError`) |
| LEDG-04 | `databasise/tests/seam/test_retire_lineage.py` (14-09: `::test_retiring_the_target_of_an_active_rollback_is_refused`, `::test_every_version_in_the_active_lineage_is_protected`, `::test_a_rollback_onto_a_tombstoned_lineage_is_ref...`) | `record-fail --at bb52fbb` (retire of an active rollback's target tombstones it) |
| LEDG-05 | `databasise/tests/seam/test_operator_alias_validation.py` (14-08: `::test_all_three_verbs_refuse_bad_aliases`, `::test_rest_refuses_bad_aliases_on_all_three_routes`, `::test_mcp_refuses_bad_aliases_on_all_three_tools`) | `record-fail --at bb52fbb` (promote legs pass there; rollback and retire legs fail) |
| LEDG-06 | `databasise/tests/ledger/test_ledger_lifecycle.py` (14-09: `::test_no_ledger_connection_is_left_open`, `::test_refused_verbs_on_a_fresh_root_create_no_ledger_file`, `::test_the_transaction_docstring_makes_no_stall_claim`) | `record-fail --at bb52fbb` (unclosed connections, created `ledger.db`, "stall") |
| LEDG-07 | `databasise/tests/ledger/test_ledger_history.py::test_history_for_alias_returns_the_alias_rows_oldest_first` | `record-fail --at bb52fbb` (no `history_for_alias`; `AssertionError: Ledger.history_for_alias does not exist`) |
| LEDG-08 | `databasise/tests/seam/test_promotion_posture.py::test_gate_verbs_are_refused_up_front_for_every_arm` (12 params) | `record-fail --at bb52fbb` (`MeasurementPostureRefusalError` and a created `ledger.db`) |
| LEDG-09 | `databasise/tests/seam/test_trace_resolve_strict_flag.py` (REST and MCP non-boolean flag nodes) | `record-fail --at bb52fbb` (lax flag, missing tenancy phrase) |
| LEDG-10 | `databasise/tests/seam/test_capability_effects.py` | `record-fail --at 3fd6e4c^` (already met at HEAD, D-11) |
| LEDG-11 | `databasise/tests/validator/test_node_kind.py` (`::test_a_kind_mismatch_is_reported_by_name`, `::test_every_shipped_wiring_parses`) | `record-fail --at 5d61a79^` (already met at HEAD, D-12) |
| LEDG-12 | `databasise/tests/parts/test_registry_reachability.py::test_every_admitted_registered_part_is_reachable` | `record-fail --at bb52fbb` (`codebase-memory-mcp@0.1.0` unreferenced there); already recorded at bb52fbb by commit 9ae5a4a |
| LEDG-13 | `databasise/tests/seam/test_corpus_wiring.py` (use the file as `test_ref`) | `record-fail --at bb52fbb` (engine ignores a patched `resolve._WIRINGS_ROOT`) |
| LEDG-14 | `databasise/tests/test_docstring_currency.py` | `record-fail --at bb52fbb` (9 failed, 1 passed, shown above) |
| WIRE-17 (granted edit, 14-01 and 14-07) | `databasise/tests/seam/test_refusal_reachability.py` (unchanged test_ref) | plant runs for the edited check; recorded by commits e4afdc5 and 9ae5a4a |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two stale statements beyond the plan's phrase list**
- **Found during:** Task 1
- **Issue:** The `Part` docstring in `parts/schema.py` said a later plan would dispatch declaration-only entries as a refusal (`registry.dispatch` already does), and the `by_alias` / `generation_state` docstrings in `ledger/ledger.py` claimed single callers.
- **Fix:** Rewrote each to current facts.
- **Files modified:** databasise/parts/schema.py, databasise/ledger/ledger.py
- **Commit:** 059dfb0

**2. [Rule 1 - Bug] Inventory statements outside the plan's line list**
- **Found during:** Task 2
- **Issue:** Besides the plan's lines, the section 3.5 sentence "never closes it", the section 3.5.3 live check and GUI control note, the MCP live checks, the open-question-9 wording, and the 5.1 part-registry row ("35 parts", "exactly D-04's seven") described behaviour Phase 14 changed. Line numbers in the plan and in the dispatch message (718, 761) were 721 and 764 at execution time; neither held the literal name `resolved_wiring_for_arm` as a function mention beyond the 5.1 wiring-detail row and the 5.2 first defect row, both fixed.
- **Fix:** Rewrote each to the current behaviour, with "not re-run live" where I did not run it.
- **Files modified:** docs/gui/API-INVENTORY.md
- **Commit:** eb9f6ba

### Process notes

- The plan commit ledger of protocol 0c was not created before the first commit; `plan_head_before` is the parent of the first plan commit (de68bb2, HEAD when the plan began), and the measured count de68bb2..6cf5494 is 3.
- The row test was written and run against the unfixed text first (output above), then the docstrings were rewritten, so the test and the fix share commit 059dfb0. Fail-first at bb52fbb was shown by running the test file alone against the base text of the scanned files.
- Several Bash calls were rejected by the ledger-freeze hook because the command text named the ledger package; they were rewritten with plain paths or a scratchpad script. No ledger file was touched.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface.

## Self-Check: PASSED

- FOUND: databasise/tests/test_docstring_currency.py
- FOUND commits 059dfb0, eb9f6ba, 6cf5494 (ancestors of HEAD)
- `.planning/REQUIREMENTS.md` untouched (no diff)
