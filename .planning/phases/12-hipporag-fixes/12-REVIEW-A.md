---
phase: 12-hipporag-fixes
lane: A
reviewed: 2026-10-19T00:00:00Z
depth: deep
files_reviewed: 32
files_reviewed_list:
  - databasise/parts_core/hipporag/assemble_result.py
  - databasise/parts_core/hipporag/chunk_embed.py
  - databasise/parts_core/hipporag/document_remover.py
  - databasise/parts_core/hipporag/dpr_fallback.py
  - databasise/parts_core/hipporag/entity_fact_embed.py
  - databasise/parts_core/hipporag/fact_edges.py
  - databasise/parts_core/hipporag/fact_score.py
  - databasise/parts_core/hipporag/graph_augment_persist.py
  - databasise/parts_core/hipporag/__init__.py
  - databasise/parts_core/hipporag/openie.py
  - databasise/parts_core/hipporag/passage_edges.py
  - databasise/parts_core/hipporag/ppr.py
  - databasise/parts_core/hipporag/qa.py
  - databasise/parts_core/hipporag/reset_vector_join.py
  - databasise/parts_core/hipporag/synonymy_edges.py
  - databasise/parts/registry.py
  - databasise/wirings/hipporag/base.json
  - databasise/wirings/hipporag/corpus-delete.json
  - databasise/wirings/hipporag/corpus-ingest.json
  - databasise/evidence/HIPPORAG-PORT-RECORD.md
  - databasise/tests/parts_core/hipporag/conftest.py
  - databasise/tests/parts_core/hipporag/test_assemble_result.py
  - databasise/tests/parts_core/hipporag/test_document_remover.py
  - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
  - databasise/tests/parts_core/hipporag/test_graph_construction.py
  - databasise/tests/parts_core/hipporag/test_index_side_extraction.py
  - databasise/tests/parts_core/hipporag/test_ppr.py
  - databasise/tests/parts_core/hipporag/test_qa_node.py
  - databasise/tests/parts_core/hipporag/test_registration.py
  - databasise/tests/parts_core/hipporag/test_thirteen_positions.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/evidence/test_hipporag_port_record.py
findings:
  critical: 1
  warning: 4
  info: 5
  total: 10
status: issues_found
---

# Phase 12: Code Review Report (Lane A)

**Reviewed:** 2026-10-19
**Depth:** deep
**Files Reviewed:** 32
**Status:** issues_found

## Summary

Lane A covers the HippoRAG part bodies, the three HippoRAG wirings, the registry merge, the port record and their tests. I traced the call chains into the stores (`stores/graph.py`, `stores/vector.py`, `stores/kv.py`), the capability proxy (`parts_core/__init__.py`), the scheduler (`runner/scheduler.py`), the refusal type (`seam/refusals.py`) and the engine's ingest and delete paths (`seam/engine.py`). The lane's tests pass: `pytest -q tests/parts_core/hipporag tests/parts/test_registry.py tests/evidence/test_hipporag_port_record.py` gives 99 passed.

The D-01 id translation, the D-04 per-chunk merge, the D-06 fact provenance union, the D-08 refusal path (the 10-entry cap and the closed-code filter sit in `ForeignEngineRefusalError`), the D-17 single embed and the D-12 remover's fact and co-occurrence subtraction all trace correctly through the stores' pending-buffer semantics.

One defect was reproduced. Re-ingesting an unchanged document deletes synonymy edges that another document's ingest created, and the D-05 new-entity rule never rebuilds them. A scratch probe showed it: after ingesting d1, ingesting d2, then re-ingesting d1 unchanged, all five d2-to-d1 synonymy edges were gone. The required re-ingest test only covers a synonym pair that lives inside one document, so it does not catch this. The other findings are an unguarded config read, a degenerate PPR path that silently returns nothing, an OpenIE validation gap that contradicts the port record's own claim, and config keys that HIPP-18's text says must be gone.

## Narrative Findings (AI reviewer)

## Critical Issues

### A-CR-01: Re-ingesting an unchanged document deletes another document's synonymy edges

**File:** `databasise/parts_core/hipporag/document_remover.py:125-134` (with `entity_fact_embed.py:140-141`, `synonymy_edges.py:55-61`)

**Issue:** On re-ingest, the remover runs before the new version is written. It treats every manifest entity that has no edge to a surviving chunk as an orphan and calls `graph.delete_node(entity)` (line 132). `CozoGraphStore.delete_node` (`stores/graph.py:395-404`) puts every disk edge of that entity into `_pending_edge_rms`, and that includes synonymy edges created by *other* documents' ingests. The run then adds the entity back. `entity-fact-embed` marks it new, and `synonymy-edges` recomputes only that entity's own top-k (`self_knn(ids=new_refs)`). An edge that came from the other side, where a later document's entity Y had X in its top-k but X's top-k does not contain Y, is never rebuilt. `graph-augment-persist` cannot restore it either, because `get_edge` returns `None` for a hidden key.

