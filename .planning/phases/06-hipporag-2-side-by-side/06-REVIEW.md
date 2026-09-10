---
phase: 06-hipporag-2-side-by-side
reviewed: 2026-09-10T03:28:20Z
depth: standard
files_reviewed: 81
files_reviewed_list:
  - databasise/eval/bundle.py
  - databasise/eval/calibration.py
  - databasise/eval/__init__.py
  - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
  - databasise/evidence/eval-bundles/bundle@v1/bundle.json
  - databasise/evidence/eval-bundles/bundle@v1/bundle.sha256
  - databasise/evidence/eval-bundles/bundle@v1/usage.jsonl
  - databasise/evidence/eval-bundles/judge-prompt-v1.txt
  - databasise/evidence/EVAL-BUNDLE-V1.md
  - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
  - databasise/evidence/f07_report.py
  - databasise/evidence/F-14-SEAM-INVARIANCE.md
  - databasise/evidence/FALSIFIER-5-EVIDENCE.md
  - databasise/evidence/HIPPORAG-PORT-RECORD.md
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/parity/build_corpus_fixture.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_cross_modality.py
  - databasise/parts_core/hipporag/assemble_result.py
  - databasise/parts_core/hipporag/chunk_embed.py
  - databasise/parts_core/hipporag/dpr_fallback.py
  - databasise/parts_core/hipporag/entity_fact_embed.py
  - databasise/parts_core/hipporag/fact_edges.py
  - databasise/parts_core/hipporag/fact_filter.py
  - databasise/parts_core/hipporag/fact_score.py
  - databasise/parts_core/hipporag/graph_augment_persist.py
  - databasise/parts_core/hipporag/__init__.py
  - databasise/parts_core/hipporag/openie.py
  - databasise/parts_core/hipporag/passage_edges.py
  - databasise/parts_core/hipporag/ppr.py
  - databasise/parts_core/hipporag/reset_vector_join.py
  - databasise/parts_core/hipporag/synonymy_edges.py
  - databasise/parts/registry.py
  - databasise/pyproject.toml
  - databasise/seam/compare.py
  - databasise/seam/engine.py
  - databasise/seam/__init__.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/selectors.py
  - databasise/stores/graph.py
  - databasise/stores/vector.py
  - databasise/tests/eval/conftest.py
  - databasise/tests/eval/__init__.py
  - databasise/tests/eval/test_bundle_versioning.py
  - databasise/tests/eval/test_calibration.py
  - databasise/tests/evidence/test_cross_modality_record.py
  - databasise/tests/evidence/test_f07_record.py
  - databasise/tests/evidence/test_f14_record.py
  - databasise/tests/evidence/test_falsifier5_record.py
  - databasise/tests/evidence/test_hipporag_port_record.py
  - databasise/tests/fixtures/eval-corpus/MANIFEST.json
  - databasise/tests/fixtures/eval-corpus/README.md
  - databasise/tests/mcp/test_dual_transport_parity.py
  - databasise/tests/mcp/test_tool_growth_invariant.py
  - databasise/tests/parity/test_cross_modality_isolation.py
  - databasise/tests/parts_core/hipporag/conftest.py
  - databasise/tests/parts_core/hipporag/__init__.py
  - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
  - databasise/tests/parts_core/hipporag/test_graph_construction.py
  - databasise/tests/parts_core/hipporag/test_index_side_extraction.py
  - databasise/tests/parts_core/hipporag/test_ppr.py
  - databasise/tests/parts_core/hipporag/test_registration.py
  - databasise/tests/parts_core/hipporag/test_thirteen_positions.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/seam/test_compare.py
  - databasise/tests/seam/test_cross_modality_run.py
  - databasise/tests/seam/test_leak.py
  - databasise/tests/seam/test_mutable_store_exclusion.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_store_isolation.py
  - databasise/tests/stores/test_graph_bulk_export.py
  - databasise/tests/stores/test_vector_score_all.py
  - databasise/tests/stores/test_vector_self_knn.py
  - databasise/tests/test_embed_startup.py
  - databasise/wirings/hipporag/base.json
  - databasise/wirings/hipporag/__init__.py
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/resolve.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-09-10T03:28:20Z
**Depth:** standard
**Files Reviewed:** 81
**Status:** issues_found

## Summary

