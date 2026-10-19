# Phase 12: HippoRAG Fixes - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous). The owner delegated grey-area decisions for Phases 9-11 ("You decide") and asked the run to continue with "Run what you recommend next". Every decision below is Claude's choice under that delegation. It is grounded in a six-agent code study: five areas plus a critic, with probes run against HEAD. Each decision is numbered, so planning and verification treat it as binding.

<domain>
## Phase Boundary

A HippoRAG ingest builds a graph whose evidence resolves and accumulates correctly. Its queries run only query-side work, and its documents have the same corpus lifecycle as LightRAG's. Requirements: HIPP-01 to HIPP-19.

The owner routed two more items here:
- **A-WR-05** (Phase 11 UAT item 4): in-process HippoRAG provider errors are logged unredacted.
- **The HippoRAG empty-namespace pre-check**: Phase 11 D-15 covered LightRAG namespaces only. This is recorded in STATE.md concerns.

**In scope:**
- the chunk-id form
- graph accumulation and provenance
- ingest failure semantics
- query-side pruning
- one query embedding
- top_k
- a generated answer
- guard-fired degradation
- corpus, delete and re-ingest
- dead config keys
- token accounting

**Out of scope:**
- WIRE-03 node-free refusal vocabulary (Phase 13)
- WIRE-08 guard comparison rewrite (Phase 13)
- WIRE-18 budget apportionment (Phase 13)
- tie-break changes (WIRE-01, Phase 13)
- promotion classing (Phase 14)
- LightRAG's own stale-ref hazard after a changed-text re-ingest (see Deferred)

</domain>

<decisions>
## Implementation Decisions

### A. Evidence identity and graph shape (HIPP-01, 02, 06, 17)

- **D-01 (HIPP-01/02):** keep the bare chunk sha as the one id form everywhere outside the graph. The vector id, the KV key and `EvidenceRef.id` all use it, in namespace `hipporag-chunks`, as the DPR branch does today.
  - The `chunk:` prefix exists only on graph vertex names. Translate it at the graph boundary only:
    - ppr readback strips it when it emits items (ppr.py:84-89);
    - reset-vector-join adds it when it keys passage weights (reset_vector_join.py:86-93).
  - Consolidate the duplicated prefix constants (`CHUNK_VERTEX_PREFIX` in entity_fact_embed.py:56 and `_PASSAGE_VERTEX_PREFIX` in ppr.py:42) into one.
  - `tests/parts_core/hipporag/conftest.py` stops seeding `chunk:c1` into KV/vector. Fact `chunk_ids` become bare ids.
  - The HIPP-02 test needs at least two chunks with different scores, because `min_max_normalize` returns zeros when the range is 0.
- **D-02 (HIPP-06):** openie passes its input chunks through in its output. It needs that per-chunk record for D-08 anyway. passage-edges emits a vertex for every chunk, and graph-augment-persist upserts that `vertices` stream. The frozen deps (`passage-edges` ← `openie`) do not change.
- **D-03 (HIPP-17):** chunk ids become `sha256(document_id:ordinal:text)` (chunk_embed.py:80, the only mint site).
  - This deliberately departs from the roadmap's wording "sha256 of text": a text-only hash gives two documents with identical text the same id, so a document-scoped delete would remove the other document's chunk.
  - `EvidenceRef` and the envelope do not change; only the opaque ref string values change.
  - Old refs fail with `UnresolvableEvidenceReferenceError` once D-12's re-ingest removal has run.
  - The re-ingest removal (D-12) must land before or together with the id change, otherwise HIPP-16 fails.

### B. Graph accumulation (HIPP-07, 08, 09, 19)

- **D-04 (HIPP-08 merge rule):**
  - Edges keep a per-chunk co-occurrence map (`cooccurrence_by_chunk: {chunk_id: count}`). The co-occurrence weight is its sum.
  - Synonymy weight is the max of the stored and the new value.
  - The passage-entity weight stays idempotent at 1.0.
  - `edge_types` is the union of types.
  - The read-merge-write happens inside graph-augment-persist: `get_edge`, then `upsert_edge`. It must keep writing through `upsert_edge`, because protected `test_ingest_abort.py` (STOR-06) monkeypatches it.
  - The per-chunk map is idempotent on re-ingest of the same chunk ids, and it can be reduced on delete (D-12).
  - An edge without a map counts as one anonymous contribution, so `test_graph_augment_persist_collapses_two_edge_types_into_summed_weight` keeps its meaning.
  - `export_to_igraph` still reads only `weight`.
