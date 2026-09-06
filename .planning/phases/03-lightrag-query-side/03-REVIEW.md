---
phase: 03-lightrag-query-side
reviewed: 2026-09-06T02:30:00Z
depth: standard
files_reviewed: 74
files_reviewed_list:
  - databasise/clients/base.py
  - databasise/clients/__init__.py
  - databasise/clients/openai_compat.py
  - databasise/evidence/DECLARED-DEVIATIONS.md
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
  - databasise/evidence/falsifier2.py
  - databasise/evidence/human_findings.json
  - databasise/evidence/PARITY-EVIDENCE.md
  - databasise/evidence/parity_report.py
  - databasise/evidence/parity_results/bypass-comparison.json
  - databasise/evidence/parity_results/bypass-storage-audit.json
  - databasise/evidence/parity_results/global-comparison.json
  - databasise/evidence/parity_results/global-storage-audit.json
  - databasise/evidence/parity_results/hybrid-comparison.json
  - databasise/evidence/parity_results/hybrid-storage-audit.json
  - databasise/evidence/parity_results/local-comparison.json
  - databasise/evidence/parity_results/local-storage-audit.json
  - databasise/evidence/parity_results/naive-comparison.json
  - databasise/evidence/parity_results/naive-storage-audit.json
  - databasise/evidence/wirings/w1-lightrag-query-side.json
  - databasise/evidence/wirings/w3-lightrag-half-decomposed.json
  - databasise/.gitignore
  - databasise/__init__.py
  - databasise/parity/build_corpus_fixture.py
  - databasise/parity/corpus.py
  - databasise/parity/import_index.py
  - databasise/parity/__init__.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - databasise/parity/storage_audit.py
  - databasise/parity/v1_arm.py
  - databasise/parity/v1_driver_script.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/embedder_index.py
  - databasise/parts_core/lightrag/embedder_query.py
  - databasise/parts_core/lightrag/entity_hydrate_expand.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/generate.py
  - databasise/parts_core/lightrag/heading_backfill.py
  - databasise/parts_core/lightrag/__init__.py
  - databasise/parts_core/lightrag/join_roundrobin.py
  - databasise/parts_core/lightrag/keywords.py
  - databasise/parts_core/lightrag/relation_hydrate_expand.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/rerank.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/pyproject.toml
  - databasise/runner/scheduler.py
  - databasise/stores/graph.py
  - databasise/stores/vector.py
  - databasise/tests/clients/__init__.py
  - databasise/tests/clients/test_capability_scoped_clients.py
  - databasise/tests/clients/test_openai_compat.py
  - databasise/tests/fixtures/corpus/MANIFEST.json
  - databasise/tests/fixtures/corpus/README.md
  - databasise/tests/parity/conftest.py
  - databasise/tests/parity/__init__.py
  - databasise/tests/parity/test_arm_conformance.py
  - databasise/tests/parity/test_embedder_index_reproduction.py
  - databasise/tests/parity/test_import_verification.py
  - databasise/tests/parity/test_keyword_variance.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parity/test_parity_evidence.py
  - databasise/tests/parity/test_retrieval_parity.py
  - databasise/tests/parity/test_storage_audit.py
  - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
  - databasise/tests/parts_core/lightrag/test_transform_parts.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/runner/test_clients_threading.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/stores/test_graph_frozen_bugs.py
  - databasise/tests/stores/test_graph.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_import_boundary.py
  - databasise/tests/validator/test_falsifier2_evidence.py
  - databasise/tests/validator/test_falsifier2_probes.py
  - databasise/tools/check_import_boundary.py
  - databasise/wirings/__init__.py
  - databasise/wirings/lightrag/arm-bypass.json-patch.json
  - databasise/wirings/lightrag/arm-global.json-patch.json
  - databasise/wirings/lightrag/arm-hybrid.json-patch.json
  - databasise/wirings/lightrag/arm-local.json-patch.json
  - databasise/wirings/lightrag/arm-naive.json-patch.json
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/lightrag/README.md
  - databasise/wirings/resolve.py
  - v1/README-PARITY.md
  - v1/scripts/run_parity_ingest.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-06
**Depth:** standard
**Files Reviewed:** 74
**Status:** issues_found

## Summary

