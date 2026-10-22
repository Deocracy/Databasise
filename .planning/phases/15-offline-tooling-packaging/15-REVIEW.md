---
phase: 15-offline-tooling-packaging
reviewed: 2026-10-21T23:51:57Z
depth: deep
diff_base: 00eeae8
parts: "A (offline CLIs: cli.py, parity harnesses, import_index, remint, corpus_ingest, client builder, v1 corpus adapter) + B (TOOL-12 floor store and two-stage gate, aa_run, calibration, bundle, admission at load, API inventory) + C (codebase-memory-mcp part and adapter, MCP server, evidence renderers, import-boundary checker, packaging, README, CODEBASE-MAP), merged; ids prefixed A-/B-/C-. The three lanes' file lists are disjoint. One finding pair described the same defect and was merged (A-WR-01 absorbs B-WR-05)."
files_reviewed: 41
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
  - databasise/seam/engine.py
  - databasise/seam/floors_store.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/evidence.py
  - databasise/eval/aa_run.py
  - databasise/eval/calibration.py
  - databasise/eval/bundle.py
  - databasise/parts/admission.py
  - databasise/parts/registry.py
  - databasise/__init__.py
  - docs/gui/API-INVENTORY.md
  - databasise/parts_core/codebase_memory_mcp.py
  - databasise/parts_core/declared_only.py
  - databasise/foreign/codebase_memory_mcp_adapter.py
  - databasise/foreign/_mcp_sdk_guard.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/mcp/__init__.py
  - databasise/evidence/parity_report.py
  - databasise/evidence/f07_report.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/__init__.py
  - databasise/tools/check_import_boundary.py
  - databasise/pyproject.toml
  - databasise/README.md
  - docs/gui/CODEBASE-MAP.md
findings:
  critical: 3
  warning: 23
  info: 19
  total: 45
status: issues_found
---
# Phase 15: Code Review Report

