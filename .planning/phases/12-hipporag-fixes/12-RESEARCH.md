# Phase 12: HippoRAG Fixes - Research

**Researched:** 2026-10-19
**Domain:** HippoRAG 2 port inside the Databasise engine (parts_core/hipporag, stores, runner, seam engine, REST/MCP surface, BAK ledger fail-first discipline)
**Confidence:** HIGH for in-repo mechanics (every claim below was read in source this session; D-12 store semantics were also run as a probe against HEAD 194ba4f). MEDIUM for BAK record-fail rules (read from kit docs, not executed).

**Provenance tags used:** `[VERIFIED: path:lines]` = opened and read this session, discrete values quoted verbatim; `[VERIFIED: probe]` = run against HEAD this session; `[CITED: ...]` = read from a document; `[ASSUMED]` = my judgement or training knowledge, listed in the Assumptions Log.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### A. Evidence identity and graph shape (HIPP-01, 02, 06, 17)

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

#### B. Graph accumulation (HIPP-07, 08, 09, 19)

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

#### C. Ingest failure semantics (HIPP-03, 04, 10, A-WR-05)

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

#### D. Corpus lifecycle (HIPP-15, 16, empty namespace, write gate)

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

#### E. Query semantics (HIPP-05, 11, 12, 13, 14)

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

#### F. Config honesty (HIPP-18)

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

#### Requirement text exceptions (record in REQUIREMENTS.md)

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

### Deferred Ideas (OUT OF SCOPE)
- **LightRAG stale-ref hazard:** this fork's v1 chunk ids are `{doc_id}-chunk-{order:03d}` (utils_pipeline.py:62-73), so a changed-text re-ingest followed by a ref resolve can return new text. This is a cross-modality follow-up. It is outside HIPP-17.
- **Selector-scoped health:** a LightRAG-only workspace always reads `degraded` because the HippoRAG stores are absent (Phase 11 D-14 meaning). Revisit if health gains a selector.
- **Export-level `edge_types` audit:** one line in `export_to_igraph` if the owner wants it.
- **Batched edge reads:** for graph-augment-persist's per-pair `get_edge`. That is acceptable at current corpus sizes.
- **Upstream fidelity gaps outside HIPP scope:** `min_max_normalize` zero-range, entity-vs-fact divisor, `passage_node_weight` 0.05 vs 1.0, synonymy top-k.

Out of scope for the phase (Phase Boundary): WIRE-03 node-free refusal vocabulary (Phase 13), WIRE-08 guard comparison rewrite (Phase 13), WIRE-18 budget apportionment (Phase 13), tie-break changes (WIRE-01, Phase 13), promotion classing (Phase 14), LightRAG's own stale-ref hazard.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HIPP-01 | PPR-path items resolve (non-empty hydrated content, resolvable refs) | D-01 mechanics below (translate at ppr readback and reset-vector-join); test needs a stub fact-filter that keeps all fact ids (parse `id=<fid>:` out of the prompt) |
| HIPP-02 | reset-vector-join passage weights keyed like graph vertex names | D-01; test needs >=2 chunks with different scores (zero-range pitfall) |
| HIPP-03 | Failed ingest commits nothing | Passes at HEAD (probe + feadf3e); test plus `record-fail --at feadf3e^` |
| HIPP-04 | Refusal carries real cause and failing node id | `node_id` private attr + log; cause already carried at HEAD |
| HIPP-05 | fact-filter receives the query | `consumes_query` edit in base.json |
| HIPP-06 | Every chunk gets a passage vertex | D-02: openie `chunks` passthrough, passage-edges `vertices`, persist upserts them |
| HIPP-07 | Synonymy matches new entities against committed+staged | `self_knn(ids=...)` pending-aware design below; re-ingest "new" hole flagged (F3) |
| HIPP-08 | Edge weights/types accumulate across ingests | per-chunk map merge skeleton below; upstream uses the same shape (`fact_source_counts`) |
| HIPP-09 | Fact chunk_ids are the union across ingests | KV record is source of truth; union then mirror |
| HIPP-10 | Extraction failures reported; bounded concurrency | refuse with `ExtractionFailed`; reuse existing `max_concurrency` key |
| HIPP-11 | At most top_k items, zero-score PPR excluded | `top_k` key on assemble-result, cut after branch selection |
| HIPP-12 | Query-only nodes, one embed per query | D-16 prune, D-17 shared vector; callers listed below |
| HIPP-13 | Answer meaning matches LightRAG | `qa` node, upstream prompt, fail_response reuse |
| HIPP-14 | Fired guard visible in non-debug envelope | scheduler `degraded` from `guards_fired`, closed node-free reason codes |
| HIPP-15 | Job/corpus/health cover HippoRAG | manifest registry, read-only KV enumerator, optional selector on 2 REST routes + MCP status |
| HIPP-16 | Delete and clean re-ingest | remover part, manifest, `corpus-delete.json`, remover-first `corpus-ingest.json` |
| HIPP-17 | Refs never resolve silently to new text | `sha256(document_id:ordinal:text)`, needs the remover |
| HIPP-18 | Config keys read or removed; docstrings honest | removal list + docstring fix list below |
| HIPP-19 | No mixed counters under one label | shared helper in `runner/trace.py` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Read from `/home/chris/coding/Databasise-2.0-fully-agnostic-system/.claude/CLAUDE.md` and the user-global CLAUDE.md:

- **GSD workflow enforcement:** repo edits go through a GSD command; this research writes only RESEARCH.md.
- **Architecture:** D4 One Machine is settled; contract vocabulary (NodeKind tagged sum, 17-member `effects[]`, three artifact scopes, budget tokens, promote/rollback ledger) is frozen input. The §18 seam must stay modality-agnostic: swapping the fitted modality changes no field a consumer sees. (This is why HIPP-13/14/10 add no envelope or IngestJob field.)
- **Runtime:** Python, local NixOS, embeddable in-process, no external DB servers, no Docker.
- **Evidence standard:** no benchmark number settles a decision (the extra qa LLM call is priced against RIG §F3 at rig-run time, not now).
- **Conventions:** async-first, `a`-prefixed async variants, early validation / fail-fast, refusals over silent fallbacks, ruff py310 target, pytest + pytest-asyncio.
- **Project memory (user auto-memory):** never read `.env*` or `v1/parity-env.txt`; never run `pytest -m live`; BAK hooks block Bash commands that name protected tests/ledger (use the Read tool); commits need a `phase/12` trailer and `.planning/` changes go in separate commits; interpreter is `databasise/.venv/bin/python` run from `databasise/`.
- **User-global:** plain technical language; file references as workspace-relative markdown links (not applicable inside this RESEARCH.md, which uses code paths).

## Summary

Phase 12 is a set of in-repo changes with no new external packages. The decision study (D-01..D-22) holds up against the code. I found four places where the locked decisions collide with existing protected tests or leave a hole, and one place where a locked mechanism can be done with an existing key. The planner must resolve the collisions before sequencing (section "Findings that change or constrain the locked decisions"):

1. **D-14 (refuse-at-once HippoRAG gate) breaks two existing concurrency tests**, one of them protected (`test_ingest_abort.py`, STOR-06). A serialising gate satisfies the intent with no protected edit.
2. **D-15 (HippoRAG empty-namespace pre-check) breaks one protected test** in `test_ingest_abort.py` that the decision did not list.
3. **D-05 plus D-12 leave a hole on re-ingest:** an orphan entity is deleted by the remover and re-added by entity-fact-embed, but its committed vector makes it "not new", so its synonymy edges are lost.
4. The manifest does not need to record entity pairs; an edge walk per manifest entity finds them. This is within the "manifest record schema" discretion.

The store mechanics the study asked about are confirmed by code reading and a probe against HEAD: Cozo read-your-writes hides a pending `delete_node` cascade (so the remover need not stage edge deletes), and a buffered delete followed by an upsert of the same id cancels in both the Faiss and KV stores.

**Primary recommendation:** build in the order ids/vertices -> faults/redaction -> store+token primitives -> graph accumulation -> extraction failures -> lifecycle (remover, manifest, gate, id change) -> corpus surface -> query semantics -> config honesty and records. Resolve the D-14/D-15 test collisions (owner grant vs design change) before plan 1 ships, and write every HIPP test so it collects and fails by assertion on pre-fix code, because BAK's `record-fail` runs the whole check file at a pre-fix commit.

## Findings that change or constrain the locked decisions (read first)

These are not re-openings of D-01..D-22. They are facts the planner needs to schedule the work without breaking protected checks. Each cites the file read.

### F1. D-14 as written fails two existing concurrency tests

- `tests/seam/test_ingest_abort.py::test_two_concurrent_hipporag_ingests_on_one_root_both_commit_in_full` (protected, STOR-06) does `await asyncio.gather(*(engine.ingest(document, selector=_selector()) for document in documents))` with no `return_exceptions`, then asserts both documents committed. [VERIFIED: tests/seam/test_ingest_abort.py:250-265]
- `tests/seam/test_concurrent_ingest_failure.py::test_a_failing_ingest_does_not_destroy_a_concurrent_ingests_staged_vectors` gathers a good and a poisoned HippoRAG ingest and asserts `isinstance(bad, ForeignEngineRefusalError)` and `isinstance(good, IngestJob)`. [VERIFIED: tests/seam/test_concurrent_ingest_failure.py:35-65]
- Why a refuse-at-once gate breaks them: `Databasise.ingest` has no `await` before `_run_corpus_ingest` acquires its gate, and `_write_gate` uses `gate.acquire(blocking=False)`. The first coroutine acquires and then suspends in `run_wiring`; the second starts, finds the gate held and gets `StoreBusyError`. [VERIFIED: seam/engine.py:1133-1241, 1297-1307, 713-724]
- Baseline: both tests pass at HEAD (46 passed for the 7-file subset I ran).
- `test_corpus_write_gate.py::test_a_hipporag_ingest_beside_a_lightrag_ingest_is_not_gated` (protected, LRAG-04) still passes if the HippoRAG gate uses a key different from `_v1_working_dir()`. Use e.g. `store_root / workspace / "hipporag-write"`; `_gate_for` keys on `str(path.resolve())` and the path need not exist. [VERIFIED: seam/engine.py:704-710; tests/seam/test_corpus_write_gate.py:210-224]
- **Recommendation:** make the HippoRAG gate *serialise* (wait) rather than refuse. It prevents the lost-update problem D-14 exists for, keeps both tests green with no grant, and REST behaviour for a lone writer is unchanged. Implement the wait as a polling `await asyncio.sleep(...)` loop around `gate.acquire(blocking=False)` with a ceiling, then `StoreBusyError(store_kind="corpus")`. Do not block with `gate.acquire()` on the loop thread (deadlock when both writers share a loop), and do not `to_thread(gate.acquire)` (a cancelled waiter leaks the lock). Acquire it before `_build_stores` for HippoRAG, because `FaissVectorStore` loads its committed snapshot at construction and the D-05 "new entity" test reads `get_by_id` against that snapshot.
- **If the owner insists on refuse-at-once,** the plan needs `grant-check-edit` for `test_ingest_abort.py` (rewrite the concurrent test to expect exactly one `IngestJob` and one `StoreBusyError`) and an edit to `test_concurrent_ingest_failure.py` (check whether it is a ledger test_ref first). Raise this with the orchestrator; do not decide it silently.
- `delete_document` currently enters `_write_gate(self._v1_working_dir())` unconditionally. Make that conditional on the family of the *selector-resolved query wiring* (`wiring_family(query_wiring)`), not of the delete wiring, because `tests/stores/test_delete_commit_contract.py` (STOR-07, protected) monkeypatches `_corpus_wiring` and runs a default-selector (LightRAG) delete through the LightRAG gate. [VERIFIED: seam/engine.py:1558-1584; tests/stores/test_delete_commit_contract.py:86-100]

