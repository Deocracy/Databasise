---
phase: 06-hipporag-2-side-by-side
fixed_at: 2026-09-10T19:15:00Z
review_path: .planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-09-10T19:15:00Z
**Source review:** `.planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 2
- Fixed: 2
- Skipped: 0

IN-01, IN-02, IN-03 were out of `fix_scope: critical_warning` and were not touched.

## Fixed Issues

### CR-01: A raw-bytes document ingested against a HippoRAG-resolving selector silently loses all content — no refusal, no partial flag, a normal-looking success

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/tests/seam/test_hipporag_write_path.py`, `databasise/tests/seam/test_rest_transport.py`
**Commits:** `5827165`, `2cb437a`
**Applied fix:** Took the review's named-refusal option (minimal fix, matching house style) over
teaching `hipporag/chunker-embedder` to parse arbitrary file formats. Added
`NoRawUploadPathForModalityError` to `databasise/seam/refusals.py`, mirroring
`NoWritePathForModalityError`'s exact shape (names only `operation`, never the resolved modality,
wiring id, arm name, or node id). In `Databasise.ingest()`, added a guard immediately after
`target_node_id`/`result_node_id` are resolved and before any node config is stamped: if
`document.raw is not None` and the target node's own `kind` in the resolved corpus wiring is not
`"opaque"`, raise the new refusal. This check is generic over the wiring's own declared `kind`
field (`databasise/parts/schema.py`'s `Depth`/`NodeKind` vocabulary — `"opaque"` denotes a v1
subprocess that parses a file itself), never a hardcoded modality name — a future third modality
whose corpus-ingest target node is likewise non-opaque is refused by the same check without a new
branch. `lightrag/full-ingest` (`"kind": "opaque"`) is unaffected; `hipporag/chunker-embedder`
(`"kind": "embedder"`) now refuses raw uploads instead of silently indexing nothing.

Added a regression test,
`test_raw_upload_against_a_hipporag_selector_refuses_by_name_rather_than_losing_content`, to
`databasise/tests/seam/test_hipporag_write_path.py`: constructs `IngestDocument(raw=...)` against
the same HippoRAG-resolving selector `test_hipporag_write_path.py`'s other tests already use,
asserts `NoRawUploadPathForModalityError` is raised with `operation == "ingest"`, that the message
names neither modality, and that no `hipporag-graph` directory or `corpus-inbox` file was ever
created. This test fails without the fix (no exception is raised; the pre-fix code path silently
returns a normal-looking `IngestJob`).

A second, mechanically-required commit (`2cb437a`) registered the new refusal in
`test_rest_transport.py`'s own exhaustive `SeamRefusalError`-subclass enumeration
(`_REFUSAL_FACTORIES`/`test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value`)
— this test walks `SeamRefusalError.__subclasses__()` recursively and fails closed on any
refusal type with no registered test factory, so adding `NoRawUploadPathForModalityError` without
extending this table left the full suite red. This is not a new finding, just CR-01's own fix
completing the codebase's existing exhaustiveness contract.

### WR-01: `DELETE /documents/{document_id}`'s default request body is a mutable module-level singleton, evaluated once at route-registration time

**Files modified:** `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`
**Commit:** `3de871b`
**Applied fix:** Took the review's second option — `frozen=True` on `_RequestModel`
(`databasise/seam/rest.py`'s shared base for `QueryRequest`/`CompareRequest`/`TraceRequest`/
`IngestRequest`/`DeleteRequest`) — mirroring `databasise/mcp/tools.py`'s own `_ToolArgs` base,
which already sets `frozen=True`. This is the root-cause fix rather than a per-route symptom
patch: freezing the shared base closes the same mutable-default-argument hazard for every request
DTO in this module, not just `DeleteRequest`, without touching the route signature or its
byte-for-byte-unchanged no-body-request behavior. Grepped the whole worktree first — no route or
test anywhere mutates a `QueryRequest`/`CompareRequest`/`TraceRequest`/`IngestRequest`/
`DeleteRequest` instance after construction, so this is a behavior-preserving change today; it
converts a future read-then-write on the shared `DeleteRequest()` default into an immediate
`pydantic.ValidationError` instead of silent cross-request state corruption.

Added a regression test,
`test_delete_request_default_body_is_frozen_and_cannot_be_silently_mutated`, to
`databasise/tests/seam/test_rest_transport.py`: constructs `DeleteRequest()` (the exact shared
default instance the route uses) and asserts `body.selector = None` raises
`pydantic.ValidationError`. This test fails without the fix (pydantic v2 permits attribute
reassignment on a non-frozen `BaseModel`).

## Skipped Issues

None — both in-scope findings were fixed.

## Verification

Ran inside an isolated git worktree (`.claude/worktrees/rf-06-94686-<epoch>/`, on temp branch
`gsd-reviewfix/06-94686`) for editing and committing. Because the main checkout's `databasise/.venv`
has `databasise` installed **editable**, pointing its import finder at the main checkout's own
absolute path (confirmed: `sys.path.insert(0, <worktree>)` did **not** shadow it — the editable
finder wins regardless of `sys.path` order), test execution could not be trusted from inside the
worktree. Verification therefore ran as follows:

1. Applied and committed both fixes (plus the one mechanically-required exhaustiveness-table
   update) inside the worktree, on `gsd-reviewfix/06-94686`.
2. Fast-forward merged `gsd-reviewfix/06-94686` into `main` in the **main checkout**
   (`git merge --ff-only`) — main checkout's working tree was clean before this, so the
   fast-forward updated its files in place with no conflicts.
3. Ran the targeted test files against the main checkout's real `.venv`:

   ```bash
   cd databasise && .venv/bin/python -m pytest -q \
     tests/seam/test_hipporag_write_path.py \
     tests/seam/test_rest_transport.py \
     tests/seam/test_delete_document.py \
     tests/seam/test_rest_corpus_endpoints.py
   ```

   First run (fixes committed, before the exhaustiveness-table fix): `1 failed, 61 passed, 1
   skipped` — `NoRawUploadPathForModalityError has no test factory registered in
   test_rest_transport.py`. Fixed by registering the new refusal in `_REFUSAL_FACTORIES`
   (commit `2cb437a`), fast-forwarded again, re-ran:

   ```text
   62 passed, 1 skipped in 11.07s
   ```

4. Ran the full project test suite (the phase's own configured `test_command`) as a final check:

   ```bash
   cd databasise && .venv/bin/python -m pytest -q
   ```

   ```text
   938 passed, 4 skipped in 139.44s (0:02:19)
   ```

**Verification ran against the main checkout** (`/home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise`), after the fast-forward merge landed all three commits there — reproducible from that tree as-is; the isolated worktree used for editing/committing was removed afterward and no longer exists.

Syntax/structure checks (Tier 1 + Tier 2), applied to every file before each commit:

- `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/seam/rest.py`,
  `databasise/tests/seam/test_hipporag_write_path.py`,
  `databasise/tests/seam/test_rest_transport.py` — `python3 -c "ast.parse(...)"` — all OK.

The worktree's branch (`gsd-reviewfix/06-94686`) was fast-forward-merged into `main`, the worktree
removed, the temp branch deleted, and the recovery sentinel cleared after all three commits landed.
`main` now carries all three fix commits (`5827165`, `3de871b`, `2cb437a`).

---

_Fixed: 2026-09-10T19:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
