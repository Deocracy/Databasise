---
phase: 09-inputs-errors-security
plan: 04
subsystem: api
tags: [mcp, refusals, call-tool, tool-error, seam]
status: complete

requires:
  - phase: 09-03
    provides: checked_page, PageBoundsError, InvalidDocumentIdError
provides:
  - "_DatabasiseServer.call_tool: the one place every MCP refusal is mapped, walking the __cause__ chain"
  - "RefusalToolError: ToolError whose str() is the bare refusal JSON (no SDK prefix)"
  - "MissingScopeArgumentError: the named refusal for the three status/resolve scope preconditions"
affects: [09-05, 09-06]

commits: 2
plan_head_before: 49e27485f0d989cf288fc2ae9abc27697e211226
plan_head_after: 8aeb07067024f3c9d528bc54c23fe3db4960a8f1

actuals:
  tokens: 11000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "MCPServer subclass overriding call_tool: refusal found anywhere on the __cause__ chain, a pydantic ValidationError unwrapped via refusal_from_errors"
    - "schema errors and crashes are re-raised unchanged so they keep the SDK text"

key-files:
  created:
    - databasise/tests/mcp/test_mcp_refusal_mapping.py
  modified:
    - databasise/mcp/server.py
    - databasise/mcp/tools.py
    - databasise/seam/refusals.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_hipporag_write_path.py

key-decisions:
  - "D-02: a refusal is CallToolResult isError=true with one text content, the bare refusal JSON, no 'Error executing tool' prefix; an in-process call_tool raises RefusalToolError (a ToolError, not UnexpectedToolError) with the same text"
  - "The per-tool _refusal_mapped decorator and the second body copy _refusal_detail are deleted; refusal_body from seam.refusals is the single builder for both transports"
  - "A schema error carrying no refusal keeps 'Error executing tool <name>: <pydantic message>'; a crash keeps 'Error executing tool <name>' (T-09-07 accepted)"

requirements-completed: [SEAM-03]

coverage:
  - id: D1
    description: "ingest {}, ingest with text and raw_base64, oversized ingest, status offset -1, the three scope preconditions and resolve trace 'nope' each return bare JSON with the expected refusal_type, in-process (ToolError) and through mcp.Client (is_error True, content[0].text starts with '{')"
    requirement: "SEAM-03"
    verification:
      - kind: integration
        ref: "databasise/tests/mcp/test_mcp_refusal_mapping.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every refusal in refusals.__all__ with a test factory (34) raised by a probe tool arrives as bare JSON with its own class name"
    requirement: "SEAM-03"
    verification:
      - kind: integration
        ref: "databasise/tests/mcp/test_mcp_refusal_mapping.py::test_every_catalogued_refusal_reaches_mcp_as_bare_json"
        status: pass
    human_judgment: false
  - id: D3
    description: "MCP status limit 999999 refusal body equals the REST /corpus?limit=999999 body field for field; limit 100 succeeds and 101 is PageSizeExceededError; HippoRAG delete over MCP carries NoWritePathForModalityError"
    requirement: "SEAM-03"
    verification:
      - kind: integration
        ref: "databasise/tests/mcp/test_mcp_refusal_mapping.py, databasise/tests/seam/test_hipporag_write_path.py"
        status: pass
    human_judgment: false
---

# Phase 9 Plan 04: MCP refusal mapping Summary

One `call_tool` override on an `MCPServer` subclass now turns any refusal, however the SDK wrapped it, into `CallToolResult(isError=True)` with the bare refusal JSON; the three scope preconditions are the named refusal `MissingScopeArgumentError`.

## Accomplishments

- `_DatabasiseServer.call_tool` catches the SDK's `ToolError`, finds the first refusal on the `__cause__` chain (unwrapping a pydantic `ValidationError` through `refusal_from_errors`), and raises `RefusalToolError(json.dumps(refusal_body(refusal)))`. It covers argument validation (query with a hash-shaped alias), models built in a tool body (`ingest {}`) and the engine (`resolve trace 'nope'`).
- Deleted `_refusal_mapped` and `_refusal_detail` (the second copy of the REST body builder) and the nine decorator lines. Module docstring rewritten with the "What an MCP client receives" contract.
- `MissingScopeArgumentError(tool, scope, argument)` added to `seam/refusals.py` and `__all__`, and to `_REFUSAL_FACTORIES`.
- `tests/mcp/test_mcp_refusal_mapping.py` (51 tests): wire-level through `mcp.Client`, in-process, catalogue-wide probe, eight REQUIREMENTS calls, page boundary 100/101, REST body equality, schema-error text kept.

## Evidence (red then green)

Task 1, before the change (`pytest -q tests/mcp/test_mcp_refusal_mapping.py`): `36 failed, 1 passed`. `ingest {}` raised `UnexpectedToolError: Error executing tool ingest`; the 34 probe cases and the query-alias case did not give bare JSON. After: `61 passed` for `test_mcp_refusal_mapping.py` plus `test_dual_transport_parity.py`; `85 passed` for `tests/mcp tests/seam/test_dual_transport.py tests/seam/test_hipporag_write_path.py`.

Task 2, before the server change (class and factory already present): `6 failed, 45 passed`; the six failures are the three scope preconditions, each in the requirements-calls test and the tool/scope/argument test, which still gave plain text `status tool: scope 'job' requires a job_id`. After: `125 passed` on the four named files, and `669 passed, 1 skipped` for `tests/seam tests/mcp tests/parts_core` (0 failed).

Acceptance: `class RefusalToolError(ToolError)` and `class _DatabasiseServer(MCPServer)` each one grep line; `one mapper` printed; `grep -c "raise MissingScopeArgumentError"` = 3; "Error executing tool" appears in the module docstring.

## Deviations from Plan

**1. [Rule 3 - Blocking] Existing parity test needed no edit.** `test_dual_transport_parity.py` and `test_dual_transport.py` parse from the first `{`, so the removed prefix needed no change; no BAK-protected file was edited.

**2. [Rule 1 - Stale docstring] `mcp/tools.py` `PromoteToolArgs` docstring** named the deleted `_refusal_mapped`; updated to `_DatabasiseServer.call_tool`. Docs under `docs/gui/` still describe the old prefix and `_refusal_mapped`; they are dated inventories, left unchanged.

Otherwise the plan ran as written. The plan's `status job` test uses the stock engine without a patch (the precondition raises before any driver call).

## Known Stubs

None.

## Threat Flags

None. The refusal text is only `refusal_body` (class name, message, the refusal's own public attributes); no pydantic `input` echo reaches a refusal response. T-09-07 (SDK text for non-refusal schema errors) accepted as planned.

## Self-Check: PASSED

- FOUND: databasise/tests/mcp/test_mcp_refusal_mapping.py, databasise/mcp/server.py, databasise/seam/refusals.py
- FOUND commits 92428c3 (Task 1) and 8aeb070 (Task 2) on main
