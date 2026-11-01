---
phase: 11-lightrag-corpus-path
part: B (query path and v1 fidelity)
reviewed: 2026-10-18T00:00:00Z
depth: standard
diff_base: 23c0ca0
files_reviewed: 36
files_reviewed_list:
  - databasise/parts_core/lightrag/keywords.py
  - databasise/parts_core/lightrag/embedder_query.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/entity_hydrate_expand.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/join_roundrobin.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/generate.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/parts_core/lightrag/prompts.py
  - databasise/parts_core/lightrag/embedder_index.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/lightrag/arm-naive.json-patch.json
  - databasise/wirings/lightrag/arm-hybrid.json-patch.json
  - databasise/wirings/lightrag/arm-local.json-patch.json
  - databasise/wirings/lightrag/arm-global.json-patch.json
  - databasise/wirings/lightrag/README.md
  - databasise/parity/run_arm.py
  - databasise/clients/base.py
  - databasise/seam/engine.py
  - databasise/seam/promotion.py
  - databasise/stores/vector.py
  - databasise/tests/parts_core/lightrag/test_kg_fidelity.py
  - databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py
  - databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py
  - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
  - databasise/tests/parts_core/lightrag/test_transform_parts.py
  - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  - databasise/tests/parity/test_arm_conformance.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parity/test_graph_arm_real_index.py
  - databasise/tests/seam/test_empty_namespace.py
  - databasise/tests/seam/test_query_trace_nodes.py
  - databasise/tests/seam/test_promote.py
  - v1/lightrag/operate.py (reference only)
findings:
  critical: 2
  warning: 6
  info: 6
  total: 14
status: issues_found
---

# Phase 11 (part B): Code Review Report

**Reviewed:** 2026-10-18
**Depth:** standard
**Status:** issues_found

## Summary

The KG-arm rewrite follows v1 `kg_query` closely: keyword fallback, three-string batched embed, ll/hl lookups, `(rank, weight)` sort, per-side chunk pick with VECTOR/WEIGHT and fallback, `chunk_top_k` cap, available-token formula, `rag_response` as system message with the query as user message, and the frequency-ordered reference list. The prompt drift test is a real byte-for-byte AST comparison against `v1/lightrag/prompt.py` and catches a change on either side (probed), with one gap (WR-05).

Two defects block. (1) Query traces no longer carry `embedder-index`, but `promotion.resolve_single_arm` still matches a trace to its arm by the exact node-id set, so `promote`, `rollback` and `retire` fail with `AssertionError` for every LightRAG arm that has a recipe node; the promote tests pass only because they seed hand-built traces with the full node set. (2) v1 drops vector hits below `COSINE_THRESHOLD` (0.2); the v2 lookups have no threshold, so the "match v1 selection" claim is false for entities, relations and chunks.

Probes (all in the scratchpad, repo untouched): `probe_promote.py`, `probe_empty.py`, `probe_float.py`, `probe_drift.py` under /tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/review11b/. Targeted tests run: `test_v1_prompt_drift`, `test_kg_retrieval_fidelity`, `test_empty_namespace`, `test_query_trace_nodes`, `test_arm_conformance` gave 38 passed.

## Divergence ledger against v1 (focus item 1)

