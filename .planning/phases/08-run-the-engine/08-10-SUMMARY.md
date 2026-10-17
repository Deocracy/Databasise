---
phase: 08-run-the-engine
plan: 10
subsystem: testing
tags: [pytest, parity, rerank, requirements-wording, testing-plan, ledger]
requires:
  - phase: 08-run-the-engine
    provides: "08-01..08-09 tests and the builder/rerank/launcher code the twelve RUN rows point at"
provides:
  - "strict-boundary unit test for the parity threshold comparison"
  - "owner-approved D-07/D-08 rerank wording in REQUIREMENTS.md RUN-05 and ROADMAP Phase 8 criterion 1"
  - "TESTING-PLAN section 2 rows for the deferred RUN-11, RUN-05 and D-10 live runs"
  - "the twelve ledger set lines, ready for the owner (pending)"
affects: [phase-8-verification, 09-*, ledger]
status: complete
status_note: "Owner-narrowed run. Task 1 and Task 3 are owner-only and deferred; Task 2 ran in part. RUN-11 is NOT complete."

actuals:
  tokens: 2845
  tasks: 1
  commits: 2
plan_head_before: 5d8ec7acacef7684c9eca6cd3223bdaf4f84adac
plan_head_after: 491cb63cd1a3414c3ca1981ba4bc45f0380fe84b

tech-stack:
  added: []
  patterns: ["owner-deferred live measurement tracked as a TESTING-PLAN row, not a phase task"]

key-files:
  created: []
  modified:
    - databasise/tests/parity/test_embedder_index_reproduction.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/TESTING-PLAN.md

key-decisions:
  - "_SIMILARITY_THRESHOLD stays 0.999 and is documented as unmeasured; the D-14 measurement is owner-deferred to TESTING-PLAN section 2"
  - "RUN-11 is not marked complete: its measured threshold and five live passes have not happened"
  - "The plan's RUN-05 evidence names two nodes that do not exist; the corrected node names below replace them"

requirements-completed: [RUN-05, RUN-01, RUN-02, RUN-03, RUN-04, RUN-06, RUN-07, RUN-08, RUN-09, RUN-10, RUN-12]

coverage:
  - id: D1
    description: "A similarity exactly equal to the threshold is not a violation (strict <)"
    requirement: RUN-11
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_embedder_index_reproduction.py#test_a_similarity_equal_to_the_threshold_is_not_a_violation"
        status: pass
    human_judgment: false
  - id: D2
    description: "RUN-05 and ROADMAP criterion 1 state the owner-approved D-07/D-08 rerank behaviour; the ledger-stored RUN-05 prefix and the ledger checksums are untouched"
    requirement: RUN-05
    verification:
      - kind: other
        ref: "python3 scripts/check-ledger.py --root . (silent) and grep -c of the RUN-05 prefix (1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The measured parity threshold and five live passes (D-14)"
    requirement: RUN-11
    verification: []
    human_judgment: true
    rationale: "Owner-deferred live measurement; no threshold has been measured"

duration: 2min
completed: 2026-10-17
---

# Phase 08 Plan 10: Owner-narrowed closing plan Summary

**Strict-boundary parity test, owner-approved rerank wording in RUN-05 and the ROADMAP, and the deferred live runs and ledger steps parked in TESTING-PLAN and this file; no live run, no ledger write.**

## Performance

- **Duration:** about 2 min of executor time
- **Started:** 2026-10-17T01:57:49Z
- **Completed:** 2026-10-17T01:59:21Z (before the state and summary commit)
- **Tasks:** 1 of 3 run (Task 2, in part); Tasks 1 and 3 are owner-only and deferred
- **Files modified:** 4

## Accomplishments

- Added `test_a_similarity_equal_to_the_threshold_is_not_a_violation`; the parity file runs `5 passed, 1 deselected` under the default command.
- Added a docstring sentence saying 0.999 is unmeasured pending the owner-deferred runs in `.planning/TESTING-PLAN.md` section 2.
- Applied the owner-approved wording to `.planning/REQUIREMENTS.md` RUN-05 and `.planning/ROADMAP.md` Phase 8 criterion 1 with scoped edits. The RUN-05 prefix through `{'llm', 'em` is byte-identical (grep count 1), `scripts/check-ledger.py --root .` is silent, and `git diff --stat -- ledger/` is empty.
- Added three rows to TESTING-PLAN section 2: RUN-11 threshold runs, RUN-05 no-spend parity-env check, D-10 optional live rerank test.

## Task Commits

1. **Task 1: owner live runs and wording** - no commit. Resolved by the orchestrator: wording approved (corrected form, see below); live runs deferred.
2. **Task 2: threshold, wording, rehearsal** - `258a580` (test: boundary test and docstring sentence), `491cb63` (docs: wording and TESTING-PLAN rows)
3. **Task 3: ledger test_refs and record-fail** - no commit. Owner-only, not run.

