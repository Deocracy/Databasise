---
phase: 15-offline-tooling-packaging
lane: A
reviewed: 2026-10-21T23:48:07Z
depth: deep
diff_base: 00eeae8
files_reviewed: 13
files_reviewed_list:
  - databasise/cli.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/run_comparison.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/storage_audit.py
  - databasise/parity/run_arm.py
  - databasise/parity/v1_driver_script.py
  - databasise/parity/v1_arm.py
  - databasise/parity/import_index.py
  - databasise/eval/remint.py
  - databasise/eval/corpus_ingest.py
  - databasise/clients/builder.py
  - databasise/foreign/v1_corpus_adapter.py
findings:
  critical: 1
  warning: 10
  info: 4
  total: 15
status: issues_found
---

# Phase 15: Code Review Report (Lane A)

**Reviewed:** 2026-10-21T23:48:07Z
**Depth:** deep
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Lane A covers the offline CLIs and the code they call: `databasise.cli`, the parity harnesses, `import_index`, `remint`, `corpus_ingest`, the client builder and the v1 corpus adapter. Call chains were followed into `clients/openai_compat.py`, `stores/kv.py`, `stores/vector.py`, `store_lock.py`, `eval/bundle.py`, `wirings/resolve.py`, `seam/selectors.py` and v1's `aquery_llm`/`kg_query`.

Each CLI was run without `--spend` from the `databasise/.venv` interpreter: `run_cross_modality`, `run_arm --arm hipporag`, `storage_audit`, `run_comparison`, `build_hipporag_index`, `remint`, `v1_arm` and `corpus_ingest`. Every one exited 0 and printed `mode: estimate-only`. No CLI was run with `--spend`, and no env file was read.

What holds:
- D-04 holds on the default path. No estimate path builds a client or takes a lock.
- No path prints env-file values. Builder refusals name keys only.
- No §18 consumer field gets a part name, node id or hash from these files. The CLIs write only to stderr and to internal evidence JSON.

What fails:
- **Critical:** `corpus_ingest --limit` accepts negative values. Python slicing then turns `--limit -5` into 286 documents (verified).
- **Named refusals escape as tracebacks after money is spent.** `ModelIdentityMissingError`, `EmptyChoicesError` and `MissingCompletionContentError` are not in the refusal tuple. `UnresolvedJudgeIdentityError` can never be raised by the real client.
- **The v1 driver mislabels a legitimate v1 outcome as a failure.** v1 answers some queries with its fail text but sets no `status`, and the driver treats that as `V1QueryFailedError`.
- **The v1 subprocess refusal keeps the wrong part of stderr.** It keeps the first characters of stderr, where v1's INFO logs are, and drops the real error at the end.
- **Read paths write.** `verify_import` creates or changes `kv.sqlite3`, and `import_index --verify` creates the store root.
- **Other gaps:**
  - a refused HippoRAG build stays on disk where cross-modality preflight accepts it;
  - `corpus_ingest` takes no store lock;
  - `run_arm` exits 0 on a partial or cyclic run;
  - `import_index` and `build_hipporag_index` read the snapshot outside their refusal handling.

## Critical Issues

### CR-01: `corpus_ingest --limit` accepts negative and zero values; a negative limit ingests almost the whole corpus

**File:** `databasise/eval/corpus_ingest.py:208` (also `:144-147` and `:191`)
**Issue:** `--limit` is declared `type=int`, not `type=cli.positive_int`. `estimate()` checks only `limit > available`. It then slices `snapshot.documents[:limit]`, and `ingest_documents` slices `snapshot.documents[: est.documents]`.

With `--limit -5` the slice is `documents[:-5]`. This was verified: `python -m databasise.eval.corpus_ingest --limit -5` prints `"documents": 286` with `"bound": "document count (--limit=-5)"` and exits 0. With `--spend` it would ingest 286 documents.

This module exists to bound spend by document count. A typo (`-5` for `5`) spends about 57 times the intended bound and reports success. `--limit 0` ingests nothing and exits 0.

