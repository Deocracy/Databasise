---
phase: 12-hipporag-fixes
plan: 10
subsystem: hipporag-query-path
tags: [hipporag, qa, answer-generation, port-record]
status: complete
requires:
  - phase: 12-hipporag-fixes
    provides: 12-06 registry at 37 parts; 12-07 query-vector reuse and six query-side nodes
provides:
  - hipporag/qa-reader@0.1.0, the 14th node and the wiring's provides
  - assemble-result without completion
  - HIPP-13 row test and qa unit tests
affects: [12-11]
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: ebe7c6be1baa901480eea27f98e5060fd223056d
plan_head_after: 41cd00ed13012a11def010ef6694eaf1128e5647
tech-stack:
  added: []
  patterns: ["the answer is a generator node over hydrated items; evidence still mints from the retrieval node"]
key-files:
  created:
    - databasise/parts_core/hipporag/qa.py
    - databasise/tests/parts_core/hipporag/test_qa_node.py
  modified:
    - databasise/parts_core/hipporag/__init__.py
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/seam/test_hipporag_query_path.py
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/tests/parts_core/hipporag/test_thirteen_positions.py
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
    - databasise/tests/evidence/test_hipporag_port_record.py
    - databasise/tests/seam/test_cross_modality_run.py
    - databasise/tests/wirings/test_query_run_pruning.py
    - databasise/tests/parts/test_registry.py
key-decisions:
  - "D-19: qa ports upstream rag_qa (HippoRAG.py:1117-1172, rag_qa_musique at d5c8329); the Wikipedia Title: prefix is kept verbatim"
  - "No hydrated passage content: no LLM call, answer is PROMPTS['fail_response'] (same object LightRAG's generator uses)"
requirements-completed: [HIPP-13]
---

# Phase 12 Plan 10: HippoRAG answers with generated text Summary

A HippoRAG query now answers with the text a new `qa` node (`hipporag/qa-reader@0.1.0`, a port of upstream `rag_qa`) generates from the hydrated passages and the query, instead of the passages joined by blank lines.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: a HippoRAG query answers with qa-generated text (HIPP-13, D-19) | e2ab6cc |
| 2 | Structural pins, port record and cross-modality answer follow the 14th node (D-19) | 41cd00e |

## HIPP row, intended ledger test_ref, fail-first evidence

| Row | Intended test_ref | Fail-first evidence |
|-----|-------------------|---------------------|
| HIPP-13 | `databasise/tests/seam/test_hipporag_query_path.py::test_the_answer_is_generated_text_not_the_joined_evidence` | Run against the source as left by 12-09 (before qa existed), plain AssertionError: `assert 'Ed Wood directed several low-budget films.' != 'Ed Wood directed several low-budget films.'` (the answer equals the joined evidence). Passes after the fix. The same run also failed `test_a_query_runs_only_query_side_nodes_and_embeds_once` on the added `qa` node (`Extra items in the right set: 'qa'`), which is the expected pin update, not a regression. |

Supporting tests in `databasise/tests/parts_core/hipporag/test_qa_node.py`: `test_no_passage_content_answers_fail_response_without_an_llm_call` (the no-context answer is the same object as `PROMPTS["fail_response"]`, zero LLM calls), `test_the_messages_are_system_one_shot_pair_then_the_passages_and_question` (four messages, `Wikipedia Title:` per passage, `Question: ...\nThought: `, no fact-filter or openie markers), `test_a_response_without_the_answer_marker_is_returned_whole`, `test_the_part_declares_a_generator_with_calls_llm`.

Edge coverage: generated answer, no-context fail_response and missing "Answer:" marker are covered; no other HIPP-13 edge was planned.

## Verification

- Task 1 verify: `pytest -q tests/seam/test_hipporag_query_path.py tests/parts_core/hipporag/test_qa_node.py tests/seam/test_hipporag_write_path.py`: 22 passed.
- Task 2 verify (first command): 156 passed, 1 failed (`tests/wirings/test_query_run_pruning.py`, see Deviations), then fixed.
- Wave command `pytest -q tests/seam tests/parts_core tests/wirings tests/parity tests/evidence tests/mcp tests/eval`: 1487 passed, 3 deselected.
- `pytest -q tests/parts tests/validator tests/runner tests/identity`: after the registry bump, `tests/parts` 23 passed; the other three directories passed in the same run (217 passed before the registry fix, 1 failed).
- Acceptance: `base.json` provides `['qa']`, `qa` in consumes_query, evidence node `assemble-result`; `qa.py` contains neither `Candidate Facts` nor `Recognised Entities`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Two pins outside the plan's file list followed the 14th node.**
- Issue: `tests/wirings/test_query_run_pruning.py::test_hipporag_pruning_keeps_exactly_the_query_side_nodes` pins the pruned query node set (6 nodes), and `tests/parts/test_registry.py` pins the default registry size (37). Both are expected to follow a new node (the orchestrator's note covered the registry count).
- Fix: `qa` added to `_HIPPORAG_QUERY_NODES`; registry count 37 to 38 with the test renamed `..._thirty_eight_entries`. Neither file was blocked as a protected file.
- Also: `tests/seam/test_hipporag_query_path.py::_QUERY_SIDE_NODES` gains `qa` (the file is in the plan's list).
- Commit: 41cd00e.

**2. Not changed:** the shared helpers in `tests/seam/test_hipporag_write_path.py` (only imported `_OBJECT`, `_PREDICATE`, `_SUBJECT`, which already existed). The new `_StubQaAwareLLMClient` is a new stub in `test_hipporag_query_path.py`.

## Known Stubs

None.

## Threat Flags

None. T-12-17 (prompt injection via passages) accepted as planned; T-12-18 (qa token spend) is bounded by 12-11's top_k cut, not by this plan.

## Self-Check: PASSED

- Commits e2ab6cc and 41cd00e are ancestors of HEAD.
- `qa.py` and `test_qa_node.py` exist.
