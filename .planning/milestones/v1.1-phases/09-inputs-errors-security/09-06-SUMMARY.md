---
phase: 09-inputs-errors-security
plan: 06
subsystem: api
tags: [evidence, namespace, path-traversal, empty-inputs, base64, refusals, seam]
status: complete

requires:
  - phase: 09-05
    provides: structured refusal and fault plumbing on REST and MCP
provides:
  - "validate_evidence_namespace: fullmatch allow-list for evidence namespaces; resolve_evidence validates, checks the directory exists, then builds only the vector store"
  - "InvalidEvidenceNamespaceError (422) and EmptyIngestDocumentError (422) in the refusal catalogue"
  - "check_consumable refuses blank query text as EmptyQueryObjectError whatever other members are set; IngestDocument refuses blank text and 0-byte raw; MCP base64 decoded with validate=True"
  - "tests/seam/_probes.py: counting stub clients, trace_row_count, inbox_files (09-07 reuses it)"
affects: [09-07]

commits: 2
plan_head_before: 5f26f0742a95151eba6c36249c36f5ed1b18acc2
plan_head_after: e27093a32f69255dd8eded578e37d18171fa853c

actuals:
  tokens: 14000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "namespace guard -> existence check -> store construction ordering, so a refused or unknown namespace creates nothing"
    - "validator-raised refusals carry the literal class name in the message"

key-files:
  created:
    - databasise/tests/seam/_probes.py
    - databasise/tests/seam/test_evidence_namespace_guard.py
    - databasise/tests/seam/test_empty_inputs.py
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/evidence.py
    - databasise/seam/engine.py
    - databasise/seam/query.py
    - databasise/seam/corpus.py
    - databasise/mcp/tools.py
    - databasise/tests/seam/test_rest_transport.py

key-decisions:
  - "D-05: an evidence namespace must fullmatch [A-Za-z0-9-]+; anything else is InvalidEvidenceNamespaceError before any store or directory exists"
  - "resolve_evidence no longer calls _build_stores: the kv and graph stores were never used by this read and opening them created ws/text_chunks and graph.cozo as a side effect"
  - "D-08: blank query text is EmptyQueryObjectError even beside another member; blank ingest text and 0-byte raw are EmptyIngestDocumentError(member); MCP base64 is strict (validate=True)"

requirements-completed: [SEAM-01, SEAM-09]

coverage:
  - id: D1
    description: "POST /evidence/resolve and MCP resolve refuse '../../escape_probe', '../other-ws/chunks', an absolute path, 'chunks\\n', 'chunks/' and '' as InvalidEvidenceNamespaceError carrying the caller's namespace; 'zzz' is 404; no directory is created inside or outside store_root; no vector store is constructed for refused or unknown namespaces"
    requirement: "SEAM-01"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_evidence_namespace_guard.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Blank query text (empty, spaces, newline/tab/U+3000) is EmptyQueryObjectError on /query, /query/stream, MCP query and MCP compare, also beside embedding or predicates; zero LLM/embedder calls and no new trace row"
    requirement: "SEAM-09"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_empty_inputs.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Blank ingest text and 0-byte uploads are EmptyIngestDocumentError (member text/raw) with an empty corpus-inbox; MCP ingest refuses '' as empty and '!!!!', 'YW*Jj', 'YW!Jj' as MalformedBase64PayloadError, while 'YWJj' still enqueues"
    requirement: "SEAM-09"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_empty_inputs.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Concurrency edges (no shared state in the namespace guard or the empty-input validators) hold by construction: pure functions and no directory creation on the lookup path"
    requirement: "SEAM-01"
    human_judgment: true
    rationale: "Backstop edge; no concurrent test was written, the property follows from the code having no shared state"

duration: 20min
completed: 2026-10-17
---

# Phase 9 Plan 06: Evidence namespace guard and empty inputs Summary

**A path-like evidence namespace is refused by a fullmatch allow-list before any store is opened or directory created (resolve_evidence now builds only the vector store), and blank query text, blank or 0-byte documents and non-alphabet base64 are refused by name.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 2
- **Files modified:** 10 (6 source, 1 edited test, 3 new test/helper files)

## Accomplishments