| # | Step | v2 vs v1 | Grade |
|---|------|----------|-------|
| 1 | Keywords, short-query fallback, `", "`-joined strings | Matches operate.py:3855-3863. Long query with no keywords: v2 keeps lists empty, context is empty, `generate` returns `fail_response` with no call: same observable result as v1 on hybrid/local/global. | matches |
| 2 | Keyword prompt | `keywords_extraction` byte-identical (drift test). `keywords_extraction_examples` is a hard-coded copy, not drift-guarded. | WR-05 |
| 3 | Keyword response parsing, language | v1 strips think tags, splits CSV strings, uses `json_repair`, takes language from `addon_params`; v2 degrades to empty lists and hard-codes "English". | IN-01 |
| 4 | ll/hl/query embeddings | One batched call, same strings. v2 embeds all non-empty strings for every arm; v1 embeds only what the mode needs and embeds nothing for a long no-keyword query. Spend differs, retrieval does not. | IN-02 |
| 5 | Entity lookup by ll, relation lookup by hl, top_k 40 | Vectors and top_k match. **No cosine threshold.** | CR-02 |
| 6 | One-hop expansion, `(rank, weight)` desc, float weights, one degree per node | Matches operate.py:5259-5261; stable sort; Cozo string weights cast. The test does not prove the float cast. | WR-04 |
| 7 | Entity and relation chunk passes | Per-side pick, relation exclusion of selected entity chunks, `int(related_chunk_number * len(items) / 2)`, zero-count and missing-vector fallback to WEIGHT, kept-empty entity items: all match operate.py:5266-5717 and utils.py:3991-4160. `split_string_by_multi_markers` strips whitespace, v2 does not. | matches, IN-05 |
| 8 | Round-robin merge, dedup | entities by name, relations by sorted pair, chunks by `chunk_id`/`id`: match. KG arms have no vector chunks, so the single-merge order is identical. | matches |
| 9 | base/mix two-stage chunk merge (v1 merges vector, entity, relation in one round-robin) | v2 merges entity and relation in `chunk-sel-kg`, then `join-chunks`. Not an exposed arm. | documented and accepted (11-04 residual) |
| 10 | Entity/relation row projection and budgets 6000/8000 | `{entity,type,description}` / `{entity1,entity2,description}`, stop at the first overflow: match. | matches |
| 11 | Token estimate | `len // 4` instead of the model tokenizer, with `shortcut:` comments in `assemble.py` and `truncator_token_budget.py`. | documented and accepted (D-16) |
| 12 | Chunk cost in the available-token loop | v2 costs the whole pipeline item; v1 costs `{content,file_path,chunk_id}`. | WR-03 |
| 13 | Available-token formula, `chunk_top_k` 20 cap before truncation, 200 buffer | Matches operate.py:4875-4938 (overhead uses `user_prompt="n/a"` vs v1 `""`, 3 chars). | matches |
| 14 | Prompt templates, system/user split, `fail_response` on empty context, `rag_response`/`naive_rag_response` | Match operate.py:3888-3952 and 5808-5918. Edge: chunks all cut by budget with no entities gives v2 `fail_response`, v1 calls the LLM with an empty context. | matches, IN-05 |
| 15 | Reference list | Frequency then first appearance, `unknown_source` and blank paths unreferenced: match utils.py:4929-4992. | matches |
| 16 | Chunk vector `top_k` | chunk-vector default 10; v1 `chunk_top_k` 20 (operate.py:4287). Deferred in 11-04 as "out of scope", no `shortcut:`. | WR-06 |
| 17 | v1 `kg_query` response post-processing (strip sys prompt, "user", "model"), history, LLM cache, streaming | Not replicated. Documented in `generate.py`; the post-processing is a v1 quirk. | documented and accepted |
| 18 | Local/global mode with only the other half's keywords | v1 falls into its hybrid `else` branch (operate.py:4406-4440) and runs the other half; v2's arm has no such node and returns nothing. | IN-01 |

## Critical Issues

### CR-01: promote, rollback and retire cannot resolve a real LightRAG query trace

**File:** `databasise/seam/promotion.py:115-129` (caller `databasise/seam/engine.py:1846`; cause `databasise/seam/engine.py:1663`, `371-382`)
**Issue:** `resolve_single_arm` identifies the arm by comparing the trace record's dispatched node-id set to `frozenset(resolved["nodes"])` for each wiring in `all_wirings()` (module docstring: "exactly the resolved wiring's own node id set"). 11-10 now runs `_without_recipe_only_nodes(resolved)`, so the persisted `RunRecord.nodes` omit `embedder-index`, while `all_wirings()` still contains it. No candidate matches, and `_arm_name_for_node_ids` raises `AssertionError` (a 500, not a refusal). `rollback` and `retire` share `_resolve_operator_preconditions` (engine.py:1824-1860) and fail the same way.
Probe (`probe_promote.py`), node set taken from the pruned run copy:
```
naive  RAISES AssertionError trace record's own dispatched node id set [...]
hybrid RAISES AssertionError ...
local  RAISES AssertionError ...
global RAISES AssertionError ...
bypass -> bypass          (bypass has no recipe node)
```
The 11-10 summary says the promotion tests still pass. They do, but vacuously: `tests/seam/test_promote.py::_seed_trace` (line 36) hand-builds a record from `resolved["nodes"].keys()`, i.e. the full set including `embedder-index`, so it never sees a real post-11-10 trace. `test_query_trace_nodes.py` proves traces omit the node but never feeds one to `promote`. Mutation-class derivation itself is unaffected (it reads the full registry wirings), which is why no existing test noticed.
**Fix:** match against the run-shape of each candidate. Move `_without_recipe_only_nodes` into `databasise/wirings/resolve.py` (or `promotion.py`) and use it in `_arm_name_for_node_ids`:
```python
for name, resolved in all_wirings():
    if frozenset(without_recipe_only_nodes(resolved)["nodes"]) == node_ids:
        return name
```
Note that after pruning, `naive`, `hybrid`, `local`, `global` sets stay distinct. Add a test that runs `engine.query` on a populated store and passes the returned `trace_token` to `engine.promote`, then `rollback`.

