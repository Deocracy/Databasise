---
phase: 05-opaque-side-admission
reviewed: 2026-09-08T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/tests/parts_core/lightrag/test_full_ingest.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/mcp/test_dual_transport_parity.py
  - databasise/tests/seam/test_rest_transport.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 05: Code Review Report (Incremental Re-Review — Gap Closure)

**Reviewed:** 2026-09-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** clean

## Summary

This is an incremental re-review of the two gap-closure plans (05-08, 05-09) that landed against
the prior `05-REVIEW.md` (`status: gaps_found`). Reviewed the actual commits (`dfeeb2e`, `03af94a`,
`cf83fe6`, `17dfa65`), not the plan documents' own claims, and ran the full affected test suite
(`67 passed, 1 skipped`) rather than trusting the diff alone.

All four carried-forward findings are resolved, confirmed by direct code inspection and by running
the regression tests that reproduce each original failure:

- **CR-01a** (MCP page-cap violation crashed with the SDK's generic `UnexpectedToolError`) —
  resolved. `databasise/mcp/server.py` now has its own `_checked_page`, mirroring
  `databasise/seam/rest.py`'s, raising `PageSizeExceededError` before `Page(...)` is ever
  constructed. Routed through `_status_job`/`_status_corpus`. Boundary and parity tests confirm the
  cap refuses rather than clamps, on both transports.
- **CR-01b** (malformed `raw_base64` crashed the same way) — resolved.
  `MalformedBase64PayloadError` added to `databasise/seam/refusals.py`, raised directly from
  `IngestToolArgs.to_ingest_document()` around the one `base64.b64decode` call, carrying only the
  field name (`raw_base64`), never the rejected payload. Registered in
  `test_rest_transport.py`'s `_REFUSAL_FACTORIES`, so the transitive `SeamRefusalError` subclass
  walk (which discovers the new class automatically via `__subclasses__()`) still proves a 422 for
  it — verified this test still enumerates and passes for the new class.
- **CR-02** (`ingest()` fabricated a successful `IngestJob(enqueued=0)` on an unclassified node
  failure) — resolved. New shared `_node_result_or_refuse` helper in `databasise/seam/engine.py`
  raises `ForeignEngineRefusalError` carrying the real recorded exception (`.cause`) for any
  recorded `node_exceptions` entry, whatever its type, or a synthesized `RuntimeError` only when
  neither a result nor an exception exists at all. `ingest()` now routes through it.
- **WR-01** (`delete_document()` degraded an unclassified node failure to a causeless
  `DeletionOutcome(status="fail", message="")`) — resolved. `delete_document()` now routes through
  the identical shared helper `ingest()` uses (genuinely shared — both call sites call the same
  module-level function, not two independently maintained copies), called *before* the MACH-11
  correlation so a refused run mints no fabricated seam events.

Also confirmed as part of this same gap-closure work (not separately tracked identifiers, but
verified because they touch the same code): the vestigial `try: pass finally:` wrapper in
`health()` (prior IN-01) was deleted in `03af94a`, and the now-fully-unused
`CorpusOpSubprocessError`/`CorpusOpTimeoutError` import was pruned from `engine.py`.

No new defects found in the changed code. Each of the seven correctness properties named in the
review brief was checked directly against the diff and, where testable, against a live pytest run:

1. **Real exception on `.cause`, never stringified/substituted.** Confirmed —
   `_node_result_or_refuse` raises `ForeignEngineRefusalError(operation=operation,
   cause=node_exception) from node_exception` using the actual recorded object; the synthesized
   `RuntimeError` is used only in the no-result/no-exception branch, where no real exception exists
   to preserve.
2. **`not_found`/`not_allowed` stay a normal `DeletionOutcome`, never refused.** Confirmed —
   `full_delete_body` returns those statuses as a normal dict payload (not a raised exception), so
   `scheduled["results"]` holds a non-`None` entry and `_node_result_or_refuse` returns it
   unmodified; `test_deleting_the_same_document_twice_yields_success_then_not_found` and
   `test_a_not_allowed_status_from_the_driver_surfaces_unchanged_never_remapped_or_raised` both
   still pass, proving the widening did not blur this distinction.
3. **No success-shaped record for a node that produced no result.** Confirmed for both `ingest()`
   and `delete_document()` — both now raise before constructing their respective return DTOs when
   `_node_result_or_refuse` refuses.
4. **Page-cap violation refused by name, never clamped.** Confirmed — `_checked_page` in
   `mcp/server.py` raises before `Page(...)` construction; the boundary test proves
   `MAX_PAGE_SIZE` succeeds and `MAX_PAGE_SIZE + 1` refuses on both transports.
5. **Refusal never echoes the offending payload, only the field name.** Confirmed —
   `MalformedBase64PayloadError.__init__` stores only `field`; the rejected `raw_base64` string is
   never retained on the exception or in its message.
6. **`MalformedBase64PayloadError` discoverable by the transitive subclass walk with a
   registered test factory.** Confirmed — it is a direct `SeamRefusalError` subclass, so
   `_all_seam_refusal_subclasses()`'s `__subclasses__()` walk finds it automatically, and its
   factory is present in `_REFUSAL_FACTORIES`, so the parametrized 422 proof covers it (would fail
   loudly with a missing-factory `AssertionError` otherwise).
7. **Both write call sites genuinely share one helper.** Confirmed by direct diff read — both
   `ingest()` (`dfeeb2e`) and `delete_document()` (`03af94a`) call the identical module-level
   `_node_result_or_refuse(scheduled, node_id, operation)`, not two copies.

The two new regression tests specifically named in the review brief were run and confirmed
non-vacuous:

- `test_an_unclassified_node_failure_through_ingest_raises_rather_than_fabricating_a_job` points
  the stub's interpreter at a nonexistent path, genuinely reproducing `MissingV1InterpreterError`,
  and asserts both `exc_info.value.operation == "ingest"` and
  `isinstance(exc_info.value.cause, MissingV1InterpreterError)`.
- `test_an_unclassified_node_failure_through_delete_document_raises_rather_than_a_causeless_fail`
  does the identical reproduction for `delete_document()`.
- `test_a_malformed_raw_base64_refuses_by_name_rather_than_crashing_the_tool` uses
  `"not-valid-base64!!!"`, independently confirmed (by direct execution) to raise a genuine
  `binascii.Error` (`Incorrect padding`) rather than silently decoding, so the test exercises the
  real failure path, not a string that happens to already be valid base64.
- `test_a_page_cap_violation_refuses_by_name_over_mcp_exactly_as_it_does_over_rest` and
  `test_the_page_cap_boundary_separates_rather_than_clamps_over_both_transports` compare MCP and
  REST responses against each other, not against hardcoded literals, so a future divergence between
  the two transports would fail the test rather than pass vacuously.

Ran `uv run pytest -q` against all 8 reviewed test/source files together: **67 passed, 1 skipped**
(the skip is the pre-existing real-v1-interpreter smoke test, gated on a local venv that is not
built in this environment — unrelated to the gap closure).

## Carried-Forward Findings

| ID | Prior severity | Resolution |
|----|----|----|
| CR-01a | Critical | **Resolved** — `_checked_page` added to `databasise/mcp/server.py`, routed through `_status_job`/`_status_corpus`. |
| CR-01b | Critical | **Resolved** — `MalformedBase64PayloadError` added and raised around the one `base64.b64decode` call in `databasise/mcp/tools.py`. |
| CR-02 | Critical | **Resolved** — `Databasise.ingest()` now routes through the shared `_node_result_or_refuse` helper. |
| WR-01 | Warning | **Resolved** — `Databasise.delete_document()` now routes through the same shared helper. |

Two findings from the prior review are outside this gap closure's scope and outside the file list
for this incremental pass (not re-verified here):

- **WR-02** (`databasise/parts_core/codebase_memory_mcp.py` forwards an unvalidated `tool`/
  `arguments` pair) — not touched by plans 05-08/05-09, not in the reviewed file list for this
  pass. Status unknown; presumed still open.
- **IN-01** (dead `try: pass finally:` in `health()`) — confirmed **resolved** as a side effect of
  `03af94a`, even though it was not one of the four identifiers this pass was asked to carry
  forward.

## Narrative Findings (AI reviewer)

No new Critical, Warning, or Info findings in the reviewed diff. The gap-closure changes are
narrow, mechanical, and match their stated intent exactly; nothing introduced by them regresses
correctness, leaks a rejected payload or an internal identity, or reintroduces silent narrowing.

---

_Reviewed: 2026-09-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
