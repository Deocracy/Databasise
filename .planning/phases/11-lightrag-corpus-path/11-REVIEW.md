---
phase: 11-lightrag-corpus-path
reviewed: 2026-10-18T00:00:00Z
depth: standard
diff_base: 23c0ca0
iteration: 1
parts: "A (write path, 11-REVIEW-A.md) + B (query path, 11-REVIEW-B.md), merged; ids prefixed A-/B-"
files_reviewed: 65
files_reviewed_list:
  - databasise/clients/base.py
  - databasise/eval/aa_run.py
  - databasise/evidence/COVERAGE.md
  - databasise/foreign/__init__.py
  - databasise/foreign/v1_corpus_adapter.py
  - databasise/foreign/v1_corpus_driver_script.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/parity/import_index.py
  - databasise/parity/run_arm.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/lightrag/assemble.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/embedder_index.py
  - databasise/parts_core/lightrag/embedder_query.py
  - databasise/parts_core/lightrag/entity_hydrate_expand.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/full_delete.py
  - databasise/parts_core/lightrag/full_ingest.py
  - databasise/parts_core/lightrag/generate.py
  - databasise/parts_core/lightrag/join_roundrobin.py
  - databasise/parts_core/lightrag/keywords.py
  - databasise/parts_core/lightrag/prompts.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/truncator_token_budget.py
  - databasise/parts_core/lightrag/v1_index_sync.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/seam/jobs_store.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/stores/vector.py
  - databasise/tests/foreign/test_v1_not_configured.py
  - databasise/tests/parity/test_arm_conformance.py
  - databasise/tests/parity/test_graph_arm_real_index.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parts_core/lightrag/test_corpus_metering.py
  - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  - databasise/tests/parts_core/lightrag/test_kg_fidelity.py
  - databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py
  - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
  - databasise/tests/parts_core/lightrag/test_transform_parts.py
  - databasise/tests/parts_core/lightrag/test_v1_index_sync.py
  - databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py
  - databasise/tests/seam/test_corpus_write_gate.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/seam/test_empty_namespace.py
  - databasise/tests/seam/test_health_honesty.py
  - databasise/tests/seam/test_interrupted_documents.py
  - databasise/tests/seam/test_job_families.py
  - databasise/tests/seam/test_lightrag_inbox.py
  - databasise/tests/seam/test_promote.py
  - databasise/tests/seam/test_query_trace_nodes.py
  - databasise/tests/seam/test_status_during_write.py
  - databasise/wirings/lightrag/README.md
  - databasise/wirings/lightrag/arm-global.json-patch.json
  - databasise/wirings/lightrag/arm-hybrid.json-patch.json
  - databasise/wirings/lightrag/arm-local.json-patch.json
  - databasise/wirings/lightrag/arm-naive.json-patch.json
  - databasise/wirings/lightrag/base.json
  - databasise/wirings/lightrag/corpus-delete.json
  - databasise/wirings/lightrag/corpus-ingest.json
  - v1/lightrag/operate.py (reference only)
findings:
  critical: 4
  warning: 11
  info: 11
  total: 26
status: issues_found
---

# Phase 11: Code Review (merged)

# Part A — write path


# Phase 11 Part A: Code Review Report (the write path)

**Reviewed:** 2026-10-18
**Depth:** standard (with runtime probes)
**Files Reviewed:** 30
**Status:** issues_found

## Summary

The write path is coherent and the test suite for it is substantive. I found no vacuous test among those read.
The 54 tests in `test_corpus_write_gate`, `test_v1_index_sync`, `test_job_families`, `test_lightrag_inbox`,
`test_upload_suffixes` and `test_health_honesty` pass.

Four of the nine risks listed in the brief are defective as built. Each was reproduced with a probe, not only read:

- **Write gate (focus 2):** cancellation releases the gate while the v1 subprocess keeps running (A-CR-01).
- **Retry and the one-id-two-suffixes case (focus 3, 4):** the deferred case is worse than 11-05 states. A delete
  reports `success` and leaves a live, queryable document behind (A-CR-02).
- **Sync heal (focus 1):** the "healed on the next sync" claim is false after a partial commit (A-WR-01).
- **Metering (focus 7):** real usage above the fixed 1,000,000 allowance fails an already-committed ingest (A-WR-02).

The other focus items held up:

- **Single-bump (focus 10):** the driver script has no commit after `50a6298` (11-03). The 11-07 changes touch the
  adapter only and map exit codes 3 and 4 that 11-03 already emitted. D-06 is intact.
- **Health (focus 9):** it writes nothing, verified by the real-driver test and by reading the code. It is not `ok`
  without both clients.
- **Job store (focus 8):** creation is lazy and reads open read-only. The one gap is A-WR-04.
- **Secrets (focus 6):** refusal bodies carry key names only. See A-WR-05 for the log side.