### F2. D-15 as written fails one protected test it did not list

- `tests/seam/test_ingest_abort.py::test_a_query_after_a_refused_ingest_returns_no_evidence_from_it` (protected, STOR-06) refuses an ingest on a fresh root, then runs a HippoRAG query and asserts `envelope.evidence == []`. After a refused ingest nothing is committed, so `hipporag-chunks` is "never populated" and the D-15 pre-check raises `EmptyNamespaceError` instead. [VERIFIED: tests/seam/test_ingest_abort.py:77-82]
- D-15's list of files to check named `test_cross_modality_run.py`, `test_compare.py` and `test_store_isolation.py`; those use populated stores (`seeded_hipporag_store`, `_build_stores` only) and are not affected. [VERIFIED: tests/seam/test_cross_modality_run.py:63-72; tests/seam/test_store_isolation.py:19-53; grep of tests/seam/test_compare.py]
- Other HippoRAG query tests are populated first: `test_query_store_fault.py` (ingests, then corrupts `hipporag-chunks/vector.faiss`; the pre-check raises `StoreCorrupted` through `load_committed`, the same class the test expects). [VERIFIED: tests/seam/test_query_store_fault.py:25-45; seam/engine.py:393-395]
- **Recommendation:** edit that one test under an owner `grant-check-edit` to expect `EmptyNamespaceError` (the refused ingest left the store unpopulated, which is the point of the pre-check), or populate the store with a good ingest first. The new HIPP-03 test must be written the same way: either ingest a good document first and show the refused document contributes no evidence, or assert `EmptyNamespaceError` on a fresh workspace.

### F3. D-05 plus D-12: re-ingest loses an orphan entity's synonymy edges

- With the remover as first node of `corpus-ingest.json`, re-ingesting a document deletes each orphan entity: `graph.delete_node(entity)` (cascades its synonymy and co-occurrence edges) and `entities_ns.delete_by_ids([entity])`. entity-fact-embed then upserts the same entity id, which cancels the buffered vector delete. [VERIFIED: probe — a buffered delete then upsert of the same id leaves the id present with the new metadata]
- D-05 defines "new entity" as `get_by_id is None` at committed level. The orphan's vector is still committed, so it is "not new", synonymy-edges never re-emits its edges, and the cascade-deleted synonymy edges are not restored. A changed-text or identical re-ingest therefore silently drops synonymy for every entity unique to that document.
- **Recommendation (no new effect declaration):** the remover returns `removed_entities` (the refs it deleted). In `corpus-ingest.json` only, give `entity-fact-embed` a direct dep on the remover. entity-fact-embed already holds a vector write proxy, so it computes `is_new = get_by_id(ref) is None or ref in removed_entities` *before* its upsert and puts `new_entities` (the refs) in its output; synonymy-edges reads `new_entities` from its existing dep and passes them as `ids=`. Keep a fallback inside synonymy-edges (`get_by_id is None` per ref) for the existing unit tests that supply only `entities`. `base.json` is untouched, so MODAL-04 is unaffected.
- Alternative that costs an effect declaration: `reads_graph` on synonymy-edges and "new = entity vertex absent read-your-writes". It changes the PARTS §H effects reconciliation table and `test_registration.py`, so I do not recommend it.
- Needs a test: ingest d1, re-ingest d1 (same text), assert the films-movies synonymy edge still exists afterwards.

### F4. The manifest does not need to store entity pairs

- D-12 lists "touched entity pairs" in the manifest; the schema is explicitly Claude's discretion. A pair list means a fourth copy of `_canonical_pair` (it is already defined in `fact_edges.py`, `synonymy_edges.py` and `graph_augment_persist.py`) and a second source of truth next to the edge attributes.
- Edge walk instead: for each manifest entity, `graph.get_node_edges(entity)` (one Cozo query per entity, read-your-writes, hides edges to chunk vertices already deleted). Every co-occurrence edge carrying this document's chunk ids has both endpoints in the document's entity list, so the walk finds all of them, including edges to entities of other documents (synonymy edges, which carry no map entry for this document).
- Recommended manifest record: `doc:<document_id>` -> `{"chunk_ids": [...], "fact_ids": [...], "entities": [...], "ingested_at": "<iso utc>"}`.
- Upstream does the equivalent: `delete()` walks every edge and strips the deleted chunks from `fact_source_counts` [VERIFIED: /home/chris/coding/reference-repos/HippoRAG/src/hipporag/HippoRAG.py:595-690].
- If the owner reads D-12's wording strictly (pairs in the manifest), the edge walk is still required for correctness, so pairs would be redundant data. Flag it, do not silently drop it.

### F5. D-08's concurrency bound already exists as `max_concurrency`

- The scheduler validates `config.max_concurrency` (default 1, refused below 1 before any node runs), builds a per-node `asyncio.Semaphore` of that size and exposes it as `ctx._semaphore`. [VERIFIED: runner/scheduler.py:348-365 (`_validated_max_concurrency`), :446-448 (`semaphore = asyncio.Semaphore(max_concurrency)`), :474 (`ctx._semaphore = semaphore`)]
- Set `"config": {"max_concurrency": 4}` on `openie` in `base.json` and `corpus-ingest.json` and have the body build its own `asyncio.Semaphore(int(config.get("max_concurrency", 1)))` (hand-built `NodeContext`s in part tests carry no `_semaphore`). No new config key is introduced, and the value-change test is "1 vs N gives max in-flight 1 vs N". The default 4 is my choice [ASSUMED A1]; v1 uses `chunk_max_async` for the same purpose.

### F6. Protected-test edit inventory (needs the owner's `grant-check-edit`)

| File | Test | Decision | Needed edit |
|------|------|----------|-------------|
| `tests/seam/test_foreign_engine_refusal.py` (SEAM-05) | `test_the_full_cause_is_logged_once_server_side`, line 118 `assert records[0].exc_info[1] is cause` | D-11 | replace with a redacted-form pin: `exc_info` falsy, `failure_class=` and `operation=` still in the message, type name present |
| `tests/seam/test_ingest_abort.py` (STOR-06) | `test_a_query_after_a_refused_ingest_returns_no_evidence_from_it` | D-15 (F2) | expect `EmptyNamespaceError`, or populate first |
| `tests/seam/test_ingest_abort.py` (STOR-06) | `test_two_concurrent_hipporag_ingests_on_one_root_both_commit_in_full` | D-14 (F1) | none if the gate serialises; rewrite if it refuses |
| `tests/seam/test_concurrent_ingest_failure.py` | `test_a_failing_ingest_does_not_destroy_a_concurrent_ingests_staged_vectors` | D-14 (F1) | none if the gate serialises; ledger status unknown |

Everything else I checked stays valid unedited: `test_query_trace_nodes.py` (LRAG-19) as long as `engine._without_recipe_only_nodes` keeps its name and `hybrid` still drops only `embedder-index` [VERIFIED: tests/seam/test_query_trace_nodes.py:65-74; and a probe shows ancestors-of-provides pruning leaves every LightRAG arm's node set equal to today's run set]; `test_empty_namespace.py` (LRAG-16) if the HippoRAG pre-check uses a separate table; `test_corpus_write_gate.py` (LRAG-04); `test_vector_validation.py`/`test_vector_reserved_keys.py` (STOR-09/16) if `ids=None` keeps the current code path; `test_health_probe.py` (STOR-04) because no namespace is added.

The BAK hooks: a Bash command that names a protected test file *and* starts with `timeout` was blocked; the same pytest command without the `timeout` prefix ran fine. Any grep over a directory holding protected tests is blocked (use the Read tool or grep an explicit unprotected file). [VERIFIED: observed this session]

### F7. How BAK `record-fail` constrains test authoring

[CITED: /home/chris/coding/GUI-research/docs/learn/15-running-a-project.md lines 133-137]
- It runs the named command, records the exit code, output tail, HEAD and the test file's hash, and refuses a passing run, a run with no output, and (for a `file::node` test_ref) a run whose output never names the node in a failure header.
- "A check file shared by several rows must hold all their tests before the first record-fail on it: adding a test to it later is an edit of every row's check in that file." Most HIPP tests live in `test_hipporag_write_path.py`, `test_graph_construction.py` and `test_index_side_extraction.py`, so author all of a file's HIPP tests before any `record-fail`, and do not touch those files after. Phase 11 handled this by recording fail-first retroactively with `--at <pre-fix commit>` (commit 51469e4). [VERIFIED: git show 51469e4]
- Therefore: no module-level import of a name that does not exist pre-fix (a collection error never names the node). Import new symbols inside the test body, or use `getattr(module, name, None)`.
- One test per row; two rows cannot share a node.
- `pytest.raises(...)` on pre-fix code that does not raise ends in `Failed`, which is a `BaseException`, not an `AssertionError` [VERIFIED: probe `_pytest.outcomes.Failed.__mro__`]. For "must raise" checks on a path that currently does not raise, capture the exception in a `try/except` and `assert` on the result so the pre-fix failure is an assertion.

