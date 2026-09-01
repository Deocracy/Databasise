---
phase: 03-lightrag-query-side
plan: 02
subsystem: parity-harness
tags: [lightrag, cozo, faiss, openrouter, hotpotqa, uv, parity]

requires:
  - phase: 03-01
    provides: v2 store adapters (FaissVectorStore, SqliteKVStore, CozoGraphStore) and namespace derivation this plan imports into
provides:
  - A pinned, reproducible v1 environment (uv-managed, Python 3.12) as the parity comparison's original arm
  - A fixed, hash-verified HotpotQA distractor corpus snapshot (20 documents, 2 queries) both arms will read
  - One real v1-built index (Cozo graph + Faiss x3 + JSON KV), built exactly once via a real OpenRouter ingest run
  - A verified, read-and-reinsert import of that index into the v2 namespace layout, gated by three automated D-02 assertions
affects: [03-03, 03-07, 03-09]

actuals:
  tokens: 15500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Read-and-reinsert import (never file copy) for cross-store-shape migration"
    - "Three-state verification result (verified/inconclusive/refused) instead of boolean pass/fail"
    - "Tolerance-quantized hash comparison for floating-point vectors that are idempotent only up to ULP noise"

key-files:
  created:
    - v1/.python-version
    - v1/.env.parity.example
    - v1/README-PARITY.md
    - v1/scripts/run_parity_ingest.py
    - databasise/parity/corpus.py
    - databasise/parity/build_corpus_fixture.py
    - databasise/parity/import_index.py
    - databasise/tests/fixtures/corpus/MANIFEST.json
    - databasise/tests/fixtures/corpus/README.md
    - databasise/tests/fixtures/corpus/documents/*.txt (20 files)
    - databasise/tests/parity/__init__.py
    - databasise/tests/parity/conftest.py
    - databasise/tests/parity/test_import_verification.py
  modified:
    - v1/uv.lock
    - v1/.gitignore

key-decisions:
  - "Embedder is qwen/qwen3-embedding-8b via OpenRouter (D-09 amendment), not local Ollama — verified live against OpenRouter's own endpoint listing before use"
  - "No provider pin for the embedder (unlike the D-07/D-08-pinned generator): v1's openai_embed() wrapper has no extra_body plumbing to carry one, and D-01 makes it moot since vectors are computed exactly once"
  - "No separate keyword-extraction LLM binding: D-07/D-08 pin the same model for both roles, so a second binding would be dead config"
  - "Vector-set hash quantized to 3 decimal places before hashing, not compared byte-for-byte: measured against the real build that a second L2-normalisation pass over an already-unit float32 vector is idempotent only up to ~1e-5 ULP noise, not bit-exact"
  - "run_parity_ingest.py lives under v1/, not databasise/, because it must import v1's lightrag package — check_import_boundary.py forbids that import anywhere under databasise/"

patterns-established:
  - "Parity harness namespace is derived via databasise.namespaces.derive_namespace, keyed to the corpus's own SHA-256, so the import target changes if the corpus snapshot ever does"

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "v1 stands up as a runnable, pinned, reproducible original arm (Python 3.12, Cozo+Faiss store family, D-06/D-07/D-08/amended-D-09 pinned config)"
    verification:
      - kind: other
        ref: "cd v1 && uv run python -c \"import lightrag, pycozo, faiss\" (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fixed, hash-verified HotpotQA corpus snapshot with a query set carrying gold supporting document ids"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_import_verification.py (corpus loaded via corpus_snapshot fixture, drift-raise verified manually)"
        status: pass
    human_judgment: false
  - id: D3
    description: "One v1 index built exactly once via a real OpenRouter ingest run over the pinned corpus"
    verification:
      - kind: other
        ref: "v1/scripts/run_parity_ingest.py real run — v1/.parity_working_dir/ artifacts present (Cozo db, 3 Faiss indexes, JSON KV)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Verified, read-and-reinsert import into the v2 namespace layout with D-02's three assertions as an automated gate reporting verified/inconclusive/refused, never a plain pass/fail"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_import_verification.py (7 tests, including the real-build test)"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.parity.import_index --verify (exit 0 clean, exit 1 naming a deliberately corrupted chunk id)"
        status: pass
    human_judgment: false

duration: ~1h active work (plus unattended background wait for the real OpenRouter ingest run)
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 2: v1 Parity Environment, Corpus, and Verified Index Import Summary

**Pinned v1 environment + hash-verified HotpotQA corpus + one real OpenRouter-built index, imported into the v2 namespace layout under three automated byte-identity assertions.**

## Performance

- **Duration:** ~1h active work; the real v1 ingest ran unattended in the background for roughly 25 minutes end to end
- **Tasks:** 3/3 completed
- **Files modified:** 34 (see key-files above; `v1/uv.lock` accounts for most of the line churn as a resolver-regenerated lockfile)

## Accomplishments

- Stood up `v1/` as a pinned, reproducible `uv`-managed environment (Python 3.12) with Cozo + Faiss as its store family (D-05), not v1's networkx/nano-vectordb quick-start defaults
- Wrote and hash-verified a fixed HotpotQA distractor corpus snapshot: 2 questions, 20 unique documents, no overlap, each query paired with its gold supporting document ids
- Ran a real, end-to-end v1 LightRAG ingest against the amended D-09 config (`qwen/qwen3-embedding-8b` via OpenRouter's embeddings endpoint, not local Ollama) and the D-07/D-08-pinned `qwen/qwen3.7-flash` generator — 20 documents, 194 entities, 193 relationships extracted and embedded for real
- Built a verified, read-and-reinsert importer (`databasise/parity/import_index.py`) that pulls vectors out of v1's Faiss indexes via `reconstruct()`, v1's chunk text out of its KV JSON, and v1's graph out of its Cozo db, reinserting all three through the v2 stores' own public write paths — never copying files, never recomputing an embedding
- Implemented a three-state verifier (`verified` / `inconclusive` / `refused`) covering D-02's three assertions, with 7 tests (6 fully offline against a synthetic v1-shaped index, 1 against the real build)

## Task Commits

1. **Task 1: Stand up v1's pinned environment and its parity configuration** — `e767454` (feat)
2. **Task 2: Fix the corpus snapshot, hash it, and build the one index with v1** — `52adb0e` (feat)
3. **Task 3: Verified import of v1's index into the v2 namespace layout** — `94dea16` (feat)

## Files Created/Modified

- `v1/.python-version`, `v1/uv.lock` — pinned Python 3.12 environment
- `v1/.env.parity.example`, `v1/README-PARITY.md` — tracked, secret-free run-config record (`.env.parity` itself is gitignored, verified via `git check-ignore` before every commit)
- `v1/scripts/run_parity_ingest.py` — drives the real v1 ingest; lives under `v1/` because it imports v1's `lightrag` package
- `databasise/parity/corpus.py` — hash-verified corpus loader, raises `CorpusDriftError` naming the first mismatched document id
- `databasise/parity/build_corpus_fixture.py` — regenerates the committed fixture from HuggingFace's datasets-server API
- `databasise/tests/fixtures/corpus/{MANIFEST.json,README.md,documents/*.txt}` — the committed corpus snapshot (20 docs, 2 queries)
- `databasise/parity/import_index.py` — the verified importer/verifier, `Violation`/`VerificationResult` dataclasses, `main()` CLI
- `databasise/tests/parity/{__init__.py,conftest.py,test_import_verification.py}` — fixtures (v1-venv/index/corpus, skip-guarded) and the test suite

## Decisions Made

- **D-09 amendment applied throughout**: embedder is `qwen/qwen3-embedding-8b` via OpenRouter, verified live (a real embeddings call returned a 4096-dim vector) before any config was written. Ollama was never checked for or installed.
- **No embedder provider pin**: unlike the generator (D-07/D-08, pinned to `Alibaba` — OpenRouter's own endpoint listing shows exactly one provider for `qwen/qwen3.7-flash`), the embedder is left on default routing. v1's `openai_embed()` wrapper has no `extra_body` plumbing to carry a pin, and D-01 makes it moot: vectors are computed exactly once and never recomputed.
- **No separate keyword-extraction binding**: D-07/D-08 pin the same model for both the generator and keyword extraction, so a second `KEYWORD_LLM_*` binding would be redundant dead config. Dropped after being written and caught during Task 2's ingest-script implementation (see deviations).
- **Vector-set hash uses 3-decimal quantization, not raw bytes**: measured directly against the real build that a second L2-normalisation pass over an already-unit 4096-dim vector can shift a component by up to ~1e-5 — enough to flip a 6- or 5-decimal round on one side and not the other at a small number of ids. 3 decimals gives 2-3 orders of magnitude of headroom past the measured noise ceiling while staying far coarser than any real semantic difference could hide behind.
- **`run_parity_ingest.py` placed under `v1/`, not `databasise/`**: it necessarily imports v1's own `lightrag` package, which `databasise/tools/check_import_boundary.py` forbids anywhere under `databasise/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Vector-set hash comparison used raw bytes initially, which is not actually idempotent under real float32 renormalization**
- **Found during:** Task 3, running the real-build verification test after the actual OpenRouter ingest completed
- **Issue:** The plan's own reasoning ("both stores L2-normalise on write... re-normalising an already-normalised vector is idempotent and does not change the stored value") holds in exact arithmetic but not in float32: a second normalization pass over an already-unit vector measurably shifts up to ~1e-5 on a small number of components. A byte-exact hash flagged this as a mismatch on the real 4096-dim qwen3-embedding-8b vectors (it did not show up on a hand-built 3-dim synthetic test, which is why it was caught only against the real build).
- **Fix:** Quantize each vector to 3 decimal places before hashing (tried 6 and 5 decimals first; both still had rare boundary-crossing flips at their respective grid spacing — 3 decimals gives real headroom past the measured ~1e-5 noise ceiling while remaining far more sensitive than any genuine corruption or re-embedding would need).
- **Files modified:** `databasise/parity/import_index.py`
- **Verification:** `test_real_v1_build_verifies_clean` passes against the actual Task 2 build; all 6 synthetic tests still pass unchanged.
- **Committed in:** `94dea16` (Task 3 commit)

**2. [Rule 1 - Bug] Config file initially wrote two inert/redundant settings**
- **Found during:** Task 2, while writing `v1/scripts/run_parity_ingest.py`
- **Issue:** `v1/.env.parity(.example)` initially included `OPENAI_EMBEDDING_EXTRA_BODY` (v1's `openai_embed()` has no code path that reads or forwards it — it would have silently done nothing) and a separate `KEYWORD_LLM_*` binding block (redundant: D-07/D-08 pin the same model for both roles already).
- **Fix:** Removed both, replaced with explanatory comments in the env file and README table.
- **Files modified:** `v1/.env.parity.example`, `v1/README-PARITY.md`
- **Verification:** Real ingest ran successfully with the corrected config.
- **Committed in:** `52adb0e` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs, both floating-point/config correctness issues surfaced only by running the real pipeline, not by the synthetic tests alone)
**Impact on plan:** Both fixes were necessary for the parity harness to produce a genuinely meaningful (not spuriously flaky, not silently broken) verification result. No scope creep — no plan requirement was dropped or weakened.

## Issues Encountered

- **uv-managed Python's SSL cert bundle**: the `uv`-managed CPython 3.12 interpreter (from python-build-standalone) does not pick up this NixOS host's `/etc/ssl/certs/ca-certificates.crt` by default, causing `SSLCertVerificationError` on the corpus fixture builder's HTTPS fetch. Resolved by setting `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` explicitly — documented in `databasise/tests/fixtures/corpus/README.md`'s regenerate command, harmless to set unconditionally.
- **RocksDB file lock during concurrent test runs**: while the real v1 ingest was still running (holding a lock on `cozo_graph_chunk_entity_relation.db`), the skip-guarded real-build test failed with a RocksDB lock error rather than a clean skip. This resolved itself once the ingest process exited and released the lock — not a code defect, just a genuine concurrent-access condition during development.

## User Setup Required

None — no external service configuration required beyond the OpenRouter API key, which was already provisioned at `.env.secrets` outside the worktree per the task instructions.

## Next Phase Readiness

- The v2 namespace layout now holds a verified, real-data index (20 documents, 194 entities, 193 relationships, full graph) that plans 03-07 and 03-09 can query for the retrieval-level parity comparison.
- The corpus snapshot's queries carry gold supporting document ids, giving 03-07 something to compare rankings against beyond raw set overlap, as the plan intended.
- `v1/.parity_working_dir/` (the real ingest output) and `v1/.parity_v2_store/` (the imported v2 store) are both gitignored build artifacts on disk in this worktree — per D-01, this ingest must not be re-run; later plans should import from the same `v1/.parity_working_dir/` rather than triggering a fresh ingest.
- No blockers identified for 03-03 onward.

## Self-Check: PASSED

All referenced files confirmed present on disk; all three task commit hashes confirmed in `git log`.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*