## Structural Findings (fallow)

None provided.

## Critical Issues

### A-CR-01: Cancelling a write releases the gate while the v1 subprocess is still running

**File:** `databasise/seam/engine.py:659-670, 1175-1182, 1203, 1408` (root cause in
`databasise/parts_core/lightrag/full_ingest.py:246` and `databasise/parts_core/lightrag/full_delete.py:214`).

**Issue:** `_write_gate` releases in `finally`. The docstring claims "a failed or cancelled write never leaves it
held", and the 11-06 plan treats release-on-cancel as the safe case. The v1 subprocess, however, runs in a worker
thread started with `asyncio.to_thread(run_corpus_op, ...)`. A thread cannot be cancelled. When the engine task is
cancelled (an `asyncio.wait_for` or `asyncio.timeout` around `ingest`, a task group, an MCP or REST host that
cancels handlers, shutdown), the coroutine unwinds, the ExitStack releases the gate, and the thread keeps running
`subprocess.run` for up to 900 s (ingest) or 300 s (delete).

Probe (`test_probe_cancel.py` in the scratchpad; fake `run_corpus_op` sleeping 2 s):

```
cancel result: CancelledError
v1 thread done? False gate held? False
second admitted while first running; concurrent v1 calls: 2
```

With the real driver the second write starts a second v1 subprocess on the same working dir. That process opens
the same RocksDB (lock failure, exit 1), or writes the same JSON KV and Faiss files beside the first. The first
process's result is never synced, because the sync node is cancelled, so v1 and v2 diverge. `corpus_status` also
reports the still-running document as `interrupted`, because the gate reads free.

The same mechanism hits the sync: `asyncio.wait_for(_sync(), 300)` in `v1_index_sync.py:82` cancels the awaiting
task, but `read_v1_snapshot` keeps running in its thread with v1's RocksDB open. The gate is already free by then.

No test covers cancellation. `test_corpus_write_gate.py` only covers raised failures and concurrent arrivals.

**Fix:** tie the gate's lifetime to the thread, not to the coroutine. Two options:

```python
# Option A: shield the blocking call so cancellation cannot unwind past it.
result = await asyncio.shield(asyncio.to_thread(run_corpus_op, ...))
# and hold the gate until the underlying thread future is done:
fut = asyncio.ensure_future(asyncio.to_thread(run_corpus_op, ...))
try:
    return await asyncio.shield(fut)
except asyncio.CancelledError:
    fut.add_done_callback(lambda _f: gate.release())   # release only when the thread ends
    raise
```

```python
# Option B: do not release the threading.Lock on the cancelled path.
# Hand the release to the worker thread's completion callback.
```

Add a test: cancel `engine.ingest` mid-driver, assert `_write_gate_held()` is still true, a second write gets
`StoreBusyError`, and the gate frees only after the fake driver returns.

### A-CR-02: One id with two suffixes: delete reports success and leaves a live, queryable document (worse than 11-05 states)

**File:** `databasise/foreign/v1_corpus_driver_script.py:241-244, 339, 385-390`; `databasise/seam/engine.py:1112, 1192`
(the exclusive-create guard only covers a file still in the inbox).

**Issue:** the deferred note in `deferred-items.md` says the second row "maps back to x by the stem rule" and stops
there. In fact:

1. The second upload is accepted and reports `enqueued: 1`.
2. `GET /corpus` lists the same `document_id` twice.
3. `DELETE /documents/x` resolves rows with `next(iter(await _resolve_v1_ids(rag, [doc_id])), doc_id)`, which is the
   first match only. It deletes one row and returns `status: success`. The other row stays PROCESSED in v1, is
   re-mirrored into v2 by the next sync, and stays retrievable.

Probe (`test_probe_real_raw.py`, real v1 driver, stub model server):

```
CORPUS after 2nd suffix [('rawone', 'processed'), ('rawone', 'processed')]
DELETE success
CORPUS after delete [('rawone', 'processed')]
V1 ROWS after delete ['doc-02d59c577d1cba91273ac01e23380d52']
```

A document the caller was told is deleted is still indexed and answerable. A caller re-uploading `x.txt` as
`x.md` (a normal "replace" gesture) triggers this.

A smaller companion: `retry` reads the status page with `limit: 1`, so with two rows of one id the row it checks is
arbitrary (`engine.py:1313-1328`). It can answer `DocumentNotInterruptedError` for an id that has an interrupted row.