Reviewed the HippoRAG 2 port (13 registered parts, the new `hipporag/base.json` wiring), the
`seam.compare`/`seam.engine` comparison surface, the new `stores/graph.py` bulk-export and
`stores/vector.py` `score_all`/`self_knn` capabilities, the REST/MCP transports, and the eval/parity
harness code. The part bodies themselves are careful, well-tested, and consistent with the
project's refusal-over-silent-narrowing house style — I traced the query-side chain
(`fact-score` → `fact-filter` → `reset-vector-join`/`dpr-fallback` → `ppr` → `assemble-result`) and
the index-side chain (`chunk-embed` → `openie` → `entity-fact-embed` → `{fact,passage,synonymy}-edges`
→ `graph-augment-persist`) end to end, confirmed the guard-aware `__eq__`/`__ne__` fix in
`fact_filter.py` behaves correctly under both `!=` orderings, and confirmed store isolation between
the LightRAG and HippoRAG arms holds at the directory level (`store_namespaces` in each wiring
resolve to disjoint on-disk paths, and vector namespace strings never collide) via both the code
path (`Databasise._build_stores`) and the existing isolation tests.

The one finding I consider blocking is not inside the HippoRAG port itself but in what the seam
exposes around it: `Databasise.ingest()`/`delete_document()` are hardcoded to the LightRAG-only
`wirings/lightrag/corpus-ingest.json`/`corpus-delete.json` files, and no equivalent HippoRAG wiring
exists — so the public write surface (in-process, REST, and MCP alike) has no way to populate or
mutate HippoRAG's index at all. This directly contradicts this phase's own `COVERAGE.md`, which
states `ingest`/`delete` "remain reachable identically for both LightRAG and HippoRAG arms." A
caller who ingests a document and then queries/compares against HippoRAG's capability set gets a
silent, unrefused empty HippoRAG result rather than an error naming the gap.

I also found one wiring/registry inconsistency (`entity-fact-embed`'s node-level `effects` in
`hipporag/base.json` under-declares relative to its own registered `Part`, and to what the port's
own evidence record says it should be) and two minor code-quality items. Everything else I traced —
Faiss/Cozo store buffering and read-your-writes semantics, the `MultiNamespaceVectorStore.select`
lazy-cache (verified race-free given this codebase's cooperative-async model, since `select()`
itself never awaits), the MACH-11 store-touch correlation, and the `compare()`/`compare_arms`
fan-out — held up under adversarial tracing.

## Critical Issues

### CR-01: `ingest()`/`delete_document()` never reach HippoRAG's index — contradicts this phase's own coverage claim

**File:** `databasise/seam/engine.py:180-190`, `databasise/seam/engine.py:596-729`
**Also see:** `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md:19-22`

**Issue:** `Databasise.ingest()` and `Databasise.delete_document()` both dispatch a single, hardcoded
wiring file:

```python
_INGEST_WIRING_PATH = (
    Path(__file__).resolve().parent.parent / "wirings" / "lightrag" / "corpus-ingest.json"
)
_INGEST_NODE_ID = "full-ingest"
...
_DELETE_WIRING_PATH = (
    Path(__file__).resolve().parent.parent / "wirings" / "lightrag" / "corpus-delete.json"
)
_DELETE_NODE_ID = "full-delete"
```

There is no `databasise/wirings/hipporag/corpus-ingest.json` (or delete equivalent) anywhere in the
repository — `find databasise/wirings -iname '*.json'` lists only `hipporag/base.json` and the
LightRAG arm/corpus files. HippoRAG's own `chunk-embed` node (the sole entry point for all seven of
its index-side positions) is only ever populated via `databasise/parity/build_hipporag_index.py`, a
standalone harness that bypasses `Databasise` entirely and drives `runner.scheduler.run_wiring`
directly — and that harness has never been invoked in this environment (06-08-SUMMARY.md).

This phase's own `COVERAGE.md` states the opposite is true:

> "Every other operation (`query`, `ingest`, `delete`, ...) is unchanged by this phase — ... all of
> which remain reachable identically for both LightRAG and HippoRAG arms with no operation-level
> change (§18.5's own modality-agnosticism holding by construction...)"

That claim is false for `ingest`/`delete`: those two operations are LightRAG-only by construction,
not by any HippoRAG-specific refusal — a caller cannot tell "HippoRAG has no ingest path" from "the
document just has not landed yet," because no error is raised. Concretely: a consumer that (1)
calls `POST /documents` (or the `ingest` MCP tool, or `engine.ingest()`) to add a document, then (2)
calls `compare()`/`query()` with a selector resolving to HippoRAG (e.g.
`Selector(capability=["reads_graph"])`) gets a normal-looking `ResponseEnvelope` with an empty
`evidence` list and `partial=False`/`degraded=False` — because `chunk-embed` runs every query with
no `documents` in its config and legitimately short-circuits to zero cost (this is the documented,
correct behavior for a *query*-time dispatch of that node — see `chunk_embed.py`'s own
"Unconfigured-run precedent" note). The empty result is indistinguishable from "HippoRAG found
nothing relevant" versus "HippoRAG's index has never been built," which undermines the phase's own
stated core value ("the same corpus, the same seam, N modalities running side-by-side and
comparable").

This is a different, and more severe, condition than the two evidence records
(`FALSIFIER-5-EVIDENCE.md`, `CROSS-MODALITY-EVIDENCE.md`) that are *deliberately* recorded BLOCKED
because a real run was never authorized — those are honest "not run yet" states with a defined entry
criterion. This finding is a structural gap: there is no wiring file that *could* be run through the
seam's own `ingest`/`delete` operations to populate HippoRAG's index at all, even if spend were
authorized today.

**Fix:** Either (a) add a `databasise/wirings/hipporag/corpus-ingest.json` (and delete) analog and
have `ingest()`/`delete_document()` route to the wiring matching the caller's intended modality (the
`ingest` operation would need its own selector concept, since — unlike `query` — there is no query
object to resolve a capability from), or (b) if HippoRAG's index is intentionally out of scope for
the public write surface in this phase (research/parity-only), correct `COVERAGE.md` to say so
explicitly rather than claim identical reachability, and have `ingest()`/`delete_document()` raise a
named refusal (mirroring `UnknownDocumentError`'s house style) when no ingest path exists for the
resolved/target modality, rather than silently no-op-ing on every subsequent HippoRAG query.

## Warnings

### WR-01: `entity-fact-embed`'s wiring-declared `effects` under-declares relative to its own Part and its own evidence record

**File:** `databasise/wirings/hipporag/base.json:18-24`

**Issue:** Every other HippoRAG node whose registered `Part` carries an "additive effects
discrepancy" has its wiring-node-level `effects` list updated to match (e.g. `chunk-embed`'s node
declares `["calls_embedding", "writes_vector", "writes_kv"]`, matching
`HIPPORAG_CHUNKER_EMBEDDER_PART.effects` exactly). `entity-fact-embed`'s node, however, still
declares only:

```json
"entity-fact-embed": {
  "component": "hipporag/entity-fact-embedder@0.1.0",
  "effects": ["calls_embedding", "writes_vector"],
  ...
}
```

while its registered `Part` (`databasise/parts_core/hipporag/entity_fact_embed.py:168`) declares
`effects=["calls_embedding", "writes_vector", "writes_kv"]` — the `writes_kv` effect 06-07-PLAN.md
explicitly added (the `fact:<id> -> {chunk_ids}` KV write `reset_vector_join.py` reads back). The
port's own evidence record, `databasise/evidence/HIPPORAG-PORT-RECORD.md:60`, states in its own
reconciliation table that `entity-fact-embed`'s effects should be
`calls_embedding, writes_vector, writes_kv` — so this is a documented intent the wiring file itself
does not carry out.

This is not a runtime bug: `CapabilityScopedStores.require` and every effect-union computation in
this codebase (`_wiring_effects`, `_accounted_store_keys`, `parse_wiring`'s extra-effects check) is
explicitly keyed off the registered `Part`'s own effects, never the wiring node's own (CR-01,
documented repeatedly across `selectors.py`, `engine.py`, `scheduler.py`, `validator/parse.py`,
`validator/blast_radius.py`), and a wiring node's `effects` is permitted to be a strict subset of its
Part's. It is, however, a real audit-trail gap: `HIPPORAG-PORT-RECORD.md`'s own
`test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set` only checks
the *union* of effects across the whole wiring, and since `chunk-embed` already contributes
`writes_kv` to that union independently, this specific node's incomplete declaration passes that
test undetected — exactly the kind of drift the additive-effects convention exists to make visible
per-node, not just in aggregate.

**Fix:** Update `entity-fact-embed`'s `effects` array in `databasise/wirings/hipporag/base.json` to
`["calls_embedding", "writes_vector", "writes_kv"]`, matching its own Part and its own evidence
record. Consider tightening `test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set`
(or adding a sibling test) to check per-node correspondence, not only the aggregate union, so a
future addition in one node cannot mask a missing declaration in another.

### WR-02: `entity_fact_embed.py` reports only the entity-embedding call's `resolved_model_identity`, silently dropping the fact-embedding call's own

**File:** `databasise/parts_core/hipporag/entity_fact_embed.py:159`

**Issue:** `_entity_fact_embed_body` makes two separate `embedding_client.embed(...)` calls — one for
`entity_texts`, one for `fact_texts` — and correctly sums both calls' token accounting via
`_sum_token_accountings`, but the returned `resolved_model_identity` is hardcoded to
`entity_embed_result.resolved_model_identity` only:

```python
return {
    ...
    "tokens": _sum_token_accountings([entity_embed_result.tokens, fact_embed_result.tokens]),
    "resolved_model_identity": entity_embed_result.resolved_model_identity,
}
```

In production this is almost certainly harmless (one embedding client resolves to one stable model
identity per process), but if a future client ever resolves a different identity per call (a
routing/fallback client, a test double simulating drift), the fact-vector write's own resolved
identity is silently discarded from this node's reported output — no assertion, no refusal, no
comparison between the two calls' identities the way `openie.py`'s own `_sum_token_accountings`
pattern at least keeps consistent per-call token counts.

**Fix:** Either assert `entity_embed_result.resolved_model_identity ==
fact_embed_result.resolved_model_identity` (raising or recording a refusal on mismatch, matching
this codebase's fail-loud house style), or report both identities distinctly if a genuine divergence
is possible.

## Info

### IN-01: `graph_augment_persist.py` iterates `weight_by_pair` in insertion order rather than sorted, unlike its own sibling `_canonical_pair` writers

**File:** `databasise/parts_core/hipporag/graph_augment_persist.py:78-82`

**Issue:** `fact_edges.py`/`passage_edges.py`/`synonymy_edges.py` all emit their own `edges` list
sorted by canonical pair (`sorted(weight_by_pair.items())`), but `graph_augment_persist.py`'s own
edge-upsert loop iterates `weight_by_pair.items()` unsorted:

```python
for pair, weight in weight_by_pair.items():
    src, tgt = pair
    await graph_store.upsert_edge(src, tgt, {...})
```

Each `upsert_edge` call is independent and idempotent per key, so this has no observed correctness
effect today (order does not change the final persisted graph), but it breaks the otherwise
consistent "always emit/iterate in canonical sorted order" convention every sibling module in this
port follows, which is otherwise relied on for reproducibility/determinism elsewhere in this
codebase.

**Fix:** `for pair, weight in sorted(weight_by_pair.items()):` for consistency with this module's own
siblings, at negligible cost.

### IN-02: `self_knn`'s self-exclusion assumes the self-match is always within the returned `top_k + 1` window

**File:** `databasise/stores/vector.py:272-315`

**Issue:** `FaissVectorStore.self_knn` requests `top_k + 1` neighbours per row and filters out
`neighbour_id == self_doc_id` wherever it appears in the returned window. Since a self-match on a
cosine-normalised index always scores the maximum possible value (1.0), it is safe under ordinary
conditions — but if two or more stored entities carry bit-identical embeddings (a plausible
degenerate case for near-duplicate entity surface forms), Faiss's internal tie-break order for
equal-score candidates is not documented as stable, and it is theoretically possible for the true
self-match to fall outside the requested `top_k + 1` window if there are more than `top_k` other
exact-score ties. In that case the method does not error or misbehave — it simply returns `top_k`
genuine (non-self) neighbours, since there is nothing to filter — but the module's own docstring
("requests `top_k + 1` ... so the self-match can be dropped") implicitly assumes the self-match is
always present in the window, which is not guaranteed under duplicate-embedding ties.

**Fix:** No functional change needed given the graceful degradation already present; consider a
one-line docstring caveat noting the behavior under duplicate-embedding ties, since a future reader
relying on "always excludes exactly one self-match" as a strict guarantee would be mistaken.

---

_Reviewed: 2026-09-10T03:28:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