D-03 says bad arguments exit 2. `cli.positive_int` was added for exactly this, but only `aa_run --n-resamples` uses it.

**Fix:**
```python
parser.add_argument("--limit", type=cli.positive_int, required=True)
```
Also guard the library entry point, since `aa_run` reuses it:
```python
if limit < 1 or limit > available:
    raise LimitExceedsCorpusError(requested=limit, available=available)  # or a separate named error for < 1
```

## Warnings

### WR-01: Named client refusals escape as tracebacks after a paid call (`remint --spend`, `run_comparison --spend`); `UnresolvedJudgeIdentityError` is unreachable

**File:** `databasise/eval/remint.py:84-86,128,156`; `databasise/parity/run_comparison.py:203-215,723-724,741`; `databasise/cli.py:47-58`
**Issue:** `OpenAICompatibleClient.chat` (`clients/openai_compat.py:181-190,218-221`) raises its own named `RuntimeError` subclasses:
- `ModelIdentityMissingError` when the response has no `model`;
- `EmptyChoicesError`;
- `MissingCompletionContentError` when `content is None`, for example a reasoning model that runs out of tokens on the `"ping"` probe.

None of these classes is in `cli.offline_refusals()`, and neither CLI adds them. So:
- `remint --spend` pays for the probe call, then dies with a traceback instead of the D-03 single line.
- `remint.resolve_judge_identity`'s own `UnresolvedJudgeIdentityError` (line 85) cannot fire with the real client. `_resolved_identity` raises `ModelIdentityMissingError` first, inside `chat()`.
- In `run_comparison`, `_run_keywords_live` calls the part body directly, outside the scheduler, which would otherwise record the failure as a trace. The same errors therefore leave `asyncio.run(_run_cli(...))` (line 796) as a traceback. The records already collected for earlier queries are lost.

**Fix:** Add the client's named refusals to the shared tuple in `cli.offline_refusals`:
```python
from databasise.clients.openai_compat import (
    EmbeddingBatchMismatchError, EmptyChoicesError, MissingCompletionContentError, ModelIdentityMissingError,
)
from databasise.clients.rerank import RerankResponseError
...
return (*BUILDER_REFUSALS, ..., ModelIdentityMissingError, EmptyChoicesError,
        MissingCompletionContentError, EmbeddingBatchMismatchError, RerankResponseError, *extra)
```
Then either delete `UnresolvedJudgeIdentityError` or catch `ModelIdentityMissingError` in `resolve_judge_identity` and re-raise it as `UnresolvedJudgeIdentityError`.

### WR-02: The v1 driver treats v1's status-less fail-response answer as a v1 exception (D-08 says exit 1 only on the exception path)

**File:** `databasise/parity/v1_driver_script.py:139-143`
**Issue:** v1's `aquery_llm` has three return shapes, not two:
1. a success dict;
2. the `no_results` failure (`lightrag.py:2437-2451`);
3. `raw_data = query_result.raw_data or {}` plus `llm_response` (`lightrag.py:2453-2465`) when `kg_query`/`naive_query` return `QueryResult(content=PROMPTS["fail_response"])` with no `raw_data`.

Shape 3 happens at `operate.py:3835`, `3860`, `5777` and `5788`. One trigger is a query of 50 or more characters with both keyword lists empty. That dict has no `status` and no `metadata`.

The driver's test `response.get("status") != "success" and metadata.get("failure_reason") != "no_results"` is true for it. The driver raises `V1QueryFailedError("v1 reported a failure")`, but v1's own `aquery` returns `fail_response` there, a non-exception answer.

Failure scenario in `run_comparison`:
1. For a `hybrid` query, the decomposed keyword extractor returns two empty lists.
2. v1 receives empty pins and extracts its own keywords (`operate.py:4027`), which also come back empty.
3. v1 answers with `fail_response`.
4. The harness refuses with `V1ArmSubprocessError`, and `_run_cli` stops at the `break` (line 745), so every remaining query is skipped.