**Plan metadata:** the docs commit that carries this file, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## Files Created/Modified

- `databasise/tests/parity/test_embedder_index_reproduction.py` - unmeasured-threshold docstring sentence; boundary test
- `.planning/REQUIREMENTS.md` - RUN-05 rerank wording; RUN-05, RUN-01..04, RUN-06..10, RUN-12 checkboxes via `requirements.mark-complete` (RUN-11 left open)
- `.planning/ROADMAP.md` - Phase 8 criterion 1 wording; plan progress
- `.planning/TESTING-PLAN.md` - three deferred-run rows and the trigger sentence

## Decisions Made

- Threshold stays 0.999, flagged as unmeasured. Not lowered: PLAN prohibition RUN-11 (never set a threshold the measurements do not justify) holds.
- Wording scope followed the owner's corrected text, not the plan's earlier proposal, because the owner chose v1-style rerank bindings in 08-05 (`RERANK_BINDING` cohere, jina or aliyun).

## Deviations from Plan

### Owner-directed deviations

**1. Task 1 live runs and parity-env check skipped.** Owner, 2026-10-16: "we dont need to run any of those mesherment untill everthing is build. we only run things for debugging". No LIVE-MEASURE values, run date or endpoint model exist. The three runs are queued as TESTING-PLAN section 2 rows.

**2. Task 2 steps 1-2 (measured threshold, docstring record) not done.** Follows from deviation 1. `_SIMILARITY_THRESHOLD = 0.999` is unchanged. The docstring gained one sentence that the threshold is unmeasured pending the owner-deferred runs in `.planning/TESTING-PLAN.md` section 2. Must-haves "threshold is set from five owner-run measurements" and "five consecutive `-m live` passes" are therefore NOT met and stay open for RUN-11.

**3. Task 2 step 5 (fail-first rehearsal on BASE and HEAD worktrees) not done.** Owner: runs things only for debugging; the rehearsal prepares owner-run record-fail, which is deferred with Task 3. No worktree was created. The BASE import probe was not run.

**4. Task 2 verify: "threshold between 0.9 and 0.999" check skipped.** It cannot pass by design while the threshold is 0.999. The `<human-check>` (five live passes) is deferred.

**5. Task 3 not run (owner-only).** No `set` or `record-fail` call was made and nothing under `ledger/` was touched. The lines are in "Owner ledger steps (pending)" below.

**6. Wording differs from the plan's proposal.** The owner approved the corrected wording supplied with this run (binding-aware, matches 08-05), replacing the plan's all-three-keys proposal. Applied exactly as given.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan names two RUN-05 evidence nodes that do not exist**
- **Found during:** Task 2 verify (`--collect-only` of the RUN-03/05/06/07 evidence nodes printed `(no match in any of [<Module test_build_clients.py>])`)
- **Issue:** Task 3's RUN-05 `--evidence` text names `test_all_three_rerank_keys_add_a_rerank_client` and `test_a_partial_rerank_set_names_the_missing_rerank_keys`. 08-05 shipped them as `test_a_complete_rerank_set_adds_a_rerank_client` (parametrized over cohere, jina, aliyun) and `test_a_partial_rerank_set_names_exactly_the_missing_rerank_keys` (parametrized over four partial sets). Left as written, the ledger evidence would cite tests that do not exist.
- **Fix:** The RUN-05 set line below uses the real names. The plan file is left as written; use the lines in this SUMMARY.
- **Verification:** `pytest -q --collect-only` over both corrected nodes plus the six `test_store_lock.py` nodes named in RUN-07 evidence: `13 tests collected`, exit 0.
- **Committed in:** this SUMMARY (no code change)

---

**Total deviations:** 6 owner-directed, 1 auto-fixed (Rule 1, evidence text).
**Impact on plan:** RUN-11 stays open. Everything the owner scoped in was done and verified; the rest is queued.

## Verification run

- `cd databasise && .venv/bin/pytest -q tests/parity/test_embedder_index_reproduction.py` - `5 passed, 1 deselected`.
- `python3 scripts/check-ledger.py --root .` - silent; `git diff --stat -- ledger/` - empty.
- RUN-05 prefix grep - `1`.
- First `--collect-only` command (twelve test_refs) - `12 tests collected`, none deselected.
- Second `--collect-only` command (evidence nodes) - as written in the plan it printed `23 tests collected` with the two missing-node warnings above; with corrected names, collects cleanly (see Auto-fixed Issue 1).
- Skipped: threshold-range check (deviation 4); human-check (deviation 4).

## Issues Encountered

