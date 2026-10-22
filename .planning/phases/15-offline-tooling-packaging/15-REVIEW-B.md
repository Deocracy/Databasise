---
phase: 15-offline-tooling-packaging
reviewed: 2026-10-21T00:00:00Z
depth: deep
files_reviewed: 13
files_reviewed_list:
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
findings:
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 15: Code Review Report (Lane B)

**Reviewed:** 2026-10-21
**Depth:** deep (diff 00eeae8..HEAD, with the call chains traced into cli.py, clients/builder.py, ledger/ledger.py, seam/selectors.py, stores/vector.py, seam/trace_store.py, wirings/resolve.py and eval/remint.py)
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This lane covers the TOOL-12 floor store and the two-stage gate, the aa_run CLI contract, the calibration changes, the bundle hash and sealed-open changes, admission at load, and the API inventory.

Checks that came back clean:
- No path spends without `--spend`. The aa_run dry run builds no client, opens no store and writes nothing. This was confirmed by running `main([...])` without `--spend`.
- No §18 leak: the new seam refusals carry only `verb` and `mutation_class`.
- No env-file contents are printed. Builder refusals withhold values.
- The stage-1 gate path creates no `ledger.db`. `Ledger.open_existing(read_only=True)` creates nothing when the file is absent.
- `run_wiring` now canonicalises before it dispatches anything.

Defects found:
- The new judge-verdict parser scores a negated verdict as CORRECT.
- The estimate under-reports spend when `--family` is repeated.
- The floor store's read path creates `-shm`/`-wal` files, although its docstring says it creates nothing.
- Some refusals still escape as tracebacks.
- A spent run loses its results when persisting fails.
- The new `sealed_opened` flag is never read.
- Several API-INVENTORY rows that this phase touched or made false are stale.

Plain pytest on the test tree was blocked by the check-guard hook in this session. No test results are claimed here. Every finding below was verified by reading the source. Where noted, it was also confirmed by running code in the scratchpad.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The judge verdict parser takes the first verdict word anywhere, so "not correct" scores 1.0

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

## Warnings

### WR-01: A repeated `--family` doubles the real spend, but the estimate shows it once

**File:** `databasise/eval/aa_run.py:716`, `databasise/eval/aa_run.py:655-662`, `databasise/eval/aa_run.py:590-598`
**Issue:** `families = tuple(args.family)` does not remove duplicates.
- `estimate_calls` keys `per_family` by name, so a duplicate collapses. Running `main(['--family','answer_level','--family','answer_level'])` prints `engine_queries: 34, judge_calls: 34`.
- `_calibrate_all` loops over the tuple and runs `calibrate_family` once per entry. A `--spend` run therefore makes 68 engine queries and 68 judge calls, then keeps the last result.

The D-04 estimate is the operator's only spend projection, and here it is half the real spend.
**Fix:** `families = tuple(dict.fromkeys(args.family)) if args.family else _DEFAULT_FAMILIES`, or reject duplicates with `parser.error(...)` so the run exits 2.

### WR-02: The floor store's "read-only" path creates `floors.db-shm` and `floors.db-wal`, and it reads every OperationalError as "no floor"

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

### WR-03: Persisting the floors runs before the results are printed, so a refusal or I/O error at that step loses a run that has already spent

**File:** `databasise/eval/aa_run.py:759-772`, `databasise/eval/aa_run.py:668-698`
**Issue:** `_persist_floors(results_by_family)` runs inside the `try`, after both passes for every family have spent. The `AARunResult` JSON prints only after it succeeds.
- An `UnkeyableFloorError` exits 1 and prints only the refusal, so the computed floors and per-family results are discarded.
- A `sqlite3.OperationalError` or `PermissionError` from `FloorStore.record` is not in `_refusals()`. It escapes as a traceback (a D-03 breach), and if it hits on the second family, the first family's row is already written. That breaks the docstring's "a refusal persists nothing".
**Fix:**
- Print the `AARunResult` to stdout before persisting.
- Write all rows in one transaction: add a `FloorStore.record_many(rows)` that does one `with conn:` around every INSERT.
- Map `sqlite3.Error` and `OSError` on this step to a named refusal.

### WR-04: Every real `--spend` run pays for both full passes before the certain cache-bypass refusal