**Fix:** Key the exception path on v1's exception shape, not on a missing `status`:
```python
status = response.get("status")
if status == "failure" and metadata.get("failure_reason") != "no_results":
    raise V1QueryFailedError(str(response.get("message") or "v1 reported a failure"))
```
Then treat a dict with no status and an `llm_response` as an empty retrieval. Correct the class docstring, which says the exception path is `status == "failure"` with `metadata == {}`.

### WR-03: `V1ArmSubprocessError` keeps the head of stderr, so the D-08 named failure line is cut off

**File:** `databasise/parity/v1_arm.py:75`; `databasise/cli.py:29`
**Issue:** v1's logger writes INFO lines to stderr (`v1/lightrag/utils.py:90-98`, a `StreamHandler` at INFO). On the exception path `aquery_llm` also logs `Query failed: ...`. The driver prints `V1QueryFailedError: <msg>`, or a traceback, last.

`V1ArmSubprocessError` keeps `stderr.strip()[:2000]`, the start of stderr. `cli.refuse` then truncates the message to its first 500 characters. The one stderr line therefore normally shows only v1's start-up INFO lines, and never the `V1QueryFailedError:` line or the exception at the bottom of the traceback.

**Fix:** Keep the tail:
```python
tail = stderr.strip()[-2000:] or "(no stderr)"
super().__init__(f"v1 driver subprocess exited {returncode}: {tail}")
```
Better still, take the last line that does not start with `INFO:`/`WARNING:` as the message, and keep the full stderr on the `stderr` attribute. `cli.refuse`'s 500-character head cut has the same problem for any long message; consider cutting the middle instead.

### WR-04: `verify_import` and `import_index --verify` are read paths that write

**File:** `databasise/parity/import_index.py:639`, `:753`; `databasise/stores/kv.py:52-61`; `databasise/store_lock.py:58-60`
**Issue:** Two writes happen on the verify path:
- `verify_import` opens `SqliteKVStore(namespace="text_chunks", ...)` to read chunk text. Its `__init__` runs `mkdir(parents=True)`, `sqlite3.connect` (which creates `kv.sqlite3`), `PRAGMA journal_mode=WAL` and `CREATE TABLE IF NOT EXISTS`. So verifying a workspace that has no `text_chunks` namespace creates one, and verifying an existing one rewrites its journal mode. `run_comparison`'s preflight calls this on every query.
- `import_index --verify` takes `store_lock(store_root)`, which runs `root.mkdir(parents=True)` and writes `.engine.lock`. `--verify --store-root /typo` creates `/typo/.engine.lock`, then reports `refused: no imported v2 store`.

**Fix:**
- Read v1-side KV state through a read-only sqlite URI: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`. Treat a missing `kv.sqlite3` as "absent", which adds a `chunk-text` violation for every v1 chunk.
- For `--verify`, check `store_root.is_dir()` before locking and refuse by name if it is missing. Alternatively, give `store_lock` a `create=False` mode for read paths.

### WR-05: `verify_import` passes vacuously when the v1 index is absent, now that `--v1-working-dir` is user-settable

**File:** `databasise/parity/import_index.py:609-707`, `:737-738`
**Issue:** `import_v1_index` refuses a missing `v1_working_dir` with `MissingV1IndexError` (line 454), but `verify_import` never checks it. With `--verify --v1-working-dir <typo>`:
- `_v1_text_chunks` returns `{}`, the vector pairs come back `[]` and `_v1_graph` returns `None`.
- If the v2 namespaces hold data, the run reports `inconclusive` with misleading "N extra in v2" violations instead of the named refusal.
- If the v2 workspace directory exists but is empty, every check passes over nothing and the result is `verified`, exit 0.

D-06 covers only one direction (v1 graph present, v2 absent). A v2 graph with no v1 graph also passes silently.

**Fix:** At the top of `verify_import`, return `refused` with a `precondition` violation when `not v1_working_dir.exists()`. Add the reverse graph case:
```python
if v1_graph is None and v2_graph is not None:
    violations.append(Violation(assertion="graph-topology", detail="v2 has a graph but v1 has none"))