- `validate_evidence_namespace` (`re.fullmatch` on `[A-Za-z0-9-]+`) runs first in `Databasise.resolve_evidence`; then `(store_root/workspace/namespace).is_dir()` decides `UnresolvableEvidenceReferenceError`; only then is `MultiNamespaceVectorStore` built, finalized in `finally`.
- `check_consumable` refuses `text.strip() == ""` as `EmptyQueryObjectError` before the set-member and consumability checks; the `UnconsumableQueryMemberError` case for non-blank text is unchanged.
- `IngestDocument` refuses blank text and 0-byte raw as `EmptyIngestDocumentError(member)` after the shape and size checks; it reaches REST and MCP through the existing validator handling.
- MCP `raw_base64` uses `validate=True`; the empty string decodes to `b""` and hits the `IngestDocument` rule.

## Red and green evidence

- Task 1 before the change (scratch script, same requests against the old code): `'../../escape_probe'`, `'../other-ws/chunks'`, the absolute path, `'chunks\n'` and `''` all returned `404 UnresolvableEvidenceReferenceError`; `'chunks/'` returned `200` with the stored record (Path normalisation). Directories created: `/escape_probe` and `/abs_target` outside store_root, `/store_root/other-ws/chunks`, `/store_root/seam-test/chunks\n`, `/store_root/seam-test/zzz`, plus `chunk_entity_relation/graph.cozo/...` and `text_chunks/kv.sqlite3` from `_build_stores`. (The new test file could not be collected pre-change: `ImportError: cannot import name 'validate_evidence_namespace'`.) After: `143 passed` over the five named files; `tests/seam tests/mcp`: `572 passed, 1 skipped`.
- Task 2 before the change: `pytest tests/seam/test_empty_inputs.py` gave `17 failed, 3 passed` (`assert 200 == 422` for blank queries, blank documents and the 0-byte upload; `DID NOT RAISE ToolError` for MCP base64). After: the five named files `121 passed`; plan verification `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/parts_core`: `753 passed, 1 skipped`, 0 failed.

## Task Commits

1. **Task 1: tracer, a path-like evidence namespace is refused before any store or directory exists** - `07c097c` (feat)
2. **Task 2: empty and whitespace-only inputs, 0-byte uploads and invalid base64 are refused by name** - `e27093a` (feat)

## Files Created/Modified

- `databasise/seam/refusals.py` - `InvalidEvidenceNamespaceError`, `EmptyIngestDocumentError`, widened `EmptyQueryObjectError` message and docstring
- `databasise/seam/evidence.py` - `_EVIDENCE_NAMESPACE_RE`, `validate_evidence_namespace`, `__all__`
- `databasise/seam/engine.py` - `resolve_evidence` reordered, no `_build_stores`
- `databasise/seam/query.py` - blank-text rule in `check_consumable`
- `databasise/seam/corpus.py` - empty rules in `IngestDocument`
- `databasise/mcp/tools.py` - `validate=True`
- `databasise/tests/seam/test_rest_transport.py` - two `_REFUSAL_FACTORIES` entries
- `databasise/tests/seam/_probes.py`, `test_evidence_namespace_guard.py`, `test_empty_inputs.py` - new

## Decisions Made

See `key-decisions`. No existing test needed editing beyond the two factory entries; the existing malformed-base64 MCP test (`not-valid-base64!!!`) still passes under strict decoding.

## Deviations from Plan

**1. [Ordering] Both new refusal classes landed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** `EmptyIngestDocumentError` was added to `refusals.py` (`__all__` and `_REFUSAL_FACTORIES`) together with `InvalidEvidenceNamespaceError` because both edits touch the same file and the transport test walks every `SeamRefusalError` subclass.
- **Fix:** accepted as is; Task 2 wires the rule that raises it.
- **Commit:** `07c097c`

**Total deviations:** 1 (commit grouping only). **Impact:** none on behaviour.

## Issues Encountered

A Bash call that wrote a scratch script via a python heredoc was rejected by the BAK check-edit guard (it named an unrelated protected test path); the script was written with the Write tool instead. The pre-change run of the namespace tests was reproduced with a scratch script in the scratchpad directory because the test module imports the new function.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

09-07 can import `counting_clients`, `trace_row_count` and `inbox_files` from `databasise.tests.seam._probes`.

## Self-Check: PASSED

- Files exist: refusals.py, evidence.py, engine.py, query.py, corpus.py, tools.py, `_probes.py`, both new test files.
- Commits `07c097c` and `e27093a` are ancestors of HEAD.
- Acceptance: `def validate_evidence_namespace` 1 line, `fullmatch` present, `validate_evidence_namespace(ref.namespace)` 1 line in engine, `validate=True` 1 line, `EmptyIngestDocumentError(member=` 2 lines, `def counting_clients` 1 line, `text.strip()` in query.py 1 line.

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
