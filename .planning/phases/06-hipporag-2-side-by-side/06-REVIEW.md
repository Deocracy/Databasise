---
phase: 06-hipporag-2-side-by-side
reviewed: 2026-09-10T18:30:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - databasise/eval/corpus_ingest.py
  - databasise/eval/remint.py
  - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
  - databasise/evidence/FALSIFIER-5-EVIDENCE.md
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/parts_core/hipporag/chunk_embed.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/tests/eval/test_corpus_ingest.py
  - databasise/tests/eval/test_remint.py
  - databasise/tests/parts_core/lightrag/test_full_ingest.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/seam/test_hipporag_write_path.py
  - databasise/tests/seam/test_rest_corpus_endpoints.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/wirings/hipporag/corpus-ingest.json
  - databasise/wirings/lightrag/corpus-ingest.json
  - databasise/wirings/resolve.py
  - .planning/phases/06-hipporag-2-side-by-side/COVERAGE.md
  - .planning/REQUIREMENTS.md
  - .planning/WINDOWS.md
findings:
  critical: 1
  warning: 1
  info: 3
  total: 5
status: issues_found
---

# Phase 06: Code Review Report (Incremental — Gap-Closure Plans 06-10..06-13)

**Reviewed:** 2026-09-10T18:30:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

This is an incremental review of phase 06's gap-closure work (06-10 through 06-13), scoped to the
files listed above. The prior review (commit `ab6a9ce`) is superseded by this document; its
findings are dispositioned as follows:

- **CR-01** (`ingest()`/`delete_document()` hardcoded to LightRAG only) — **confirmed fixed.**
  `databasise/seam/engine.py`'s `_corpus_wiring()` now resolves the write path per the selector's
  own resolved modality via `databasise.wirings.resolve.wiring_family`, `databasise/wirings/hipporag/
  corpus-ingest.json` now exists, and `NoWritePathForModalityError` refuses by name rather than
  silently falling back — verified in code and by `test_hipporag_write_path.py`'s own tracer tests.