```

### WR-06: A refused HippoRAG build stays in the store, and cross-modality preflight accepts it

**File:** `databasise/parity/build_hipporag_index.py:284-323`; `databasise/parity/run_cross_modality.py:268-271`
**Issue:** `build_index` commits the stores (`index_done_callback`, lines 284-285) before it verifies them. It then raises `ChunkCountMismatchError` or `HippoRAGIndexBuildRefusedError` for these cases: empty entities, empty facts, zero edges, no `entity:` vertex, or a chunk-count mismatch. The written namespaces stay on disk.

`run_cross_modality.preflight` checks only that `hipporag-chunks` is non-empty. A later `run_cross_modality --spend` therefore runs and records a comparison against an index its own builder refused. That defeats the "never report a build that has not been verified" rule this pair exists to enforce.

**Fix:** Do one of the following:
- write a verified marker, such as a `build.json` with the corpus hash, as the last step of a successful `build_index`, and have `preflight` require it;
- have `preflight` repeat the builder's checks (`hipporag-entities`, `hipporag-facts`, graph non-empty);
- build into a staging workspace and rename it only after verification passes.

### WR-07: `corpus_ingest --spend` writes the eval store with no store lock

**File:** `databasise/eval/corpus_ingest.py:228-242`
**Issue:** Every other spending CLI in this phase wraps its run in `store_lock(...)` (marked D-03). `corpus_ingest` builds a `Databasise` engine on `_EVAL_INGEST_STORE_ROOT` and ingests with no lock. The engine does not lock either: `seam/` never calls `store_lock`.

Two concurrent `corpus_ingest --spend` runs, or one running alongside `aa_run`, which reads the same root and writes `floors.db`, can interleave writes to `trace.db`, `jobs.db`, the Faiss namespaces and the v1 `lightrag-v1` working directory. Phase 10 G-36 and RUN-07 ("one engine process per store root") forbid this.

**Fix:**
```python
with store_lock(_EVAL_INGEST_STORE_ROOT):
    engine = Databasise(store_root=_EVAL_INGEST_STORE_ROOT, ...)
    jobs = asyncio.run(ingest_documents(engine, snapshot, limit=args.limit, arm=args.arm))
```
Also add `StoreLockedError` handling; it is already in `offline_refusals`. Apply the same fix to `aa_run`, which is outside this lane.

### WR-08: `run_arm` exits 0 for a cyclic or partial run (D-03 code 3 is never used)

**File:** `databasise/parity/run_arm.py:246-247,311-317`
**Issue:** `run_arm()` returns `{"cycle": [...]}` for a cyclic wiring, or a run record with `partial=True` or `degraded=True`. `main()` prints that and returns `EXIT_OK` either way. D-03 defines 3 as "ran but inconclusive", and the sibling CLIs use it: `storage_audit` (lines 285-307) and `run_comparison` (lines 812-813).

A script that runs `run_arm --spend` and checks the exit code treats a budget-halted, half-run arm as success.

**Fix:**
```python
print(json.dumps(result, indent=2, default=str))
if "cycle" in result or result["run_record"]["partial"]:
    return cli.EXIT_INCONCLUSIVE