### F8. Names protected or sibling tests import from `test_hipporag_write_path.py`

Do not rename or remove: `_DOCUMENT_TEXT`, `_HIPPORAG_CAPABILITY`, `_WORKSPACE`, `_make_engine`, `_StubEmbeddingClient`, `_StubIngestQueryLLMClient`. They are imported by `test_ingest_abort.py`, `test_corpus_write_gate.py`, `test_concurrent_ingest_failure.py`, `test_query_store_fault.py` and `test_job_families.py`. [VERIFIED: import lines of each file]. Keep `_StubIngestQueryLLMClient`'s default behaviour for the existing prompts (it dispatches on `messages[0]["content"]`; fact-filter keeps `[]`). Add new stub classes for the PPR-branch and qa tests instead of changing it.

### F9. Smaller edge cases the planner should cover

- A PPR-branch query can yield zero positive items (ppr returns all zeros when the reset vector sums to 0), so after D-20's zero-score drop the answer is `fail_response` and evidence is empty although the guard did not fire. Decide whether that is acceptable (I read D-20 as accepting it); add a test pinning the behaviour. [VERIFIED: parts_core/hipporag/ppr.py:67-73]
- Stores built before Phase 12 have bare chunk ids hashed without text, no `doc:` manifests and `chunk:`-free vertex edges that lack `cooccurrence_by_chunk`. Re-ingesting a pre-Phase-12 document id leaves its old chunks (no manifest to remove them by). Treat such stores as rebuild-required and say so in the port record. A missing manifest must make the remover a no-op, never an error. [ASSUMED A4]
- `parity/build_hipporag_index.py` runs `corpus-ingest.json` directly and stamps documents only on `consumes_documents[0]`; the remover therefore must tolerate a missing/empty `documents` config and `chunk-embed` must stay `consumes_documents[0]`. [VERIFIED: parity/build_hipporag_index.py:146-160, 215-217]
- Strict extraction (D-08) means a real-provider parity or eval ingest now fails on the first malformed JSON where it used to degrade to zero findings. That is the accepted trade-off; mention it in the port record.
- `eval/aa_run.py` raises `ConfoundedPassError` on any `degraded` envelope, so after D-21 an A/A pass on the HippoRAG arm that takes the DPR fallback is refused. [VERIFIED: eval/aa_run.py:156-170, 381-382]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chunk id mint and vertex-name translation | parts_core/hipporag (index parts + ppr/reset-vector-join) | — | `chunk_embed.py:80` is the only mint site; translation belongs at the graph boundary parts |
| Edge accumulation, orphan detection, fact union | parts_core/hipporag (graph-augment-persist, entity-fact-embed, remover) | stores (graph/kv/vector read-your-writes) | engine commits all stores atomically; parts only stage |
| Pending-aware self-KNN | stores/vector.py | parts_core (synonymy-edges) | §14.2 batched self-KNN is a store capability |
| Per-document manifest and document registry | stores/kv (key `doc:<id>`) | seam/engine (read-only listing) | one registry, written in the same commit as the data |
| Document lifecycle (delete, re-ingest) | wirings + remover part | seam/engine (stamping, gate) | on-disk `corpus-<op>.json` is the write-path lookup table |
| HippoRAG write serialisation | seam/engine (`_write_gate` pattern) | — | machine-owned lifecycle, not a part concern |
| Query-run pruning | wirings/resolve.py (`without_recipe_only_nodes`) | seam/selectors.py, seam/engine.py, seam/promotion.py | shared with LightRAG; one helper |
| Degraded semantics for a fired guard | runner/scheduler.py + runner/trace.py | seam/engine.py (`_node_result_or_refuse`) | the scheduler owns the guard record |
| Failure-class vocabulary, `node_id`, log redaction | seam/refusals.py, seam/engine.py `_foreign_fault` | foreign/v1_corpus_adapter.py (`redact_secrets`), runner/scheduler.py | single fault-logging choke point |
| Answer generation | parts_core/hipporag/qa (new) | clients (LLM) | same `fail_response` string as LightRAG |
| Corpus read selector | seam/rest.py, mcp/tools.py + server.py | seam/engine.py | transports stay thin; engine resolves the selector |

## Standard Stack

All work is in-repo. No new external package is recommended.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.13 [VERIFIED: probe] | runtime | project interpreter `databasise/.venv/bin/python` |
| pytest + pytest-asyncio | pytest 9.1.1 [VERIFIED: probe], `asyncio_mode = "auto"` | test runner | `[tool.pytest.ini_options]` in pyproject.toml, `addopts = '-m "not live"'` |
| faiss-cpu | 1.15.0 [VERIFIED: probe `faiss.__version__`] | vector stores, self-KNN | already the store backend |
| python-igraph | 1.0.0 [VERIFIED: probe] | PPR | already used by ppr |
| pycozo (embedded) | as installed | graph store | read-your-writes semantics verified |
| sqlite3 (stdlib) | stdlib | KV store, read-only manifest listing | no new dependency |
| numpy | 2.5.2 [VERIFIED: probe] | pending-vector scoring in `self_knn(ids=...)` | already a store dependency |
| FastAPI / pydantic | 0.141.1 / 2.13.5 [VERIFIED: probe] | REST selector query parameter | existing transport |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| serialising HippoRAG gate | refuse-at-once gate (D-14 literal) | needs protected-test edits (F1) |
| existing `max_concurrency` key | new `max_async` key | extra key needs its own value-change test and hash churn |
| edge walk per manifest entity | pairs in the manifest | duplicate source of truth (F4) |
| `removed_entities` threaded to entity-fact-embed | `reads_graph` on synonymy-edges | changes effects tables and tests (F3) |

**Installation:** none.

**Version verification:** versions above were read from the live venv this session; no registry lookup applies because nothing is installed.

## Package Legitimacy Audit

No external packages are installed or added by this phase, so the package-legitimacy gate does not apply.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
INGEST (selector -> hipporag)                         QUERY (selector -> hipporag, run pruned to ancestors of qa)
 IngestDocument                                        QueryObject.text
   |                                                     |  _inject_query: fact-score, fact-filter, qa get config.query
   v                                                     v
 [HippoRAG gate] (D-14, key != v1 dir)                 [EmptyNamespace pre-check: hipporag-chunks] (D-15)
   |                                                     |
   v                                                     v
 document-remover (NEW, first node)                    fact-score ---- embeds query ONCE, emits query_vector (D-17)
   |  reads doc:<id>; stages deletes: chunk vectors,     |        \
   |  KV, chunk vertices (cascade), reduced facts,       v         \
   |  reduced co-occurrence maps, orphan entities        fact-filter (LLM, sees query) --guard--> guards_fired
   |  emits removed_entities                             |   \                                     |
   v                                                     |    +--> reset-vector-join (uses query_vector, adds 'chunk:' prefix)
 chunk-embed (ids sha256(doc:ordinal:text), writes        |          |
   vector+KV+doc:<id> base manifest)                      |          v
   |                                                     |        ppr (strips 'chunk:' on readback)
   v                                                     |          |
 openie (bounded concurrency, collect ALL failures,      +--> dpr-fallback (uses query_vector)
   passes chunks through)  -- any failure ->                         |
   |        ExtractionFailed refusal (nothing commits)               v
   +--> entity-fact-embed (union fact chunk_ids, merge        assemble-result (guard picks ppr|dpr, drop zero PPR,
   |     manifest, flags new_entities)                         cut to top_k, hydrate content from KV)
   +--> fact-edges (cooccurrence_by_chunk)                       |  evidence minted here (evidence_position)
   +--> passage-edges (vertex for EVERY chunk)                   v
   +--> synonymy-edges (self_knn(ids=new_entities))            qa (LLM; fail_response if no passages)  -> answer
   |        \                                                    |
   v         v                                                  v
 graph-augment-persist (get_edge -> merge -> upsert_edge)     ResponseEnvelope (degraded=true + node-free reason
   |                                                           when the DPR fallback fired, D-21)
   v
 engine: all-or-none  prepare-all -> commit-all (kv, vector, graph)   |  any node exception => _drop_pending, refusal
                                                                        v
 IngestJob / jobs.db record (job registry);  doc:<id> manifest = document registry (D-13)

