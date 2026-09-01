---
phase: 03-lightrag-query-side
reviewed: 2026-09-01T00:00:00Z
depth: standard
files_reviewed: 61
files_reviewed_list:
  - databasise/clients/base.py
  - databasise/clients/__init__.py
  - databasise/clients/openai_compat.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/parity_report.py
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
  - databasise/runner/scheduler.py
  - databasise/stores/graph.py
  - databasise/stores/vector.py
  - databasise/tests/clients/test_capability_scoped_clients.py
  - databasise/tests/clients/test_openai_compat.py
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
  - databasise/tests/stores/test_graph_frozen_bugs.py
  - databasise/tests/stores/test_graph.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_import_boundary.py
  - databasise/tests/validator/test_falsifier2_evidence.py
  - databasise/tests/validator/test_falsifier2_probes.py
  - databasise/tools/check_import_boundary.py
  - databasise/wirings/__init__.py
  - databasise/wirings/resolve.py
  - v1/scripts/run_parity_ingest.py
findings:
  critical: 1
  warning: 1
  info: 1
  total: 3
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-01
**Depth:** standard
**Files Reviewed:** 61 Python files (non-source `.md`/`.json`/`.lock`/`.example`/`pyproject.toml` paths in the phase's file list were cross-checked against the code above for accuracy, not reviewed as findings targets in their own right)
**Status:** issues_found

## Summary

This is a re-review of the post-fix state at HEAD, after CR-01/WR-01/WR-02/WR-03 from the prior
review (`03-REVIEW-FIX.md`) were applied in commits `350caad`/`c339cb9`/`e20df3a`/`5105aa6`. All
four fixes hold up under direct re-reading — the narrowed Cozo re-create guard, the
`FaissVectorStore.iter_vectors()` accessor, the `ts.done()`-skip invariant comment, and the
`run_comparison.py` relation-id dual-shape extraction are all present and correct as described.
IN-01 (the `_load_env_file` duplication) was explicitly skipped as out-of-scope and remains open —
carried forward below at the same Info tier, since re-verification confirms the behavioral
asymmetry it names still exists.

This pass found one new, high-confidence correctness bug that the prior review did not surface:
the query text `embedder-query` is supposed to embed for every arm that keeps the `keywords` node
(`hybrid`/`local`/`global` — three of the five arms) silently collapses to an empty string,
because the real `keywords` part body's output shape and `embedder-query`'s own reader of that
output were never reconciled after `keywords` got a real body in plan 03-05. The one unit test
covering this path stubs a shape that does not match what `keywords.py` actually returns, which is
why this has gone undetected. See CR-01 below.

## Critical Issues

### CR-01: `embedder-query` embeds an empty string for every arm that keeps the `keywords` node — `hybrid`/`local`/`global` retrieval is built on a null query vector

**File:** `databasise/parts_core/lightrag/embedder_query.py:23-31`, `databasise/parts_core/lightrag/keywords.py:105-131`

**Issue:** `_query_text` reads the query to embed from `ctx.inputs["keywords"]` whenever the
`keywords` node is one of `embedder-query`'s deps:

```python
def _query_text(ctx: NodeContext) -> str:
    keywords_output = ctx.inputs.get("keywords")
    if keywords_output is not None:
        if isinstance(keywords_output, dict):
            return str(keywords_output.get("query") or keywords_output.get("text") or "")
        return str(keywords_output)
    config = ctx.config or {}
    return str(config.get("query", ""))
```

But the real `lightrag/keyword-extractor@0.1.0` part body (`keywords.py`'s `_keywords_body`, both
the live-call branch at line ~122-131 and the pinned-replay branch at line ~109-115) never emits a
`"query"` or `"text"` key — its return dict only ever carries
`high_level_keywords`/`low_level_keywords`/`tokens`(/`resolved_model_identity`). So whenever
`embedder-query` depends on `keywords` (`ctx.inputs.get("keywords")` is a non-`None` dict — true
for every arm except `naive`/`bypass`, which remove the `keywords` node entirely and set
`embedder-query`'s `deps: []`), `keywords_output.get("query")` and `.get("text")` both miss, and
`_query_text` returns `""`. The `config["query"]` fallback branch is therefore dead code for every
arm that has a `keywords` dependency, even though `databasise/parity/run_arm.py`'s
`_inject_query()` carefully stamps `config["query"]` onto the `embedder-query` node for *every*
arm (it has no way to know this stamp will be ignored).

Concretely: for the `hybrid`, `local`, and `global` arms (per `databasise/wirings/lightrag/
base.json`, `"embedder-query": {"deps": ["keywords"], ...}`, unmodified by any of those three
arms' patches), every real run — including `databasise/parity/run_comparison.py`'s pinned parity
path, where `_inject_pinned_keywords` short-circuits `keywords` to return the exact same
`{"high_level_keywords": [...], "low_level_keywords": [...]}` shape — embeds the literal empty
string as the query vector for `entity-lookup`, `relation-lookup`, and `chunk-vector`. This is not
a refusal and not an exception: `client.embed([""])` succeeds and returns *some* vector, and
`store.query(vector, top_k=...)` returns *some* top-k neighbours — silently wrong retrieval
results with no error signal, for three of the five published arms.

The one existing unit test for this path,
`databasise/tests/parts_core/lightrag/test_naive_arm_parts.py::test_embedder_query_prefers_the_keywords_node_output_when_present`,
passes `inputs={"keywords": {"query": "keywords-path text"}}` — a shape `keywords.py`'s real body
never produces — so it exercises a code path that is unreachable in production and gives false
confidence. No test in this phase drives `hybrid`/`local`/`global` end to end through
`runner.scheduler.run_wiring` with the real `keywords` and `embedder-query` bodies both live
(`test_storage_audit.py`'s only full scheduler run uses the `naive` arm, which has no `keywords`
dependency at all); the gap is invisible to the current test suite.

**Fix:** Reconcile the two node contracts. The minimal fix is to have `keywords.py`'s
`_keywords_body` also emit the resolved query text it actually used for entity/relation retrieval
(v1's own `hybrid`/`local`/`global` behavior embeds a keyword-derived string, not the raw question
— check `v1/lightrag/operate.py`'s `_get_node_data`/`_get_edge_data` call sites for the exact
hl/ll-keyword-joining convention to port), e.g.:

```python
    return {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        "query": query,  # or the v1-equivalent keyword-derived string, per the arm's own mode
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }
```

and the same addition to the pinned-replay branch's return dict. Then fix the misleading unit test
to assert against the real shape, and add an integration-level test that runs the `hybrid` (or
`local`/`global`) arm end to end through `runner.scheduler.run_wiring` with real `keywords` and
`embedder-query` bodies and a spy embedding client, asserting the text actually embedded is
non-empty and derived from the keyword extraction — the exact gap this review found no coverage
for.

## Warnings

### WR-01: `_validated_token_allowance` does not refuse a negative `config.token_allowance`, unlike its sibling `_validated_max_concurrency`

**File:** `databasise/runner/scheduler.py:348-361`

**Issue:** `_validated_max_concurrency` explicitly refuses (`InvalidMaxConcurrencyError`) any
declared value below 1, at validation time, before any node dispatches. `_validated_token_allowance`
only catches a value `int()` cannot coerce at all (`TypeError`/`ValueError`) — it never checks the
coerced result is non-negative:

```python
def _validated_token_allowance(node_id: str, config: dict[str, Any] | None) -> int:
    raw = DEFAULT_TOKEN_ALLOWANCE
    if config:
        raw = config.get("token_allowance", DEFAULT_TOKEN_ALLOWANCE)
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise InvalidTokenAllowanceError(node_id, raw) from None
```

A wiring (untrusted author input, per this same module's own CR-01 docstring paragraph) that
declares `config.token_allowance: -1` sails through validation. Downstream, `runner/budget.py`'s
`meter()` computes `state = "within_budget" if spent <= allowance else "halted"` — with
`allowance=-1` and `spent=0` (the default for a node that makes no metered call at all), `0 <= -1`
is `False`, so the node is stamped `"halted"` even though it spent nothing. Every node sharing that
config value halts the run, with no named refusal pointing at the offending node the way
`InvalidMaxConcurrencyError` does for the analogous `max_concurrency` case — the module's own
stated contract ("refused at validation, before any node is dispatched, naming the offending node
id") holds for one sibling field and silently doesn't for the other.

**Fix:** Mirror `_validated_max_concurrency`'s shape:

```python
def _validated_token_allowance(node_id: str, config: dict[str, Any] | None) -> int:
    raw = DEFAULT_TOKEN_ALLOWANCE
    if config:
        raw = config.get("token_allowance", DEFAULT_TOKEN_ALLOWANCE)
    try:
        allowance = int(raw)
    except (TypeError, ValueError):
        raise InvalidTokenAllowanceError(node_id, raw) from None
    if allowance < 0:
        raise InvalidTokenAllowanceError(node_id, allowance)
    return allowance
```

## Info

### IN-01 (carried forward, still open): `_load_env_file` is duplicated between `run_arm.py` and `v1_arm.py`, with drifted absent-file behavior

**File:** `databasise/parity/run_arm.py:74-93`, `databasise/parity/v1_arm.py:98-116`

**Issue:** Re-verified against the current HEAD — this finding from the prior review was
explicitly skipped as out of scope for `fix_scope=critical_warning` and no code change touched
either function. Both modules still carry a near-identical `KEY=VALUE` `.env.parity` parser, but
`run_arm._load_env_file` raises `MissingParityEnvError` when the file is absent while
`v1_arm._load_env_file` silently returns `{}`. In the normal `compare_arm_on_query` flow this
asymmetry is masked (the `run_arm`-imported copy is called first and raises before `run_v1_arm` is
ever reached), but a caller that invokes `run_v1_arm`/`v1_arm.main()` directly with a missing
`.env.parity` gets silent fallthrough to `os.environ` rather than the same named refusal
`run_arm.py`'s copy gives every other caller.

**Fix:** Unchanged from the prior review's suggestion — a one-line comment on each definition
cross-referencing the sibling copy and stating the asymmetry is deliberate (or, if it is not
deliberate, make `v1_arm._load_env_file` raise the same way). Still Info-tier and still optional
per the original invocation's scope.

---

_Reviewed: 2026-09-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
