---
phase: 11-lightrag-corpus-path
plan: 11
subsystem: generation
tags: [lightrag, kg-query, fidelity, d-16, lrag-17, prompts, token-budget, phase-gate]
status: complete

requires:
  - phase: 11-04
    provides: v1-ordered KG retrieval (keyword-string embeddings, per-side chunk selection, vector-first chunk merge, rerank query)
  - phase: 11-10
    provides: the engine's run copy without recipe-only nodes and the empty-namespace pre-check
provides:
  - "parts_core/lightrag/prompts.py: verbatim v1 PROMPTS (fail_response, rag_response, naive_rag_response, kg_query_context, naive_query_context, keywords_extraction), guarded by an ast drift test"
  - "assemble builds v1's kg_query_context (kg-template) or naive_query_context (naive-template); UnknownOrderPolicyError; template_kind; chunk_top_k cap; v1's available-token chunk budget"
  - "generate sends [system: filled rag_response / naive_rag_response, user: query]; bypass sends the bare query; empty context returns fail_response with no call; priority_class echoed; UnknownPromptTemplateError"
  - "budget-entities / budget-relations cost v1's projected rows and emit entities_context / relations_context"
  - "seam/engine.py _inject_max_total_tokens: setdefault 30000 on every lightrag/assembler-kg-context node"
  - "wirings: assemble deps gain the two budget nodes, consumes_query gains assemble, arm-naive resets assemble deps; README provenance edits 7-9"
affects: [LRAG-17, ROADMAP criterion 5, Phase 12 HippoRAG answer path, parity evidence]

estimate:
  tokens: 45000
  tasks: 3
actuals:
  tokens: 11085
  tasks: 3
  commits: 2
plan_head_before: b538852ac6ade17702f19b0c8885a81367dd34f6
plan_head_after: 5466841b6c1d10dfd37b6d614dc11b8a9bfc548d

tech-stack:
  added: []
  patterns:
    - "duplicated upstream strings live in one module and an ast drift test compares them with the upstream source"
    - "a budget node emits both the kept originals (for downstream retrieval) and the projected rows (for the prompt)"

key-files:
  created:
    - databasise/parts_core/lightrag/prompts.py
    - databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py
    - databasise/tests/parts_core/lightrag/test_kg_fidelity.py
  modified:
    - databasise/parts_core/lightrag/assemble.py
    - databasise/parts_core/lightrag/generate.py
    - databasise/parts_core/lightrag/truncator_token_budget.py
    - databasise/parts_core/lightrag/keywords.py
    - databasise/clients/base.py
    - databasise/seam/engine.py
    - databasise/wirings/lightrag/base.json
    - databasise/wirings/lightrag/arm-naive.json-patch.json
    - databasise/wirings/lightrag/README.md
    - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
    - databasise/tests/parts_core/lightrag/test_transform_parts.py
    - databasise/tests/seam/test_evidence_refs.py
    - databasise/tests/seam/test_query_object.py
    - databasise/tests/seam/test_query_trace_nodes.py

key-decisions:
  - "Chunk rows carry v1's reference_id (the file-path reference number from generate_reference_list_from_chunks), not the DC1.. ids: v1 assigns DC ids to chunk['id'] but writes reference_id into the context"
  - "keywords.py reads PROMPTS['keywords_extraction'] from prompts.py, so all six duplicated v1 strings have one home and one drift test"
  - "The row projection and row costing (Pattern F row 8) landed in Task 1, in the truncator, so the tracer's KG context was real and the projection exists in one place"
  - "assemble costs each chunk as v1 does, the JSON of the whole chunk item; naive subtracts no context-template overhead, as v1 naive_query does"
  - "assemble defaults max_total_tokens to 30000 when absent (parity run_arm path), and the engine also stamps it so the value is in the wiring instance hash"
  - "All part versions unchanged (body-only changes, effects unchanged)"

requirements-completed: [LRAG-17]

duration: 40min
completed: 2026-10-18
---

# Phase 11 Plan 11: LightRAG KG answer fidelity and the phase gate Summary

**The hybrid, local and global arms now answer the way v1 `kg_query` does. The model receives v1's `rag_response` as the system message, filled with a `kg_query_context` of budgeted entity rows, relation rows, chunks and a reference list, and the query as the user message. The naive arm uses `naive_rag_response`, and bypass sends the bare query. The engine always caps the context. The full offline gate passes under both pytest styles: 2036 passed each, exit 0.**

## What changed