**Reproduced:** d1 has `xray` and five near neighbours `a1..a5`. d2 has `yankee`. Ingest d1, ingest d2, then re-ingest d1 unchanged. Before the re-ingest the synonymy edges were `(a1..a4, yankee)` and `(xray, yankee)`. After it there were none, and the graph's edge set was not equal to its previous state. This breaks D-12's stated outcome ("re-ingesting the same document keeps its synonymy edges"). It is also data loss: an idempotent operation on document A destroys graph structure contributed by document B, and PPR results change. D-05's accepted asymmetric recall covers new entities, not the deletion of existing edges. `test_reingesting_a_document_keeps_its_synonymy_edges` (`tests/seam/test_hipporag_write_path.py:439-467`) only checks the films/movies pair, which lives inside one document, so the defect passes it.

**Fix:** Do not delete an entity that the same run adds back. The cleanest form keeps the remover's chunk, fact and co-occurrence work where it is and moves the orphan sweep after the writes:
```jsonc
// corpus-ingest.json: the sweep runs last and sees the re-added passage edges
"orphan-sweep": { "component": "hipporag/document-remover@0.1.0", "config": {"phase": "orphans"},
                  "deps": ["graph-augment-persist"], ... }
// corpus-delete.json: run both phases in one node (or two nodes, chained)
```
```python
# document_remover.py: phase "content" skips the orphan block (lines 125-134);
# phase "orphans" deletes manifest entities that still have no chunk-prefixed neighbour.
```
This also makes the `removed_entities` / `new_entities` override unnecessary. If the node split is not wanted, the remover can instead return each orphan's synonymy edges (`pair -> synonymy_weight`), and `graph-augment-persist` can restore every returned edge whose two endpoints are both present at the end of the run. In either case, add a cross-document regression test that has the asymmetric top-k shape described above.

## Warnings

### A-WR-01: `assemble-result` reads `ctx.config` without a None guard and accepts a negative `top_k`

**File:** `databasise/parts_core/hipporag/assemble_result.py:52`

**Issue:** `ctx.config.get("top_k", 5)` raises `AttributeError` when `config` is `None`. `NodeContext.config` is typed `dict | None`, and the scheduler passes `node.config` through unchanged. Every other HippoRAG part uses `ctx.config or {}`. A wiring variant or patch that drops this node's config block crashes the query, and the failure surfaces as an opaque node fault. `int(...)` is also never range-checked, so `top_k: -1` silently cuts the last item instead of refusing, and `0` silently returns no evidence.

**Fix:**
```python
top_k = int((ctx.config or {}).get("top_k", 5))
if top_k < 1:
    raise ValueError(f"{ctx.node_id!r}: config.top_k must be >= 1, got {top_k}")
selected_items = selected_items[:top_k]
```

### A-WR-02: A degenerate PPR reset vector now produces an empty answer and no evidence, with no degradation signal

**File:** `databasise/parts_core/hipporag/assemble_result.py:49-51`, `databasise/parts_core/hipporag/ppr.py:69-75`

**Issue:** When the guard did not fire but every reset entry is 0 or negative, `ppr` returns all-zero scores (lines 69-75). This happens when the surviving facts score at or below 0 and min-max normalisation gives every passage 0, which is always the case for a single-chunk corpus because `_min_max_normalise` returns zeros when the span is 0. The new D-20 filter `item["score"] > 0.0` then drops every item. `qa` answers `fail_response`, evidence is empty, and the run reports `degraded=False`, even though `dpr-fallback` computed usable passages in the same run. Before Phase 12 these items passed through unfiltered. The filter is tested at node level (`test_an_all_zero_ppr_branch_passes_no_item_on`), but the end-to-end consequence, a silently empty answer on a clean run, is not handled.

**Fix:** When the PPR branch is empty after the zero filter, select the `dpr-fallback` items. If that path is meant to count as a declared degradation, surface it through the guard machinery rather than as a silent empty result. For example:
```python
if not guard_fired:
    selected_items = [i for i in selected_items if i["score"] > 0.0]
    if not selected_items:
        selected_items = list(ctx.inputs["dpr-fallback"].get("items", []))
```
If this fallback is not acceptable under D-21, at least record the case in the port record's limits section.

### A-WR-03: Malformed triple items are dropped silently, which contradicts D-08 and the port record

**File:** `databasise/parts_core/hipporag/openie.py:113-129`; `databasise/evidence/HIPPORAG-PORT-RECORD.md:131-133`

**Issue:** `_parse_triples` returns `None`, which counts as a failure, only when the response is not an object holding a `triples` list. Any item with the wrong arity, a non-string member or an empty string is skipped (lines 122-128). So `{"triples": [["Ed Wood","directed"]]}` or `{"triples": [[1,2,3]]}` counts as a valid response with zero triples, and the chunk silently adds nothing to the graph. The port record states: "An OpenIE response that fails to parse or validate raises instead of yielding an empty finding ... a loud refusal over a silently thinner graph." Item-level validation failures produce exactly the silently thinner graph that sentence rules out. `_parse_entities` has the same item-level leniency at line 110.