- A pipe in the new RUN-11 command broke the TESTING-PLAN table (extra column); escaped as `\|` before commit.
- The BAK ledger hook rejects compound commands that mention `ledger/`; the ledger checks were run as separate plain commands.

## Requirements state

`requirements.ready-ids` reported "12/12 requirement(s) ready to mark complete" (no sibling plan still pending). Per the owner's scoping, `requirements.mark-complete` was run for the eleven IDs other than RUN-11. RUN-11 is left open because its measurement and five live passes did not happen. This updates the REQUIREMENTS.md checkboxes only; the BAK ledger rows stay `open` with an empty test_ref until the owner runs the steps below.

## Owner ledger steps (pending)

Run from the repo root, in this order. These are the plan's twelve lines with the RUN-05 node names corrected (Auto-fixed Issue 1).

```
python3 scripts/ledger-amend.py --root . set --id RUN-01 --test-ref "databasise/tests/mcp/test_tool_growth_invariant.py::test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool"
python3 scripts/ledger-amend.py --root . set --id RUN-02 --test-ref "databasise/tests/clients/test_openai_compat.py::test_16_a_chat_response_with_no_usage_counts_one_unbudgetable_call"
python3 scripts/ledger-amend.py --root . set --id RUN-03 --test-ref "databasise/tests/clients/test_openai_compat.py::test_24_out_of_order_items_return_vectors_in_input_order" --evidence "test_ref covers check 4 (item ordering). Check 1: databasise/tests/clients/test_openai_compat.py::test_20_empty_choices_raise_empty_choices_error. Check 2: databasise/tests/clients/test_openai_compat.py::test_21_none_content_raises_missing_completion_content_error. Check 3: databasise/tests/clients/test_openai_compat.py::test_23_two_vectors_for_three_inputs_raise_embedding_batch_mismatch_error and databasise/tests/clients/test_openai_compat.py::test_25_duplicate_or_missing_indices_raise_embedding_batch_mismatch_error (08-02-SUMMARY.md)"
python3 scripts/ledger-amend.py --root . set --id RUN-04 --test-ref "databasise/tests/foreign/test_mcp_sdk_guard.py::test_sdk_detected_from_inside_the_project_directory"
python3 scripts/ledger-amend.py --root . set --id RUN-05 --test-ref "databasise/tests/clients/test_build_clients.py::test_six_keys_build_exactly_llm_and_embedding" --evidence "test_ref covers check 1 (six keys give exactly llm and embedding). Check 2: databasise/tests/clients/test_build_clients.py::test_two_missing_keys_are_both_named. Check 3: databasise/tests/clients/test_build_clients.py::test_run_arm_uses_the_shared_builder_not_a_private_copy. Check 4: databasise/tests/clients/test_build_clients.py::test_live_rerank_with_builder_clients_raises_client_not_wired_naming_rerank. Routing pin kept: databasise/tests/parity/test_naive_arm_end_to_end.py::test_build_clients_passes_a_present_and_parseable_provider_routing_body_to_the_llm_client and databasise/tests/parity/test_naive_arm_end_to_end.py::test_build_clients_refuses_by_name_on_an_unparseable_provider_routing_body. D-07/D-08 rerank cases: databasise/tests/clients/test_build_clients.py::test_a_complete_rerank_set_adds_a_rerank_client and databasise/tests/clients/test_build_clients.py::test_a_partial_rerank_set_names_exactly_the_missing_rerank_keys. Rerank reported as not available: databasise/tests/seam/test_corpus_status.py::test_health_reports_which_clients_are_wired. Keys never values: databasise/tests/clients/test_build_clients.py::test_builder_errors_name_keys_never_values (08-01-SUMMARY.md, 08-05-SUMMARY.md)"
python3 scripts/ledger-amend.py --root . set --id RUN-06 --test-ref "databasise/tests/launcher/test_launchers.py::test_databasise_rest_serves_health_from_the_installed_script" --evidence "test_ref covers the REST launcher serving create_app with builder clients. Entry points: databasise/tests/launcher/test_launchers.py::test_both_console_scripts_are_installed_entry_points. python -m modules: databasise/tests/launcher/test_launchers.py::test_python_m_modules_print_help. MCP over stdio: databasise/tests/launcher/test_launchers.py::test_databasise_mcp_stdio_lists_the_in_process_tool_set. MCP sse and streamable-http: databasise/tests/launcher/test_launchers.py::test_databasise_mcp_passes_each_transport_to_the_server_run_method. Default store root, workspace and host: databasise/tests/launcher/test_launchers.py::test_engine_argument_defaults_are_the_populated_store_on_loopback. Example MCP client config: databasise/tests/launcher/test_launchers.py::test_example_mcp_config_invokes_databasise_mcp_over_stdio (08-01-SUMMARY.md, 08-06-SUMMARY.md)"
python3 scripts/ledger-amend.py --root . set --id RUN-07 --test-ref "databasise/tests/launcher/test_launchers.py::test_second_launcher_on_a_held_store_root_exits_with_the_store_lock_error" --evidence "test_ref covers the second REST or MCP launcher exiting before serving with the store root and holder PID. --workers above 1 refused naming the store lock: databasise/tests/launcher/test_launchers.py::test_workers_above_one_is_refused_naming_the_store_lock. Lock released on exit: databasise/tests/launcher/test_launchers.py::test_a_released_store_root_can_be_launched_again. Lock unit behaviour: databasise/tests/launcher/test_store_lock.py::test_acquire_creates_a_missing_root_and_writes_the_pid, databasise/tests/launcher/test_store_lock.py::test_a_second_acquire_in_the_same_process_is_refused_with_this_pid, databasise/tests/launcher/test_store_lock.py::test_a_symlinked_spelling_of_a_held_root_is_refused, databasise/tests/launcher/test_store_lock.py::test_a_holder_that_wrote_no_pid_is_reported_as_unknown, databasise/tests/launcher/test_store_lock.py::test_the_lock_fd_is_not_inheritable and databasise/tests/launcher/test_store_lock.py::test_the_context_manager_releases_on_exit (08-01-SUMMARY.md, 08-06-SUMMARY.md)"
python3 scripts/ledger-amend.py --root . set --id RUN-08 --test-ref "databasise/tests/seam/test_rest_cors.py::test_listed_origin_preflight_returns_200_with_matching_allow_origin"
python3 scripts/ledger-amend.py --root . set --id RUN-09 --test-ref "databasise/tests/seam/test_rest_corpus_endpoints.py::test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document"
python3 scripts/ledger-amend.py --root . set --id RUN-10 --test-ref "databasise/tests/seam/test_rest_corpus_endpoints.py::test_upload_poll_delete_round_trip"
python3 scripts/ledger-amend.py --root . set --id RUN-11 --test-ref "databasise/tests/parity/test_embedder_index_reproduction.py::test_a_similarity_equal_to_the_threshold_is_not_a_violation" --evidence "five consecutive owner-run -m live passes of test_embedder_index_reproduces_v1_stored_vectors_on_a_sample at the measured threshold (08-10-SUMMARY.md)"
python3 scripts/ledger-amend.py --root . set --id RUN-12 --test-ref "databasise/tests/test_check_offline_suite.py::test_a_not_installed_skip_is_contradictory_when_mcp_is_installed" --evidence "databasise/tools/check_offline_suite.py exit 0 under both invocation styles (08-09-SUMMARY.md)"
```

