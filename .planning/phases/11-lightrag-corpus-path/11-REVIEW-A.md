---
phase: 11-lightrag-corpus-path
reviewed: 2026-10-18T00:00:00Z
depth: standard
part: A (the write path)
diff_base: 23c0ca0
files_reviewed: 30
files_reviewed_list:
  - databasise/foreign/v1_corpus_adapter.py
  - databasise/foreign/v1_corpus_driver_script.py
  - databasise/foreign/__init__.py
  - databasise/seam/engine.py
  - databasise/seam/jobs_store.py
  - databasise/seam/corpus.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/mcp/tools.py
  - databasise/mcp/server.py
  - databasise/parity/import_index.py
  - databasise/parts_core/lightrag/v1_index_sync.py
  - databasise/parts_core/lightrag/full_ingest.py
  - databasise/parts_core/lightrag/full_delete.py
  - databasise/parts_core/declared_only.py
  - databasise/wirings/lightrag/corpus-ingest.json
  - databasise/wirings/lightrag/corpus-delete.json
  - databasise/stores/vector.py
  - databasise/eval/aa_run.py
  - databasise/evidence/COVERAGE.md
  - databasise/tests/seam/test_corpus_write_gate.py
  - databasise/tests/seam/test_lightrag_inbox.py
  - databasise/tests/seam/test_interrupted_documents.py
  - databasise/tests/seam/test_job_families.py
  - databasise/tests/seam/test_status_during_write.py
  - databasise/tests/seam/test_health_honesty.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/parts_core/lightrag/test_v1_index_sync.py
  - databasise/tests/parts_core/lightrag/test_corpus_metering.py
  - databasise/tests/foreign/test_v1_not_configured.py
findings:
  critical: 2
  warning: 5
  info: 5
  total: 12
status: issues_found
---

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

- **Write gate (focus 2):** cancellation releases the gate while the v1 subprocess keeps running (CR-01).
- **Retry and the one-id-two-suffixes case (focus 3, 4):** the deferred case is worse than 11-05 states. A delete
  reports `success` and leaves a live, queryable document behind (CR-02).
- **Sync heal (focus 1):** the "healed on the next sync" claim is false after a partial commit (WR-01).
- **Metering (focus 7):** real usage above the fixed 1,000,000 allowance fails an already-committed ingest (WR-02).

The other focus items held up:

- **Single-bump (focus 10):** the driver script has no commit after `50a6298` (11-03). The 11-07 changes touch the
  adapter only and map exit codes 3 and 4 that 11-03 already emitted. D-06 is intact.
- **Health (focus 9):** it writes nothing, verified by the real-driver test and by reading the code. It is not `ok`
  without both clients.
- **Job store (focus 8):** creation is lazy and reads open read-only. The one gap is WR-04.
- **Secrets (focus 6):** refusal bodies carry key names only. See WR-05 for the log side.

## Structural Findings (fallow)

None provided.

## Critical Issues

### CR-01: Cancelling a write releases the gate while the v1 subprocess is still running

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

### CR-02: One id with two suffixes: delete reports success and leaves a live, queryable document (worse than 11-05 states)

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

### WR-01: "Healed on the next sync" is false after a partial commit; the prune manifest advances ahead of the vector and graph stores

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

### WR-02: Real token usage above the fixed 1,000,000 allowance fails an ingest whose v1 write already committed

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

### WR-03: A caller-supplied document id of `unknown_source` deletes an unrelated document

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

### WR-04: A HippoRAG job-record failure after commit reports the ingest as failed

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

### WR-05: Server logs carry the v1 stderr tail, a staged absolute path and (via provider errors) key fragments

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

### IN-01: Retry of a raw upload is proven only for a document interrupted after parse

**File:** `databasise/tests/seam/test_interrupted_documents.py` (text document only);
`databasise/seam/engine.py:1283-1339`.

The 11-08 retry of a `doc-<md5>` row was never covered by a test. I ran it (`test_probe_real_raw.py`, real
driver): a raw `s.txt` upload timed out in `processing`, the source had already been moved to
`corpus-inbox/__parsed__/slowraw.txt`, and `POST retry` returned `processed` with the inbox empty afterwards. The
retry path works for that state. The `parsing` state, where the kept file is still in the inbox root and the driver
must re-read it through `INPUT_DIR`, cannot be produced with the stub server (a `.txt` parses instantly) and
remains unproven. Add a real-driver test with a kill during parse, or a fake that leaves the file in the inbox and
asserts the driver reaches it through `input_dir`.

### IN-02: A deterministic driver failure keeps the staged upload and blocks the id until a delete

**File:** `databasise/seam/engine.py:319, 1188-1196, 1231-1239`.

`_KEEP_STAGED` keeps the file for every `CorpusOpSubprocessError`, including exit-1 failures that occur before v1
enqueued anything (dimension mismatch, store lock). The next upload of that id gets `DuplicateDocumentIdError`,
retry answers `UnknownDocumentError`, and only `DELETE` (which answers `not_found` and cleans the inbox) clears it.
This is pinned by `test_a_driver_fault_keeps_the_file_logs_it_once_and_a_later_delete_removes_it`, so it is a
design choice. Consider letting `ingest` overwrite a kept file when `status` shows no v1 row for the id.

### IN-03: `jobs.db` is shared across workspaces

**File:** `databasise/seam/jobs_store.py:11-17`, `databasise/seam/engine.py:917`.

The file is `<store_root>/jobs.db` with no workspace column. A HippoRAG job id minted in workspace A answers
`processed` (with A's `document_id`) when polled in workspace B. Ids are unguessable hex, so exposure is low. D-02
asks for one file under the store root, so add a `workspace` column and filter on it when the multi-workspace
deployment becomes real.

### IN-04: The sync mirror is bounded by a 300 s ceiling and rewrites the whole corpus per write

**File:** `databasise/parts_core/lightrag/v1_index_sync.py:70-82`.

The `shortcut:` comment records the O(corpus) cost. The consequence beyond speed is that once a corpus is large
enough for the mirror to pass 300 s, every ingest fails after v1 has committed (the same failure shape as WR-02),
and the timed-out thread keeps v1's RocksDB open (see CR-01). Record the corpus size at which this bites, and
upgrade by diffing doc-status snapshots before that point.

### IN-05: Lint and housekeeping in the touched files

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
  ingest, delete and retry, and releases on every raised path. Retry holds it. The cancellation hole is CR-01.
- **Inbox (focus 4):** names are generated from a token-validated id and a regex-validated, allow-listed suffix, so no
  traversal is possible. `_remove_inbox_files` matches the exact `<id>.` prefix and cannot hit another id, because ids
  cannot contain a dot. Success, refusal and delete remove the file and the `__parsed__` copy. A timeout keeps it.
  After a real ingest only an empty `__parsed__/` directory remains.
- **Status (focus 5):** status is facade-free. v1 writes JSON through `atomic_write`, so the retry-then-409 path for a
  torn read is effectively defensive. The stem mapping is correct apart from CR-02 and WR-03.
- **Metering (focus 7):** `tokens_from_usage` is consistent with the `counted_by` rules in the tests. Embedding spend is
  carried in `usage` and is not surfaced beyond the node result.
- **Single-bump (focus 10):** confirmed. Last driver-script commit is `50a6298` (11-03). `git diff 50a6298 HEAD` on
  `databasise/foreign` shows adapter-only changes. `parts_core` part files have no change after `e587d04`.

---

_Reviewed: 2026-10-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