DELETE: gate -> document-remover alone (corpus-delete.json) -> commit-all -> DeletionOutcome(success|not_found)
CORPUS READ: GET /corpus?selector=..  /corpus/counts?selector=.. , MCP status.selector -> read-only manifest listing
```

### Recommended Project Structure (additions)

```
databasise/
├── parts_core/hipporag/
│   ├── vertices.py            # NEW: ENTITY_/CHUNK_VERTEX_PREFIX + chunk_vertex()/chunk_id_of() (one definition; entity_fact_embed re-exports)
│   ├── document_remover.py    # NEW: remover Part (name at Claude's discretion)
│   ├── qa.py                  # NEW: upstream rag_qa port
│   └── (existing parts edited)
├── wirings/hipporag/
│   ├── base.json              # +qa node, provides [qa], consumes_query [fact-score, fact-filter, qa], pruned keys removed
│   ├── corpus-ingest.json     # +remover first node, chunk-embed deps [remover], consumes_documents [chunk-embed, remover]
│   └── corpus-delete.json     # NEW: {remover}, provides [remover], store_namespaces as corpus-ingest.json
├── stores/vector.py           # self_knn(ids=...)
├── stores/kv.py               # module-level read-only prefix lister (or in probes.py)
├── runner/trace.py            # UNBUDGETABLE_SENTINEL, sum_token_accountings(), relaxed invariant, reason-code constants
└── evidence/HIPPORAG-PORT-RECORD.md   # updated sections
```

### Pattern 1: D-12 store semantics (verified)

[VERIFIED: probe `ryw_probe.py` against HEAD; code seam/../stores/graph.py:232-282, 395-409, 432-459]

- `CozoGraphStore.delete_node(n)` drops pending edge puts touching `n`, marks every committed edge incident to `n` in `_pending_edge_rms`, and adds `n` to `_pending_node_rms`. `_edge_hidden` hides an edge when its key is in `_pending_edge_rms` or either endpoint is in `_pending_node_rms`. `get_edge`, `has_edge`, `node_degree`, `get_node_edges`, `export_to_igraph` all consult it.
- Probe output: after `delete_node("chunk:a")` over a committed graph, `get_edge("chunk:a","entity:x")` is `None`, `has_node("chunk:a")` is `False`, `get_node_edges("entity:x")` no longer lists the chunk edge, `node_degree` drops by one. After `upsert_node("chunk:a", {})` only, the edge stays hidden; after `upsert_edge` it reads back the new attrs. After `delete_node("entity:y")`, `get_edge("entity:x","entity:y")` is `None`.
- Conclusion: the remover does **not** need to stage edge deletes explicitly. graph-augment-persist's `get_edge` sees the post-removal state, and `upsert_edge` (which discards the key from `_pending_edge_rms`) cleanly re-creates an edge for an unchanged chunk.
- `FaissVectorStore.upsert` does `self._pending_deletes.discard(doc_id)`; `delete_by_ids` pops any pending upsert and adds the delete. Probe: delete `{a,b}` then upsert `a` leaves `_pending_deletes == {'b'}`, and after flush `a` carries the new metadata. [VERIFIED: stores/vector.py:355-366]
- `SqliteKVStore.upsert` discards the id from `_pending_deletes`; `delete` pops the pending upsert. Probe: delete `{a,b}`, upsert `a` -> `a` readable with the new value, `b` is `None`, and the flush keeps that. [VERIFIED: stores/kv.py:69-97]
- A vector delete of an id with no committed entry is a no-op at flush; a namespace emptied by deletes keeps a zero-row index, so a later query is "no match", not `EmptyNamespaceError`. [VERIFIED: stores/vector.py:526-535; tests/seam/test_empty_namespace.py:97-108]

### Pattern 2: the remover (mechanics for D-12)

Part effects: `writes_kv`, `writes_vector`, `writes_graph` (write proxies expose reads; `_READ_ALLOWLIST` applies only to mode `"r"`). [VERIFIED: parts_core/__init__.py:73-86, 130-165]. Config: `documents` (ingest path, list of `{document_id,...}`, stamped by the engine) or `doc_id` (delete path, stamped the way `delete_document` stamps `doc_id` today). Missing/empty config is a no-op.

Per document:
1. `manifest = await kv.get_by_id("doc:<id>")`; `None` -> `not_found`, nothing staged.
2. Delete chunk vectors (`select("hipporag-chunks").delete_by_ids`), chunk KV rows, and `graph.delete_node("chunk:<id>")` for every chunk id.
3. Facts: for each `fact_id`, `rec = await kv.get_by_id("fact:<id>")`; `remaining = rec.chunk_ids - removed`. If empty, `kv.delete(["fact:<id>"])` and `facts_ns.delete_by_ids([fid])`. Otherwise `kv.upsert` the reduced record and refresh the fact vector metadata. `FaissVectorStore` has no metadata-only update, so re-upsert the same vector: read it with one `iter_vectors()` pass over the facts namespace (committed entries only), `get_by_id(fid)` for the metadata, set `chunk_ids = remaining`. Cost is O(facts) once per remover run [ASSUMED A5 acceptable at current sizes].
4. Entities, after the chunk vertices are deleted: for each manifest entity, `edges = await graph.get_node_edges(entity)`. Orphan = no remaining neighbour whose name starts with the chunk prefix. Orphan -> `graph.delete_node(entity)` + `entities_ns.delete_by_ids([entity])`, add to `removed_entities`. Collect orphans first, then for surviving entities reduce each incident edge once (dedupe by canonical key) that has a removed chunk id in `cooccurrence_by_chunk`, skipping edges whose other endpoint is an orphan: recompute `weight`, `delete_edge` when the map is empty and no synonymy remains, else `upsert_edge`.
5. `kv.delete(["doc:<id>"])`. Result: `{"status": "success" | "not_found", "message": "", "removed_entities": [...]}`; `delete_document` passes `status` through `DeletionOutcome` and commits on `success`/`not_found`. [VERIFIED: seam/engine.py:1604-1615]

Upstream equivalent for citation: `HippoRAG.delete` strips deleted chunks from per-edge source maps, removes unreferenced entities/facts, and keeps shared ones. [VERIFIED: reference clone HippoRAG.py:595-690]

### Pattern 3: manifest writing

`document_id` is available to `chunk-embed` and, through openie's chunk passthrough (D-02), to `entity-fact-embed`. Two writers, one key, merged in-run (KV reads are read-your-writes):
- `chunk-embed` writes `doc:<document_id>` = `{"chunk_ids": [...], "fact_ids": [], "entities": [], "ingested_at": ...}` for every document with chunks, even when OpenIE finds nothing (HIPP-06 / delete must still find those chunks).
- `entity-fact-embed` re-reads that key and sets `fact_ids` and `entities` for the documents it processed. Its early return when there are no findings (`entity_fact_embed.py:76-77`) is then harmless.
- Keep the chunk KV row exactly `{"content": text}`; an existing test asserts `stored == {"content": record["text"]}`. [VERIFIED: tests/parts_core/hipporag/test_index_side_extraction.py:96]
- `test_ingest_abort._committed_chunks` compares the full KV id set between a sequential and a concurrent run; manifest and fact keys appear in both, so it still holds.

### Pattern 4: `self_knn(ids=...)` (D-05)

Signature: `async def self_knn(self, *, top_k: int, ids: Sequence[str] | None = None)`. `ids is None` keeps today's body unchanged (the existing test pins exactly one `search` call). [VERIFIED: stores/vector.py:436-484; tests/stores/test_vector_self_knn.py:63-71]

For `ids` given (skeleton, not final code):
```python
if top_k <= 0: raise InvalidTopKError(top_k)             # STOR-09 stays first
dead = self._pending_deletes
shadow = set(self._pending) & set(self._entries)          # committed ids superseded by a pending upsert
def vec(i):                                               # pending wins over committed
    if i in dead: return None
    if i in self._pending: return self._pending[i].vector            # already L2-normalised
    e = self._entries.get(i);  return None if e is None else self._index.reconstruct(e["int_id"])