**Fix:** no driver change is needed to stop the loss. In `Databasise.ingest` (inside the gate, before staging) run
the same status probe `retry` uses with `{"document_id": document_id}`. If v1 already holds any row for the id
(any suffix, text or file), refuse with `DuplicateDocumentIdError`. The exclusive-create guard then protects the
state v1 itself holds, not only the inbox. For defence in depth, make the driver's delete loop over all matches
(a protocol-neutral change to behaviour, but it needs a D-06 decision because it alters what `full-delete@0.2.0`
does). Add a real-driver test: upload `x.txt` then `x.md`, expect a refusal.

## Warnings

### A-WR-01: "Healed on the next sync" is false after a partial commit; the prune manifest advances ahead of the vector and graph stores

**File:** `databasise/parts_core/lightrag/v1_index_sync.py:74-77`, `databasise/seam/engine.py:681-703, 1175`,
`databasise/parity/import_index.py` (`mirror_snapshot` stale logic).

**Issue:** the sync stores its prune manifest in the `text_chunks` kv store, and `_commit_all` commits stores in the
order kv, vector, graph. If `kv.commit_prepared` succeeds and the vector commit then fails (disk full, `os.replace`
error), the manifest in kv has already advanced to the new snapshot and the stale text chunks are already deleted.
`_abort_prepared` only covers the stores not yet committed. The next sync computes `stale = previous manifest -
current`, and the previous manifest no longer lists the dropped ids, so nothing prunes the vector and graph rows. The
engine docstring (lines 155-159) says the next sync "re-mirrors the whole index and so heals them". That holds for
upserts, not for deletes.

Probe (`test_probe_heal.py`, fake v1 dir, `FaissVectorStore.commit_prepared` forced to raise once during
`delete_document("a")`, then a normal `ingest("c")`):

```
delete raised: ForeignEngineRefusalError StoreFault
kv a-c: False
vector a-c still present after healing sync: True
kv manifest: ['b-c', 'c-c']
```

The deleted document's chunk vector, whose Faiss metadata carries the chunk text, stays in `chunks` permanently
and is returned by retrieval with no kv row behind it.

**Fix:** make the manifest commit last, so a failure before it leaves the old manifest in place and the next sync
still prunes. Either store it in the graph store (committed last), or have the sync derive stale ids from what the
v2 namespaces actually hold (enumerate ids, subtract the snapshot, restrict to the sync-written set). Add a test
that injects a vector commit failure on a delete and asserts the next sync removes the vector row.

### A-WR-02: Real token usage above the fixed 1,000,000 allowance fails an ingest whose v1 write already committed

**File:** `databasise/seam/engine.py:407, 1127`; `databasise/parts_core/lightrag/full_ingest.py:60-81`
(`tokens_from_usage`); scheduler `runner/budget.py:128-139` and `runner/scheduler.py` (budget halt breaks the batch).

**Issue:** before 11-03 the corpus ports reported `unbudgetable`, which meters as zero spend. D-13 now meters real
LLM usage against `_DEFAULT_TOKEN_ALLOWANCE = 1_000_000`, applied per node. A large document (extraction plus gleaning
over a few hundred chunks) exceeds it. The scheduler then marks the run halted and `partial`, skips the sync node,
and `_node_result_or_refuse` raises `RunIncomplete`. The engine drops all staged v2 writes and removes the staged
raw upload (RunIncomplete is not in `_KEEP_STAGED`). v1 has committed and billed.

Probe (`test_probe_budget.py`, fake driver returning 1.2M prompt plus 50k completion tokens):

```
INGEST RAISED ForeignEngineRefusalError RunIncomplete
v1 doc_status exists: True
```

The caller gets a 502 for a write that succeeded in v1. v2 stays empty until another write syncs. A caller retry
reports `enqueued: 0`. For a raw upload the source file is already gone.

**Fix:** a budget cannot prevent spend that a subprocess has already made. Do not let the corpus-op nodes halt:
give the ingest, delete and retry wirings an allowance that cannot be hit (or have `_node_result_or_refuse` ignore a
`budget_halt` for opaque corpus ops and still run the sync), and surface the spend in the trace only. Add a metering
test with usage above the allowance that expects a committed job.

### A-WR-03: A caller-supplied document id of `unknown_source` deletes an unrelated document

**File:** `databasise/foreign/v1_corpus_driver_script.py:241-244` (`_our_id_matches`), used at 254, 339, 409.

**Issue:** `_listed_id` guards against v1's `unknown_source` placeholder (line 388), but `_our_id_matches` does not.
A text-ingested document has `file_path == "unknown_source"`, so for `our_id == "unknown_source"` (a valid token)
`Path("unknown_source").stem == our_id` holds for every `doc-*` text row. The delete and retry resolvers then pick
one of them.

Probe (`test_probe_unknown_source.py`, real v1 driver):

```
before: [('doc-keep', 'processed')]
delete of 'unknown_source': success Document doc-keep successfully deleted
after: []
```