This is iteration 2 of the auto fix loop's re-review. Three fixes landed since the prior review
(`03-REVIEW.iter2.md`) and were each verified directly against current source, not taken on the
fixer's word:

- **CR-01** (`entity_hydrate_expand.py`/`relation_hydrate_expand.py`, commit `1827695`) — confirmed
  fixed. Both bodies now use `seed.get(...)` with an explicit `is None` check instead of a bare
  subscript, routing a malformed seed to `missing_seeds` with `malformed_seed: True` and a
  diagnostic naming the missing field, exactly mirroring the existing absent-graph-node path. The
  two new regression tests in `test_graph_half_parts.py`
  (`test_entity_hydrate_expand_reports_a_malformed_seed_missing_entity_name`,
  `test_relation_hydrate_expand_reports_a_malformed_seed_missing_src_or_tgt_id`) construct exactly
  the malformed-seed shape (a seed dict missing `entity_name` / missing `tgt_id`) that used to raise
  `KeyError`, and assert the new `missing_seeds` entry shape — they genuinely exercise the fixed
  path, not just a passing shape. Cross-checked against the actual committed evidence: the exact
  `KeyError: 'entity_name'` / `KeyError: 'src_id'` strings this fix targets are present verbatim in
  `parity_results/{hybrid,local,global}-comparison.json`'s `decomposed_run_record.stop_reason`, so
  the fix targets the real, previously-measured crash rather than a hypothetical one. Downstream
  consumers of `missing_seeds`/`entities`/`relations` (`join_roundrobin.py`) only read the
  `entities`/`relations` fields, never `missing_seeds`, so the new dict shape introduces no
  regression there.
- **WR-01** (`run_arm.py`, commit `35898e8`) — confirmed fixed. `MissingParityEnvKeyError` is
  defined, `_REQUIRED_ENV_KEYS` names all six keys `_build_clients` needs, and `_build_clients` now
  checks every key up front before constructing either client. The two new tests in
  `test_naive_arm_end_to_end.py` assert both the failure path (partial env → all four missing keys
  named on the exception) and the success path (all six keys present → both clients constructed) —
  real coverage of the fixed branch, not just an import check.
- **WR-03** (`parity_report.py`, commit `b54d7b8`) — confirmed fixed. `_degraded_but_vacuous_arms()`
  scans each arm's committed comparison file for a `completed` record with
  `decomposed_run_record.degraded=true` and an all-empty diff, and `main()`'s `--check-results` path
  now qualifies the clean line with the degraded arm names instead of printing a bare `clean (5
  arms)`. The real-data test
  (`test_degraded_but_vacuous_arms_on_the_real_committed_data_names_the_three_known_degraded_arms`)
  runs the function against the actual committed `parity_results/` directory and asserts it names
  exactly `hybrid`/`local`/`global` — this is a genuine assertion against production data, not a
  synthetic-only test.

All three fixes are correct, complete, and covered by tests that actually exercise the previously-
broken path. None are re-listed as findings below.

**WR-02** (AI-authored `declared_causes` in `human_findings.json`) was correctly skipped by the
fixer. CONTRACT §5 requires a human-authored cause; fabricating one to close the finding would
create a false attestation, which is a worse defect than the disclosed gap already on file. It
still holds in current source (`human_findings.json:12,26` still read `"recorded_by": "Claude (AI
agent, gsd-code-fixer)... NOT recorded by the human owner"`) and is carried forward below,
explicitly flagged as requiring human action rather than a code change, so the automated fix loop
does not keep re-selecting it.

A fresh pass over the rest of the scope surfaced one new finding: the CR-01 code fix changes what
would happen if the `hybrid`/`local`/`global` arms were re-run (a malformed seed now degrades one
item observably instead of crashing the whole node), but the committed evidence
(`PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md`, `parity_results/*.json`) was last regenerated
*before* the fix and still describes the old crash as the live, unrepaired state of the code. See
WR-04 below.

`embedder_query.py`'s `IN-01` (the `or`-chain treating an empty `"query"` the same as an absent one)
was not in the fixer's Critical+Warning scope and remains unchanged in current source — carried
forward below since it was never resolved, not because it is newly found.

No new Critical issues were found in this pass.

## Warnings

### WR-04: The committed parity evidence documents describe a crash that CR-01's fix has since changed the behavior of, without any note that the code has moved since the evidence was rendered