rows = {i: v for i in ids if (v := vec(i)) is not None}
# committed candidates: ONE batched search with k widened by the ids that may be filtered out
k = min(top_k + 1 + len(dead & set(self._entries)) + len(shadow), ntotal)
# pending candidates: numpy dot of the stacked normalised pending vectors
# merge, drop self / dead / shadowed-committed, sort by (-score, id), cut to top_k
```
- Handle `self._index is None` (first ingest ever: committed index absent, pending present). The default path returns `{}` there; the `ids` path must not.
- Pending vectors are stored normalised, and committed vectors come back normalised from an inner-product index, so numpy dot equals Faiss scores. [VERIFIED: stores/vector.py:352-357, 486-494]
- Also add `ids` to `MultiNamespaceVectorStore.self_knn`'s signature (it only raises `VectorNamespaceNotSelectedError`). The read allowlist already contains `self_knn`. [VERIFIED: parts_core/__init__.py:75; stores/vector.py:748-749]
- Add tests in a new file (`tests/stores/test_vector_self_knn_pending.py`) rather than editing `test_vector_self_knn.py`, whose protection I did not establish.

### Pattern 5: edge merge in graph-augment-persist (D-04)

Edge attrs written: `{"weight", "edge_types", "cooccurrence_by_chunk"?, "synonymy_weight"?, "passage_weight"?}`.
```python
stored = await graph.get_edge(src, tgt) or {}
co = dict(stored.get("cooccurrence_by_chunk") or {})
co.update(incoming_by_chunk)                       # overwrite per chunk key => idempotent on re-ingest
syn = max(stored.get("synonymy_weight", 0.0), incoming_syn)
passage = 1.0 if (incoming_passage or stored.get("passage_weight")) else 0.0
weight = sum(co.values()) + syn + passage          # must equal 2.0 + 0.95 in the existing collapse test
types = ordered_union(stored.get("edge_types", []), incoming_types)
await graph.upsert_edge(src, tgt, {...})           # keep upsert_edge: test_ingest_abort monkeypatches it
```
- `fact-edges` must emit the per-chunk map: `{"src","tgt","weight","edge_type","by_chunk":{chunk_id: count}}` (count per finding, so the same triple twice in one chunk counts 2, matching `fact_edges.py:62-67`'s per-finding count). An incoming edge without `by_chunk` contributes an anonymous amount: key it `""` in the map so the existing unit test (`weight == 2.0 + 0.95`) keeps its meaning. [VERIFIED: tests/parts_core/hipporag/test_graph_construction.py:244-262]
- Legacy stored edge with no map: treat its `weight` as `{"": weight}` only when its types are exactly `["fact-cooccurrence"]`; otherwise leave it. Pre-Phase-12 stores are rebuild-required anyway (F9) [ASSUMED A4].
- `upsert_node(vertex, {})` currently runs for every vertex and wipes node attrs; harmless (no node carries attrs). [VERIFIED: graph_augment_persist.py:80-81]
- One `get_edge` per pair is acceptable at current sizes (CONTEXT deferred this). Export keeps reading only `weight`. [VERIFIED: stores/graph.py:356-363]

### Pattern 6: D-16 pruning

Generalise `without_recipe_only_nodes(resolved)` in `wirings/resolve.py` in place: compute ancestors of `provides` over `deps` and delete every other node from the deep copy; fall back to the old recipe-only rule when `provides` is empty or names no existing node (fixture wirings), otherwise an empty `provides` would delete every node.

Every caller [VERIFIED: grep over non-test dirs + test greps]:
| Caller | Use | Effect of the change |
|--------|-----|----------------------|
| `seam/engine.py:379` alias `_without_recipe_only_nodes` | name pinned by protected `test_query_trace_nodes.py:67,74` | keep the name |
| `seam/engine.py:1843` `_execute_resolved` | dispatched run | HippoRAG run drops 7 index nodes; LightRAG sets unchanged |
| `seam/promotion.py:125` `_arm_name_for_node_ids` | matches persisted trace node set to an arm | new 6/7-node HippoRAG traces match the pruned set, old 13-node traces still match the full set |
| `tests/seam/test_promote.py:42` `_seed_trace` | builds trace node ids | follows automatically |
| `seam/selectors.py:160` `_match_capability` | NEW call | effect union over the pruned copy; keep `len(candidate[1]["nodes"])` (full) as the tie-break key |

Not changed: `_wiring_effects` itself (used by `promotion.declared_surface` and the compare `mutates_store` refusal). [VERIFIED: seam/selectors.py:142-167; seam/promotion.py:175-183; seam/engine.py:1122-1125]

Probe results (computed this session over `all_wirings()`): ancestors-of-provides equals today's run set for naive, bypass, hybrid, local, global; for hipporag it drops exactly `chunk-embed, entity-fact-embed, fact-edges, graph-augment-persist, openie, passage-edges, synonymy-edges` (13 -> 6; 7 with `qa`). Effect union lost by pruning: naive/hybrid/local/global lose `writes_artifact`; hipporag loses `writes_artifact, writes_graph, writes_kv, writes_vector` and keeps `calls_embedding, calls_llm, reads_graph, reads_kv, reads_vector`. [VERIFIED: probe `eff_probe.py`] So `[writes_artifact]` stops resolving to `naive`; no test I read resolves such a selector, but the `_resolve_default` path (`_is_default_eligible`) is unaffected.

### Pattern 7: D-21 degraded from guards

[VERIFIED: runner/scheduler.py:668-704, runner/trace.py:99-133, runner/guards.py:67-84]
- `evaluate_guards` already fills `NodeTrace.guards_fired` per node; the final `return` hard-codes `"degraded": partial`.
- Change to `degraded = partial or any(t.guards_fired for t in node_traces)`. When degraded but not partial, set `stop_reason` and `degradation_reason` from a small closed set. Suggested (my choice, [ASSUMED A3]): constants in `runner/trace.py`, `STOP_REASON_DECLARED_FALLBACK = "declared_fallback"` and `DEGRADATION_REASON_FALLBACK_PATH = "fallback_path_taken"`. Neither contains a node id or the substring `guard`, which the existing envelope test requires. [VERIFIED: tests/parts_core/hipporag/test_dpr_fallback_guard.py:266-275 asserts "guard" not in the serialised envelope]
- `RunRecord.__post_init__`: remove the `partial != degraded` raise; keep "either flag true needs both reasons" (the frozen schema's two `allOf` clauses require both reasons for either flag) and "no reason when neither flag". `tests/runner/test_run_record.py::test_12` only pins the reason/flag mismatches, not `partial != degraded`. [VERIFIED: tests/runner/test_run_record.py:188-197; docs/system-model/rig-trace.schema.json allOf]
- RIG.md `§LC.2` supports partial without degraded. [CITED: docs/system-model/RIG.md ~line 625]
- `_node_result_or_refuse`: change `if scheduled.get("partial") or stop_reason:` to `if scheduled.get("partial"):` so a declared fallback on an ingest or delete wiring can never refuse the run. [VERIFIED: seam/engine.py:823-824]
- Other `degraded` consumers pick the new meaning up automatically: `parity/run_arm.py:236`, `parity/run_comparison.py:390`, `parity/build_hipporag_index.py` (refuses a degraded index build; the ingest wiring declares no guards), `parity/run_cross_modality.py:339-345`, `eval/aa_run.py:381`.

### Pattern 8: D-19 `qa` node

Upstream (reference clone @ d5c8329, `HippoRAG.py:1117-1172` and `prompts/templates/rag_qa_musique.py`): messages are `[system rag_qa_system, user one_shot_rag_qa_input, assistant one_shot_rag_qa_output, user prompt_user]` where `prompt_user` is `"Wikipedia Title: {passage}\n\n"` per passage (first `qa_top_k`) followed by `"Question: " + question + "\nThought: "`; the answer is `response.split('Answer:')[1].strip()`, falling back to the whole response. `qa_top_k` defaults to 5. [VERIFIED: reference clone files read this session; config_utils.py:203-206]
- The LLM client forwards `messages` unchanged, so an `assistant` message and a leading system message both work. [VERIFIED: clients/openai_compat.py:168-179; clients/base.py LLMClient docstring]
- The `qa` Part: kind `"generator"`, `structural_depth="opaque"` (keeps `depth_label` opaque and the existing "all opaque" tests), effects `["calls_llm"]`, `upstream_ref="hipporag/src/hipporag/HippoRAG.py"`, deps `["assemble-result"]`, query from `config["query"]` (add `qa` to `consumes_query`).
- Empty hydrated passages: return `{"completion": PROMPTS["fail_response"], "tokens": TokenAccounting(counted_by="none")}` with no call, exactly as `lightrag/generator-llm` does. Import the constant from `databasise.parts_core.lightrag.prompts` (the text is `"Sorry, I'm not able to provide an answer to that question.[no-context]"`) and add a one-line equality test so the two cannot drift. [VERIFIED: parts_core/lightrag/generate.py:54-60; parts_core/lightrag/prompts.py:14-16]
- None of the upstream prompt text contains `---Candidate Facts---` or `---Recognised Entities---`. The existing stubs dispatch on `messages[0]["content"]`, which for qa is the system prompt, so they fall through to their default branch; tests that need a generated answer need a stub that recognises `"As an advanced reading comprehension assistant"`.
- Evidence is still minted from `assemble-result`; `_select_answer` reads `completion` from the `provides` node (`qa`). `assemble-result` stops emitting `completion` (remove the join and its "named limitation" docstring).
- Selector margin: 14 nodes vs local/global 15 keeps `[reads_graph, reads_kv]` resolving to hipporag. [VERIFIED: probe node counts above]

### Pattern 9: D-08 openie

[VERIFIED: parts_core/hipporag/openie.py:72-194 read in full]
- `_parse_entities`/`_parse_triples` must distinguish "unparseable" from "valid but empty". Unparseable: not JSON, not an object, or missing/non-list `entities`/`triples`. Valid with zero items is not a failure. Individual malformed triple items may still be skipped.
- Per chunk: NER call then triple call, sequential (the triple prompt needs the entities). Run chunks under the semaphore; catch `Exception` (not `BaseException`) inside each task and return a failure record `{"chunk_id", "reason"}`, so a plain `asyncio.gather(*tasks)` never swallows `CancelledError`. Order results by input order.
- After gathering: any failure -> `raise ExtractionFailedError(failed_chunks=n, failure_reasons=[...capped...])`. Define the exception in `openie.py`; map it by class name in `_FOREIGN_FAILURE_CLASSES["ExtractionFailedError"] = "ExtractionFailed"` (the table is keyed by the cause's type name and `refusals.py` imports nothing from parts). [VERIFIED: seam/refusals.py:750-758, 777-789]
- In `ForeignEngineRefusalError.__init__`, mirror the `V1NotConfigured` precedent: `if self.failure_class == "ExtractionFailed": self.failed_chunks = int(getattr(cause, "failed_chunks", 0)); self.failure_reasons = [r for r in getattr(cause, "failure_reasons", ())[:CAP] if _CLOSED_CODE.fullmatch(r)]`. Closed code grammar: `unparseable_response` or `llm_call_failed:<identifier up to 64 chars>`. Cap 10 entries so the JSON body stays under 1 KB. The exception's own `str()` must be a fixed summary, because `NodeTrace.cross_process_failure_cause` embeds `str(cause)` (it is redacted by D-11 but should not carry LLM text anyway).
- REST: `_status_for` already answers 502 for every class not in `_ENGINE_UNAVAILABLE`; `refusal_body` dumps public `vars(exc)`, so the two attributes appear on REST and MCP with no transport change. [VERIFIED: seam/rest.py:135-146; seam/refusals.py:46-60]
- Token cost of a refused ingest is not reported (the node raises), a known trade-off.

### Pattern 10: D-09 / D-11 fault surface

[VERIFIED: seam/engine.py:299-308, 794-833]
- `_foreign_fault(operation, cause, *, failure_class=None, node_id=None)`; `ForeignEngineRefusalError.__init__` gains `node_id: str | None = None`, stored as `self._node_id`, exposed by a `node_id` property. `refusal_body` skips underscore attributes, and the generic REST refusal test asserts private attributes never reach the body. [VERIFIED: tests/seam/test_rest_transport.py:546-554]
- `_node_result_or_refuse` knows the key it took the exception from (`node_id` or the fallback key); pass it through.
- Log line: keep `operation=%s failure_class=%s` (the protected test asserts both substrings), add `node=%s` and a redacted detail. Replace `exc_info=cause` with `redact_secrets("".join(traceback.format_exception(cause)))` run through `seam.corpus._URL_RE.sub("<url>", ...)`. Exactly one ERROR record per fault must remain (`len(records) == 1` is asserted). [VERIFIED: tests/seam/test_foreign_engine_refusal.py:108-119]
- `redact_secrets`: add `(re.compile(r"(?i)([?&]key=)[^\s'\",&]+"), r"\1[REDACTED]")`. Anchor on `?`/`&` so `base_url=http://127.0.0.1:9/v1` and `risk-free` stay untouched; the existing parametrised test pins both. [VERIFIED: foreign/v1_corpus_adapter.py:60-74; tests/foreign/test_secret_redaction.py:25-51]
- `runner/scheduler.py:606` builds `f"NodeExecutionError: {exc.cause}"`; wrap it in `redact_secrets`. `scheduler` may import `databasise.foreign.v1_corpus_adapter` (stdlib-only module, no cycle) or, cleaner, the pattern table can move to a neutral module and be re-exported from the adapter; either keeps `from databasise.foreign.v1_corpus_adapter import redact_secrets` working for the existing tests and `full_ingest.py`.
- The A-WR-05 check goes in unprotected `tests/foreign/test_secret_redaction.py`: an LLM stub raising `RuntimeError("provider 401: invalid api_key=sk-SECRET123 at https://api.example.com/v1")` during openie of a HippoRAG ingest; assert `caplog.text` holds none of `sk-SECRET123` / `api.example.com` and still holds `RuntimeError`. Pre-fix it fails by assertion (the text rides `exc_info`).

### Pattern 11: D-13 read-only listing and the transports