Any caller that can reach `DELETE /documents/unknown_source` removes a document it did not name. Only caller-chosen
ids that start with `doc-` are exposed (engine-minted ids are hex), but caller-chosen ids are part of the API.

**Fix:** treat `unknown_source` like `_listed_id` does:

```python
def _our_id_matches(v1_id, file_path, our_id):
    if v1_id == our_id:
        return True
    return (
        v1_id.startswith("doc-")
        and file_path not in (None, "", "unknown_source")
        and Path(file_path).stem == our_id
    )
```

This is a bug fix inside the driver with no protocol change, but it is a driver edit after 11-03, so record the
D-06 exception when applying it. Add a case to `test_status_filters_by_our_document_id_with_the_stem_rule`.

### A-WR-04: A HippoRAG job-record failure after commit reports the ingest as failed

**File:** `databasise/seam/engine.py:928-933, 1266-1267`.

**Issue:** for a non-gated (HippoRAG) ingest, `_record_job` runs after `_commit_all` has committed. A sqlite or OS
error then raises `ForeignEngineRefusalError(StoreFault)`. The caller sees a 502 for an ingest that is durably
committed, and the job handle is lost: polling the id would give `UnknownJobError` (404). A retry re-ingests the
document. The LightRAG path records before the run, so only HippoRAG is exposed. No test covers a failing record
write (`test_a_refused_hipporag_ingest_records_nothing` covers the opposite order).

**Fix:** record before the commit and delete the row on a refused run, or make the post-commit record best-effort
(log and return the job):

```python
if not gated:
    try:
        self._record_job(job.job_id, family, document_id)
    except ForeignEngineRefusalError:
        logger.exception("job family record failed after a committed ingest")
```

If the record is best-effort, `get_job_status` for that id must fall back to a defined answer instead of 404.

### A-WR-05: Server logs carry the v1 stderr tail, a staged absolute path and (via provider errors) key fragments

**File:** `databasise/seam/engine.py:301, 314`; `databasise/foreign/v1_corpus_adapter.py:77`.

**Issue:** the brief says logs must carry no stderr, no paths and no config values. `_foreign_fault` logs
`exc_info=cause`, and `CorpusOpSubprocessError.__str__` embeds the last 2000 characters of driver stderr. A
provider auth error in that tail commonly echoes a partial key and the base URL. `_log_staged_left` logs the
absolute inbox path. D-11 explicitly sends stderr to the server log, and the health path logs only the type name
(11-09 T-11-19). The two statements conflict, so this is a decision to settle, not a clear defect.

**Fix:** if the brief governs, log `type(cause).__name__` plus the fixed failure class and keep the full text behind
an explicit debug flag. If D-11 governs, redact `Authorization`/`api_key`/`sk-` patterns and `file://`/absolute paths
from the tail before logging, and say in D-11 that redaction is the control.

## Info

### A-IN-01: Retry of a raw upload is proven only for a document interrupted after parse

**File:** `databasise/tests/seam/test_interrupted_documents.py` (text document only);
`databasise/seam/engine.py:1283-1339`.

The 11-08 retry of a `doc-<md5>` row was never covered by a test. I ran it (`test_probe_real_raw.py`, real
driver): a raw `s.txt` upload timed out in `processing`, the source had already been moved to
`corpus-inbox/__parsed__/slowraw.txt`, and `POST retry` returned `processed` with the inbox empty afterwards. The
retry path works for that state. The `parsing` state, where the kept file is still in the inbox root and the driver
must re-read it through `INPUT_DIR`, cannot be produced with the stub server (a `.txt` parses instantly) and
remains unproven. Add a real-driver test with a kill during parse, or a fake that leaves the file in the inbox and
asserts the driver reaches it through `input_dir`.

### A-IN-02: A deterministic driver failure keeps the staged upload and blocks the id until a delete

**File:** `databasise/seam/engine.py:319, 1188-1196, 1231-1239`.

`_KEEP_STAGED` keeps the file for every `CorpusOpSubprocessError`, including exit-1 failures that occur before v1
enqueued anything (dimension mismatch, store lock). The next upload of that id gets `DuplicateDocumentIdError`,
retry answers `UnknownDocumentError`, and only `DELETE` (which answers `not_found` and cleans the inbox) clears it.
This is pinned by `test_a_driver_fault_keeps_the_file_logs_it_once_and_a_later_delete_removes_it`, so it is a
design choice. Consider letting `ingest` overwrite a kept file when `status` shows no v1 row for the id.

### A-IN-03: `jobs.db` is shared across workspaces

**File:** `databasise/seam/jobs_store.py:11-17`, `databasise/seam/engine.py:917`.