**Reviewed:** 2026-10-21
**Depth:** deep (lane A traced into `clients/openai_compat.py`, `stores/kv.py`, `stores/vector.py`, `store_lock.py`, `eval/bundle.py`, `wirings/resolve.py`, `seam/selectors.py` and v1's `aquery_llm`/`kg_query`; lane B traced into `cli.py`, `clients/builder.py`, `ledger/ledger.py`, `seam/selectors.py`, `stores/vector.py`, `seam/trace_store.py`, `wirings/resolve.py` and `eval/remint.py`; lane C probed the renderers and adapter against temp copies)
**Files Reviewed:** 41 (lane A 13, lane B 13, lane C 15)
**Status:** issues_found (3 Critical; 23 Warning, 19 Info)

## Summary

The diff is `git diff 00eeae8 HEAD`. Lane A covers the offline CLIs and the code they call. Lane B covers the TOOL-12 floor store and two-stage gate, the aa_run CLI contract, the calibration changes, the bundle hash and sealed-open changes, admission at load, and the API inventory. Lane C covers the codebase-memory-mcp part and adapter (allowlist, launch timeout, lazy admission), the MCP server tool descriptions, the three evidence renderers, the import-boundary checker, packaging metadata, and the README and CODEBASE-MAP edits.

The lanes verified the following against the source and with probes:

- **D-04 estimate-only default.** Lane A ran every lane-A CLI without `--spend` (`run_cross_modality`, `run_arm --arm hipporag`, `storage_audit`, `run_comparison`, `build_hipporag_index`, `remint`, `v1_arm`, `corpus_ingest`); each exited 0 and printed `mode: estimate-only`. Lane B ran `aa_run.main([...])` without `--spend`; it built no client, opened no store and wrote nothing. No estimate path builds a client or takes a lock.
- **Secrets.** No path in any lane prints env-file contents. Builder refusals name keys only. No CLI was run with `--spend`, and no env file was read.
- **§18.** No consumer field gets a part name, node id or hash from the files in scope. The new seam refusals carry only `verb` and `mutation_class`. No leak was found in the MCP tool descriptions. One forward risk is recorded as Info (C-IN-07).
- **Stage-1 gate.** It creates no `ledger.db`: `Ledger.open_existing(read_only=True)` creates nothing when the file is absent.
- **`run_wiring`** canonicalises before it dispatches anything.
- **Adapter.** The codebase-memory-mcp allowlist and lazy admission work as described.
- **Tests.** Lane C: 538 offline tests across evidence, mcp, foreign and parts_core pass. Lane B: plain pytest was blocked by the check-guard hook, so no lane-B test results are claimed; every lane-B finding was verified by reading the source, and where noted by running code in the scratchpad. Lane A claims no test run beyond the estimate-only CLI runs.

There are three blockers:

1. **`corpus_ingest --limit -5` ingests 286 documents** (A-CR-01). The spend bound accepts negative values and Python slicing inverts them. Verified.
2. **The aa_run judge parser scores "not correct" as CORRECT** (B-CR-01). It takes the first verdict word anywhere in the reply, so the A/A floor the gate persists is computed from wrong scores. Verified with the regex.
3. **The Falsifier 2 verdict ignores the named wirings' own validator results** (C-CR-01). A wiring with `effects-exceed-part` still renders "did not fire" and exits 0, and a self-declared `effective_depth` crashes the renderer with a `KeyError`. Both verified.

The 23 warnings, by theme:

- **D-03 breaches (named refusals escape as tracebacks):** A-WR-01 (client and vector-store refusals missing from the shared tuple, merged with B-WR-05), A-WR-09, B-WR-03, B-WR-06, C-WR-01, C-WR-04.
- **Read paths that write:** A-WR-04 (`verify_import`, `import_index --verify`), B-WR-02 (`floors.db-shm`/`-wal`), C-WR-03 (evidence CLIs overwrite package files by default).
- **Spend and evidence integrity:** A-WR-02, A-WR-03, A-WR-05, A-WR-06, A-WR-07, A-WR-08, A-WR-10, B-WR-01, B-WR-04, B-WR-07, C-WR-02.
- **Stale Phase 16 GUI inputs:** B-WR-08 (API-INVENTORY.md), C-WR-05 and C-WR-06 (CODEBASE-MAP.md).

**Merge notes.**

- A-WR-01 and B-WR-05 describe the same defect: `cli.offline_refusals` (`cli.py:36-58`) omits named `RuntimeError` subclasses that callees raise, so they escape as tracebacks. Merged under A-WR-01. Lane A contributed the client refusals (`ModelIdentityMissingError`, `EmptyChoicesError`, `MissingCompletionContentError`) and the unreachable `UnresolvedJudgeIdentityError`. Lane B contributed `VectorStoreCorruptedError` from `load_committed` on the aa_run index probe. Reading `aa_run.py:634-637` at merge time confirms that `aa_run._refusals()` is built on `cli.offline_refusals`, so one fix in the shared tuple covers both.
- A-WR-09 (`import_index` and `build_hipporag_index` read the snapshot outside the `try`) also names `VectorStoreCorruptedError`. It is cross-referenced to A-WR-01, not merged: adding the class to the shared tuple fixes only part of it, and the try-placement defect remains.
- A-WR-07 says the missing store lock applies to `aa_run` too, which is a lane-B file. A grep at merge time confirms that `eval/aa_run.py` never calls `store_lock`. That extension is recorded in A-WR-07, not as a separate finding.
- A-WR-04 and B-WR-02 are both read paths that write, in different stores (`kv.sqlite3`/`.engine.lock` vs `floors.db`). They are cross-referenced. This is the same class of defect as Phase 14 A-WR-01.
- A-IN-02, A-IN-04 and C-WR-03 all fail on a read-only (wheel or Nix) install, in three different modules. They are cross-referenced.
- B-WR-08 (API-INVENTORY.md) and C-WR-05/C-WR-06 (CODEBASE-MAP.md) are stale Phase 16 GUI inputs in different files. They are cross-referenced.
- A-WR-02 and A-IN-03 share a trigger (empty pinned keywords) but describe different defects (a false v1 failure vs a silently unpinned comparison). Both are kept.
- B-WR-04 and B-IN-03 both concern work done before a certain refusal in aa_run (paid passes vs env read and `trace.db` creation). Both are kept.
- B-IN-05 also applies to `parity/run_arm.py:81`, a lane-A file.

## Narrative Findings (AI reviewer)

## Critical Issues

### A-CR-01: `corpus_ingest --limit` accepts negative and zero values; a negative limit ingests almost the whole corpus

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

### B-CR-01: The judge verdict parser takes the first verdict word anywhere, so "not correct" scores 1.0

**File:** `databasise/eval/aa_run.py:131`, `databasise/eval/aa_run.py:354`
**Issue:** `_VERDICT_PATTERN.search(result.text.upper())` returns the first whole-word CORRECT, PARTIAL or INCORRECT anywhere in the reply. The old parser read the first word only and refused anything else. The new one turns negations and echoed instructions into the wrong score:
- `"not correct"` gives CORRECT (1.0).
- `"Partially correct"` gives CORRECT (1.0), not PARTIAL (0.5).
- `"The answer is not CORRECT; verdict: INCORRECT"` gives CORRECT.

This was confirmed by running the regex. The committed judge prompt (`evidence/eval-bundles/judge-prompt-v1.txt`) lists `- CORRECT — ...` first. A judge that echoes the option list before its verdict is therefore always scored CORRECT. These are wrong `answer_level` scores, and they feed the A/A floor that the gate persists. `UnparseableJudgeVerdictError` was meant to catch exactly these replies, and it no longer does.
**Fix:** Accept a verdict only when it is the whole reply after stripping punctuation and markdown, or after a single `Verdict:` label. Refuse a reply that contains more than one distinct verdict word:
```python
_VERDICT_PATTERN = re.compile(r"^\W*(?:VERDICT:\s*)?\**\s*(CORRECT|PARTIAL|INCORRECT)\b\W*")
found = set(re.findall(r"\b(CORRECT|PARTIAL|INCORRECT)\b", text_upper))
match = _VERDICT_PATTERN.match(text_upper.strip())
if match is None or len(found) != 1:
    raise UnparseableJudgeVerdictError(result.text)
```

### C-CR-01: The Falsifier 2 verdict and exit code ignore validator violations in the three named wirings

**File:** `databasise/evidence/falsifier2.py:319-361`, `:570-594`, `:597-604`
**Issue:** `evaluate_wiring()` computes `violations` and `cycles` for each named wiring (lines 359-360). Neither field is rendered anywhere in `render_markdown()`, and neither feeds the verdict. The verdict and `main()`'s exit code depend only on `failing_probes()`, so the "did not fire" text (which says "All three named wirings above compute without any self-declaration") is printed without checking it.

**Confirmed scenario:** Add `writes_artifact` to the w2 node's effects (a temp copy of `wirings/`, with `WIRINGS_DIR` and `EVIDENCE_PATH` retargeted). `evaluate_wiring("w2-codebase-memory-mcp").violations == ['effects-exceed-part']`, yet `main([])` returns 0. The document says "Falsifier 2 did not fire", and the violation code appears nowhere in the wiring sections.

**Second scenario:** Put a self-declared `effective_depth` on a named-wiring node. `parse_wiring` drops the node, and line 333 (`parsed.parts[node_id]`) raises a bare `KeyError: 'cbm'`. The run crashes with a traceback and does not report "Falsifier 2 fired". That is the exact self-declaration case this falsifier exists to catch.

**Fix:** Include the named wirings in the verdict and the exit code, and render their violations:
```python
def failing_wirings() -> tuple[str, ...]:
    failing = []
    for stem in NAMED_WIRINGS:
        parsed = parse_wiring(load_wiring(stem), probe_registry())
        if parsed.report.violations or set(parsed.node_order) != set(parsed.parts):
            failing.append(stem)
    return tuple(failing)

# render_markdown: render each wiring's violations; verdict "fired" when
# failing_probes() or failing_wirings(); evaluate_wiring skips nodes absent from parsed.parts
# main: return 1 if failing_probes() or failing_wirings() else 0
```

**Related:** C-WR-04 (the same `KeyError` as a D-03 breach).

## Warnings

### A-WR-01: Named client and vector-store refusals escape as tracebacks (`remint --spend`, `run_comparison --spend`, `aa_run --spend`); `UnresolvedJudgeIdentityError` is unreachable (merged with B-WR-05)

**File:** `databasise/cli.py:36-58` (`offline_refusals`); `databasise/eval/remint.py:84-86,128,156`; `databasise/parity/run_comparison.py:203-215,723-724,741`; `databasise/eval/aa_run.py:615-620`, `:631-651`
**Issue:** The shared D-03 refusal tuple omits named `RuntimeError` subclasses that its callers' callees raise.

Client refusals (lane A). `OpenAICompatibleClient.chat` (`clients/openai_compat.py:181-190,218-221`) raises its own named `RuntimeError` subclasses:
- `ModelIdentityMissingError` when the response has no `model`;
- `EmptyChoicesError`;
- `MissingCompletionContentError` when `content is None`, for example a reasoning model that runs out of tokens on the `"ping"` probe.

None of these classes is in `cli.offline_refusals()`, and neither CLI adds them. So:
- `remint --spend` pays for the probe call, then dies with a traceback instead of the D-03 single line.
- `remint.resolve_judge_identity`'s own `UnresolvedJudgeIdentityError` (line 85) cannot fire with the real client. `_resolved_identity` raises `ModelIdentityMissingError` first, inside `chat()`.
- In `run_comparison`, `_run_keywords_live` calls the part body directly, outside the scheduler, which would otherwise record the failure as a trace. The same errors therefore leave `asyncio.run(_run_cli(...))` (line 796) as a traceback. The records already collected for earlier queries are lost.

Vector-store refusal (lane B, formerly B-WR-05). `load_committed` raises `VectorStoreCorruptedError` (a `RuntimeError` subclass, `stores/vector.py:81`) for a half-written pair. That class is not in `aa_run._refusals()` or `cli.offline_refusals`. A `--spend` run on an interrupted ingest therefore crashes with a traceback from the index probe instead of the D-03 one-line `ClassName: message` and exit 1. `aa_run._refusals()` is built on `cli.offline_refusals` (`aa_run.py:634-637`, confirmed at merge), so the shared tuple is the fix point.

**Fix:** Add the client and store refusals to the shared tuple in `cli.offline_refusals`:
```python
from databasise.clients.openai_compat import (
    EmbeddingBatchMismatchError, EmptyChoicesError, MissingCompletionContentError, ModelIdentityMissingError,
)
from databasise.clients.rerank import RerankResponseError
from databasise.stores.vector import VectorStoreCorruptedError
...
return (*BUILDER_REFUSALS, ..., ModelIdentityMissingError, EmptyChoicesError,
        MissingCompletionContentError, EmbeddingBatchMismatchError, RerankResponseError,
        VectorStoreCorruptedError, *extra)
```
Then either delete `UnresolvedJudgeIdentityError` or catch `ModelIdentityMissingError` in `resolve_judge_identity` and re-raise it as `UnresolvedJudgeIdentityError`. For aa_run, an alternative is to catch `VectorStoreCorruptedError` in `_assert_eval_index_populated` and raise `EmptyEvalIndexError`, or a sibling class, naming the location.

**Related:** A-WR-09 (the same class escapes `import_index`, plus a try-placement defect), B-WR-06 (`JSONDecodeError` outside the tuple), C-WR-01 and C-WR-04 (evidence CLIs).

### A-WR-02: The v1 driver treats v1's status-less fail-response answer as a v1 exception (D-08 says exit 1 only on the exception path)

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

**Related:** A-IN-03 (the same empty-pin trigger silently unpins the comparison).

### A-WR-03: `V1ArmSubprocessError` keeps the head of stderr, so the D-08 named failure line is cut off

**File:** `databasise/parity/v1_arm.py:75`; `databasise/cli.py:29`
**Issue:** v1's logger writes INFO lines to stderr (`v1/lightrag/utils.py:90-98`, a `StreamHandler` at INFO). On the exception path `aquery_llm` also logs `Query failed: ...`. The driver prints `V1QueryFailedError: <msg>`, or a traceback, last.

`V1ArmSubprocessError` keeps `stderr.strip()[:2000]`, the start of stderr. `cli.refuse` then truncates the message to its first 500 characters. The one stderr line therefore normally shows only v1's start-up INFO lines, and never the `V1QueryFailedError:` line or the exception at the bottom of the traceback.

**Fix:** Keep the tail:
```python
tail = stderr.strip()[-2000:] or "(no stderr)"
super().__init__(f"v1 driver subprocess exited {returncode}: {tail}")
```
Better still, take the last line that does not start with `INFO:`/`WARNING:` as the message, and keep the full stderr on the `stderr` attribute. `cli.refuse`'s 500-character head cut has the same problem for any long message; consider cutting the middle instead.

### A-WR-04: `verify_import` and `import_index --verify` are read paths that write

**File:** `databasise/parity/import_index.py:639`, `:753`; `databasise/stores/kv.py:52-61`; `databasise/store_lock.py:58-60`
**Issue:** Two writes happen on the verify path:
- `verify_import` opens `SqliteKVStore(namespace="text_chunks", ...)` to read chunk text. Its `__init__` runs `mkdir(parents=True)`, `sqlite3.connect` (which creates `kv.sqlite3`), `PRAGMA journal_mode=WAL` and `CREATE TABLE IF NOT EXISTS`. So verifying a workspace that has no `text_chunks` namespace creates one, and verifying an existing one rewrites its journal mode. `run_comparison`'s preflight calls this on every query.
- `import_index --verify` takes `store_lock(store_root)`, which runs `root.mkdir(parents=True)` and writes `.engine.lock`. `--verify --store-root /typo` creates `/typo/.engine.lock`, then reports `refused: no imported v2 store`.

**Fix:**
- Read v1-side KV state through a read-only sqlite URI: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`. Treat a missing `kv.sqlite3` as "absent", which adds a `chunk-text` violation for every v1 chunk.
- For `--verify`, check `store_root.is_dir()` before locking and refuse by name if it is missing. Alternatively, give `store_lock` a `create=False` mode for read paths.

**Related:** B-WR-02 (the floor store's read path writes), C-WR-03.

### A-WR-05: `verify_import` passes vacuously when the v1 index is absent, now that `--v1-working-dir` is user-settable

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

### A-WR-06: A refused HippoRAG build stays in the store, and cross-modality preflight accepts it

**File:** `databasise/parity/build_hipporag_index.py:284-323`; `databasise/parity/run_cross_modality.py:268-271`
**Issue:** `build_index` commits the stores (`index_done_callback`, lines 284-285) before it verifies them. It then raises `ChunkCountMismatchError` or `HippoRAGIndexBuildRefusedError` for these cases: empty entities, empty facts, zero edges, no `entity:` vertex, or a chunk-count mismatch. The written namespaces stay on disk.

`run_cross_modality.preflight` checks only that `hipporag-chunks` is non-empty. A later `run_cross_modality --spend` therefore runs and records a comparison against an index its own builder refused. That defeats the "never report a build that has not been verified" rule this pair exists to enforce.

**Fix:** Do one of the following:
- write a verified marker, such as a `build.json` with the corpus hash, as the last step of a successful `build_index`, and have `preflight` require it;
- have `preflight` repeat the builder's checks (`hipporag-entities`, `hipporag-facts`, graph non-empty);
- build into a staging workspace and rename it only after verification passes.

### A-WR-07: `corpus_ingest --spend` (and `aa_run --spend`) write the eval store with no store lock

**File:** `databasise/eval/corpus_ingest.py:228-242`; `databasise/eval/aa_run.py` (no `store_lock` call anywhere, confirmed by grep at merge)
**Issue:** Every other spending CLI in this phase wraps its run in `store_lock(...)` (marked D-03). `corpus_ingest` builds a `Databasise` engine on `_EVAL_INGEST_STORE_ROOT` and ingests with no lock. The engine does not lock either: `seam/` never calls `store_lock`.

Two concurrent `corpus_ingest --spend` runs, or one running alongside `aa_run`, which reads the same root and writes `floors.db`, can interleave writes to `trace.db`, `jobs.db`, the Faiss namespaces and the v1 `lightrag-v1` working directory. Phase 10 G-36 and RUN-07 ("one engine process per store root") forbid this. `aa_run` has the same gap.

**Fix:**
```python
with store_lock(_EVAL_INGEST_STORE_ROOT):
    engine = Databasise(store_root=_EVAL_INGEST_STORE_ROOT, ...)
    jobs = asyncio.run(ingest_documents(engine, snapshot, limit=args.limit, arm=args.arm))
```
Also add `StoreLockedError` handling; it is already in `offline_refusals`. Apply the same fix to `aa_run`'s `--spend` path.

### A-WR-08: `run_arm` exits 0 for a cyclic or partial run (D-03 code 3 is never used)

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

### A-WR-09: Snapshot loads outside the refusal handler in `import_index` and `build_hipporag_index`; `import_index` catches only two classes

**File:** `databasise/parity/import_index.py:739-756`; `databasise/parity/build_hipporag_index.py:352-353,361`
**Issue:** In `import_index.main`:
- `_import_workspace()` and `load_snapshot()` (lines 741-742) run before the `try`;
- the `try` catches only `MissingV1IndexError` and `StoreLockedError`.

So these escape as tracebacks:
- a `CorpusDriftError` or `FileNotFoundError` from the snapshot;
- a `VectorStoreCorruptedError` from the import;
- the RocksDB "lock held" error from `_v1_graph`.

`build_hipporag_index.main` also calls `load_snapshot()` and `estimate()` at lines 352-353, before its `try`, so a drifted corpus crashes the estimate-only path with a traceback.

**Fix:** In both modules, move the snapshot/workspace lines inside the `try`. In `import_index`, use `except cli.offline_refusals(MissingV1IndexError, VectorStoreCorruptedError) as exc: return cli.refuse(exc)` so it matches the other CLIs (the explicit `VectorStoreCorruptedError` becomes redundant once A-WR-01 adds it to the shared tuple).

**Related:** A-WR-01.

### A-WR-10: `run_comparison` overwrites `<arm>.json` with a truncated run that carries no refusal marker

**File:** `databasise/parity/run_comparison.py:741-745,802-811`
**Issue:** If a refusal hits query k (k > 1), `_run_cli` breaks the loop. `main` then writes the k-1 completed records to `.comparison_results/<arm>.json`, replacing the previous full result, and exits 1.

Every record in the file has `"status": "completed"`, and nothing records that the run stopped early. A later reader of the JSON, such as an evidence render, sees a clean but shorter comparison. `run_cross_modality` marks the same case with `"status": "refused"`, `reason` and `query_id`. This module does not.

**Fix:** When `had_error` is set, write a wrapper object, for example `{"status": "refused", "reason": <refusal line>, "records": [...]}`, or write to `<arm>.refused.json`. Never overwrite the last complete result with an unmarked partial one.

### B-WR-01: A repeated `--family` doubles the real spend, but the estimate shows it once

**File:** `databasise/eval/aa_run.py:716`, `databasise/eval/aa_run.py:655-662`, `databasise/eval/aa_run.py:590-598`
**Issue:** `families = tuple(args.family)` does not remove duplicates.
- `estimate_calls` keys `per_family` by name, so a duplicate collapses. Running `main(['--family','answer_level','--family','answer_level'])` prints `engine_queries: 34, judge_calls: 34`.
- `_calibrate_all` loops over the tuple and runs `calibrate_family` once per entry. A `--spend` run therefore makes 68 engine queries and 68 judge calls, then keeps the last result.

The D-04 estimate is the operator's only spend projection, and here it is half the real spend.
**Fix:** `families = tuple(dict.fromkeys(args.family)) if args.family else _DEFAULT_FAMILIES`, or reject duplicates with `parser.error(...)` so the run exits 2.

### B-WR-02: The floor store's "read-only" path creates `floors.db-shm` and `floors.db-wal`, and it reads every OperationalError as "no floor"

**File:** `databasise/seam/floors_store.py:9-11`, `databasise/seam/floors_store.py:64-87`
**Issue:** `record()` puts the file in WAL mode. On a WAL database, a `mode=ro` connection creates the `-shm` and `-wal` side files when they are absent, and a read-only close does not remove them. Reproduced in the scratchpad: after `record()` the directory held `['floors.db']`. After one `any_floor()` it held `['floors.db', 'floors.db-shm', 'floors.db-wal']`. Every gate-verb `promote` on the eval store root therefore writes two files, which contradicts the docstrings: "create nothing" and "a refused gate verb leaves the store root untouched".

The bare `except sqlite3.OperationalError` also hides real faults: "unable to open database file" (reproduced with a read-only directory and no `-shm`), "database is locked", and "disk I/O error". With a valid floor on disk, `any_floor()` then returns `False` and the gate reports `GateNotCalibratedError`.
**Fix:**
- Open the read paths with `?mode=ro&immutable=1` when no writer is active, or use the `stores/probes.py` pattern (Phase 10 D-14) that `/health` already uses.
- Catch only the missing-table case:
```python
except sqlite3.OperationalError as exc:
    if "no such table" not in str(exc):
        raise
    return False
```

**Related:** A-WR-04.

### B-WR-03: Persisting the floors runs before the results are printed, so a refusal or I/O error at that step loses a run that has already spent

**File:** `databasise/eval/aa_run.py:759-772`, `databasise/eval/aa_run.py:668-698`
**Issue:** `_persist_floors(results_by_family)` runs inside the `try`, after both passes for every family have spent. The `AARunResult` JSON prints only after it succeeds.
- An `UnkeyableFloorError` exits 1 and prints only the refusal, so the computed floors and per-family results are discarded.
- A `sqlite3.OperationalError` or `PermissionError` from `FloorStore.record` is not in `_refusals()`. It escapes as a traceback (a D-03 breach), and if it hits on the second family, the first family's row is already written. That breaks the docstring's "a refusal persists nothing".
**Fix:**
- Print the `AARunResult` to stdout before persisting.
- Write all rows in one transaction: add a `FloorStore.record_many(rows)` that does one `with conn:` around every INSERT.
- Map `sqlite3.Error` and `OSError` on this step to a named refusal.

### B-WR-04: Every real `--spend` run pays for both full passes before the certain cache-bypass refusal

**File:** `databasise/eval/aa_run.py:515-560`, `databasise/eval/calibration.py:274-282`
**Issue:** The module docstring and D-13 both record that no production part reports `cache_hit`. Every real run therefore ends in `UnusableFloorError`. `_verify_cache_bypassed` runs only inside `calibrate_aa_floor`, after `run_a` and `run_b` have both run. With the current registry, every `--spend` run makes 2 × N engine queries, plus 2 × N judge calls for `answer_level`, and is then refused. Knowing the outcome in advance does not justify paying for it.
**Fix:** Check the bypass precondition on `run_a.node_traces` right after `run_a`, before `run_b` starts. Better, check it after the first question of `run_a`. Reuse `_verify_cache_bypassed(run_a.node_traces, ())` so the refusal text stays the same.

**Related:** B-IN-03.

### B-WR-05: merged into A-WR-01

`VectorStoreCorruptedError` from the aa_run index probe escapes as a traceback. The finding text and fix are in A-WR-01.

### B-WR-06: `load_bundle` now parses the usage log, so one bad line breaks every load, the dry run and minting included

**File:** `databasise/eval/bundle.py:481`, `databasise/eval/bundle.py:501-506`
**Issue:** `load_bundle` now calls `_load_usage_entries`, which runs `json.loads` on every line of `usage.jsonl`. A truncated append from `_append_usage_entry` (a crash or a full disk mid-write) raises `json.JSONDecodeError` on every later `load_bundle` for that version. That includes:
- the aa_run estimate path, which escapes as a traceback because `JSONDecodeError` is a bare `ValueError` and so outside `_refusals()`;
- `mint_bundle` through `_find_version_by_content_hash`, so remint is also blocked.

The usage log is not covered by `bundle.sha256`, so this file can fail where the checksummed body cannot.
**Fix:** In `load_bundle`, scan for the sealed-open kind with a tolerant reader (skip blank lines, raise a named `CorruptUsageLogError` that the CLIs map to exit 1). Alternatively, compute `sealed_opened` only in the callers that need it.

### B-WR-07: `sealed_opened` is computed but never read, so an opened version is still handed back and used as if sealed

**File:** `databasise/eval/bundle.py:35-38`, `databasise/eval/bundle.py:162-163`, `databasise/eval/bundle.py:420-422`, `databasise/eval/bundle.py:552-554`
**Issue:**
- After `open_sealed`, both the source and the copy log `sealed_open`. The copy recomputes to the same content hash, and `_find_version_by_content_hash` walks versions in ascending order. A remint with unchanged inputs therefore returns the opened source version.
- The module docstring says this means `mint_bundle` "never hands back an opened version as if unopened". The only change, though, is a boolean nobody reads: a grep finds no consumer of `sealed_opened` outside `bundle.py`, and `remint.main` prints only `version` and `judge_instance`.
- `open_sealed` also mints a new max version, which makes every persisted floor stale. The engine's stage 2 requires `bundle@v{max(versions)}`, even though the content is identical.

The RIG §EV.1 rule that a touched partition is no longer sealed is still not enforced.
**Fix:** In `mint_bundle`, skip versions with `sealed_opened` during dedup (mint fresh), or refuse by name. Report the flag in remint's output. State in API-INVENTORY that `open_sealed` invalidates every floor.

### B-WR-08: API-INVENTORY rows edited or made false by this phase still describe the pre-phase behaviour

**File:** `docs/gui/API-INVENTORY.md:654`, `:736`, `:836`, `:866`, `:867`, `:868`, `:869`
**Issue:** These rows contradict the phase-15 code:
- **:867 (aa_run):** says "aa_run queries ... v2 namespaces that `corpus_ingest`'s LightRAG arm never writes, so every score is 0". That is no longer true: `wirings/lightrag/corpus-ingest.json:18` runs `lightrag/v1-index-sync`, and `corpus_ingest.py`'s new comment lists the v2 namespaces. The row also says "Several named errors escape as tracebacks (`FileNotFoundError` ..., `BundleDriftError`, `KeyError` on `document_id`)". All three are now mapped: `cli.offline_refusals` covers the first two, and `GoldPassageMappingError` replaces the `KeyError`.
- **:868 (remint):** "Spends on every run; no `--spend` gate". remint now has `--spend` and a dry run.
- **:736:** "`eval.remint` and `parity.build_hipporag_index` (both spend with no flag)". Both are now gated.
- **:869 (bundle):** "logs the opening only there ... apparently unopened version. The content hash omits question text and gold document ids". All of this is fixed by TOOL-13 (D-14).
- **:866 (corpus_ingest):** "documents land in the shared `v1/.corpus_working_dir`". This contradicts `corpus_ingest.py`'s new comment ("Nothing is written to `v1/.corpus_working_dir`") and D-12.
- **:836:** "no module in `databasise/seam/` ... imports `databasise.parity`, `databasise.eval`". `engine._refuse_gate_verb` now imports `databasise.eval.aa_run`, `eval.bundle`, `eval.calibration` and `eval.remint`, and remint imports `parity.run_arm`. The same row says `databasise.tools` and `evidence/eval-bundles/**` are not packaged. pyproject now ships both (TOOL-01).
- **:654:** "registers nine tools ... Seven of nine tools publish an empty description". D-18 fixes the count at ten and gives every tool a description.

A GUI built from this document would hide working CLIs and warn about defects that are fixed.
**Fix:** Rewrite these rows against the current code, and remove the claims the phase discharged.

**Related:** C-WR-05 and C-WR-06 (stale rows in CODEBASE-MAP.md, the other Phase 16 GUI input).

### C-WR-01: parity_report.main lets four failure classes escape as tracebacks and can write one of its two documents only

**File:** `databasise/evidence/parity_report.py:1688-1700`, `:1722-1730`; raise sites `:115-125`, `:824-834`, `:868-874`, `:1212`, `:1290`, `:992`
**Issue:** `main()` maps only `ParityRecordFormatError` to `refuse()`. The class docstring promises "a caller never sees `JSONDecodeError` or `KeyError`". A probe against temp copies of `parity_results/` shows these escaping instead:
- a comparison record missing `status` raises `KeyError: 'status'` (line 1212, `record['status']`). `check_results` reports this as a violation, but the render path does not run that check;
- a missing `<arm>-comparison.json` raises a raw `FileNotFoundError`. This is the normal case from an installed wheel, because `parity_results/` and `human_findings.json` are not package data;
- an orphan `declared_causes` entry raises `OrphanDeviationCauseError` (a `ValueError`, not mapped);
- a `judgment` outside the allowed set raises `InvalidJudgmentError`.

`notes: null` in a spot-check raises `AttributeError` at line 992 (`_escape_cell(None)`).

The `InvalidJudgmentError` case also shows a partial write. `DECLARED-DEVIATIONS.md` is written at line 1724, then `render_markdown()` raises, so `PARITY-EVIDENCE.md` is left stale beside a freshly written deviations file.
**Fix:** Render both texts before writing either. Map the module's named refusals through `refuse`. Run `check_results()` first and refuse on violations:
```python
def _run(args):
    ...
    violations = check_results()
    if violations:
        raise ParityRecordFormatError("; ".join(map(str, violations)))
    deviations_text = render_deviations_document(_collect_deviations())
    evidence_text = render_markdown()
    DEVIATIONS_PATH.write_text(deviations_text, encoding="utf-8")
    EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")
...
except (ParityRecordFormatError, UnreasonedDeviationError, InvalidJudgmentError, FileNotFoundError) as exc:
    return refuse(exc)
```
Also coerce `raw.get("notes") or ""`.

**Related:** C-WR-04, A-WR-01.

### C-WR-02: parity_report's inconclusive and mixed prose states a cause it never reads, which D-07 has made false

**File:** `databasise/evidence/parity_report.py:543-554`, `:1097-1103`, `:1115-1128`, `:1376-1395`, `:1598-1611`, `:225-231`
**Issue:** D-07 (15-06) changed `run_comparison`. A partial, degraded or cyclic decomposed run is now written as `status="inconclusive"` with `decomposed_run_record` populated (`parity/run_comparison.py:611-618`). The renderer was not updated for this, and still asserts precondition causes it never reads:
- the all-inconclusive branch says `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store` and `v1/.env.parity` "are all absent" (1116-1127);
- the storage-audit branch says the audits hit `MissingParityEnvError` (1390-1394);
- the verdict says every arm "reports an environment-precondition refusal" (1601-1604);
- the mixed branch says each inconclusive record "stopped at a precondition" (1099-1101).

Meanwhile `_arm_degraded()` (225-231) inspects only `completed` records. Its "Degraded run — read the zero diffs" disclosure therefore cannot fire for a fresh run.

**Scenario:** The owner re-runs the arms with `--spend`, and hybrid, local and global degrade (as the committed 2026-09 runs did). The rendered PARITY-EVIDENCE.md then blames missing env files and preconditions that were present. This breaks D-16 ("render only states they read").
**Fix:** Derive the cause per record from `inconclusive_reason` and `decomposed_run_record`, and render it. Delete the fixed precondition text. In `_arm_degraded`, treat an `inconclusive` record whose `decomposed_run_record.degraded` is true as degraded.

### C-WR-03: Evidence CLIs write into the package directory by default, and a wheel install writes into site-packages

**File:** `databasise/evidence/f07_report.py:324-331`, `databasise/evidence/falsifier2.py:597-604`, `databasise/evidence/parity_report.py:1722-1727`
**Issue:** The phase boundary says the offline CLIs never "write outside their own store, by default". All three renderers overwrite a committed document beside `__file__` on every bare run, with no flag and no dry run. From a wheel (`databasise.evidence` ships), `python -m databasise.evidence.f07_report` rewrites `site-packages/databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`. A root-owned install instead fails with a `PermissionError` traceback.

`f07_report.main()` is new in this phase, and it writes on a bare run while `parity_report` at least offers `--check-results`.
**Fix:** Make the bare run print to stdout only, and write only with an explicit `--write` (or refuse to write when `Path(__file__)` resolves under `site-packages`). Map `OSError` and the renderers' `ValueError`s through `databasise.cli.refuse`.

**Related:** A-IN-02 and A-IN-04 (the same read-only-install failure in `remint` and `run_cross_modality`), A-WR-04, B-WR-02.

### C-WR-04: The evidence renderers' named refusals escape as tracebacks (D-03)

**File:** `databasise/evidence/f07_report.py:160-166`, `:324-331`; `databasise/evidence/falsifier2.py:333`, `:411-415`, `:597-604`
**Issue:** These modules gained argparse and an int `main()` this phase, so they are treated as D-03 CLIs. None of them calls `refuse`:
- `f07_report`: a registry part declaring `mutates_store` without a `_KNOWN_REASONS` entry raises a bare `ValueError` traceback. D-16 names this case: rendering from `probe_registry()` raises.
- `falsifier2`: a malformed `boundary_knobs` entry (`ValueError`) and the `KeyError` from C-CR-01 escape the same way.
**Fix:** Give each one a named refusal class (for example `UnreasonedMutableStoreError(ValueError)`) and wrap `main()` in `try: ... except (<named>, FileNotFoundError) as exc: return refuse(exc)`.

**Related:** C-CR-01, C-WR-01, A-WR-01.

### C-WR-05: CODEBASE-MAP's new launch command uses an interpreter without the project's dependencies

**File:** `docs/gui/CODEBASE-MAP.md:431`
**Issue:** The line changed from `cd databasise && uv run python -m <module>` to "`uv run python -m <module>` from the repository root". The repository root has no `pyproject.toml` and no `.venv`, so uv runs outside any project.

Verified from the repo root: `uv run --offline python -c ...` resolves `~/.local/share/uv/python/cpython-3.13-.../python3.13` (uv warns "`--no-sync` has no effect when used outside of a project"), and `import pycozo` raises `ModuleNotFoundError`. A console author who follows the map gets an import failure from every CLI.
**Fix:** Use `uv run --project databasise python -m databasise.<module>` (or `databasise/.venv/bin/python -m databasise.<module>`) and state the `databasise.` prefix explicitly.

**Related:** B-WR-08.

### C-WR-06: CODEBASE-MAP still lists f07_report as library-only after it became a file-writing CLI

**File:** `docs/gui/CODEBASE-MAP.md:451` (also `:202`)
**Issue:** This phase gave `evidence.f07_report` a `main()` and an `if __name__ == "__main__"` that overwrites `F-07-MUTABLE-STORE-DISPOSITION.md` (`f07_report.py:324-344`). The surfaces table still says "`evidence.f07_report` | Library only | Ignore", so an operator console wrapping CLIs would not know it writes a committed file. The same table line was edited this phase, but the f07 entry was not updated.
**Fix:** Change the row to "`evidence.f07_report` | CLI, overwrites a committed file, exit 0 | Ignore", and fix line 202 to match.

**Related:** C-WR-03, B-WR-08.

## Info

### A-IN-01: The cross-modality estimate overstates the LightRAG arm

**File:** `databasise/parity/run_cross_modality.py:446-447`; `databasise/parity/run_arm.py:146-165,276-287`
**Issue:** `estimate_arm("naive", ...)` goes through `resolve_query_arm`, which keeps LightRAG's recipe-only `embedder-index`. The estimate therefore prints `nodes: 7, calls_embedding: 2` (observed). `run_cross_modality` runs through `engine.compare`, whose query path drops recipe-only nodes (`without_recipe_only_nodes`, LRAG-19), so the real run makes 6 nodes and 1 embedding call. The figure is correct for `run_arm` and `storage_audit` but not for this CLI.
**Fix:** In `_print_estimate`, compute the LightRAG estimate on `without_recipe_only_nodes(resolve_arm(...))`, or label the figure an upper bound.

### A-IN-02: `remint --spend` from a wheel spends the probe call before discovering the bundle root is not writable

**File:** `databasise/eval/remint.py:132-133,153-166`
**Issue:** The pre-check confirms only that `_COMMITTED_BUNDLE_ROOT.is_dir()`. In a read-only install (a system or Nix site-packages), `_write_version`'s `mkdir` raises `PermissionError`, which is not in the refusal tuple. This happens after the paid chat call and prints a traceback. The docstring says minting needs a source checkout, but the code does not enforce that.
**Fix:** Before building clients, check `os.access(_COMMITTED_BUNDLE_ROOT, os.W_OK)` and refuse by name. Related: A-IN-04, C-WR-03.

### A-IN-03: Empty pinned keywords silently unpin the v1 arm

**File:** `databasise/parity/run_comparison.py:595-599,632-641`; `databasise/parity/v1_driver_script.py:133`
**Issue:** v1 short-circuits only when `hl_keywords or ll_keywords` is truthy (`operate.py:4027`). When the live pin call returns two empty lists, the decomposed arm runs pinned-empty while v1 extracts its own keywords. The record still says `pinned_keywords: {[], []}`. This can be detected through `hl_keywords_used`, but the comparison is no longer pinned.
**Fix:** Treat an empty pin pair as `inconclusive` ("pin produced no keywords"), or record `pin_reached_v1: false` when v1's echoed keywords differ from the pin. Related: A-WR-02.

### A-IN-04: `_write_result` inside the refusal handler can raise and mask the refusal

**File:** `databasise/parity/run_cross_modality.py:482-492`
**Issue:** `_write_result` runs `mkdir` and `write_text` inside the `except` block. An `OSError` there, such as a read-only site-packages (see 15-CONTEXT Specifics), replaces the one-line refusal with a chained traceback.
**Fix:** Wrap the write in `try/except OSError` and print one extra stderr line naming the failed write, then still `return cli.refuse(exc)`. Related: A-IN-02, C-WR-03.

### B-IN-01: The seam's promote path imports the aa_run CLI module to read two string constants

**File:** `databasise/seam/engine.py:2354-2357`
**Issue:** The gate path pulls in `databasise.eval.aa_run` (which imports `databasise.cli`, `parity.run_arm`, `eval.corpus_ingest` and `default_registry`) and `databasise.eval.remint`. It needs only `ANSWER_LEVEL_METRIC`, `GOLD_PASSAGE_METRIC` and `_COMMITTED_BUNDLE_ROOT`. This creates a seam → eval → seam lazy cycle and adds a REST dependency on CLI modules.
**Fix:** Move the two metric names and the bundle-root path into `eval/bundle.py` (or `eval/calibration.py`), and import them from there in both the engine and aa_run. Related: B-WR-08 (`:836` row).

### B-IN-02: The stage-2 gate does synchronous sqlite and filesystem I/O on the event loop

**File:** `databasise/seam/engine.py:2339-2407`, called at `:2474`
**Issue:** `_refuse_gate_verb` opens `ledger.db`, opens `floors.db` once per instance hash, lists the bundle directory, and does the first-time imports, all on the loop thread inside the async `promote`. The rest of `promote` deliberately offloads to `run_in_executor`. This is the "Synchronous I/O in Async Code" anti-pattern named in CLAUDE.md.
**Fix:** Run `_refuse_gate_verb` through `run_in_executor`, as `_promote_sync` already is.

### B-IN-03: The index probe runs only after the env file is read and the eval store is created

**File:** `databasise/eval/aa_run.py:733-748`, `databasise/eval/aa_run.py:515`
**Issue:** `_load_env_file`, `_build_clients` and `Databasise(...)` all run before `calibrate_family` calls `index_probe()`. `TraceStore.__init__` (`seam/trace_store.py:59-66`) runs `mkdir`, creates `trace.db` and switches it to WAL. A `--spend` run refused for an empty index has therefore loaded the secrets file and created `v1/.eval_corpus_store/trace.db` for nothing.
**Fix:** Call `_eval_index_probe(args.arm)()` right after `check_named_arm`, before `_load_env_file`. Related: B-WR-04.

### B-IN-04: Refusal docstrings describe the pre-TOOL-12 gate

**File:** `databasise/seam/refusals.py:600-612`, `databasise/seam/refusals.py:615-620`, `databasise/seam/promotion.py:264-275`
**Issue:**
- `GateVerbNotBuiltError` says it is "Refused immediately, before any trace resolution". It is now also raised in stage 2 for `promote-next` and `promote-now`, after trace resolution.
- `GateNotCalibratedError` says `UncalibratedFloorRefusalError` "stay[s] for that path". The engine raises `GateVerbNotBuiltError` there instead.
- `enforce_gate_verb_posture` has no production caller.
**Fix:** Update both docstrings. Delete `enforce_gate_verb_posture` and its `UncalibratedFloorRefusalError` branch, or mark them test-only.

### B-IN-05: The engine still hardcodes the executor version

**File:** `databasise/seam/engine.py:434`, `:2148`; also `databasise/parity/run_arm.py:81`
**Issue:** `_EXECUTOR_VERSION = "databasise@0.1.0"` is written into every seam run record. D-01 makes `databasise.__version__` the one version source, and `rest.py:672` and `__init__.py:118` already read it. After a version bump, seam traces will record a stale executor version.
**Fix:** `_EXECUTOR_VERSION = f"databasise@{__version__}"`. Do the same in `parity/run_arm.py:81`.

### B-IN-06: The condition-10 refusal message misstates an inferred scope

**File:** `databasise/parts/admission.py:251-257`
**Issue:** `scope` is now inferred as `"shared"` when `artifact_scope` is `None` and the part declares `writes_artifact`. The message still says "declares artifact_scope='shared'", which names a declaration that does not exist.
**Fix:** Branch the message: "declares no artifact_scope while writing artifacts, which reads as shared (validator/blast_radius.py)".

### B-IN-07: Admission at load skips declaration-only opaque parts with no record, and never validates their records

**File:** `databasise/parts/admission.py:209-220`, `databasise/parts/registry.py:208-211`
**Issue:**
- `admit_registry` skips any opaque part whose `admission is None`.
- `register` runs `validate_admission` only when `body is not None`.

A declaration-only opaque part can therefore be registered with no record, or with a record naming a different part (the D-17 name-match check never runs). D-17 says the check covers "every opaque part". The impact is low because a declaration-only part cannot dispatch.
**Fix:** Run `validate_admission` for every opaque part that carries a record, and decide explicitly whether a declaration-only opaque part needs one.

### C-IN-01: The codebase-memory-mcp admission evidence now describes a tool its adapter refuses

**File:** `databasise/parts_core/codebase_memory_mcp.py:145-152`, `:238-246`; `databasise/foreign/codebase_memory_mcp_adapter.py:97-100`, `:309-310`
**Issue:** `wall_clock_ceiling_basis` is measured on `index_repository` "through the adapter", and condition 6 cites calling `index_repository` "directly". `call_tool` now refuses `index_repository`, so the part cannot reproduce its own ceiling measurement or build an index. Every read tool depends on an index built outside the adapter. D-17 and LRAG-12 forbid rewording these strings, and D-19 keeps `mutates_store`, so this is a recorded limit rather than a defect.
**Fix:** Record the limit in ADMISSION-CODEBASE-MEMORY-MCP.md (the evidence strings stay unchanged).

### C-IN-02: The lazy `functools.cache` builders are not synchronised

**File:** `databasise/parts_core/declared_only.py:74-91`; `databasise/parts_core/codebase_memory_mcp.py:87-94`, `:309`
**Issue:** `functools.cache` does not lock. Two threads touching `CODEBASE_MEMORY_MCP_PART` for the first time at once can each build a `Part` (and hash the 293 MB binary twice). That breaks the "same object every time" property the comment says `test_admission.py` relies on.
**Fix:** Guard the builders with a module `threading.Lock`, or accept the race and note it.

### C-IN-03: The f07 verdict renders "()" when no part declares mutates_store, and its empty-table guard is unreachable

**File:** `databasise/evidence/f07_report.py:193-201`, `:266`
**Issue:** `all_rows` always includes `_CATALOGUED_NOT_BUILT`, so the `if not all_rows` refusal never fires. With zero live rows, the new `registered` string is empty, and the verdict reads "every registered mutable-store component this project has built () and ...".
**Fix:** Check `if not live_rows` (or render "none registered").

### C-IN-04: The import-boundary scan misses some dynamic forms, and relative imports can be false positives

**File:** `databasise/tools/check_import_boundary.py:104-113`, `:132-148`
**Issue:**
- `import importlib as il; il.import_module("lightrag")` is not detected, and neither is `importlib.import_module(name="lightrag")`;
- `ImportFrom.level` is ignored, so a legitimate `from .lightrag import x` inside `parts_core/` (a real subpackage) would be flagged as a v1 import.
**Fix:** Track `import importlib as X` aliases, read the `name=` keyword, and skip `ImportFrom` nodes with `level > 0`.

### C-IN-05: The adapter's exception handler converts interrupts into transport faults and has a dead branch

**File:** `databasise/foreign/codebase_memory_mcp_adapter.py:268-283`
**Issue:**
- `except BaseException` turns `KeyboardInterrupt`, `SystemExit` and an outer `CancelledError` into `CbmTransportError`;
- `except ForeignEngineUnavailableError: raise` is unreachable, because `_resolve_binary` runs before the `try`;
- `_unwrap` takes only the first leaf of an exception group, so a group of `[Cancelled, CbmToolCallError]` is reported as a transport fault.
**Fix:** Catch `Exception` and re-raise `BaseException` subclasses as they are. Search the group for a `CbmToolCallError` or `UntypedForeignItemError` leaf instead of taking `exceptions[0]`.

### C-IN-06: The `databasise.mcp` docstring contradicts how the SDK is actually imported

**File:** `databasise/mcp/__init__.py:7-13`
**Issue:** The docstring says every import is an absolute `from mcp.server.mcpserver import MCPServer`. `server.py:92-93` deliberately resolves the SDK through `import_sdk`, because the bare form self-shadows. The docstring's first lines were edited this phase, but this paragraph was not.
**Fix:** Say that the SDK resolves through `databasise.mcp._sdk.import_sdk`.

### C-IN-07: The normalised cbm records carry raw engine output and internal citations, and `derived_from` is stored twice

**File:** `databasise/foreign/codebase_memory_mcp_adapter.py:373-391`
**Issue:**
- each record keeps `raw` (engine file paths, project names), `tool_name`, and a `tier_reason` that cites "PARTS.md ## §X". None of these may reach a §18 consumer field. The part is unregistered today, so nothing leaks yet;
- `derived_from` now lives both inside the tagged `kind` payload and at the top level, two copies that can diverge.
**Fix:** Keep only the tagged payload copy. Before the part is ever wired, document that the seam must redact `raw`, `tool_name` and `tier_reason`.

### C-IN-08: The provenance check is skipped silently with exit 0 in a source checkout that lacks v1/

**File:** `databasise/tools/check_import_boundary.py:226-230`
**Issue:** The wheel heuristic `(repo_root / "v1").is_dir()` also fires in a source checkout where `v1/` is missing or renamed. The provenance check is then skipped with only a stderr note, and the exit code stays 0, even though every `upstream_ref` in that checkout fails to resolve.
**Fix:** Decide "installed" by `"site-packages" in package_root.parts`, and treat a missing `v1/` in a source tree as a provenance violation.

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