**Fix:** Treat a list that contains any invalid item as `unparseable_response`, and keep `[]` as the only valid zero-triple response:
```python
for item in raw:
    if not (isinstance(item, (list, tuple)) and len(item) == 3
            and all(isinstance(v, str) and v.strip() for v in item)):
        return None
    triples.append(tuple(v.strip() for v in item))
```
If item-level leniency is intended, correct the port record's sentence and add the case to the HIPP-10 exception clause.

### A-WR-04: `declared_capability` is still an unread config key, which HIPP-18's text forbids

**File:** `databasise/wirings/hipporag/base.json:42,53,101`; `databasise/wirings/hipporag/corpus-ingest.json:48,59`; `databasise/tests/parts_core/hipporag/test_registration.py:130-138`

**Issue:** HIPP-18 says: "Every config key in wirings/hipporag/base.json and wirings/hipporag/corpus-ingest.json is either read by its part body or removed." No Python module under `parts/`, `parts_core/`, `runner/`, `seam/`, `validator/` or `wirings/` reads `declared_capability`. I checked all of them. It remains on three nodes in `base.json` and two in `corpus-ingest.json`. The port record (lines 152-154) says it was kept on purpose. However, the REQUIREMENTS exception clauses in 12-CONTEXT.md cover HIPP-03/04/10/15/17 only, not HIPP-18. The pinning test checks a fixed list of seven key names, so it cannot detect any other unread key, this one or a future one.

**Fix:** Remove `declared_capability` from both wirings (this changes only `config_hash`, as the record already says), or record a HIPP-18 exception clause in REQUIREMENTS.md. Either way, change the test from a denylist to an allowlist of the keys each part actually reads (for example `{"openie": {"max_concurrency"}, "assemble-result": {"top_k"}, ...}`), so a new unread key fails the test.

## Info

### IN-01: The `qa` one-shot text sends `$$94` / `$$940.3`, while upstream renders `$94` / `$940.3`

**File:** `databasise/parts_core/hipporag/qa.py:30`

**Issue:** Upstream builds its chat template with `string.Template` and calls `.substitute()` (`prompt_template_manager.py:120-133` in the reference clone), so the `$$` in `rag_qa_musique.py` reaches the model as `$`. The port copies `$$` into a plain string. The docstring claims the one-shot pair is "kept verbatim", but the model sees different text from what upstream sends.

**Fix:** Use `$94 million` and `$940.3 million` in `_ONE_SHOT_DOCS`, or note the difference in the port record.

### IN-02: The DPR tests still put `chunk:`-prefixed ids into the `hipporag-chunks` vector namespace

**File:** `databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py:82,114,148`

**Issue:** D-01 limits the `chunk:` prefix to graph vertex names, and conftest was migrated to bare ids. These three tests still seed `chunk:c1` and similar ids into the chunk vector namespace. They pass, but they show an id form the real write path never produces.

**Fix:** Seed bare ids (`c1`, `c2`, `c3`) and update the expected id lists.

### IN-03: The "thirteen" wording is stale after the 14th node

**File:** `databasise/evidence/HIPPORAG-PORT-RECORD.md:1,38,40,42`; `databasise/tests/parts_core/hipporag/test_thirteen_positions.py:4-5`

**Issue:** The record's title and findings rows 2, 4 and 6 still say "all thirteen" or "every one of the thirteen", while the cited tests now cover 14 nodes. The test module docstring still says "a single 13-node base wiring".

**Fix:** Change these to "the thirteen governing positions plus the recorded `qa`".

### IN-04: The chunk-id preimage is ambiguous when a document id contains `:`

**File:** `databasise/parts_core/hipporag/chunk_embed.py:89`

**Issue:** `f"{document_id}:{ordinal}:{piece}"` gives the same preimage for (`"a:1"`, 0, `"x"`) and (`"a"`, 1, `"0:x"`). The seam's `_DOCUMENT_ID_TOKEN_RE` refuses `:`, so ingest through the engine is safe. The part itself accepts any id, though, for example from a parity build or a hand-built context.

**Fix:** Hash a length-prefixed or JSON-encoded tuple, for example `json.dumps([document_id, ordinal, piece])`. This changes the D-03 id values, so do it only together with a rebuild.

### IN-05: OpenIE's fallback semaphore and model-identity handling

**File:** `databasise/parts_core/hipporag/openie.py:198-200,209-211`

**Issue:** On a hand-built context, the fallback `asyncio.Semaphore(int(config.get("max_concurrency", 1)))` hangs forever on `0` and raises `ValueError` on a negative value. The scheduler validates the value, but this fallback does not. The node also reports the last non-None `resolved_model_identity` across all chunk calls without a check, while `entity_fact_embed.py:131-137` refuses on a per-call identity mismatch (the WR-02 precedent).

**Fix:** Use `max(1, int(...))` in the fallback, and apply the same identity-divergence refusal across the chunk results.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