The file is `<store_root>/jobs.db` with no workspace column. A HippoRAG job id minted in workspace A answers
`processed` (with A's `document_id`) when polled in workspace B. Ids are unguessable hex, so exposure is low. D-02
asks for one file under the store root, so add a `workspace` column and filter on it when the multi-workspace
deployment becomes real.

### A-IN-04: The sync mirror is bounded by a 300 s ceiling and rewrites the whole corpus per write

**File:** `databasise/parts_core/lightrag/v1_index_sync.py:70-82`.

The `shortcut:` comment records the O(corpus) cost. The consequence beyond speed is that once a corpus is large
enough for the mirror to pass 300 s, every ingest fails after v1 has committed (the same failure shape as A-WR-02),
and the timed-out thread keeps v1's RocksDB open (see A-CR-01). Record the corpus size at which this bites, and
upgrade by diffing doc-status snapshots before that point.

### A-IN-05: Lint and housekeeping in the touched files

**File:** `databasise/seam/engine.py:170, 628, 677, 1192`; `databasise/seam/rest.py:477, 486`.

`ruff` reports an unsorted import block (the new `jobs_store` import sits between `envelope` and `evidence`), two
unused `noqa: BLE001`, blocking `open()` in async code (`ASYNC230`, the raw-bytes write of a large upload runs on
the event loop), and B008 on the new `RetryRequest()` default. Most were already logged in `deferred-items.md`.
`run_corpus_op` also returns whatever JSON the driver prints (it is annotated `dict`), so a driver printing a list
or string surfaces as an `AttributeError` inside the node and classifies as `UnclassifiedEngineFailure`.

## Verification notes (no finding)

- **Sync filter and parity safety (focus 1):** the PROCESSED-only filter is correct row by row
  (`test_the_snapshot_keeps_only_rows_of_processed_documents`). Prune deletes only ids the previous manifest lists, so
  parity-imported ids are not deleted, except an id both hold (documented limit). Nothing from a timed-out document is
  mirrored: when full-ingest raises, the sync node never runs, and later syncs keep only PROCESSED chunks.
- **Gate coverage (focus 2):** the gate spans the v1 call, the sync, the commit, finalize and inbox cleanup for
  ingest, delete and retry, and releases on every raised path. Retry holds it. The cancellation hole is A-CR-01.
- **Inbox (focus 4):** names are generated from a token-validated id and a regex-validated, allow-listed suffix, so no
  traversal is possible. `_remove_inbox_files` matches the exact `<id>.` prefix and cannot hit another id, because ids
  cannot contain a dot. Success, refusal and delete remove the file and the `__parsed__` copy. A timeout keeps it.
  After a real ingest only an empty `__parsed__/` directory remains.
- **Status (focus 5):** status is facade-free. v1 writes JSON through `atomic_write`, so the retry-then-409 path for a
  torn read is effectively defensive. The stem mapping is correct apart from A-CR-02 and A-WR-03.
- **Metering (focus 7):** `tokens_from_usage` is consistent with the `counted_by` rules in the tests. Embedding spend is
  carried in `usage` and is not surfaced beyond the node result.
- **Single-bump (focus 10):** confirmed. Last driver-script commit is `50a6298` (11-03). `git diff 50a6298 HEAD` on
  `databasise/foreign` shows adapter-only changes. `parts_core` part files have no change after `e587d04`.

---

_Reviewed: 2026-10-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_


# Part B — query path and v1 fidelity


# Phase 11 (part B): Code Review Report

**Reviewed:** 2026-10-18
**Depth:** standard
**Status:** issues_found

## Summary

The KG-arm rewrite follows v1 `kg_query` closely: keyword fallback, three-string batched embed, ll/hl lookups, `(rank, weight)` sort, per-side chunk pick with VECTOR/WEIGHT and fallback, `chunk_top_k` cap, available-token formula, `rag_response` as system message with the query as user message, and the frequency-ordered reference list. The prompt drift test is a real byte-for-byte AST comparison against `v1/lightrag/prompt.py` and catches a change on either side (probed), with one gap (B-WR-05).

Two defects block. (1) Query traces no longer carry `embedder-index`, but `promotion.resolve_single_arm` still matches a trace to its arm by the exact node-id set, so `promote`, `rollback` and `retire` fail with `AssertionError` for every LightRAG arm that has a recipe node; the promote tests pass only because they seed hand-built traces with the full node set. (2) v1 drops vector hits below `COSINE_THRESHOLD` (0.2); the v2 lookups have no threshold, so the "match v1 selection" claim is false for entities, relations and chunks.

Probes (all in the scratchpad, repo untouched): `probe_promote.py`, `probe_empty.py`, `probe_float.py`, `probe_drift.py` under /tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/review11b/. Targeted tests run: `test_v1_prompt_drift`, `test_kg_retrieval_fidelity`, `test_empty_namespace`, `test_query_trace_nodes`, `test_arm_conformance` gave 38 passed.

## Divergence ledger against v1 (focus item 1)

| # | Step | v2 vs v1 | Grade |
|---|------|----------|-------|
| 1 | Keywords, short-query fallback, `", "`-joined strings | Matches operate.py:3855-3863. Long query with no keywords: v2 keeps lists empty, context is empty, `generate` returns `fail_response` with no call: same observable result as v1 on hybrid/local/global. | matches |
| 2 | Keyword prompt | `keywords_extraction` byte-identical (drift test). `keywords_extraction_examples` is a hard-coded copy, not drift-guarded. | B-WR-05 |
| 3 | Keyword response parsing, language | v1 strips think tags, splits CSV strings, uses `json_repair`, takes language from `addon_params`; v2 degrades to empty lists and hard-codes "English". | B-IN-01 |
| 4 | ll/hl/query embeddings | One batched call, same strings. v2 embeds all non-empty strings for every arm; v1 embeds only what the mode needs and embeds nothing for a long no-keyword query. Spend differs, retrieval does not. | B-IN-02 |
| 5 | Entity lookup by ll, relation lookup by hl, top_k 40 | Vectors and top_k match. **No cosine threshold.** | B-CR-02 |
| 6 | One-hop expansion, `(rank, weight)` desc, float weights, one degree per node | Matches operate.py:5259-5261; stable sort; Cozo string weights cast. The test does not prove the float cast. | B-WR-04 |
| 7 | Entity and relation chunk passes | Per-side pick, relation exclusion of selected entity chunks, `int(related_chunk_number * len(items) / 2)`, zero-count and missing-vector fallback to WEIGHT, kept-empty entity items: all match operate.py:5266-5717 and utils.py:3991-4160. `split_string_by_multi_markers` strips whitespace, v2 does not. | matches, B-IN-05 |
| 8 | Round-robin merge, dedup | entities by name, relations by sorted pair, chunks by `chunk_id`/`id`: match. KG arms have no vector chunks, so the single-merge order is identical. | matches |
| 9 | base/mix two-stage chunk merge (v1 merges vector, entity, relation in one round-robin) | v2 merges entity and relation in `chunk-sel-kg`, then `join-chunks`. Not an exposed arm. | documented and accepted (11-04 residual) |
| 10 | Entity/relation row projection and budgets 6000/8000 | `{entity,type,description}` / `{entity1,entity2,description}`, stop at the first overflow: match. | matches |
| 11 | Token estimate | `len // 4` instead of the model tokenizer, with `shortcut:` comments in `assemble.py` and `truncator_token_budget.py`. | documented and accepted (D-16) |
| 12 | Chunk cost in the available-token loop | v2 costs the whole pipeline item; v1 costs `{content,file_path,chunk_id}`. | B-WR-03 |
| 13 | Available-token formula, `chunk_top_k` 20 cap before truncation, 200 buffer | Matches operate.py:4875-4938 (overhead uses `user_prompt="n/a"` vs v1 `""`, 3 chars). | matches |
| 14 | Prompt templates, system/user split, `fail_response` on empty context, `rag_response`/`naive_rag_response` | Match operate.py:3888-3952 and 5808-5918. Edge: chunks all cut by budget with no entities gives v2 `fail_response`, v1 calls the LLM with an empty context. | matches, B-IN-05 |
| 15 | Reference list | Frequency then first appearance, `unknown_source` and blank paths unreferenced: match utils.py:4929-4992. | matches |
| 16 | Chunk vector `top_k` | chunk-vector default 10; v1 `chunk_top_k` 20 (operate.py:4287). Deferred in 11-04 as "out of scope", no `shortcut:`. | B-WR-06 |
| 17 | v1 `kg_query` response post-processing (strip sys prompt, "user", "model"), history, LLM cache, streaming | Not replicated. Documented in `generate.py`; the post-processing is a v1 quirk. | documented and accepted |
| 18 | Local/global mode with only the other half's keywords | v1 falls into its hybrid `else` branch (operate.py:4406-4440) and runs the other half; v2's arm has no such node and returns nothing. | B-IN-01 |

## Critical Issues

### B-CR-01: promote, rollback and retire cannot resolve a real LightRAG query trace

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

### B-CR-02: no cosine threshold on any vector lookup, so v1 selection is not matched

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

### B-WR-01: the empty-namespace pre-check refuses a populated corpus whose extraction yielded no entities or relations

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

### B-WR-02: `compare` aborts and discards finished arms when a later arm hits `EmptyNamespaceError`

**File:** `databasise/seam/engine.py:1039` (pre-check at 1678)
**Issue:** `compare` runs `{key: await self._execute_resolved(...)}` sequentially with no per-arm handling. Because the pre-check runs inside `_execute_resolved`, `compare([naive, hybrid])` on a corpus where the entities namespace is missing runs `naive` in full (LLM and embedding spend), then raises 422 for `hybrid` and returns nothing. Before 11-10 the same call returned two envelopes. With B-WR-01 this is reachable on populated corpora.
**Fix:** run `_refuse_empty_namespaces` for every resolved wiring before executing any of them (it only needs the resolved wirings), or catch the refusal per arm and surface it as that arm's degraded entry.

### B-WR-03: assemble costs chunks differently from v1, so the budget cuts earlier

**File:** `databasise/parts_core/lightrag/assemble.py:121-125`
**Issue:** v1 costs `json.dumps(chunk)` of the merged chunk, which at that point is `{"content","file_path","chunk_id"}` (operate.py:4795-4829; naive costs `_get_vector_context`'s dict, operate.py:4302-4309). v2 costs the whole pipeline item (`id`, `chunk_id`, `source_type`, `score`, `full_doc_id`, `chunk_order_index`, `tokens`, `rank_position`, `derived_from`, ...), roughly 150-250 extra characters per chunk. With 20 chunks near the 30000 budget this moves the cut by up to one chunk. The 11-11 summary justifies it as "the JSON of the whole chunk item", which is v1's rule applied to a different item. No test compares against v1's three-key shape.
**Fix:**
```python
cost_row = {"content": item.get("content"), "file_path": item.get("file_path", "unknown_source"), "chunk_id": item.get("chunk_id") or item.get("id")}
running += _tokens(json.dumps(cost_row, ensure_ascii=False))
```

### B-WR-04: the float-weight sort test does not discriminate float from string comparison

**File:** `databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py:205` (test at ~212-228)
**Issue:** the focus item asks whether weights compare as floats. The only edges at equal rank are weights `"1.0"` and `"5.0"`, whose lexicographic and numeric orders agree. Probe (`probe_float.py`): with `_as_float` replaced by an identity (string compare) the test still passes; with weights `"9.0"` and `"10.0"` string compare orders A-B before A-C, float compare orders A-C first. The 11-04 "Rule 1 bug" fix is therefore untested.
**Fix:** use `("A","B","9.0")` and `("A","C","10.0")` at equal rank and assert `A-C` precedes `A-B`.

### B-WR-05: `keywords_extraction_examples` is duplicated but not drift-guarded

**File:** `databasise/parts_core/lightrag/keywords.py:35-40`, `databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py:19-26`
**Issue:** v1 fills `{examples}` from `"\n".join(PROMPTS["keywords_extraction_examples"])` (operate.py:4175), a list. v2 hard-codes the single current element. `_DUPLICATED` omits it and the AST helper only collects string constants. Probe (`probe_drift.py`): a one-token change to the v1 list is not detected, while a typo in `rag_response`, a v1 string turned into a non-constant expression, and a trailing space on the v2 `naive_rag_response` are all detected. The drift test is otherwise sound (byte-exact on both sides).
**Fix:** move the example into `prompts.py` as `PROMPTS["keywords_extraction_examples"]`, extend the AST collector to accept a list of string constants, and add it to `_DUPLICATED`.

### B-WR-06: chunk-vector retrieves 10 chunks where v1 retrieves `chunk_top_k` = 20

**File:** `databasise/parts_core/lightrag/chunk_vector.py:17`
**Issue:** v1 `_get_vector_context` uses `chunk_top_k or top_k` (operate.py:4287), 20 by default. v2 uses 10, deferred in 11-04 ("Row 3 ... out of scope") and 11-RESEARCH A10 as a parity-pin risk. It carries no `shortcut:` comment and no requirement, so the naive arm sees half of v1's recall, and the new `chunk_top_k = 20` cap in `assemble` can never bind on that arm. Outside D-16's KG scope, but the naive arm now claims v1's templates and budget.
**Fix:** either set the default to 20 and update the parity pins, or mark the line `# shortcut: v1 retrieves chunk_top_k=20; upgrade with the parity re-baseline` and track it as a requirement.

## Info

### B-IN-01: keyword parsing and mode edge cases are leaner than v1

**File:** `databasise/parts_core/lightrag/keywords.py:59-73, 111`
**Issue:** v1 `_parse_keywords_payload` strips `<think>` tags, splits CSV-string fields, and repairs malformed JSON; v2 returns two empty lists on any failure. A reasoning model that emits a think block silently degrades to `ll = [query]` (short query) or `fail_response` (long query). The language comes from `config["language"]` ("English"), not v1's `_resolved_summary_language`/`addon_params`. Also, v1 `mix` mode returns `fail_response` for a long keyword-less query even when chunks exist (operate.py:3855-3860); the base (mix) wiring does not. And v1 local/global with no keywords of their own fall into the other half's lookup (see ledger row 18).
**Fix:** add think-tag stripping (one regex) and log the degrade at warning level; document the language source.

### B-IN-02: embedding spend differs from v1

**File:** `databasise/parts_core/lightrag/embedder_query.py:49-60`
**Issue:** every KG arm embeds all non-empty members of `[query, ll, hl]`. The local arm embeds an hl string it never uses; the global arm embeds an unused ll string; a long query with no keywords still embeds the query where v1 returns before any embed. Retrieval is unaffected; `token_accounting` and parity cost comparisons are inflated.
**Fix:** read the arm's needs from config (`ll`/`hl` flags) or from which lookup nodes are present, and skip the others.

### B-IN-03: recipe-only pruning has no guard for `provides` or `evidence_position`

**File:** `databasise/seam/engine.py:371-382`; `databasise/seam/engine.py:391` (hard-coded `vector.faiss`)
**Issue:** `_without_recipe_only_nodes` deletes any recipe-named node nothing depends on. `embedder-index` is neither provided nor an evidence node, and HippoRAG's recipe nodes (`chunk-embed`, `openie`) are depended on, so nothing breaks today (focus item 3: `wiring_instance_hash`, `wiring_id`, `provides` and `evidence_position` are all taken from the full `resolved`, lines 1735-1760, and `derive_mutation_class` reads registry wirings, so promotion classes do not change; the break is B-CR-01). A future wiring whose terminal node is also a recipe value would lose it and return `None` from `provided`. Separately, the pre-check hard-codes the store's file layout (`vector.faiss`) instead of asking the store.
**Fix:** skip nodes listed in `provides` or named by `evidence_position`; expose a `FaissVectorStore.is_committed(root, workspace, namespace)` helper beside the layout it depends on.

### B-IN-04: parity `_inject_query` and a stale comment

**File:** `databasise/parity/run_arm.py:128`, `143-146`
**Issue:** the hard-coded `("keywords","embedder-query","generate")` means parity runs give `assemble` and `rerank` no `config["query"]` (focus item 6). Effects: `assemble` counts zero query tokens, so its chunk budget is larger by `len(query)//4` tokens (about 10-30), which changes the cut only at the margin; `rerank` is a pass-through unless `live_rerank` is set, so no output changes. Nothing breaks: `max_total_tokens` falls back to assemble's own 30000, equal to the engine value. Parity runs also still dispatch `embedder-index`, as `embedder_index.py` states. The comment at 143-146 says "six listed edits"; the README now lists nine.
**Fix:** read `resolved["consumes_query"]` as `seam/engine.py::_inject_query` does; change the comment to "the README's listed edits".

### B-IN-05: minor v1 differences in chunk selection and assembly

**File:** `databasise/parts_core/lightrag/chunk_sel_kg.py:69`, `databasise/parts_core/lightrag/assemble.py:130-140`, `databasise/parts_core/lightrag/generate.py:72`
**Issue:** (a) `source_id` pieces are not `.strip()`ped as in v1's `split_string_by_multi_markers`. (b) When entities and relations are absent and every chunk is cut by the budget, v2 returns `fail_response`; v1 sends the LLM an empty context. (c) `assemble.order_policy` and `generate.prompt_template` independently choose the template pair; a wiring with `naive-template` and the default `rag_response` produces a naive context inside the KG system prompt with no refusal.
**Fix:** strip ids; accept (b) as documented; have `generate` read `assemble["template_kind"]` and refuse a mismatch.

### B-IN-06: `max_total_tokens` and HippoRAG pre-check confirmations (focus items 4 and 5)

**File:** `databasise/seam/engine.py:408, 472-482, 364-368, 1662`
**Issue:** no code defect; answers to the review questions.
- Item 5: `QueryObject` has no cap field, so a caller cannot set one. A wiring value (arm patch or promoted alias) is kept by `setdefault`; otherwise the engine stamps 30000, so "no cap" cannot occur (assemble also defaults to 30000). The stamped value enters `wiring_instance_hash`, so changing `_DEFAULT_MAX_TOTAL_TOKENS` changes every identity. A non-numeric wiring value raises in `int()` and degrades the envelope.
- Item 4: the pre-check runs after `_build_stores` (engine.py:1676-1678) inside the `try` whose `finally` finalises stores, so open errors keep precedence. It covers only `lightrag/retriever-chunk-topk`, `entity-lookup` and `relation-lookup` (`_RETRIEVAL_NAMESPACES`); HippoRAG's `hipporag-*` parts are not listed, so HippoRAG queries on an empty root keep the old behaviour. Confirmed, but no requirement or roadmap item in REQUIREMENTS.md or ROADMAP.md tracks the Phase 12 extension (only the 11-10 summary notes it).
**Fix:** add the HippoRAG extension to a Phase 12 requirement so it is not lost.

---

_Reviewed: 2026-10-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