### CR-02: no cosine threshold on any vector lookup, so v1 selection is not matched

**File:** `databasise/parts_core/lightrag/entity_lookup.py:40-44`, `relation_lookup.py:35-40`, `chunk_vector.py:28-30` (store `databasise/stores/vector.py:371-394`)
**Issue:** v1's Faiss storage drops every hit with `dist < cosine_better_than_threshold` (`v1/lightrag/kg/faiss_impl.py:420-422`; default `COSINE_THRESHOLD` 0.2, `v1/lightrag/lightrag.py:735-736`, `base.py:222`). `FaissVectorStore.query` returns the top-k regardless of score, and none of the three lookup parts filters. Grep for `threshold`/`cosine` in `parts_core/lightrag`, `seam/engine.py` and the Phase 11 planning docs finds nothing relevant. Consequences:
- On any corpus with fewer than 40 entities or relations (every small corpus), v2 returns all of them, irrelevant ones included, and they fill the entity, relation and chunk-selection lists that v1 would have cut.
- v1's "no hit above threshold" path (`_build_query_context` returns `None`, `kg_query` returns `fail_response`) is unreachable in v2 except on a truly empty index, so an off-topic question gets an LLM answer from irrelevant context where v1 refuses.
The research table (Pattern F rows 4 and 7) marked the lookups "Equivalent" and never examined the store-level filter, so the gap is not documented anywhere and is not a `shortcut:`. D-16 and LRAG-18 say "match v1 selection".
**Fix:** apply the filter in the three parts, with `cosine_better_than_threshold` as config defaulting to v1's 0.2 (scores from `FaissVectorStore` are already normalised inner product = cosine):
```python
threshold = float(config.get("cosine_better_than_threshold", 0.2))
raw_items = [i for i in await store.query(vector, top_k=top_k) if i["score"] >= threshold]
```
Do not filter `score_all` in `chunk-sel-kg` (v1's `get_vectors_by_ids` has no threshold). Add a test with one near and one orthogonal vector.

## Warnings

### WR-01: the empty-namespace pre-check refuses a populated corpus whose extraction yielded no entities or relations

**File:** `databasise/seam/engine.py:385-392` with `databasise/stores/vector.py:518-519`
**Issue:** the check treats a missing `vector.faiss` as "never populated". `FaissVectorStore.prepare` returns without writing when nothing is pending (line 518), so a namespace that received zero rows during sync never gets a file. A short document that yields entities but no relationships therefore makes every `global` and `hybrid` query a 422 `EmptyNamespaceError` forever, although the corpus is populated and v1 answers. Probe (`probe_empty.py`, chunks and entities written, relationships empty):
```
global REFUSED EmptyNamespaceError
hybrid REFUSED EmptyNamespaceError
local ok
naive ok
```
A namespace emptied by a delete is handled correctly (the zero-row index persists, tested). A first ingest in flight reads as "never populated" until commit, which is acceptable. `test_empty_namespace.py` covers fresh root, emptied-by-delete and populated, but not partial population.
**Fix:** refuse only on the corpus-level namespace. Check `chunks` for every arm and treat a missing `entities` or `relationships` namespace as an empty index (the node already returns `[]` for a missing directory):
```python
_REFUSAL_NAMESPACE = "chunks"   # corpus never ingested; entities/relationships may legitimately be empty
```
Or have `v1-index-sync` commit a zero-row index for all three kinds. Add the partial-population test.

### WR-02: `compare` aborts and discards finished arms when a later arm hits `EmptyNamespaceError`

**File:** `databasise/seam/engine.py:1039` (pre-check at 1678)
**Issue:** `compare` runs `{key: await self._execute_resolved(...)}` sequentially with no per-arm handling. Because the pre-check runs inside `_execute_resolved`, `compare([naive, hybrid])` on a corpus where the entities namespace is missing runs `naive` in full (LLM and embedding spend), then raises 422 for `hybrid` and returns nothing. Before 11-10 the same call returned two envelopes. With WR-01 this is reachable on populated corpora.
**Fix:** run `_refuse_empty_namespaces` for every resolved wiring before executing any of them (it only needs the resolved wirings), or catch the refusal per arm and surface it as that arm's degraded entry.

### WR-03: assemble costs chunks differently from v1, so the budget cuts earlier

**File:** `databasise/parts_core/lightrag/assemble.py:121-125`
**Issue:** v1 costs `json.dumps(chunk)` of the merged chunk, which at that point is `{"content","file_path","chunk_id"}` (operate.py:4795-4829; naive costs `_get_vector_context`'s dict, operate.py:4302-4309). v2 costs the whole pipeline item (`id`, `chunk_id`, `source_type`, `score`, `full_doc_id`, `chunk_order_index`, `tokens`, `rank_position`, `derived_from`, ...), roughly 150-250 extra characters per chunk. With 20 chunks near the 30000 budget this moves the cut by up to one chunk. The 11-11 summary justifies it as "the JSON of the whole chunk item", which is v1's rule applied to a different item. No test compares against v1's three-key shape.
**Fix:**
```python
cost_row = {"content": item.get("content"), "file_path": item.get("file_path", "unknown_source"), "chunk_id": item.get("chunk_id") or item.get("id")}
running += _tokens(json.dumps(cost_row, ensure_ascii=False))
```

### WR-04: the float-weight sort test does not discriminate float from string comparison

**File:** `databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py:205` (test at ~212-228)
**Issue:** the focus item asks whether weights compare as floats. The only edges at equal rank are weights `"1.0"` and `"5.0"`, whose lexicographic and numeric orders agree. Probe (`probe_float.py`): with `_as_float` replaced by an identity (string compare) the test still passes; with weights `"9.0"` and `"10.0"` string compare orders A-B before A-C, float compare orders A-C first. The 11-04 "Rule 1 bug" fix is therefore untested.
**Fix:** use `("A","B","9.0")` and `("A","C","10.0")` at equal rank and assert `A-C` precedes `A-B`.

### WR-05: `keywords_extraction_examples` is duplicated but not drift-guarded

**File:** `databasise/parts_core/lightrag/keywords.py:35-40`, `databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py:19-26`
**Issue:** v1 fills `{examples}` from `"\n".join(PROMPTS["keywords_extraction_examples"])` (operate.py:4175), a list. v2 hard-codes the single current element. `_DUPLICATED` omits it and the AST helper only collects string constants. Probe (`probe_drift.py`): a one-token change to the v1 list is not detected, while a typo in `rag_response`, a v1 string turned into a non-constant expression, and a trailing space on the v2 `naive_rag_response` are all detected. The drift test is otherwise sound (byte-exact on both sides).
**Fix:** move the example into `prompts.py` as `PROMPTS["keywords_extraction_examples"]`, extend the AST collector to accept a list of string constants, and add it to `_DUPLICATED`.

### WR-06: chunk-vector retrieves 10 chunks where v1 retrieves `chunk_top_k` = 20

**File:** `databasise/parts_core/lightrag/chunk_vector.py:17`
**Issue:** v1 `_get_vector_context` uses `chunk_top_k or top_k` (operate.py:4287), 20 by default. v2 uses 10, deferred in 11-04 ("Row 3 ... out of scope") and 11-RESEARCH A10 as a parity-pin risk. It carries no `shortcut:` comment and no requirement, so the naive arm sees half of v1's recall, and the new `chunk_top_k = 20` cap in `assemble` can never bind on that arm. Outside D-16's KG scope, but the naive arm now claims v1's templates and budget.
**Fix:** either set the default to 20 and update the parity pins, or mark the line `# shortcut: v1 retrieves chunk_top_k=20; upgrade with the parity re-baseline` and track it as a requirement.

## Info

### IN-01: keyword parsing and mode edge cases are leaner than v1

**File:** `databasise/parts_core/lightrag/keywords.py:59-73, 111`
**Issue:** v1 `_parse_keywords_payload` strips `<think>` tags, splits CSV-string fields, and repairs malformed JSON; v2 returns two empty lists on any failure. A reasoning model that emits a think block silently degrades to `ll = [query]` (short query) or `fail_response` (long query). The language comes from `config["language"]` ("English"), not v1's `_resolved_summary_language`/`addon_params`. Also, v1 `mix` mode returns `fail_response` for a long keyword-less query even when chunks exist (operate.py:3855-3860); the base (mix) wiring does not. And v1 local/global with no keywords of their own fall into the other half's lookup (see ledger row 18).
**Fix:** add think-tag stripping (one regex) and log the degrade at warning level; document the language source.

### IN-02: embedding spend differs from v1

**File:** `databasise/parts_core/lightrag/embedder_query.py:49-60`
**Issue:** every KG arm embeds all non-empty members of `[query, ll, hl]`. The local arm embeds an hl string it never uses; the global arm embeds an unused ll string; a long query with no keywords still embeds the query where v1 returns before any embed. Retrieval is unaffected; `token_accounting` and parity cost comparisons are inflated.
**Fix:** read the arm's needs from config (`ll`/`hl` flags) or from which lookup nodes are present, and skip the others.

### IN-03: recipe-only pruning has no guard for `provides` or `evidence_position`

**File:** `databasise/seam/engine.py:371-382`; `databasise/seam/engine.py:391` (hard-coded `vector.faiss`)
**Issue:** `_without_recipe_only_nodes` deletes any recipe-named node nothing depends on. `embedder-index` is neither provided nor an evidence node, and HippoRAG's recipe nodes (`chunk-embed`, `openie`) are depended on, so nothing breaks today (focus item 3: `wiring_instance_hash`, `wiring_id`, `provides` and `evidence_position` are all taken from the full `resolved`, lines 1735-1760, and `derive_mutation_class` reads registry wirings, so promotion classes do not change; the break is CR-01). A future wiring whose terminal node is also a recipe value would lose it and return `None` from `provided`. Separately, the pre-check hard-codes the store's file layout (`vector.faiss`) instead of asking the store.
**Fix:** skip nodes listed in `provides` or named by `evidence_position`; expose a `FaissVectorStore.is_committed(root, workspace, namespace)` helper beside the layout it depends on.

### IN-04: parity `_inject_query` and a stale comment

**File:** `databasise/parity/run_arm.py:128`, `143-146`
**Issue:** the hard-coded `("keywords","embedder-query","generate")` means parity runs give `assemble` and `rerank` no `config["query"]` (focus item 6). Effects: `assemble` counts zero query tokens, so its chunk budget is larger by `len(query)//4` tokens (about 10-30), which changes the cut only at the margin; `rerank` is a pass-through unless `live_rerank` is set, so no output changes. Nothing breaks: `max_total_tokens` falls back to assemble's own 30000, equal to the engine value. Parity runs also still dispatch `embedder-index`, as `embedder_index.py` states. The comment at 143-146 says "six listed edits"; the README now lists nine.
**Fix:** read `resolved["consumes_query"]` as `seam/engine.py::_inject_query` does; change the comment to "the README's listed edits".

### IN-05: minor v1 differences in chunk selection and assembly

**File:** `databasise/parts_core/lightrag/chunk_sel_kg.py:69`, `databasise/parts_core/lightrag/assemble.py:130-140`, `databasise/parts_core/lightrag/generate.py:72`
**Issue:** (a) `source_id` pieces are not `.strip()`ped as in v1's `split_string_by_multi_markers`. (b) When entities and relations are absent and every chunk is cut by the budget, v2 returns `fail_response`; v1 sends the LLM an empty context. (c) `assemble.order_policy` and `generate.prompt_template` independently choose the template pair; a wiring with `naive-template` and the default `rag_response` produces a naive context inside the KG system prompt with no refusal.
**Fix:** strip ids; accept (b) as documented; have `generate` read `assemble["template_kind"]` and refuse a mismatch.

### IN-06: `max_total_tokens` and HippoRAG pre-check confirmations (focus items 4 and 5)

**File:** `databasise/seam/engine.py:408, 472-482, 364-368, 1662`
**Issue:** no code defect; answers to the review questions.
- Item 5: `QueryObject` has no cap field, so a caller cannot set one. A wiring value (arm patch or promoted alias) is kept by `setdefault`; otherwise the engine stamps 30000, so "no cap" cannot occur (assemble also defaults to 30000). The stamped value enters `wiring_instance_hash`, so changing `_DEFAULT_MAX_TOTAL_TOKENS` changes every identity. A non-numeric wiring value raises in `int()` and degrades the envelope.
- Item 4: the pre-check runs after `_build_stores` (engine.py:1676-1678) inside the `try` whose `finally` finalises stores, so open errors keep precedence. It covers only `lightrag/retriever-chunk-topk`, `entity-lookup` and `relation-lookup` (`_RETRIEVAL_NAMESPACES`); HippoRAG's `hipporag-*` parts are not listed, so HippoRAG queries on an empty root keep the old behaviour. Confirmed, but no requirement or roadmap item in REQUIREMENTS.md or ROADMAP.md tracks the Phase 12 extension (only the 11-10 summary notes it).
**Fix:** add the HippoRAG extension to a Phase 12 requirement so it is not lost.

---

_Reviewed: 2026-10-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