- **D-05 (HIPP-07):**
  - `self_knn` gains an optional `ids` parameter that also searches the pending buffer. This is a documented exception to Faiss's committed-only reads, for this one method only. The default (`ids=None`) behaviour is unchanged, which keeps STOR-09 and STOR-16.
  - "New entity" means `get_by_id` is None at committed level: not committed before this run.
  - synonymy-edges matches only new entities against committed and staged entities. Pending deletes (D-12) are excluded.
  - Accepted recall difference: an asymmetric neighbour can be missed, where a new X sits in an old entity's top-k but not the reverse. Record it in the HippoRAG port record.
  - `test_synonymy_edges_emits_deduped_canonical_edges_above_threshold` stages `cat` in the same run instead of committing it.
- **D-06 (HIPP-09):** the KV `fact:<id>` record is the source of truth. entity-fact-embed unions the stored `chunk_ids` with this run's, then mirrors the union into the fact vector metadata on the upsert it already makes. No effect declaration changes, because write proxies expose reads.
- **D-07 (HIPP-19):**
  - One shared helper in `runner/trace.py` sums token accountings. Mixed `counted_by` values give the unbudgetable sentinel; the trace schema does not change.
  - `"unbudgetable"` is defined once there. `openie.py`, `entity_fact_embed.py` and `seam/tokens.py` import it.

### C. Ingest failure semantics (HIPP-03, 04, 10, A-WR-05)

- **D-08 (HIPP-10 = refuse):**
  - Any per-chunk extraction failure refuses the whole ingest. That covers a `chat()` exception and an unparseable NER or triple JSON response; a valid response with zero triples is not a failure. Nothing commits (Phase 10 D-06/D-07). This matches v1, which fails the document on the first chunk error.
  - The refusal is the existing `ForeignEngineRefusalError` with a new `failure_class` value, `ExtractionFailed`, added to `_FOREIGN_FAILURE_CLASSES`. It has two public attributes:
    - `failed_chunks`, a count;
    - `failure_reasons`, a capped list of closed codes such as `llm_call_failed:<ExceptionClass>` and `unparseable_response`, never raw LLM text, paths or keys. It stays within SEAM-05's 1 KB / no-leak rule.
  - REST maps it to 502 like the other non-unavailable classes. No IngestJob/§18 field is added.
  - NER and triple calls run with bounded concurrency: an `asyncio.Semaphore` whose bound is set in the wiring config and read by the body. All chunks are collected, using `gather(return_exceptions=True)` or failure collection inside the semaphore, so every failure is counted. Do not use a cancel-on-first TaskGroup.
  - "Ingest outcome (and trace)" in HIPP-10 means the refusal body plus the in-run NodeTrace/server log. Ingest persists no trace.