- `parts_core/lightrag/prompts.py` (new): one `PROMPTS` dict holding verbatim copies of v1's `fail_response`, `rag_response`, `naive_rag_response`, `kg_query_context`, `naive_query_context` and `keywords_extraction`. `keywords.py` now takes its prompt from this module and its own copy is deleted.
- `assemble.py`:
  - `kg-template` fills `kg_query_context` with the entity and relation rows from `budget-entities` / `budget-relations`, the chunk rows and the reference list. `naive-template` fills `naive_query_context`. Any other policy raises `UnknownOrderPolicyError(ValueError)`.
  - Chunk rows are `{"reference_id", "content"[, "content_headings"]}`. File paths are numbered by frequency, then first appearance.
  - Chunks are capped at `chunk_top_k` (20), then cut from the end, whole chunks only, to `max_total_tokens - (sys_prompt + kg_context + query + 200)` at `len // 4`.
  - With no entity, relation or chunk the context is `""`. Output gains `template_kind`.
- `generate.py`: `prompt_template` absent or `rag_response` selects `rag_response`, and `naive` selects `naive_rag_response`. Both are formatted with `response_type="Multiple Paragraphs"` and `user_prompt="n/a"`. A value starting with `none` sends one user message. Anything else raises `UnknownPromptTemplateError`. An empty context returns `fail_response` with `TokenAccounting(counted_by="none")` and makes no call. `priority_class` is echoed in the result.
- `truncator_token_budget.py`: each item is projected to `{entity, type, description}` or `{entity1, entity2, description}` (handling `src_tgt` or `src_id`/`tgt_id`) and costed as `len(json.dumps(row)) // 4`. The node emits the kept `items` plus `entities_context` / `relations_context`.
- `clients/base.py`: the `LLMClient.chat` docstring documents a leading system message.
- `seam/engine.py`: `_DEFAULT_MAX_TOTAL_TOKENS = 30000` and `_inject_max_total_tokens`, called in `_execute_resolved` beside `_inject_token_allowance`.
- Wirings: base `assemble` deps are `["rerank", "budget-entities", "budget-relations"]` and `consumes_query` gains `"assemble"`. The naive patch resets assemble's deps to `["rerank"]`. No `resulting_node_id_set` changed. README provenance edits 7-9 record these changes.

## TDD evidence

- Task 1 RED (unchanged assemble, generate and truncator): `ImportError: cannot import name 'UnknownOrderPolicyError'`, `1 error during collection`. The drift test was written after `prompts.py`, so its first run was green (`3 passed in 0.07s`); a run before the new module existed would only have shown an ImportError.
- Task 1 GREEN: `test_v1_prompt_drift.py test_kg_fidelity.py test_arm_conformance.py`: `23 passed in 6.83s`, with no skips. The two real-driver arm tests ran against the hermetic v1 harness. The tracer gate re-ran the same command: `23 passed in 6.98s`.
  - `tests/parts_core tests/parity tests/wirings tests/seam`: `4 failed, 1147 passed, 3 deselected` on the first run. The four were unprotected tests that pinned the old one-message prompt or the whole-item costing (listed below). After the updates the four files gave `58 passed`.
- Task 2 RED (unchanged assemble and engine): `3 failed, 11 passed`.
  - `assert (11608 // 4) <= 2000`: the system prompt was 2902 tokens.
  - `assert 30 == 20`: no `chunk_top_k` cap.
  - `KeyError: 'max_total_tokens'`: the engine did not set it.
- Task 2 GREEN:
  - `test_kg_fidelity.py tests/parts_core/lightrag tests/parity`: `275 passed, 3 deselected`.
  - `tests/seam tests/mcp tests/runner tests/wirings tests/eval`: `2 failed, 1061 passed`. Both failures were in `test_query_trace_nodes.py`, whose expected instance hash lacked the new injection. After the fix, that file plus the fidelity tests gave `22 passed`.
- Task 3, the phase gate `cd databasise && .venv/bin/python tools/check_offline_suite.py`: **exit 0**
  - `pytest -q -rs: 2036 passed, 4 deselected in 482.42s (0:08:02)`
  - `python -m pytest -q -rs: 2036 passed, 4 deselected in 480.74s (0:08:00)`
  - 0 skipped, so no real-driver test skipped on this machine. The 4 deselected are the `live`-marked tests.
  - Against baselines: Phase 10 had 1861 passed and 11-10's gate had 2019, so this run adds 17 tests over 11-10 and 175 over Phase 10.