- `SqliteKVStore.__init__` runs `mkdir(parents=True)` and `CREATE TABLE`, so it cannot back a read. [VERIFIED: stores/kv.py:50-66] Write a module-level function (next to `probe_kv` in `stores/probes.py`, or in `kv.py`) that opens `file:<path>?mode=ro` (or `&immutable=1`), returns `None` when `kv.sqlite3` is absent, and queries with a range, not `LIKE`: `SELECT id, value FROM kv WHERE id >= 'doc:' AND id < 'doc;' ORDER BY id LIMIT ? OFFSET ?`, plus a total count query. Parameterised.
- `probe_kv` is "always immutable" to avoid creating `-shm`/`-wal`. [VERIFIED: stores/probes.py:5-12, 54-77] Immutable ignores a live WAL, so for a listing that must see a just-committed write choose immutable only when no `-wal` sidecar exists, else plain `mode=ro` [ASSUMED A2]. The engine closes every store (`finalize` closes the connection) at the end of each operation, which checkpoints the WAL.
- `Databasise.corpus_status(page=None, selector=None)` and `document_counts(selector=None)`: when `selector is None` take the existing v1 path unchanged (do not call `resolve_selector` for the no-selector case, to keep the response byte-identical and the call cheap); otherwise `wiring_family(resolve_selector(...))`; `hipporag` answers from the manifest listing with `DocumentStatusEntry(document_id, status="processed", updated_at=manifest["ingested_at"])`, `counts={"processed": n}`, `total=n`, `next_offset` via `_next_offset`.
- REST: add `selector: str | None = Query(default=None)` (JSON text) to `GET /corpus` and `GET /corpus/counts`; factor the existing upload route's `Selector.model_validate_json` + `refusal_from_errors` handling into one helper in `rest.py` and reuse it. The AST test forbids `rest.py` *calling* functions named in `selectors.__all__` (except `Selector`) or `redact.__all__`; `model_validate_json` is not among them. [VERIFIED: tests/seam/test_rest_transport.py:197-215; seam/rest.py:458-466]
- MCP: add `selector: Selector | None = None` to `StatusToolArgs` and pass it in `_status_corpus`/`_status_counts`. `test_tool_growth_invariant.py` pins the tool set, a forbidden-token check over argument *names* (`selector` is not a modality/node name), and the COVERAGE.md operation rows; it does not pin `StatusToolArgs` fields. [VERIFIED: tests/mcp/test_tool_growth_invariant.py:87-94, 200-218, 253-273]
- jobs.db stays the job registry; a deleted HippoRAG document's old job id still answers `processed` (D-13 keeps jobs.db unchanged). Note it, no action.
- An `alias` selector resolves through the promotion ledger and may create ledger files; that is existing behaviour for ingest/delete too, so I do not treat it as a regression.

### Anti-Patterns to Avoid
- Do not change `_StubIngestQueryLLMClient`'s default branches (imported by protected tests).
- Do not import new symbols at module level in any HIPP test (F7).
- Do not edit `_wiring_effects`; add the pruned view at the call site.
- Do not make `dense_passage_retrieval` cut to `top_k`, and keep the literal `top_k` out of `dpr_fallback.py`'s source (an existing test asserts `"top_k" not in inspect.getsource(dpr_fallback_module)`). [VERIFIED: tests/parts_core/hipporag/test_dpr_fallback_guard.py:179-183]
- Do not add a store namespace for the manifest (health drift tests pin the exact namespace set). [VERIFIED: CONTEXT; tests/seam/test_health_probe.py is protected]
- Do not call `kv.get_by_ids` expecting alignment with the input: it drops missing ids. Loop `get_by_id`. [VERIFIED: stores/kv.py:77-83]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bounded concurrency | a new semaphore key/pool | `config.max_concurrency` (scheduler-validated, default 1) | already refused below 1 before any node runs |
| Write serialisation | a new lock class | `_gate_for`/`_write_gate` pattern with a distinct path key | keeps the cancel/deferred-release handling |
| Secret masking | a second regex set | `redact_secrets` + add one pattern; `seam.corpus._URL_RE` | single control point, existing tests pin it |
| Refusal public attributes | a new refusal class | `ForeignEngineRefusalError` + `failure_class` allow-list | CONTRACT.md:785, Phase 9 D-04 |
| Document registry | a new store/namespace | `doc:<id>` keys in `hipporag-text-chunks` | health drift tests |
| Graph cascade | explicit edge deletes | `CozoGraphStore.delete_node` | verified to hide incident edges read-your-writes and cascade at commit |
| Token summing | a third copy of `_sum_token_accountings` | one helper in `runner/trace.py` | HIPP-19 |
| Answer-failure text | a new string | `PROMPTS["fail_response"]` | same no-context answer for both modalities |
| Pending-aware KNN | N x N numpy over all vectors | batched Faiss search for committed + numpy only for the (small) pending set | §14.2 forbids pointwise emulation |