**File:** `databasise/eval/aa_run.py:515-560`, `databasise/eval/calibration.py:274-282`
**Issue:** The module docstring and D-13 both record that no production part reports `cache_hit`. Every real run therefore ends in `UnusableFloorError`. `_verify_cache_bypassed` runs only inside `calibrate_aa_floor`, after `run_a` and `run_b` have both run. With the current registry, every `--spend` run makes 2 × N engine queries, plus 2 × N judge calls for `answer_level`, and is then refused. Knowing the outcome in advance does not justify paying for it.
**Fix:** Check the bypass precondition on `run_a.node_traces` right after `run_a`, before `run_b` starts. Better, check it after the first question of `run_a`. Reuse `_verify_cache_bypassed(run_a.node_traces, ())` so the refusal text stays the same.

### WR-05: A corrupt eval index escapes the index probe as a traceback

**File:** `databasise/eval/aa_run.py:615-620`, `databasise/eval/aa_run.py:631-651`
**Issue:** `load_committed` raises `VectorStoreCorruptedError` (a `RuntimeError` subclass, `stores/vector.py:81`) for a half-written pair. That class is not in `_refusals()` or `cli.offline_refusals`. A `--spend` run on an interrupted ingest therefore crashes with a traceback instead of the D-03 one-line `ClassName: message` and exit 1.
**Fix:** Add `VectorStoreCorruptedError` to `_refusals()`, or catch it in `_assert_eval_index_populated` and raise `EmptyEvalIndexError`, or a sibling class, naming the location.

### WR-06: `load_bundle` now parses the usage log, so one bad line breaks every load, the dry run and minting included

**File:** `databasise/eval/bundle.py:481`, `databasise/eval/bundle.py:501-506`
**Issue:** `load_bundle` now calls `_load_usage_entries`, which runs `json.loads` on every line of `usage.jsonl`. A truncated append from `_append_usage_entry` (a crash or a full disk mid-write) raises `json.JSONDecodeError` on every later `load_bundle` for that version. That includes:
- the aa_run estimate path, which escapes as a traceback because `JSONDecodeError` is a bare `ValueError` and so outside `_refusals()`;
- `mint_bundle` through `_find_version_by_content_hash`, so remint is also blocked.

The usage log is not covered by `bundle.sha256`, so this file can fail where the checksummed body cannot.
**Fix:** In `load_bundle`, scan for the sealed-open kind with a tolerant reader (skip blank lines, raise a named `CorruptUsageLogError` that the CLIs map to exit 1). Alternatively, compute `sealed_opened` only in the callers that need it.

### WR-07: `sealed_opened` is computed but never read, so an opened version is still handed back and used as if sealed

**File:** `databasise/eval/bundle.py:35-38`, `databasise/eval/bundle.py:162-163`, `databasise/eval/bundle.py:420-422`, `databasise/eval/bundle.py:552-554`
**Issue:**
- After `open_sealed`, both the source and the copy log `sealed_open`. The copy recomputes to the same content hash, and `_find_version_by_content_hash` walks versions in ascending order. A remint with unchanged inputs therefore returns the opened source version.
- The module docstring says this means `mint_bundle` "never hands back an opened version as if unopened". The only change, though, is a boolean nobody reads: a grep finds no consumer of `sealed_opened` outside `bundle.py`, and `remint.main` prints only `version` and `judge_instance`.
- `open_sealed` also mints a new max version, which makes every persisted floor stale. The engine's stage 2 requires `bundle@v{max(versions)}`, even though the content is identical.

The RIG §EV.1 rule that a touched partition is no longer sealed is still not enforced.
**Fix:** In `mint_bundle`, skip versions with `sealed_opened` during dedup (mint fresh), or refuse by name. Report the flag in remint's output. State in API-INVENTORY that `open_sealed` invalidates every floor.

### WR-08: API-INVENTORY rows edited or made false by this phase still describe the pre-phase behaviour

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

## Info

### IN-01: The seam's promote path imports the aa_run CLI module to read two string constants