Notes for the owner:

- RUN-11's `--evidence` claims five live passes at a measured threshold. Do not run that line until the TESTING-PLAN section 2 RUN-11 row has been done, or reword the evidence.
- Pre-step before any `record-fail` (it copies untracked, non-ignored files into /tmp worktrees): from the repo root run `git status --porcelain --untracked-files=all | grep -E '^\?\? "?(.*/)?\.env'`. It must print nothing. At plan time it listed `v1/.env.teachers` (still untracked now): move it out of the repo or add it to `.gitignore` first. Nobody opens or prints the listed files. The executor's secret-file guard blocks it from running this check.
- RUN-02..RUN-08 `record-fail` needs `--at <BASE>`, where BASE is the parent of the first `(08-NN)` commit: `git rev-parse $(git log --reverse --format=%H -E --grep='\(08-[0-9]{2}\)' | head -1)^`. BASE is not resolved here and the BASE/HEAD worktree rehearsal has not been run; both are left for later, ahead of the owner's record-fail calls (deviation 3). Command shape for each row: `python3 scripts/ledger-amend.py --root . record-fail --id <ID> --at <BASE> --timeout 600 --cmd 'PYTHONPATH="$PWD" /home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise/.venv/bin/python -m pytest -q <the row's test_ref>'`.
- RUN-01, RUN-09, RUN-10, RUN-11, RUN-12 have no production fix to show on BASE; the owner picks their BAK route (plan Task 3 instructions).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 plan files are all summarised. Phase 8 is not fully closed: RUN-11 (threshold and live passes) and the twelve ledger test_refs and fail-first records remain with the owner.
- The `v1/.env.teachers` untracked file must be moved or ignored before any record-fail call.

## Known Stubs

None. `_SIMILARITY_THRESHOLD = 0.999` is a documented, unmeasured value, not a stub; the owner-deferred measurement is tracked in `.planning/TESTING-PLAN.md` section 2.

## Threat Flags

None. No new endpoints, auth paths or file-access surface; no env file was read or printed.

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*

## Self-Check: PASSED

- FOUND: databasise/tests/parity/test_embedder_index_reproduction.py (boundary test present)
- FOUND commits: 258a580, 491cb63