return cli.EXIT_OK
```
Update the docstring's exit table to match.

### WR-09: Snapshot loads outside the refusal handler in `import_index` and `build_hipporag_index`; `import_index` catches only two classes

**File:** `databasise/parity/import_index.py:739-756`; `databasise/parity/build_hipporag_index.py:352-353,361`
**Issue:** In `import_index.main`:
- `_import_workspace()` and `load_snapshot()` (lines 741-742) run before the `try`;
- the `try` catches only `MissingV1IndexError` and `StoreLockedError`.

So these escape as tracebacks:
- a `CorpusDriftError` or `FileNotFoundError` from the snapshot;
- a `VectorStoreCorruptedError` from the import;
- the RocksDB "lock held" error from `_v1_graph`.

`build_hipporag_index.main` also calls `load_snapshot()` and `estimate()` at lines 352-353, before its `try`, so a drifted corpus crashes the estimate-only path with a traceback.

**Fix:** In both modules, move the snapshot/workspace lines inside the `try`. In `import_index`, use `except cli.offline_refusals(MissingV1IndexError, VectorStoreCorruptedError) as exc: return cli.refuse(exc)` so it matches the other CLIs.

### WR-10: `run_comparison` overwrites `<arm>.json` with a truncated run that carries no refusal marker

**File:** `databasise/parity/run_comparison.py:741-745,802-811`
**Issue:** If a refusal hits query k (k > 1), `_run_cli` breaks the loop. `main` then writes the k-1 completed records to `.comparison_results/<arm>.json`, replacing the previous full result, and exits 1.

Every record in the file has `"status": "completed"`, and nothing records that the run stopped early. A later reader of the JSON, such as an evidence render, sees a clean but shorter comparison. `run_cross_modality` marks the same case with `"status": "refused"`, `reason` and `query_id`. This module does not.

**Fix:** When `had_error` is set, write a wrapper object, for example `{"status": "refused", "reason": <refusal line>, "records": [...]}`, or write to `<arm>.refused.json`. Never overwrite the last complete result with an unmarked partial one.

## Info

### IN-01: The cross-modality estimate overstates the LightRAG arm

**File:** `databasise/parity/run_cross_modality.py:446-447`; `databasise/parity/run_arm.py:146-165,276-287`
**Issue:** `estimate_arm("naive", ...)` goes through `resolve_query_arm`, which keeps LightRAG's recipe-only `embedder-index`. The estimate therefore prints `nodes: 7, calls_embedding: 2` (observed). `run_cross_modality` runs through `engine.compare`, whose query path drops recipe-only nodes (`without_recipe_only_nodes`, LRAG-19), so the real run makes 6 nodes and 1 embedding call. The figure is correct for `run_arm` and `storage_audit` but not for this CLI.
**Fix:** In `_print_estimate`, compute the LightRAG estimate on `without_recipe_only_nodes(resolve_arm(...))`, or label the figure an upper bound.

### IN-02: `remint --spend` from a wheel spends the probe call before discovering the bundle root is not writable

**File:** `databasise/eval/remint.py:132-133,153-166`
**Issue:** The pre-check confirms only that `_COMMITTED_BUNDLE_ROOT.is_dir()`. In a read-only install (a system or Nix site-packages), `_write_version`'s `mkdir` raises `PermissionError`, which is not in the refusal tuple. This happens after the paid chat call and prints a traceback. The docstring says minting needs a source checkout, but the code does not enforce that.
**Fix:** Before building clients, check `os.access(_COMMITTED_BUNDLE_ROOT, os.W_OK)` and refuse by name.

### IN-03: Empty pinned keywords silently unpin the v1 arm

**File:** `databasise/parity/run_comparison.py:595-599,632-641`; `databasise/parity/v1_driver_script.py:133`
**Issue:** v1 short-circuits only when `hl_keywords or ll_keywords` is truthy (`operate.py:4027`). When the live pin call returns two empty lists, the decomposed arm runs pinned-empty while v1 extracts its own keywords. The record still says `pinned_keywords: {[], []}`. This can be detected through `hl_keywords_used`, but the comparison is no longer pinned.
**Fix:** Treat an empty pin pair as `inconclusive` ("pin produced no keywords"), or record `pin_reached_v1: false` when v1's echoed keywords differ from the pin.

### IN-04: `_write_result` inside the refusal handler can raise and mask the refusal

**File:** `databasise/parity/run_cross_modality.py:482-492`
**Issue:** `_write_result` runs `mkdir` and `write_text` inside the `except` block. An `OSError` there, such as a read-only site-packages (see 15-CONTEXT Specifics), replaces the one-line refusal with a chained traceback.
**Fix:** Wrap the write in `try/except OSError` and print one extra stderr line naming the failed write, then still `return cli.refuse(exc)`.

---

_Reviewed: 2026-10-21T23:48:07Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