- **WR-01** (`entity-fact-embed`'s wiring-declared `effects` under-declared `writes_kv`) — **confirmed
  fixed.** `databasise/wirings/hipporag/base.json`'s `entity-fact-embed` node now declares
  `["calls_embedding", "writes_vector", "writes_kv"]`, matching its own `Part`.
- **WR-02** (`entity_fact_embed.py` silently reported only the entity-embedding call's
  `resolved_model_identity`) — **confirmed fixed.** The body now raises `ValueError` naming both
  identities on divergence rather than silently discarding one, per the diff against
  `ab6a9ce..HEAD`.
- **IN-01** (`graph_augment_persist.py` iterates `weight_by_pair` unsorted) and **IN-02**
  (`self_knn`'s self-exclusion assumes the self-match is always within the requested window) — both
  files are untouched by this incremental scope (`git diff ab6a9ce..HEAD` shows no changes to
  `graph_augment_persist.py` or `stores/vector.py`); both findings are **carried forward, still
  open**, unchanged in substance from the prior review. Not re-detailed here since neither file is
  in this review's scope; see the prior review's text (`git show ab6a9ce:.planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md`) for the original write-up.

While tracing the new per-modality write dispatch (`_corpus_wiring`, `ingest()`, `delete_document()`)
end to end against `hipporag/chunker-embedder`'s own body (`chunk_embed.py`), I found one new
BLOCKER: a caller who uploads a raw-bytes document (PDF, DOCX, etc.) with a selector that resolves
to HippoRAG gets a normal-looking successful `IngestJob` — but the document's content is silently
never chunked, embedded, or written to any store. This is the same general defect class the
`known_context` flagged (an unguarded input shape reaching a part body) manifesting as silent data
loss rather than a provider-side 400, and it is untested: every test exercising the HippoRAG write
path (`test_hipporag_write_path.py`, `test_corpus_ingest.py`) uses `IngestDocument(text=...)` only,
never `IngestDocument(raw=...)`, so the gap has no regression coverage anywhere in this phase.

The `corpus_ingest.py`/`remint.py` spend-gating (dry-run default, `--spend`/checkpoint discipline,
no client construction before authorization) and `remint.py`'s content-addressed
never-edit-`bundle@v1`-in-place behavior both held up under adversarial tracing — confirmed by
`test_default_path_spends_nothing`'s `Databasise` construction guard and
`test_remint_mints_a_new_version_and_leaves_v1_bytes_untouched`'s byte-level before/after
comparison. The evidence documents (`FALSIFIER-5-EVIDENCE.md`, `CROSS-MODALITY-EVIDENCE.md`) are
honest, internally consistent records of blocked/refused real runs, with no fabricated numbers.

## Critical Issues

### CR-01: A raw-bytes document ingested against a HippoRAG-resolving selector silently loses all content — no refusal, no partial flag, a normal-looking success

**File:** `databasise/seam/engine.py:665-685` (the `document.raw is not None` branch of `ingest()`),
`databasise/parts_core/hipporag/chunk_embed.py:66-91` (`_chunk_embed_body`)

**Issue:** `Databasise.ingest()` dispatches both of `IngestDocument`'s two input shapes (`text`,
`raw`) through one identical code path regardless of which modality the caller's selector resolves
to (06-10-PLAN.md's own stated design: "Both of `IngestDocument`'s two input shapes ... take this
identical path ... one operation, two input shapes, never two execution paths"). For a `raw`
payload it always stamps:

```python
node_config["documents"] = [{"id": document_id, "document_id": document_id, "text": ""}]
node_config["file_paths"] = [str(on_disk_path)]
node_config["docs_format"] = _DOCS_FORMAT_PENDING_PARSE
```

— i.e. `text` is *always* the empty string for a raw upload; the real bytes are only reachable via
`file_paths`/`docs_format`. This is correct for LightRAG's opaque `full-ingest` node, which is a v1
subprocess that knows how to parse `pending_parse`-tagged files. It is silently wrong for HippoRAG's
`hipporag/chunker-embedder` (`chunk_embed.py`), whose body reads only `document["text"]` and
`document["document_id"]` — it has no knowledge of `file_paths` or `docs_format` at all:

```python
document_id = str(document["document_id"])
text = str(document.get("text", ""))
for ordinal, piece in enumerate(_split_into_chunks(text, chunk_size, chunk_overlap)):
    ...
```

For a raw-payload document, `text` is always `""`, so `_split_into_chunks("", ...)` returns `[]`
(its own explicit `if not text: return []` guard), `chunk_records` stays empty for that document,
and the node returns `{"chunks": []}` early — making **no** embedding call, writing **no** vector or
KV record. Every downstream HippoRAG node degrades gracefully on an empty `chunks`/`findings` list
(confirmed for `openie.py`: `if not chunks: return {"findings": []}`), so the entire seven-node
index-side chain completes "successfully" having written nothing at all for that document.

Back in `engine.py`, `ingest()`'s own no-fabricated-zero rule then reports the request as a success:

```python
enqueued = result.get("enqueued")
if enqueued is None:
    enqueued = 1
return IngestJob(job_id=str(result.get("track_id") or track_id), enqueued=int(enqueued))
```

`graph-augment-persist` (HippoRAG's `provides` node) reports no `enqueued` field, so this falls
through to the literal `1` — the caller receives `IngestJob(enqueued=1)`, identical in shape to a
real, successful ingest, with no `partial`/`degraded` signal anywhere (ingest returns an `IngestJob`,
never a `ResponseEnvelope`, so there is no `partial`/`degraded` field to carry the signal even if
one were computed). A subsequent `query()`/`compare()` against the same selector returns an
empty-evidence result indistinguishable from "HippoRAG legitimately found nothing relevant" — the
exact failure mode CR-01 in the prior review already named as the worst case for this phase's own
core value ("the same corpus, the same seam, N modalities running side-by-side and comparable").

This is untested in every direction: `test_hipporag_write_path.py`'s three ingest tests all use
`IngestDocument(document_id=..., text=_DOCUMENT_TEXT)`; `test_full_ingest.py`'s own raw-upload test
(`test_a_raw_upload_ingest_reaches_the_driver_via_a_server_side_path_never_a_caller_string`) only
exercises the no-selector (LightRAG) default path; `test_rest_corpus_endpoints.py`'s
`test_post_documents_upload_returns_an_ingest_job_via_the_deferred_parse_path` and
`test_hipporag_ingest_parity_across_rest_mcp_and_in_process_transports` in
`test_hipporag_write_path.py` never combine `raw=` with a HippoRAG-resolving selector. Both the REST
`/documents` and `/documents/upload` routes and the MCP `ingest` tool reach the identical
`Databasise.ingest()` code path, so this affects all three transports uniformly — it is not a
transport-specific gap.

**Fix:** Either (a) give `hipporag/chunker-embedder` real (or explicitly stubbed/quarantined, as
HippoRAG's own upstream chunker already is per this node's own docstring) file-parsing awareness of
`file_paths`/`docs_format`, so a raw upload actually reaches the modality's index, or — matching
this codebase's own refusals-over-silent-narrowing house style, and the minimal fix given
`chunk-embed`'s own stated scope is a "fused chunk-store-and-embed" position, not a file-format
parser — refuse a raw-bytes `IngestDocument` against a selector resolving to a modality whose
corpus-ingest wiring's target node cannot consume `file_paths`/`docs_format` (e.g. a new
`NoRawUploadPathForModalityError`, raised in `ingest()` before any node config is stamped, mirroring
`NoWritePathForModalityError`'s own house style: name only the operation, never the resolved
modality). A silent, reported-successful data loss is strictly worse than either of these.

## Warnings

### WR-01: `DELETE /documents/{document_id}`'s default request body is a mutable module-level singleton, evaluated once at route-registration time

**File:** `databasise/seam/rest.py:287`

**Issue:**

```python
@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, body: DeleteRequest = DeleteRequest()) -> DeletionOutcome:
```

`DeleteRequest` (via `_RequestModel`) declares `extra="forbid"` but not `frozen=True`, so
`DeleteRequest()` is a single mutable `BaseModel` instance constructed once when this route is
registered (module/app-construction time), then reused as the default for every request that omits
a body — the classic Python mutable-default-argument shape, applied to a route handler rather than a
plain function. No code in this route currently mutates `body`, so this is not observed to cause
incorrect behavior today, but it is fragile: a future edit that reads-then-writes a field on `body`
(e.g. a default-filling step) would silently corrupt every subsequent no-body request in the same
process, and the bug would not reproduce in a single-request test.

**Fix:** `body: DeleteRequest | None = None` with `selector = (body.selector if body else None)`
inside the function body, or mark `DeleteRequest`/`_RequestModel` `frozen=True` (mirroring
`databasise/mcp/tools.py`'s own `_ToolArgs` base, which already sets `frozen=True`) so a future
mutation raises immediately instead of silently corrupting shared state.

## Info

### IN-01 (carried forward from `ab6a9ce`): `graph_augment_persist.py` iterates `weight_by_pair` in insertion order rather than sorted

**File:** `databasise/parts_core/hipporag/graph_augment_persist.py:78-82`

Untouched by this incremental scope. Still open, unchanged in substance from the prior review: this
module's own sibling edge-builders (`fact_edges.py`/`passage_edges.py`/`synonymy_edges.py`) all emit
`sorted(weight_by_pair.items())`, but `graph_augment_persist.py`'s own upsert loop does not — no
observed correctness effect (each `upsert_edge` call is independent and idempotent), but it breaks
the otherwise-consistent canonical-sorted-order convention this port's other modules follow.

**Fix:** `for pair, weight in sorted(weight_by_pair.items()):` for consistency.

### IN-02 (carried forward from `ab6a9ce`): `self_knn`'s self-exclusion assumes the self-match is always within the returned `top_k + 1` window

**File:** `databasise/stores/vector.py:272-315`

Untouched by this incremental scope. Still open, unchanged in substance from the prior review: under
a degenerate case of more than `top_k` bit-identical-embedding ties, the true self-match could
theoretically fall outside the requested `top_k + 1` window, in which case the method silently
returns `top_k` genuine neighbours rather than erroring — graceful in practice, but in tension with
the module's own docstring, which implies the self-match is always present to be dropped.

**Fix:** No functional change needed; consider a docstring caveat.

### IN-03: `resolved.get("consumes_documents")`/`resolved.get("provides")` indexing in `ingest()`/`delete_document()` assumes exactly one element with no bounds check

**File:** `databasise/seam/engine.py:662-663`, `databasise/seam/engine.py:772`

**Issue:** `_corpus_wiring()`'s returned dict is indexed unconditionally:

```python
target_node_id = resolved["consumes_documents"][0]
result_node_id = resolved["provides"][0]
```

and, in `delete_document()`:

```python
delete_node_id = resolved["provides"][0]
```

Both `databasise/wirings/lightrag/corpus-ingest.json` and `databasise/wirings/hipporag/
corpus-ingest.json` (and the two corresponding `corpus-delete.json` files) declare exactly one entry
in each list today, so this holds for every wiring this machine currently ships. There is no
validation, however — at `_corpus_wiring()`'s own load site or via `parse_wiring` before this
indexing runs — that a `corpus-<operation>.json` file added for a future third modality actually
declares a non-empty `consumes_documents`/`provides` list; a malformed file (an empty list, or a
missing key entirely, since `.get(...)` would then return `None` and `None[0]` raises `TypeError`)
would surface as an unhandled `IndexError`/`TypeError`/`KeyError` rather than a named refusal, at
odds with this codebase's otherwise-consistent "refuse by name" convention for a malformed
machine-owned artifact.

**Fix:** Low priority given today's actual wiring files are all well-formed by construction (hand-
authored, reviewed) — but a schema check inside `_corpus_wiring()` (or `parse_wiring`, if corpus
wirings are meant to be validated the same way query wirings are) asserting a non-empty
`consumes_documents`/`provides` list before this indexing runs would turn a future malformed-file
mistake into a named, debuggable refusal rather than a raw Python exception surfacing through the
seam boundary.

---

_Reviewed: 2026-09-10T18:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