**File:** `databasise/evidence/PARITY-EVIDENCE.md:50,59,68,117,119,121,133,135,137`,
`databasise/evidence/parity_results/{hybrid,local,global}-comparison.json`

**Issue:** `PARITY-EVIDENCE.md`'s Verdict section states, for `hybrid`/`local`/`global`: "`hybrid`'s
decomposed run degraded before completing a real retrieval (node 'entity-hydrate-expand':
NodeExecutionError: 'entity_name' ...). ... Fixing that defect is out of this plan's scope." This
was accurate when rendered (commit `d110313`, before `1827695`), but `1827695` has since changed
`entity_hydrate_expand.py`/`relation_hydrate_expand.py` so that the exact seed shape that produced
`NodeExecutionError: 'entity_name'` / `'src_id'` no longer raises at all — it now degrades one seed
into `missing_seeds` and lets the run continue. The committed `parity_results/{hybrid,local,global}
-comparison.json` files (and the prose that reads them) were never regenerated after the fix
landed, so they currently assert, as the live state of the code, a crash that the code no longer
produces. This is a live discrepancy between what's committed as evidence and what the current
source actually does — a reader trusting `PARITY-EVIDENCE.md`'s Verdict section today would
reasonably (and incorrectly) conclude that `hybrid`/`local`/`global` still crash the same way,
when in fact re-running the comparison would very likely change the measured diffs (a
degraded-but-continuing run reaches further downstream nodes — `assemble`, `budget-*`, `generate`,
etc. — that never executed in the crash-truncated run these numbers reflect, per
`PARITY-EVIDENCE.md`'s own list of never-dispatched nodes at lines 117-121).

**Fix:** Either (a) re-run `run_comparison.py` for the three affected arms and re-render
`parity_report.py` now that CR-01 has landed, replacing the stale crash-based numbers with whatever
the degraded-but-completing run actually measures, or (b) if a re-run is deliberately deferred to a
later plan, add an explicit note to `PARITY-EVIDENCE.md`'s Verdict section (and ideally a dated
marker in the comparison JSON itself) stating that the underlying `NodeExecutionError` this
document describes was patched by commit `1827695` after this evidence was rendered, so the
document's own crash description is understood as historical rather than current.

### WR-02: `human_findings.json`'s two `declared_causes` entries are AI-authored, not human-authored, despite CONTRACT §5 requiring a human-authored cause for every named excursion

**Requires human action, not a code change — do not re-select for the automated fix loop.**

**File:** `databasise/evidence/human_findings.json:12-14,26-27`, `databasise/evidence/DECLARED-DEVIATIONS.md:9-10`

**Issue:** Both `declared_causes` entries still carry `"recorded_by": "Claude (AI agent,
gsd-code-fixer) — commit 2ce3c30; NOT recorded by the human owner, despite this file's own name"`.
CONTRACT §5's parity-not-gain record requires a human-reasoned cause for a named excursion; an
AI-authored cause does not satisfy that requirement no matter how honestly it discloses its own
provenance. The fixer correctly declined to fabricate a human attribution for this iteration — that
would be a false attestation, strictly worse than the disclosed gap.

**Fix:** The human owner (christopher@deocracy.org) needs to actually review the two named
excursions in `DECLARED-DEVIATIONS.md` and re-record `declared_causes` with their own reasoning and
`recorded_by`. No code change closes this; the automated fix loop should stop selecting it and
instead surface it as a pending human task.

## Info

### IN-01: `embedder_query._query_text`'s `or`-chain silently treats a genuinely empty query string the same as an absent key

**File:** `databasise/parts_core/lightrag/embedder_query.py:23-31`

**Issue:** Unchanged since the prior review — not newly introduced. `keywords_output.get("query")
or keywords_output.get("text") or ""` treats a present-but-empty `"query"` value identically to an
absent one, falling through to `.get("text")` and then to `""`. `keywords.py`'s `_keywords_body`
always stamps `config["query"]` (which `run_arm._inject_query` always sets to the real user query
text), so this remains a low-probability defensive edge case rather than an observed defect.

**Fix:** `keywords_output.get("query") if keywords_output.get("query") is not None else
keywords_output.get("text", "")` if the "explicitly empty" vs. "absent" distinction ever needs to
be preserved; optional given the low current likelihood of it mattering.

---

_Reviewed: 2026-09-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