**File:** `databasise/seam/engine.py:2354-2357`
**Issue:** The gate path pulls in `databasise.eval.aa_run` (which imports `databasise.cli`, `parity.run_arm`, `eval.corpus_ingest` and `default_registry`) and `databasise.eval.remint`. It needs only `ANSWER_LEVEL_METRIC`, `GOLD_PASSAGE_METRIC` and `_COMMITTED_BUNDLE_ROOT`. This creates a seam → eval → seam lazy cycle and adds a REST dependency on CLI modules.
**Fix:** Move the two metric names and the bundle-root path into `eval/bundle.py` (or `eval/calibration.py`), and import them from there in both the engine and aa_run.

### IN-02: The stage-2 gate does synchronous sqlite and filesystem I/O on the event loop

**File:** `databasise/seam/engine.py:2339-2407`, called at `:2474`
**Issue:** `_refuse_gate_verb` opens `ledger.db`, opens `floors.db` once per instance hash, lists the bundle directory, and does the first-time imports, all on the loop thread inside the async `promote`. The rest of `promote` deliberately offloads to `run_in_executor`. This is the "Synchronous I/O in Async Code" anti-pattern named in CLAUDE.md.
**Fix:** Run `_refuse_gate_verb` through `run_in_executor`, as `_promote_sync` already is.

### IN-03: The index probe runs only after the env file is read and the eval store is created

**File:** `databasise/eval/aa_run.py:733-748`, `databasise/eval/aa_run.py:515`
**Issue:** `_load_env_file`, `_build_clients` and `Databasise(...)` all run before `calibrate_family` calls `index_probe()`. `TraceStore.__init__` (`seam/trace_store.py:59-66`) runs `mkdir`, creates `trace.db` and switches it to WAL. A `--spend` run refused for an empty index has therefore loaded the secrets file and created `v1/.eval_corpus_store/trace.db` for nothing.
**Fix:** Call `_eval_index_probe(args.arm)()` right after `check_named_arm`, before `_load_env_file`.

### IN-04: Refusal docstrings describe the pre-TOOL-12 gate

**File:** `databasise/seam/refusals.py:600-612`, `databasise/seam/refusals.py:615-620`, `databasise/seam/promotion.py:264-275`
**Issue:**
- `GateVerbNotBuiltError` says it is "Refused immediately, before any trace resolution". It is now also raised in stage 2 for `promote-next` and `promote-now`, after trace resolution.
- `GateNotCalibratedError` says `UncalibratedFloorRefusalError` "stay[s] for that path". The engine raises `GateVerbNotBuiltError` there instead.
- `enforce_gate_verb_posture` has no production caller.
**Fix:** Update both docstrings. Delete `enforce_gate_verb_posture` and its `UncalibratedFloorRefusalError` branch, or mark them test-only.

### IN-05: The engine still hardcodes the executor version

**File:** `databasise/seam/engine.py:434`, `:2148`
**Issue:** `_EXECUTOR_VERSION = "databasise@0.1.0"` is written into every seam run record. D-01 makes `databasise.__version__` the one version source, and `rest.py:672` and `__init__.py:118` already read it. After a version bump, seam traces will record a stale executor version.
**Fix:** `_EXECUTOR_VERSION = f"databasise@{__version__}"`. Do the same in `parity/run_arm.py:81`.

### IN-06: The condition-10 refusal message misstates an inferred scope

**File:** `databasise/parts/admission.py:251-257`
**Issue:** `scope` is now inferred as `"shared"` when `artifact_scope` is `None` and the part declares `writes_artifact`. The message still says "declares artifact_scope='shared'", which names a declaration that does not exist.
**Fix:** Branch the message: "declares no artifact_scope while writing artifacts, which reads as shared (validator/blast_radius.py)".

### IN-07: Admission at load skips declaration-only opaque parts with no record, and never validates their records

**File:** `databasise/parts/admission.py:209-220`, `databasise/parts/registry.py:208-211`
**Issue:**
- `admit_registry` skips any opaque part whose `admission is None`.
- `register` runs `validate_admission` only when `body is not None`.

A declaration-only opaque part can therefore be registered with no record, or with a record naming a different part (the D-17 name-match check never runs). D-17 says the check covers "every opaque part". The impact is low because a declaration-only part cannot dispatch.
**Fix:** Run `validate_admission` for every opaque part that carries a record, and decide explicitly whether a declaration-only opaque part needs one.

---

_Reviewed: 2026-10-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