- **D-09 (HIPP-04 = keep ForeignEngineRefusalError):**
  - The class, `refusal_type`, `failure_class` vocabulary and REST/MCP bodies stay unchanged. This follows Phase 9 D-04, Phase 10 D-06/D-13 and CONTRACT.md:785. A distinct class would also contradict HIPP-03's own test text.
  - The real cause is already carried at HEAD (`_node_result_or_refuse` falls back to any node's exception since feadf3e). What is missing is the failing node id. Add it as a private `_node_id` with a read-only `node_id` property, following the `cause` and CR-03 `_internal_node_id` precedents, and add it to the server log line.
  - It never appears in `str(refusal)` or the public body (§18.2 low-entropy identity rule, WIRE-03).
  - The test asserts `getattr(refusal, "node_id", None) == "chunk-embed"`, which fails pre-fix by assertion, and `str(refusal.cause)` names `embedding`.
- **D-10 (HIPP-03):**
  - Current code already meets the behaviour (feadf3e, 10-04).
  - Add the requirement's seam test in `test_hipporag_write_path.py`, which is unguarded: embedding wired, no llm. It asserts `ForeignEngineRefusalError`, zero records in hipporag-chunks/text-chunks/graph, and no query evidence from that document.
  - It does not assert 422: the class maps to 502.
  - Record the fail-first proofs for HIPP-03 and HIPP-04's cause half with `record-fail --at feadf3e^`.
- **D-11 (A-WR-05):**
  - `_foreign_fault` (engine.py:299-308) logs `type(cause).__name__` plus `redact_secrets` over `traceback.format_exception(cause)`, then the corpus `_URL_RE` `<url>` substitution. It drops `exc_info=cause`.
  - `redact_secrets` also gains a bare `key=` query-parameter pattern.
  - `refusal.cause` stays readable in-process.
  - Also apply `redact_secrets` to `NodeTrace.cross_process_failure_cause` (scheduler.py:606), which reaches debug trace consumers.
  - Pinned by editing protected `tests/seam/test_foreign_engine_refusal.py:118` (SEAM-05). This needs the owner's `grant-check-edit`; the owner routed the item with that grant in mind.

### D. Corpus lifecycle (HIPP-15, 16, empty namespace, write gate)

- **D-12 (HIPP-16):**
  - A new `corpus-delete.json` HippoRAG wiring runs a remover part. Re-ingest prepends the same remover as the first node of `corpus-ingest.json`, so delete-then-ingest happens inside one run and one all-or-none commit. A refused re-ingest therefore never destroys the previous version (Phase 10 D-06/D-07). A buffered delete followed by an upsert of the same id cancels, so unchanged chunks survive.
  - A per-document manifest `doc:<document_id>` in the existing `hipporag-text-chunks` KV records chunk ids, fact ids, entity names and touched entity pairs. It needs no new namespace, so the health drift tests stay unchanged.
  - The remover deletes:
    - the document's chunk vectors, KV records and passage vertices (cascade via `delete_node`);
    - each fact's `chunk_ids` minus the removed ones. A fact left with none is removed from the vector store and KV;
    - the removed chunk ids from `cooccurrence_by_chunk` on every manifest pair edge, recomputing the weight. An edge with no co-occurrence and no synonymy left is deleted;
    - any manifest entity with no passage-entity edge to a surviving chunk vertex (orphan), together with its vertex and entity vector.
  - Verify that Cozo read-your-writes reflects a pending `delete_node` cascade before graph-augment-persist merges. If it does not, the remover must also stage the edge deletes explicitly.
  - `delete_document` with a HippoRAG selector returns the existing `DeletionOutcome` and no longer enters the v1 write gate or stamps the v1 working dir.
  - `test_hipporag_write_path.py:215-229` (the NoWritePath assertion, not protected) is replaced.
- **D-13 (HIPP-15):**
  - `GET /jobs` (Phase 11 D-02) and health (`_HEALTH_PROBES` already includes all five hipporag namespaces) already pass.
  - `corpus_status` and `document_counts`, plus MCP status, gain an optional selector. With no selector the responses are byte-identical to today. With a HippoRAG selector they answer from the existing shapes with status `processed`.
  - The listing source is the D-12 manifest set, read through a read-only path that creates nothing (LRAG-13). jobs.db stays the job registry.
  - So there is one HippoRAG document registry, the manifest, written in the same commit as the data. That closes the jobs.db-write-after-commit gap.
  - HippoRAG ingest keeps returning its final `IngestJob`, and no per-modality field is added.
  - The HIPP-15 test goes in `test_hipporag_write_path.py`. Its fail-first assertion is the `/corpus` or `/corpus/counts` leg.
  - Protected `test_rest_corpus_endpoints.py` (RUN-10, disputed) is not edited.
  - "Health for the HippoRAG selection" is met by health reporting the hipporag namespaces.
- **D-14 (HippoRAG write gate):**
  - HippoRAG ingest and delete take a per-workspace write gate built from the existing `_write_gate` helper. A concurrent HippoRAG write is refused at once with the existing `StoreBusyError` (409), as LightRAG does (Phase 11 D-07). Without it, the D-04/D-06/D-12 read-merge-write steps lose updates.
  - The LightRAG gate behaviour and protected `test_corpus_write_gate.py` (LRAG-04) stay unchanged.
- **D-15 (HippoRAG empty-namespace pre-check):**
  - A HippoRAG query on a never-populated `hipporag-chunks` is refused before the run with the existing `EmptyNamespaceError` (422, public `store_kind` only), the same as LightRAG.
  - Use a separate HippoRAG table: protected `test_empty_namespace.py:152-158` pins `_RETRIEVAL_NAMESPACES` to the three LightRAG entries. Do not pre-check `hipporag-facts`, which is legitimately absent when OpenIE finds no triples.
  - Check the fresh-root expectations of `test_cross_modality_run.py`, `test_compare.py` and `test_store_isolation.py`.

### E. Query semantics (HIPP-05, 11, 12, 13, 14)

- **D-16 (HIPP-12 index nodes = prune, option 2):**
  - `without_recipe_only_nodes` in `runner/resolve.py` is generalised in place to prune the query run to the ancestors of `provides`. Keep the `engine._without_recipe_only_nodes` alias name, which protected LRAG-19's `test_query_trace_nodes.py` calls.
  - Pruning applies to the dispatched run and to the selector effect union (selectors.py `_match_capability`). It does not apply to `_wiring_effects` itself: promotion's `declared_surface` and the compare `mutates_store` refusal stay on full wirings.
  - The node-count tie-break stays on full wirings.
  - base.json keeps its nodes, so MODAL-04 and PARTS §H stay as they are.
  - Accepted selector change: a `[writes_artifact]` selector no longer resolves (UnsatisfiableSelectorError), because no query run writes artifacts. writes_graph/kv/vector no longer resolve to hipporag.
  - promotion.py:122-127 still matches old full-set traces.
- **D-17 (HIPP-12 embed once):**
  - fact-score's output carries the query vector. reset-vector-join and dpr-fallback get a direct dep on fact-score and reuse the vector. This leaves scheduling order unchanged.
  - Their `calls_embedding` effects are narrowed. Update `test_registration.py`, `test_hipporag_port_record.py` and `HIPPORAG-PORT-RECORD.md` to match.
  - Sharing the duplicated `score_all` scan is optional.
- **D-18 (HIPP-05):** add `fact-filter` (and D-19's `qa`) to `consumes_query` in base.json. Fix the stale `_inject_query` docstring (engine.py:449-453).
- **D-19 (HIPP-13 = generator node):**
  - Add a `qa` node, the upstream HippoRAG 2 `rag_qa` step, as the 14th node and the new `provides`. It takes assemble-result's hydrated passages and the query, declares `calls_llm`, and returns the answer.
  - With no passages it returns the same fail_response string LightRAG uses, so the no-context answer reads the same for both modalities.
  - Port the prompt from upstream `prompts/templates/rag_qa_musique.py` (reference clone `/home/chris/coding/reference-repos/HippoRAG` @ d5c8329). The prompt must not contain the `---Candidate Facts---` or `---Recognised Entities---` markers that test stubs dispatch on.
  - Record the 14th node as a documented divergence in `HIPPORAG-PORT-RECORD.md`, following the assemble-result deps precedent. Update `test_thirteen_positions.py`'s node-set equality to the governing 13 plus the recorded `qa`, and confirm with the BAK guard at plan time that the file is unprotected.
  - Evidence still mints from assemble-result (`evidence_position`), and `depth_label` stays opaque. At 14 nodes the selector margin under local/global (15) holds.
  - Each HippoRAG query costs one more LLM call. Price it against RIG §F3 when rig runs happen.
  - `test_cross_modality_run.py:85-89` changes from joined-text assertions to generated-answer assertions.
- **D-20 (HIPP-11 = wiring config):**
  - QueryObject is unchanged (§18.1's five members). Add one `top_k` key on assemble-result. Its default is 5 (upstream `qa_top_k`), stated in base.json and the port record.
  - Zero-score PPR items are dropped, then the cut applies after branch selection (assemble_result.py:52-53). Evidence mints from assemble-result, so the one cut bounds answer and evidence on both branches.
  - Do not cut inside `dense_passage_retrieval`, which reset-vector-join reuses.
  - The qa node takes everything assemble-result passes and has no second top_k.
- **D-21 (HIPP-14 = reuse degraded):**
  - CONTRACT §18.2 and §19.8 and PARTS §H:254 settle it: a fired guard is a declared-and-taken degradation path and gets no new envelope field. RIG.md:625 allows `partial` without `degraded`.
  - The scheduler sets `degraded = partial or any NodeTrace.guards_fired` (scheduler.py:668/701), keyed off the scheduler's guard record and not assemble-result, so the WIRE-08 rewrite carries over.
  - Relax the `partial != degraded` refusal at runner/trace.py:123 and correct its docstring.
  - A completed fallback run carries a non-empty, node-free and guard-name-free `stop_reason`/`degradation_reason` code drawn from a small closed set that WIRE-03 can adopt.
  - Narrow `_node_result_or_refuse`'s `partial or stop_reason` check (engine.py:823-824) to `partial`, so a declared guard never refuses an ingest or delete.
  - `test_dpr_fallback_guard.py:254-263` changes; it is not protected.
  - Owner note: `parity/run_cross_modality.py` will refuse a HippoRAG arm that took the fallback, per CONTRACT §5's tenth refusal.

### F. Config honesty (HIPP-18)

- **D-22:**
  - Remove the unread keys:
    - entity-fact-embed `namespaces` (it names LightRAG's namespaces, so reading it would be wrong);
    - synonymy-edges `guard` (D-05's new-entities rule is the guard, hard-coded and documented);
    - reset-vector-join `socket_shape`, `arm_precedence` and `apportionment_policy` (WIRE-18 owns apportionment);
    - ppr `readback`;
    - assemble-result `order_policy`.
  - Every new key a part reads (D-08's concurrency bound, D-20's `top_k`) has a value-change test.
  - Fix the docstrings: edge_types is "persisted, not exported" and `export_to_igraph` does not change; reset-vector-join no longer claims "no token spend" until D-17 makes it true; correct the stale conftest-seeding note (reset_vector_join.py:8-12) and synonymy_edges.py:15-25.
  - Every Phase 12 config edit changes the hipporag `config_hash`, as expected.

### Requirement text exceptions (record in REQUIREMENTS.md)

Under the owner's delegation, these Phase 12 exception clauses are recorded:
- HIPP-03: the refusal is 502, not 422. graph-augment-persist no longer commits in-node; the engine commits all stores together (Phase 10 D-07).
- HIPP-04: "names node chunk-embed" means the private `refusal.node_id` plus the server log, never the public message or body.
- HIPP-10: the outcome is a refusal carrying `failed_chunks`/`failure_reasons` (D-08). Malformed JSON counts as a failure.
- HIPP-15: the corpus legs go in `test_hipporag_write_path.py` and not the protected `test_rest_corpus_endpoints.py`. Health meets the text by reporting the hipporag namespaces.
- HIPP-17: ids are `sha256(document_id:ordinal:text)` and not "sha256 of text".

### Claude's Discretion
- The exact name of the remover part and the manifest record schema.
- The closed reason-code sets (D-08, D-21).
- The concurrency bound default.
- Whether D-17 also shares the `score_all` scan.
- Plan split and ordering, constrained as follows: D-01 before D-19 (qa reads hydrated content); D-12 with or before D-03; D-04's per-chunk map before D-12's subtraction.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (the Phase 12 goal, success criteria and owner-decision list) and `.planning/REQUIREMENTS.md` (HIPP-01 to HIPP-19 and their test texts, the acceptance contract, with the exception clauses above).
- `docs/gui/DEFECTS.json`: HIPPO-1 to HIPPO-15, D-05, D-07, D-12, D-13, ENG-05, T-07 and T-08.
- `docs/system-model/CONTRACT.md` (§5, §8, §14.2, §18.1-§18.5, §19.8, line 785) and `docs/system-model/PARTS.md` §H (the governing 13 positions, :224 and :254). `RIG.md`:625.
- `databasise/evidence/HIPPORAG-PORT-RECORD.md`: the divergence record (qa node, narrowed effects, KNN recall note, top_k default).
- Upstream: `/home/chris/coding/reference-repos/HippoRAG` @ d5c8329. QA is at HippoRAG.py:1117-1172, the prompt is `prompts/templates/rag_qa_musique.py`, query embedding is at :1841-1890 and `qa_top_k` is in config_utils.py:203-206.
- Locked decisions: `.planning/phases/08-*` to `11-lightrag-corpus-path/11-CONTEXT.md`, in particular Phase 9 D-04, Phase 10 D-06/D-07/D-13/D-14 and Phase 11 D-02/D-04/D-07/D-15.
- The research output, kept in this session's scratchpad (not tracked): the full evidence for each decision.

</canonical_refs>

<code_context>
## Existing Code Insights

- **The engine.py line numbers in the requirement text have drifted.** Current locations:

  | Code | engine.py |
  |---|---|
  | `_foreign_fault` | 299-308 |
  | `_HEALTH_PROBES` | 353-364 |
  | `_without_recipe_only_nodes` alias | 379 |
  | EmptyNamespace pre-check | 382-397 |
  | `_NON_DEBUG_TRACE_FIELDS` | 418-433 |
  | `_inject_query` | 445-464 |
  | `_corpus_wiring` | 587-600 |
  | `_drop_pending` | 673-683 |
  | `_commit_all` | 749-774 |
  | `_node_result_or_refuse` | 794-833 |
  | `_select_answer` | 927-961 |
  | ingest | 1133 |
  | `_run_corpus_ingest` | 1239 |
  | refuse-and-drop | 1342-1347 |
  | commit | 1359 |
  | jobs record | 1396-1402 |
  | `delete_document` | ~1564-1600 |
  | `get_job_status` | 1630-1679 |
  | `corpus_status` | 1681-1719 |
  | `document_counts` | 1721-1739 |
  | `health` | 1741-1811 |
  | `_execute_resolved` | 1825-1964 |

  Elsewhere:
  - stores: `self_knn` vector.py:436-484; `iter_vectors` vector.py:486-494; `upsert_edge` graph.py:385-393; `:put` graph.py:441-445; `delete_node` cascade graph.py:395-404; KV read-your-writes kv.py:69-77.
  - runner: `degraded=partial` scheduler.py:701; trace refusal trace.py:123.
  - refusals: `_FOREIGN_FAILURE_CLASSES` refusals.py:750-758; `refusal_body` refusals.py:46-60.
  - `redact_secrets` foreign/v1_corpus_adapter.py:60-74.
- **The HippoRAG part line references in HIPP-01/02/06/09/19 still match.**
- **Protected tests (ledger `test_ref` files) need the owner's `grant-check-edit`.**
  - Expected in this phase: `tests/seam/test_foreign_engine_refusal.py` (SEAM-05, for D-11).
  - Relied on, not edited: `test_ingest_abort.py` (STOR-06, which imports `_make_engine`, `_DOCUMENT_TEXT`, `_HIPPORAG_CAPABILITY` and `_WORKSPACE` from `test_hipporag_write_path.py`; do not rename them), `test_query_trace_nodes.py` (LRAG-19), `test_empty_namespace.py` (LRAG-16), `test_corpus_write_gate.py` (LRAG-04), `test_health_probe.py` (STOR-04), `test_rest_corpus_endpoints.py` (RUN-10), the store tests STOR-03/07/09/10/16 and `test_evidence_namespace_guard.py` (SEAM-01).
  - No file under `tests/parts_core/hipporag/` is a test_ref.
  - The BAK check guard blocks Bash commands (including read-only grep, or any tests/ path combined with shell operators) that name protected files. Use the Read tool.
- **The interpreter is `databasise/.venv/bin/python`.** Commits need a `phase/12` trailer, and `.planning/` changes go in commits separate from code and trace.

</code_context>

<specifics>
## Specific Ideas

There are no owner requirements beyond the decisions above. The REQUIREMENTS.md test descriptions for each HIPP ID are the acceptance contract, with the exception clauses above.

Fail-first proofs need care:
- HIPP-03 and HIPP-04's cause half pass at HEAD, so record them `--at feadf3e^`.
- HIPP-15's jobs and health legs already pass, so its failing assertion must be the corpus leg.

</specifics>

<deferred>
## Deferred Ideas

- **LightRAG stale-ref hazard:** this fork's v1 chunk ids are `{doc_id}-chunk-{order:03d}` (utils_pipeline.py:62-73), so a changed-text re-ingest followed by a ref resolve can return new text. This is a cross-modality follow-up. It is outside HIPP-17.
- **Selector-scoped health:** a LightRAG-only workspace always reads `degraded` because the HippoRAG stores are absent (Phase 11 D-14 meaning). Revisit if health gains a selector.
- **Export-level `edge_types` audit:** one line in `export_to_igraph` if the owner wants it.
- **Batched edge reads:** for graph-augment-persist's per-pair `get_edge`. That is acceptable at current corpus sizes.
- **Upstream fidelity gaps outside HIPP scope:** `min_max_normalize` zero-range, entity-vs-fact divisor, `passage_node_weight` 0.05 vs 1.0, synonymy top-k.

</deferred>

---

*Phase: 12-hipporag-fixes*
*Context gathered: 2026-10-19*
