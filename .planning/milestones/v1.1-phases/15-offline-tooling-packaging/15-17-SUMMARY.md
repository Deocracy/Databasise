---
phase: 15-offline-tooling-packaging
plan: 17
subsystem: evidence
tags: [falsifier2, f07, modal-05, docstring-facts, tool-15, tool-20]

requires:
  - phase: 15-04
    provides: "lazy codebase-memory-mcp part and record"
  - phase: 15-07
    provides: "MCP package text fixed (tools.py ingest-effect sentence, TOOL_NAMES count)"
  - phase: 15-14
    provides: "run_cross_modality docstring corrected"
  - phase: 15-15
    provides: "build_hipporag_index docstring corrected"
provides:
  - "falsifier2 verdict paragraph and main() exit status computed from evaluate_probe results (failing_probes)"
  - "f07_report.main and EVIDENCE_PATH; verdict component list derived from the registered mutates_store rows; MODAL_05_STATEMENT constant"
  - "CROSS-MODALITY-EVIDENCE.md title, Status and Real-run verdict carry the one MODAL-05 statement; Findings row and deferral sections marked superseded"
  - "evidence/__init__ docstring, w2 boundary-knob rationale, falsifier2 scope comment and mutable-store refusal docstring state current facts"
affects: [15-18]

actuals:
  tokens: 12900
  tasks: 3
  commits: 3

plan_head_before: 7a8e54da7eddd146fa3bc800a76a09b8b3b78501
plan_head_after: a0090bad1d86194464422104242f2b33292e8214

tech-stack:
  added: []
  patterns:
    - "int main(argv=None) with argparse and sys.exit(main()) guard (D-03) on both evidence renderers"
    - "one shared constant (MODAL_05_STATEMENT) pinned verbatim in two committed records"

key-files:
  created:
    - databasise/tests/evidence/test_falsifier2_verdict.py
    - databasise/tests/evidence/test_docstring_facts.py
  modified:
    - databasise/evidence/falsifier2.py
    - databasise/evidence/f07_report.py
    - databasise/evidence/__init__.py
    - databasise/evidence/wirings/w2-codebase-memory-mcp.json
    - databasise/evidence/FALSIFIER-2-EVIDENCE.md
    - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
    - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
    - databasise/seam/refusals.py
    - databasise/clients/builder.py
    - databasise/foreign/v1_corpus_adapter.py
    - databasise/tests/evidence/test_f07_record.py
    - databasise/tests/evidence/test_cross_modality_record.py

key-decisions:
  - "A failing probe is a DID NOT FIRE or UNEXPECTED VIOLATION verdict cell; failing_probes() feeds both the 'Falsifier 2 fired' paragraph (naming the probe ids) and exit 1"
  - "MODAL_05_STATEMENT lives in f07_report and the hand-written cross-modality record repeats it verbatim; test_both_records_state_one_modal05_value pins title line, Status and body"
  - "The F-07 verdict states that MutableStoreComparisonExcludedError is defined but no served wiring reaches the comparison path; the codebase-memory-mcp row stays 'admitted, not registered'"

requirements-completed: [TOOL-15, TOOL-20]

duration: 45min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 17: Evidence records render only what their inputs show Summary

**Falsifier 2's verdict and exit code now follow its probe results, f07_report has a computed-record `main`, MODAL-05 has one stated value in both committed records, and the evidence, registry and env-loader docstrings state current facts.**

## Accomplishments