**Key insight:** every mechanism the decisions need already exists in the repo (store buffers, the scheduler's concurrency key, the refusal vocabulary, the write-gate pattern). The work is wiring them consistently and writing tests that fail first.

## Runtime State Inventory

This phase changes chunk-id minting and adds a document manifest, so existing HippoRAG stores matter.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Any workspace with a HippoRAG ingest made before Phase 12: `hipporag-chunks` vectors and `hipporag-text-chunks` KV rows keyed by `sha256(document_id:ordinal)`; fact KV records and fact vector metadata with `chunk_ids` of the old form; graph edges with no `cooccurrence_by_chunk`; no `doc:<id>` manifests | none by code; document as rebuild-required (delete the workspace's `hipporag-*` directories and re-ingest). The remover treats a missing manifest as a no-op. Parity indexes under `parity/` use bare keys and are read-only here. |
| Live service config | None. HippoRAG runs in-process; no external service holds these names. Verified by reading `seam/engine.py` family dispatch. | none |
| OS-registered state | None. | none |
| Secrets/env vars | None renamed. `redact_secrets` only masks values; no env var name changes. (Never read `.env*` / `v1/parity-env.txt`.) | none |
| Build artifacts | `HIPPORAG-PORT-RECORD.md` and the pinned test tables go stale until updated; `config_hash`/`wiring_instance_hash` of the hipporag wiring change (D-22, D-17..D-20), so persisted traces and promotion rows bound to the old hash stop matching the new wiring. | update the record and tests in the closing plan; flag the hash change to the owner |

## Common Pitfalls

### Pitfall 1: a test that cannot be fail-first recorded
**What goes wrong:** the check file does not collect at the pre-fix commit, or it passes there, or two rows share a node; `record-fail` refuses.
**Why:** a module-level import of a new symbol, `pytest.raises` on a path that currently does not raise (ends in `Failed`, a `BaseException`), or assertions that already hold (HIPP-03, HIPP-15 jobs/health legs).
**Avoid:** import new names inside the test; capture exceptions and assert; make the failing leg explicit (see the fail-first table). **Warning sign:** the failure header does not name the test node.

### Pitfall 2: stale Faiss snapshot under a waiting gate
`FaissVectorStore` reads its committed pair at construction. If a serialising gate is taken after `_build_stores`, the second writer's `get_by_id` ("new entity") sees pre-first-commit data. Take the HippoRAG gate before building stores. [VERIFIED: stores/vector.py:291-312]

### Pitfall 3: `min_max_normalize` zero range
reset-vector-join returns zeros when all passage scores are equal, so a stub embedding that returns one vector for every text gives zero passage weight. HIPP-02 needs >=2 chunks with different scores; HIPP-01 does not depend on passage weights because entity weights are non-zero. [VERIFIED: reset_vector_join.py:52-59]

### Pitfall 4: `assemble-result` zero-PPR drop empties the answer
See F9. A PPR run with a zero reset vector yields no positive items; qa then returns `fail_response`.

### Pitfall 5: deleting an entity vector and re-adding it in one run
See F3. The buffered delete cancels; "new" detection must not rely only on the committed vector.

### Pitfall 6: node-id leakage
Putting the failing node id in `str(refusal)` or a public attribute breaks the §18.2 low-entropy identity rule and Phase 13's node-free vocabulary (WIRE-03). The current NoWritePath delete test asserts node ids are absent from the refusal message (`for node_id in ("chunk-embed", ...): assert node_id not in message`, test_hipporag_write_path.py:228-229); that test is being replaced, so carry the same absence assertion into the HIPP-04 test (`"chunk-embed" not in str(refusal)` and not in `refusal_body(refusal)`). Keep the id in `_node_id` and the log only. [VERIFIED: tests/seam/test_hipporag_write_path.py:228-229]

### Pitfall 7: protected import coupling
Renaming the helpers listed in F8 breaks five protected or sibling test files at import time.

### Pitfall 8: guard comparison coupling
The HippoRAG guard fires only because `fact_filter` returns a `_GuardAwareResult` whose `__eq__` reads `guard_fired`; `evaluate_guards` compares the node's whole output with `value_when_not_fired`. Key D-21 off `NodeTrace.guards_fired` and do not touch that comparison (WIRE-08 owns the rewrite). [VERIFIED: parts_core/hipporag/fact_filter.py:55-77; runner/guards.py:67-84]

### Pitfall 9: `fact-score` must keep empty deps
`tests/parity/test_build_hipporag_index.py::test_3_...` asserts `base["nodes"]["fact-score"]["deps"] == []` and that `run_arm._inject_query` stamps no base query-side node; `test_2_...` asserts the corpus-ingest node ids are disjoint from `base["consumes_query"]`. So the remover and any new ingest node must not be named `fact-score`, `fact-filter` or `qa`. [VERIFIED: tests/parity/test_build_hipporag_index.py:151-180]

### Pitfall 10: ReDoS / unbounded output in the new redaction and reason codes
Keep the new `key=` pattern bounded (`[^\s'\",&]+`) and cap `failure_reasons` and each code's length; never include raw exception text.

## Code Examples

Skeletons only (not final code); patterns are in Patterns 4, 5, 6, 9, 10, 11 above. Two more:

### Serialising HippoRAG gate (F1 recommendation)
```python
@contextlib.asynccontextmanager
async def _hipporag_write_gate(root: Path, *, wait_s: float = 600.0):
    path = root                                     # e.g. store_root / workspace / "hipporag-write"
    gate = _gate_for(path)
    deadline = time.monotonic() + wait_s
    while not gate.acquire(blocking=False):         # cancel-safe: no thread parked on acquire()
        if time.monotonic() >= deadline:
            raise StoreBusyError(store_kind="corpus")
        await asyncio.sleep(0.02)
    try:
        yield
    finally:
        gate.release()
```
(`_write_gate` also parks abandoned v1 worker futures; HippoRAG runs spawn no v1 thread, so plain release is enough.)

### Scheduler degraded rule (D-21)
```python
guard_fired = any(t.guards_fired for t in node_traces)
degraded = partial or guard_fired
if guard_fired and not partial:
    stop_reason = stop_reason or STOP_REASON_DECLARED_FALLBACK
degradation_reason = stop_reason if partial else (DEGRADATION_REASON_FALLBACK_PATH if guard_fired else None)
```

## State of the Art

| Old approach | Current approach | Source | Impact |
|--------------|------------------|--------|--------|
| plain summed edge weight | per-edge `fact_source_counts` map, `synonym_score`, `weight = max(sum(counts), synonym_score)` | upstream HippoRAG.py:`_remove_fact_sources_from_graph` (read) | D-04's `cooccurrence_by_chunk` matches upstream's shape; our weight sums co-occurrence + synonymy + passage because the existing test pins `2.0 + 0.95`. Record the `max` vs sum divergence in the port record. |
| delete = rebuild | upstream `delete()` strips sources and removes unreferenced entities/facts | HippoRAG.py:595-690 | the remover follows it |
| QA reads top `qa_top_k=5` docs | one LLM `qa` call with a one-shot prompt | HippoRAG.py:1117-1172 | D-19, D-20 |

**Deprecated/outdated inside the repo:**
- `HIPPORAG-PORT-RECORD.md` "guard-observability resolution" says `degraded` is unusable for a fired guard; D-21 reverses it. Rewrite that section (the record test only requires the lowercase words `guard-observability`, `guards_fired` and `degraded` to appear). [VERIFIED: tests/evidence/test_hipporag_port_record.py:128-132]
- `assemble_result.py` docstring ("named limitation: completion carries assembled context", "degraded unusable") and `engine._inject_query` docstring.
- `docs/gui/API-INVENTORY.md` and `CODEBASE-MAP.md` G-12 still describe 422/`cause`-in-body/"only provides node inspected" for refusals (from the prior study); update if the phase has a docs task.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `max_concurrency: 4` is a sensible openie default | F5 | too high for a rate-limited provider; the key is per-wiring and cheap to change |
| A2 | read-only listing: immutable only when no `-wal` sidecar, else `mode=ro` | Pattern 11 | a stale or `SQLITE_CORRUPT` read during a concurrent write |
| A3 | reason codes `declared_fallback` / `fallback_path_taken` | Pattern 7 | WIRE-03 may prefer other strings; discretion item, closed set so cheap to rename |
| A4 | pre-Phase-12 HippoRAG stores are rebuild-required; remover no-ops on a missing manifest | F9, Runtime State | an operator expects in-place upgrade |
| A5 | an O(facts) `iter_vectors` pass per remover run is acceptable | Pattern 2 | slow deletes on large fact namespaces |
| A6 | serialising instead of refusing satisfies D-14's intent | F1 | owner wanted a visible 409 on contention |
| A7 | `qa` user prompt keeps upstream's `Wikipedia Title:` per-passage prefix verbatim | Pattern 8 | answer quality on non-wiki corpora; owner may prefer a neutral prefix |
| A8 | record-fail behaviour as described in the kit docs (not executed) | F7 | planner mis-sequences test authoring |

## Open Questions

1. **D-14: serialise or refuse?** (F1)
   - Known: refusing breaks two concurrency tests, one protected.
   - Unclear: owner preference between a visible 409 and queuing.
   - Recommendation: serialise; if the owner wants refusal, the plan must carry a `grant-check-edit` task for `test_ingest_abort.py`.
2. **D-15: how to treat `test_a_query_after_a_refused_ingest_returns_no_evidence_from_it`?** (F2) Grant an edit to expect `EmptyNamespaceError`, or populate first. Needs the owner's grant either way.
3. **F3 fix: thread `removed_entities` through a new entity-fact-embed dep, or accept the `reads_graph` effect on synonymy-edges?** Recommend the former.
4. **Manifest pairs (F4):** confirm the edge-walk reading of D-12 is acceptable.
5. **Is `test_concurrent_ingest_failure.py` a ledger test_ref?** I could not tell without the ledger rows; read `ledger/REQUIREMENTS.json` with the Read tool at plan time.
6. **Are `test_thirteen_positions.py`, `test_registration.py`, `tests/evidence/test_hipporag_port_record.py` and `test_cross_modality_run.py` guarded?** The prior study found no guarded file under `tests/parts_core/hipporag/`; CONTEXT asks to confirm for `test_thirteen_positions.py`. Confirm at plan time. Note the new HIPP test files become guarded the moment their `test_ref`s are set.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `databasise/.venv/bin/python` | all tests | yes | 3.12.13 | — |
| pytest, pytest-asyncio | tests | yes | 9.1.1 | — |
| faiss, igraph, numpy, pycozo | stores / ppr | yes | faiss 1.15.0, igraph 1.0.0, numpy 2.5.2 | — |
| fastapi (TestClient), mcp extra | REST/MCP tests | yes (fastapi 0.141.1); `mcp` presence is checked by `check_offline_suite.py` | — | MCP tests skip when absent |
| upstream clone `/home/chris/coding/reference-repos/HippoRAG` | qa prompt port | yes, commit d5c8329 | — | — |
| v1 interpreter / `real_v1` fixture | LightRAG real-v1 tests only | not needed for HippoRAG work | — | those tests skip |

Baseline observed: `pytest -q tests/parts_core/hipporag tests/seam/test_hipporag_write_path.py tests/evidence/test_hipporag_port_record.py` all pass at HEAD; 7 more seam/store files (test_ingest_abort, test_concurrent_ingest_failure, test_query_trace_nodes, test_empty_namespace, test_vector_self_knn, test_job_families, test_query_store_fault; 46 tests) pass in about 16 s.

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio, `asyncio_mode = "auto"`, `addopts = '-m "not live"'` |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd databasise && .venv/bin/pytest -q -p no:cacheprovider tests/parts_core/hipporag tests/seam/test_hipporag_write_path.py tests/evidence/test_hipporag_port_record.py` |
| Wave command | quick + `tests/seam/test_ingest_abort.py tests/seam/test_concurrent_ingest_failure.py tests/seam/test_corpus_write_gate.py tests/seam/test_query_trace_nodes.py tests/seam/test_empty_namespace.py tests/seam/test_job_families.py tests/seam/test_query_store_fault.py tests/stores tests/runner tests/foreign` (do not prefix with `timeout`; the guard blocks it) |
| Full suite command | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (both pytest styles, about 8 minutes each per Phase 11 VALIDATION) |
| Never | `-m live`, any `.env*` read |

### Phase Requirements -> Test Map

Fail-first column: how the test fails on pre-fix code. "assert" means a plain `AssertionError`. Each row needs its own node (one test per row).

| Req ID | Behavior | Test file | Suggested node | Fails pre-fix by | Needs special record-fail |
|--------|----------|-----------|----------------|------------------|---------------------------|
| HIPP-01 | PPR-branch query hydrates content; every ref resolves | tests/seam/test_hipporag_write_path.py | `test_a_ppr_branch_query_hydrates_content_and_every_ref_resolves` (new stub keeps every fact id, parsed from `id=<fid>:` in the prompt) | assert: hydrated content `''` | no |
| HIPP-02 | non-zero reset weight on matching chunk vertex | tests/parts_core/hipporag/test_ppr.py | `test_reset_vector_join_seeds_the_matching_chunk_vertex_and_ppr_ranks_it_first` (chunk-embed output with 2 chunks, distinct vectors) | assert: weight 0 / rank wrong | no |
| HIPP-03 | refused ingest commits nothing | write_path | `test_an_ingest_with_no_llm_client_refuses_and_commits_nothing` | none: passes at HEAD | `record-fail --at feadf3e^` |
| HIPP-04 | refusal names failing node, real cause | write_path | `test_an_ingest_with_no_embedding_client_names_chunk_embed_privately` (`getattr(r, "node_id", None) == "chunk-embed"`, `str(r.cause)` contains `embedding`, `"chunk-embed" not in str(r)`) | assert: node_id None | no (the node_id assertion fails at HEAD) |
| HIPP-05 | fact-filter prompt carries the query | write_path | `test_fact_filter_prompt_contains_the_query_between_the_markers` | assert: `''` | no |
| HIPP-06 | passage vertex for every chunk | tests/parts_core/hipporag/test_graph_construction.py | `test_a_chunk_with_no_triples_still_gets_a_passage_vertex` | assert: vertex missing | no |
| HIPP-07 | synonymy on the ingest that introduces it; no re-emit | test_graph_construction.py | `test_synonymy_edge_appears_on_the_introducing_ingest_and_is_not_reemitted` (+ re-ingest same doc keeps edge, F3) | assert | no |
| HIPP-08 | weights and types accumulate | test_graph_construction.py | `test_cooccurrence_sums_across_ingests_and_survives_an_unrelated_ingest` | assert: 1.0 not 2.0 | no |
| HIPP-09 | fact keeps union of chunk_ids | tests/parts_core/hipporag/test_index_side_extraction.py | `test_a_fact_from_two_documents_keeps_both_chunk_ids_in_kv_and_vector_metadata` | assert | no |
| HIPP-10 | failures counted, refused; overlapping calls | test_index_side_extraction.py | `test_openie_refuses_with_a_failure_count_and_closed_reasons_and_runs_chunks_concurrently` (3+ chunks: malformed JSON, raising chat, one good; capture the exception, assert type name `ExtractionFailedError`, `failed_chunks == 2`, observed max in-flight > 1) | assert | no |
| HIPP-11 | at most top_k items, no zero PPR | write_path | `test_a_query_returns_at_most_top_k_evidence_items_on_both_branches` (20 single-chunk docs) | assert: 20 > 5 | no |
| HIPP-12 | query-side nodes only; one embed; no write selector | write_path | `test_a_query_dispatches_only_query_side_nodes_and_embeds_once` (capture selector exception, assert unresolved) | assert | no |
| HIPP-13 | answer is generated, not joined evidence | write_path | `test_the_answer_is_the_generated_text_not_the_joined_evidence` | assert: equals join | no |
| HIPP-14 | fired fallback visible in non-debug envelope | write_path | `test_a_fired_fallback_is_visible_as_degraded_with_a_node_free_reason` (and PPR path not degraded) | assert: degraded False | no |
| HIPP-15 | job, corpus, health cover HippoRAG | write_path | `test_hipporag_documents_appear_in_jobs_corpus_counts_and_health` (corpus legs over REST: `GET /corpus?selector=...` with `engine_module.run_corpus_op` monkeypatched to an empty v1 corpus, so the pre-fix failure is an assertion, not a `TypeError` from an unknown keyword) | assert: total 0 | no (jobs/health legs pass at HEAD; corpus leg fails) |
| HIPP-16 | clean re-ingest and delete | write_path | `test_reingest_leaves_no_stale_chunk_and_delete_removes_everything` (3-chunk text needs >2300 chars at the default 1200/100 chunker; assert stores before reaching `delete_document`, so pre-fix fails by assertion) | assert: 3 chunks not 1 | no |
| HIPP-17 | old refs never resolve to new text | write_path | `test_an_old_ref_never_resolves_to_the_new_text_after_reingest` (try/except around resolve) | assert | no |
| HIPP-18 | no unread keys; honest docstrings | tests/parts_core/hipporag/test_registration.py | `test_no_unread_config_key_remains_and_edge_types_claim_is_honest` | assert | no |
| HIPP-19 | no mixed counters under one label | new `tests/runner/test_token_sum.py` (or test_index_side_extraction.py) | `test_mixed_counters_never_share_one_label` | assert | no |
| A-WR-05 | in-process provider error is logged redacted | tests/foreign/test_secret_redaction.py | `test_an_in_process_provider_error_is_logged_without_its_key_or_url` | assert | no |

Additional (not row-bound) tests the work needs: store-level pending `self_knn` and its pending-delete exclusion (new `tests/stores/test_vector_self_knn_pending.py`); read-only listing creates nothing on a fresh root (LRAG-13 style); remover unit tests (orphan vs shared entity, shared fact keeps remaining chunk, edge reduction and deletion, unchanged re-ingest keeps synonymy, missing manifest no-op); `top_k` and `max_concurrency` value-change tests (D-22); REST `GET /corpus?selector=` malformed selector -> 422 not 500; `ExtractionFailed` body < 1 KB and free of raw text; HippoRAG gate behaviour (serialising: second ingest waits and both commit; LightRAG ingest beside HippoRAG ingest not blocked).

### Existing tests that need edits (unprotected unless F6)
- `tests/parts_core/hipporag/conftest.py` (bare ids; fact `chunk_ids` bare) and every consumer of its `chunk:c1` ids: `test_ppr.py` readback assertions (now bare ids), `test_dpr_fallback_guard.py` (ids, `dense_passage_retrieval` signature, effects pin `["calls_embedding","reads_vector"]`, `degraded False` at lines 254-263), `test_cross_modality_run.py` (answer assertion), `test_compare.py` (check).
- `test_registration.py`: `_EXPECTED_SHAPE` and the count of 13 -> 15 parts (qa, remover); narrowed effects for `reset-vector-join` and `dpr-fallback`; new `fact-score` output; `test_thirteen_positions.py`: node-set equality becomes governing 13 + `qa`; `tests/evidence/test_hipporag_port_record.py`: `_SECTION_H_EFFECTS` has no `qa` entry (the pinned-transcription and divergent-set helpers index it by node id), two new divergent rows (`reset-vector-join`, `dpr-fallback`) and a changed `graph-augment-persist` row if it gains `writes_kv`.
- `tests/seam/test_hipporag_write_path.py`: replace `test_hipporag_selected_delete_raises_the_named_refusal_...` (lines 215-229 of the version I read) **and** the delete assertions at the end of `test_hipporag_ingest_parity_across_rest_mcp_and_in_process_transports` (REST 422 `NoWritePathForModalityError`, MCP ToolError); update the stub docstring that explains the DPR forcing.
- `tests/seam/test_hipporag_write_path.py::test_write_path_invariant_holds_over_every_wiring_name` adapts on its own once `corpus-delete.json` exists.

### Sampling Rate
- **Per task commit:** the task's test file plus the quick command.
- **Per wave merge:** the wave command above.
- **Phase gate:** `tools/check_offline_suite.py` green in both styles before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] All HIPP tests authored first, per file, importing no new symbol at module level (F7).
- [ ] `tests/stores/test_vector_self_knn_pending.py`, `tests/stores/test_kv_readonly_listing.py` (or in probes tests), `tests/parts_core/hipporag/test_document_remover.py`, `tests/parts_core/hipporag/test_qa_node.py`, `tests/runner/test_token_sum.py`, a degraded-guard scheduler test.
- [ ] New stub classes in `test_hipporag_write_path.py` (keep-all-facts, qa-aware, counting/overlap LLM); leave `_StubIngestQueryLLMClient` alone.
- [ ] Owner `grant-check-edit` requests: SEAM-05 file (D-11), STOR-06 file (D-15, and D-14 only if refusing).
- [ ] Ledger bookkeeping after the code: `set --id HIPP-NN --test-ref file::node` per row, `record-fail --at <pre-fix commit>` using the absolute venv python and `PYTHONPATH=$PWD` (STATE.md Phase 11 note); executors run no ledger command (Phase 9 precedent).

### Suggested plan split and wave order

Constraints honoured: D-01 before D-19; D-12 with or before D-03; D-04 map before D-12 subtraction; D-14 gate before any concurrency test. Hot files (many plans touch them, so keep each in one plan per wave or order the waves): `seam/engine.py`, `openie.py`, `entity_fact_embed.py`, `graph_augment_persist.py`, `reset_vector_join.py`, `base.json`, `corpus-ingest.json`, `tests/seam/test_hipporag_write_path.py`.

| Plan | Wave | Covers | Depends on |
|------|------|--------|------------|
| P1 ids and passage vertices | 1 | HIPP-01, 02, 06 (D-01, D-02): `vertices.py`, ppr/reset-vector-join prefix translation, passage-edges `vertices`, persist upserts them, openie `chunks` passthrough, conftest rewrite | — |
| P2 fault surface and redaction | 1 | HIPP-03, 04, A-WR-05 (D-09, D-10, D-11): `node_id`, `_foreign_fault`, `redact_secrets` pattern, scheduler.py:606 redaction | grant for SEAM-05 |
| P3 store and accounting primitives | 1 | HIPP-19 (D-07), `self_knn(ids=)` store half (D-05), read-only KV prefix lister (D-13 store half) | — |
| P4 graph accumulation | 2 | HIPP-07, 08, 09 (D-04, D-05 part half, D-06): fact-edges map, persist merge, synonymy `ids` + `new_entities`, entity-fact-embed union | P1, P3 |
| P5 extraction failures | 2 | HIPP-10 (D-08): openie rewrite, `ExtractionFailed` class + attributes, wiring `max_concurrency` | P1, P2, P3 |
| P6 lifecycle | 3 | HIPP-16, 17 (D-12, D-03, D-14): remover, manifest writers, `corpus-delete.json`, remover-first ingest, engine stamping, HippoRAG gate, delete route, id change | P4, P5; gate decision (F1) |
| P7 corpus surface | 4 | HIPP-15 (D-13): engine selector, REST/MCP, listing | P6 |
| P8 query semantics A | 4 | HIPP-05, 11, 12 (D-16 prune, D-17 embed-once, D-18 fact-filter, D-20 top_k, resolve/selectors/engine alias) | P1 |
| P9 query semantics B | 5 | HIPP-13, 14 and D-15 (qa node, degraded rule, relax invariant, narrow `_node_result_or_refuse`, HippoRAG empty-namespace table) | P8; grant for the STOR-06 query test (F2) |
| P10 config honesty and records | 5 | HIPP-18 (D-22), port record, registration/thirteen-positions/record tests, docs | all structural plans |

P8 and P4/P5 touch different files and can share a wave if the executor serialises `engine.py` and the two wiring JSON files.

## Sources

### Primary (HIGH confidence, read this session)
- `databasise/stores/graph.py`, `kv.py`, `vector.py`, `probes.py`; `parts_core/__init__.py`; `parts_core/hipporag/*.py`; `parts_core/lightrag/generate.py`, `prompts.py`
- `databasise/seam/engine.py` (ingest, delete, corpus ops, health, `_foreign_fault`, `_node_result_or_refuse`, gates), `refusals.py`, `rest.py`, `selectors.py`, `promotion.py`, `tokens.py`, `corpus.py`, `jobs_store.py`
- `databasise/runner/scheduler.py`, `trace.py`, `guards.py`, `budget.py`; `wirings/resolve.py`, `wirings/hipporag/*.json`, `wirings/lightrag/corpus-delete.json`
- `databasise/mcp/tools.py`, `mcp/server.py`; `foreign/v1_corpus_adapter.py`; `clients/base.py`, `clients/__init__.py`
- Tests read: `test_hipporag_write_path.py`, `test_ingest_abort.py`, `test_concurrent_ingest_failure.py`, `test_corpus_write_gate.py`, `test_empty_namespace.py`, `test_query_trace_nodes.py`, `test_foreign_engine_refusal.py`, `test_query_store_fault.py`, `test_delete_commit_contract.py`, `test_tool_growth_invariant.py`, `test_run_record.py`, `tests/parts_core/hipporag/*`, `tests/evidence/test_hipporag_port_record.py`, `tests/parity/test_build_hipporag_index.py`, `tests/stores/test_vector_self_knn.py`, `tests/foreign/test_secret_redaction.py`
- Reference clone `/home/chris/coding/reference-repos/HippoRAG` @ d5c8329: `HippoRAG.py` (`delete` 595-690, `qa` ~1117-1172), `prompts/templates/rag_qa_musique.py`, `utils/config_utils.py` (`qa_top_k = 5`)
- `docs/system-model/CONTRACT.md` (:772, :785), `PARTS.md` (:224, :254), `RIG.md` (~:625), `rig-trace.schema.json` (`allOf`)
- Probes run against HEAD: `ryw_probe.py` (store semantics), `prune_probe.py`, `eff_probe.py`

### Secondary (MEDIUM confidence)
- BAK kit docs `/home/chris/coding/GUI-research/docs/learn/15-running-a-project.md` (record-fail rules), `git show 51469e4` (Phase 11 precedent)
- `.planning/phases/11-lightrag-corpus-path/11-VALIDATION.md` (validation structure, suite commands), `.planning/STATE.md` notes

### Tertiary (LOW confidence)
- none beyond the Assumptions Log

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new is installed and every version was read from the venv.
- Architecture and mechanics: HIGH, source read plus store probes; the F1/F2 collisions are determined by reading the tests and the engine control flow, and the baseline for the affected tests is green.
- Pitfalls: HIGH for the repo-specific ones; MEDIUM for the `record-fail` interaction (kit docs, not executed).

**Research date:** 2026-10-19
**Valid until:** 2026-11-18 (stable in-repo; re-check F1/F2 if the owner changes D-14/D-15 or any protected test changes)

*Security Domain section omitted: `workflow.security_enforcement` is explicitly `false` in `.planning/config.json`. The redaction, closed-code and body-size concerns are covered in Patterns 9-10 and Pitfall 10.*