- Ruff `seam mcp stores parts_core foreign`: 39 errors before (HEAD b538852) and 39 after. None is new; the 4 that ruff reports in touched files were present before this plan.

## Unprotected tests updated (each with a one-line reason in the file)

1. `tests/parts_core/lightrag/test_naive_arm_parts.py::test_generate_with_no_assemble_input_still_calls_the_llm_with_just_the_query` now sets bypass's `prompt_template`. Without it, the KG default answers `fail_response`.
2. `test_naive_arm_parts.py::test_assemble_respects_a_configured_max_total_tokens_budget_by_dropping_whole_chunks`: the budget now includes v1's reserved system-template and 200-token overhead.
3. `tests/parts_core/lightrag/test_transform_parts.py::test_truncator_preserves_input_order_and_removes_from_the_tail`: the per-item cost is now the projected v1 row.
4. `tests/seam/test_evidence_refs.py::test_zero_item_retrieval_yields_an_empty_but_present_evidence_list`: with zero chunks the answer is `PROMPTS["fail_response"]`, as in v1.
5. `tests/seam/test_query_object.py`: the echo client echoes the last message, which is now the user message.
6. `tests/seam/test_query_trace_nodes.py::_expected_instance_hash` also applies `_inject_max_total_tokens`.

No protected (ledger `test_ref`) file was edited. `test_store_effects_wired.py` and the four seam tests that query `synthetic_naive_store` passed unchanged in the gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's chunk ids would not have matched v1**
- **Found during:** Task 1, reading `utils.py:4335-4440` and `operate.py:4935-4964`
- **Issue:** the plan said chunk rows use `DC1`, `DC2` ids. v1 writes `id = "DC{i}"` onto the chunk, but the context row's `reference_id` is the file-path reference number from `generate_reference_list_from_chunks`.
- **Fix:** rows use v1's file-path reference number, so the system prompt matches v1. This follows D-16 ("match v1").
- **Commit:** 65f059b

**2. [Rule 3 - Blocking] Row projection moved from Task 2 into Task 1**
- **Found during:** Task 1
- **Issue:** the tracer's hybrid test needs real entity and relation rows. The plan's interim fix was a second projection inside assemble, to be replaced in Task 2.
- **Fix:** the truncator's projection and row costing (Pattern F row 8) landed in Task 1, so the projection exists only in the truncator. Task 2 then covered `chunk_top_k`, the token formula, the engine cap and the README.
- **Commit:** 65f059b

**3. [Rule 3 - Blocking] Three seam tests outside the plan's file list pinned the old behaviour**
- `test_evidence_refs.py`, `test_query_object.py` and `test_query_trace_nodes.py` are listed above. Each is unprotected and owned by an earlier plan.
- **Commits:** 65f059b, 5466841

**4. Spy point for the engine-cap test**
- The plan named a `run_wiring` spy. The test spies on `parse_wiring`, which receives the same run wiring before any store opens, so the test needs no populated store.

Otherwise the plan executed as written. `keywords.py` now references `prompts.py`, as the plan allowed when the text stays byte-identical, which the drift test proves.

## Known Stubs

None.

## Threat Flags

None. T-11-24 is mitigated: the engine always sets `max_total_tokens`, `chunk_top_k` caps the chunk count, and the oversized-fixture test proves the cap. T-11-23 is accepted as planned.

## Notes for later plans

- `parity/run_arm.py`'s `_inject_query` is still hardcoded to `keywords`, `embedder-query` and `generate`. On parity runs, assemble therefore sees no query and its budget counts zero query tokens. That error is small (only the query's length), and assemble's own 30000 default still applies.
- `len // 4` remains a `shortcut:` in `assemble.py` and `truncator_token_budget.py`. Replace it when an offline-safe tokenizer ships.

## Self-Check: PASSED

- FOUND: databasise/parts_core/lightrag/prompts.py
- FOUND: databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py
- FOUND: databasise/tests/parts_core/lightrag/test_kg_fidelity.py
- FOUND: 65f059b (Task 1)
- FOUND: 5466841 (Task 2)
- Measured commits: `git rev-list --count b538852..HEAD` = 2. Task 3 changed no file.
- Acceptance greps: `kg_query_context` appears in both prompts.py and assemble.py; generate.py has a `"role": "system"` line; the base.json assertion printed BASE_OK; there is one `/nodes/assemble/deps` line; truncator_token_budget.py has `entities_context`; engine.py has one `def _inject_max_total_tokens`; both modules have a `shortcut: len // 4` line