- `evidence/falsifier2.py`: `failing_probes()` drives the verdict paragraph ("Falsifier 2 fired" naming the failing probe ids, else today's text) and `main(argv=None) -> int` (argparse, no flags, unknown flag exits 2, returns 1 on a failing probe). The module ends with `sys.exit(main())`. The cbm part is imported inside `probe_registry()`. The committed `FALSIFIER-2-EVIDENCE.md` was byte-identical after Task 1 and changed only in the w2 boundary row after Task 3.
- `evidence/f07_report.py`: `EVIDENCE_PATH`, `main(argv=None) -> int` writing `render_f07_record(default_registry())`, `MODAL_05_STATEMENT`. The verdict lists the registered components from the rows and replaces the "enforced as an explicit refusal in the comparison path" claim with the recorded reasons.
- `CROSS-MODALITY-EVIDENCE.md`: the title line, Status section and the 2026-09-10 Verdict carry the shared sentence; the single Findings row opens with its supersession by "Real run — 2026-09-10"; each deferral section and the refused-attempt section carries a one-line superseded marker; the 06-08 footer is qualified. No section was deleted.
- TOOL-20 lanes: `evidence/__init__` describes the renderers, committed data and records; the w2 rationale states the native-chunking leg only and cites FALSIFIER-4-EVIDENCE.md; `falsifier2.py` states `part.artifact_scope or "shared"` (`validator/blast_radius.py:50`); the `MutableStoreComparisonExcludedError` docstring names `test_mutable_store_exclusion.py` and `test_refusal_reachability.py` and keeps "unreachable".
- The two docstrings 15-12 reported (`clients/builder.py` `load_env_file`, `foreign/v1_corpus_adapter.py` `_load_env_file`) cited the deleted `v1_arm._load_env_file` returning `{}`. Both are corrected (one-line each, node `test_the_env_loader_docstrings_do_not_cite_a_deleted_helper`).

## Row test node ids and fail-first evidence

Ledger `test_ref` intent: TOOL-15 `databasise/tests/evidence/test_falsifier2_verdict.py`; TOOL-20 `databasise/tests/evidence/test_docstring_facts.py`.

**TOOL-15** (`record-fail --at 7a8e54da7eddd146fa3bc800a76a09b8b3b78501`, the commit before this plan's first code commit):

| Node | Pre-change failure |
|------|--------------------|
| `test_a_probe_that_does_not_fire_renders_fired_and_exits_one` | `AssertionError: verdict is fixed text, not computed` |
| `test_the_unpatched_run_renders_did_not_fire_and_exits_zero` | `AssertionError: main([]) raised TypeError: main() takes 0 positional arguments but 1 was given` |
| `test_f07_main_exists_and_regenerates_the_committed_record` | `AssertionError: f07_report has no main()` |
| `test_a_third_mutates_store_part_appears_in_the_verdict` | `assert 'probe/third-mutator@0.1.0' in "...## Verdict..."` |
| `test_the_f07_verdict_claims_no_enforced_comparison_path` | `assert 'enforced as an explicit refusal' not in ...` |
| `test_both_records_state_one_modal05_value` | `AssertionError: f07_report has no MODAL_05_STATEMENT` |

All six were run on the unchanged source (nodes 1-2 before Task 1, nodes 3-6 before Task 2) and again by copying the file into a detached worktree of `00eeae8` (`docs(15): create phase plan`): every node fails by AssertionError there. That worktree was removed.

**TOOL-20** (`record-fail --at 00eeae8`, the `docs(15): create phase plan` commit, where all seven nodes fail; verified in the same worktree):

| Node | Failure at `00eeae8` |
|------|----------------------|
| `test_no_parity_module_says_it_was_never_run_for_real` | `parity/build_hipporag_index.py still says 'has not been invoked for real'` |
| `test_the_never_invoked_findings_row_is_marked_superseded` | `the never-invoked row is not marked superseded` |
| `test_the_evidence_package_docstring_names_its_modules` | `databasise.evidence.__doc__ does not mention parity_report` |
| `test_no_machine_chunk_leg_is_claimed` | `the w2 rationale still claims a machine-chunk leg` |
| `test_the_mcp_lane_states_current_facts` | `mcp/tools.py still contrasts mutates_store with writes_artifact` |
| `test_the_registry_lane_states_current_facts` | `falsifier2.py still describes the getattr default` |
| `test_the_env_loader_docstrings_do_not_cite_a_deleted_helper` | `clients/builder.py cites the deleted v1_arm copy` |

On the working tree before Task 3, four nodes failed (package docstring, machine-chunk, registry lane, env-loader) and three passed (parity and MCP lanes by 15-07/14/15, the Findings row by Task 2).

## Test results

- Task 1 set (`test_falsifier2_verdict`, `test_falsifier2_evidence`, `test_falsifier2_probes`, `test_tool_descriptions`, `tests/parts_core`): 296 passed.
- Task 2/3 set (`tests/evidence`, `tests/validator`): green; evidence plus `test_falsifier2_evidence`: 112 passed.
- Final set: `tests/evidence`, `tests/validator`, `tests/foreign`, `tests/clients`, `test_tool_descriptions` and the protected `test_docstring_currency.py`, `test_refusal_catalogue.py`, `test_refusal_status_codes.py`, `test_refusal_body_shape.py`, `test_seam_doc_consistency.py`, `test_refusal_reachability.py` (plus `test_mutable_store_exclusion.py`): 496 passed, 1 deselected. No protected test failed and none was edited.
- `python -m databasise.evidence.falsifier2` and `python -m databasise.evidence.f07_report` exit 0 and leave the committed documents unchanged; `falsifier2 --bogus` exits 2.
- Full `pytest -q databasise` run on the final tree (with 15-16's commits present): exit 0, no failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale docstrings outside the plan's file list**
- **Found during:** Task 3 (orchestrator dispatch note from 15-12)
- **Issue:** `clients/builder.py` `load_env_file` and `foreign/v1_corpus_adapter.py` `_load_env_file` described the deleted `v1_arm._load_env_file` returning `{}`.
- **Fix:** Rewrote both docstring passages to cite the live behaviour; added one test node to `test_docstring_facts.py`.
- **Files modified:** `databasise/clients/builder.py`, `databasise/foreign/v1_corpus_adapter.py`
- **Commit:** a0090ba

**2. [Rule 3 - Blocking] `test_modal05_claim_quoted_verbatim` read hard-wrapped quote text**
- **Found during:** Task 2
- **Issue:** The phrase "the milestone proof point" had been matched only inside the removed BLOCKED Status prose; the verbatim quote hard-wraps it.
- **Fix:** The test now strips the blockquote markers and collapses whitespace before matching. The assertions are unchanged.
- **Files modified:** `databasise/tests/evidence/test_cross_modality_record.py`
- **Commit:** b10df2e

**Total deviations:** 2 auto-fixed. **Impact:** none on scope; neither touches a protected file.

## Known Stubs

None.

## Threat Flags

None. The plan adds no endpoint, auth path or schema change; T-15-47, T-15-48 and T-15-49 are mitigated by the computed verdict, the shared constant and the replaced claim.

## Commits

- 1362600: feat(15-17): the Falsifier 2 verdict and exit status are computed from the probe results (TOOL-15)
- b10df2e: feat(15-17): f07_report.main writes the computed record and both records state one MODAL-05 value (TOOL-15)
- a0090ba: docs(15-17): evidence, registry and env-loader docstrings state current facts (TOOL-20)

## Self-Check: PASSED

All twelve modified and two created files exist; the three commits are ancestors of HEAD.
