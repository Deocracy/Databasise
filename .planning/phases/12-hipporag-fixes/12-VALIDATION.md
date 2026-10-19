---
phase: "12"
slug: "hipporag-fixes"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-19"
---

# Phase 12: Validation Strategy

> Per-phase validation contract for feedback sampling during execution. The source is 12-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd databasise && .venv/bin/pytest -q -p no:cacheprovider tests/parts_core/hipporag tests/seam/test_hipporag_write_path.py tests/evidence/test_hipporag_port_record.py` |
| **Wave command** | quick, plus `tests/seam/test_ingest_abort.py tests/seam/test_concurrent_ingest_failure.py tests/seam/test_corpus_write_gate.py tests/seam/test_query_trace_nodes.py tests/seam/test_empty_namespace.py tests/seam/test_job_families.py tests/seam/test_query_store_fault.py tests/stores tests/runner tests/foreign` |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (runs both pytest styles) |
| **Estimated runtime** | quick about 60 s; full about 16 min |
| **Never** | `-m live`, or reading any `.env*` file |

---

## Sampling Rate

- **After every task commit:** run the task's test file and the quick command.
- **After every plan wave:** run the wave command.
- **Before `/gsd-verify-work`:** the full suite must be green in both styles.
- **Max feedback latency:** 120 s, for the quick command.

---

## Per-Requirement Verification Map

Each row has its own test node, and on pre-fix code that node must fail with a plain `AssertionError`. Pre-fix code here means the code before Phase 12, or `feadf3e^` where the table says so. A node that fails to collect, or fails with an ImportError or AttributeError, does not count. Do not import a new symbol at module level.

| Req | Behavior | Test file | Pre-fix failure | Status |
|-----|----------|-----------|-----------------|--------|
| HIPP-01 | A PPR-branch query hydrates content, and every ref resolves | tests/seam/test_hipporag_write_path.py | hydrated content is `''` | ⬜ |
| HIPP-02 | The matching chunk vertex gets a non-zero reset weight | tests/parts_core/hipporag/test_ppr.py | the weight is 0 | ⬜ |
| HIPP-03 | A refused ingest commits nothing | tests/seam/test_hipporag_write_path.py | already passes at HEAD; record with `--at feadf3e^` | ⬜ |
| HIPP-04 | The refusal names the failing node privately and carries the real cause | tests/seam/test_hipporag_write_path.py | node_id is None | ⬜ |
| HIPP-05 | The fact-filter prompt carries the query | tests/seam/test_hipporag_write_path.py | the query section is `''` | ⬜ |
| HIPP-06 | Every chunk gets a passage vertex | tests/parts_core/hipporag/test_graph_construction.py | the vertex is missing | ⬜ |
| HIPP-07 | A synonymy edge appears on the ingest that introduces it and is not re-emitted | tests/parts_core/hipporag/test_graph_construction.py | assertion | ⬜ |
| HIPP-08 | Co-occurrence weight and edge types accumulate across ingests | tests/parts_core/hipporag/test_graph_construction.py | weight is 1.0, not 2.0 | ⬜ |
| HIPP-09 | A fact keeps the union of its chunk_ids | tests/parts_core/hipporag/test_index_side_extraction.py | assertion | ⬜ |
| HIPP-10 | Extraction failures are counted, the ingest is refused, and calls overlap | tests/parts_core/hipporag/test_index_side_extraction.py | assertion | ⬜ |
| HIPP-11 | At most top_k evidence items, and no zero-score PPR item | tests/seam/test_hipporag_write_path.py | 20 > 5 | ⬜ |
| HIPP-12 | Only query-side nodes run, the query is embedded once, and no write selector resolves | tests/seam/test_hipporag_write_path.py | assertion | ⬜ |
| HIPP-13 | The answer is generated text, not the joined evidence | tests/seam/test_hipporag_write_path.py | answer equals the joined evidence | ⬜ |
| HIPP-14 | A fired fallback shows as `degraded` with a node-free reason | tests/seam/test_hipporag_write_path.py | degraded is False | ⬜ |
| HIPP-15 | The corpus listing and counts cover HippoRAG (corpus leg over REST) | tests/seam/test_hipporag_write_path.py | total is 0 | ⬜ |
| HIPP-16 | A re-ingest leaves no stale chunk, and delete removes everything | tests/seam/test_hipporag_write_path.py | 3 chunks, not 1 | ⬜ |
| HIPP-17 | An old ref never resolves to the new text | tests/seam/test_hipporag_write_path.py | resolves to text B | ⬜ |
| HIPP-18 | No unread config key remains, and the docstrings make no false claim | tests/parts_core/hipporag/test_registration.py | assertion | ⬜ |
| HIPP-19 | Mixed counters never share one label | tests/runner/test_token_sum.py | the first label wins | ⬜ |
| A-WR-05 | An in-process provider error is logged redacted | tests/foreign/test_secret_redaction.py, plus the granted edit at tests/seam/test_foreign_engine_refusal.py:118 | the raw key is in the log | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Write each file's HIPP tests before the first `record-fail` for any row that shares the file.
- [ ] New test files: `tests/stores/test_vector_self_knn_pending.py`, a read-only KV listing test, `tests/parts_core/hipporag/test_document_remover.py`, `tests/parts_core/hipporag/test_qa_node.py`, `tests/runner/test_token_sum.py`, and a scheduler test for degraded-on-guard.
- [ ] Add new stub classes to `test_hipporag_write_path.py`. Do not rename `_DOCUMENT_TEXT`, `_HIPPORAG_CAPABILITY`, `_WORKSPACE`, `_make_engine`, `_StubEmbeddingClient` or `_StubIngestQueryLLMClient`, and do not change their behaviour.
- [ ] Owner `grant-check-edit`: `tests/seam/test_foreign_engine_refusal.py` (D-11).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A HippoRAG qa answer from a real provider, and its cost | HIPP-13 | `-m live` is never run in this phase; owner rule: debug only | TESTING-PLAN §2 row, to add at phase close |

---

## Validation Sign-Off

- [ ] Every task has an `<automated>` verify, or depends on Wave 0.
- [ ] No 3 consecutive tasks lack an automated verify.
- [ ] Wave 0 covers every MISSING reference.
- [ ] No watch-mode flags.
- [ ] Quick-command feedback latency is under 120 s.
- [ ] `nyquist_compliant: true` is set in the frontmatter.

**Approval:** pending
