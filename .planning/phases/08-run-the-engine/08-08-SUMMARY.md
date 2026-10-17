---
phase: 08-run-the-engine
plan: 08
subsystem: api
tags: [cors, fastapi, starlette, trustedhost, dns-rebinding, mcp-transport-security, launcher]

requires:
  - phase: 08-run-the-engine
    provides: "08-01 launcher package (serve_rest.build_parser/build_app) and 08-06 databasise-mcp launcher"
provides:
  - "create_app(cors_origins=()) with exact-origin validation (InvalidCorsOriginError, validate_cors_origin)"
  - "databasise-rest --cors-origin (repeatable, empty by default)"
  - "--allow-remote-unauthenticated: both launchers refuse a non-loopback --host (exit 2) without it"
  - "DNS-rebinding guards: TrustedHostMiddleware on the launcher-built REST app, TransportSecuritySettings on MCP sse/streamable-http"
affects: [08-10, CONN phases (seam authentication stays open), 16-18 operator console GUI]

actuals:
  tokens: 4940
  tasks: 3
  commits: 6
plan_head_before: 056565ae8b3f02694f229f2ccb5d41122e2db917
plan_head_after: 8ef42bb4bf8242edfc06c5878b39e03486c9ecfd
commits: 6

tech-stack:
  added: []
  patterns:
    - "launcher-only hardening: create_app keeps its permissive default; the launcher wraps the app it serves"
    - "refusals that must not bind a port are tested by stubbing open_engine so a red run cannot bind"

key-files:
  created:
    - databasise/tests/seam/test_rest_cors.py
    - databasise/tests/launcher/test_bind_guard.py
  modified:
    - databasise/seam/rest.py
    - databasise/launcher/__init__.py
    - databasise/launcher/serve_rest.py
    - databasise/launcher/serve_mcp.py
    - databasise/tests/launcher/test_launchers.py

key-decisions:
  - "CORS allows GET/POST/DELETE and the Content-Type header only; allow_credentials is never set and '*' is refused at validation (D-12)"
  - "Origins are validated, not normalised: the browser Origin header is matched byte for byte"
  - "Non-loopback bind is refused by default; the check runs in check_engine_arguments so both launchers share it and it runs before the store lock"
  - "TrustedHostMiddleware lives in serve_rest.build_app, not create_app, so embedded and TestClient use keep accepting any Host"
  - "Seam authentication is NOT added; it stays an open owner decision for the CONN phases"

patterns-established:
  - "check_engine_arguments reads getattr(args, 'transport', None) so the one shared check covers REST (always binds) and MCP (stdio exempt)"

requirements-completed: [RUN-08]

coverage:
  - id: D1
    description: "databasise-rest --cors-origin <origin> answers a browser preflight and GET /health from that exact origin; unlisted origins get no allow header; no flag leaves the app unchanged"
    requirement: RUN-08
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_cors.py (18 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Origins with a trailing slash, path, query, wildcard or '*' are refused by create_app and by the launcher (exit 2, before the store lock)"
    requirement: RUN-08
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_cors.py#test_invalid_origins_are_refused_by_create_app, #test_the_launcher_refuses_an_invalid_origin_with_exit_2"
        status: pass
    human_judgment: false
  - id: D3
    description: "A non-loopback --host is refused with exit 2 unless --allow-remote-unauthenticated is given (REST, MCP sse/streamable-http; stdio exempt)"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_bind_guard.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Foreign Host header gets 400 from the launcher-built REST app and 421 from the MCP transport validator; loopback and the bound host pass"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_bind_guard.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "CORSMiddleware is stateless per request, so concurrent listed and unlisted origins are answered independently (backstop)"
    requirement: RUN-08
    verification: []
    human_judgment: true
    rationale: "Backstop truth from the plan: a property of Starlette's middleware, asserted by no test here"

duration: 35min
completed: 2026-10-17
status: complete
---

# Phase 8 Plan 08: Opt-in CORS allow-list and unauthenticated-seam bind guard Summary

**`databasise-rest --cors-origin` (repeatable, exact origins, never `*`, no credentials) plus a loopback-only bind guard and DNS-rebinding protection on both launchers**

## Performance

- **Duration:** about 35 min
- **Completed:** 2026-10-17T01:36:27Z
- **Tasks:** 3 (2 planned, 1 orchestrator-directed security addendum)
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `create_app(cors_origins=())`: validates every origin against `https?://[^/\s*?#]+`, de-duplicates, and adds `CORSMiddleware` with `allow_methods=["GET","POST","DELETE"]`, `allow_headers=["Content-Type"]` and no credentials. Empty list adds no middleware: `OPTIONS /query` stays 405.
- `databasise-rest --cors-origin` validates before the store lock (exit 2) and passes the list to `create_app`.
- Addendum: both launchers refuse a non-loopback `--host` (exit 2, message names the missing authentication and the override flag) unless `--allow-remote-unauthenticated`; `databasise-mcp --transport stdio` is exempt.
- Addendum: REST app is wrapped in `TrustedHostMiddleware` in `serve_rest.build_app` (foreign Host gets 400); MCP sse/streamable-http get `TransportSecuritySettings(enable_dns_rebinding_protection=True, ...)` through `server.run(..., transport_security=...)` (foreign Host gets 421, foreign Origin 403).

## Task Commits

1. **Task 1: create_app(cors_origins=...)**
   - RED `7decfc3` (test): 13 failed, 1 passed. Failure reason: `TypeError: create_app() got an unexpected keyword argument 'cors_origins'`. The one pass is the no-origins 405 case, which pins the unchanged default.
   - GREEN `4f878d7` (feat): `tests/seam/test_rest_cors.py` 14 passed; `test_rest_transport.py`, `test_rest_corpus_endpoints.py`, `test_dual_transport.py` pass (94 total).
2. **Task 2: databasise-rest --cors-origin**
   - RED `bc3a0dc` (test): 3 failed, 15 passed. Failures: `databasise-rest: error: unrecognized arguments: --cors-origin ...`; the invalid-origin test additionally asserts the stderr names `invalid CORS origin 'http://localhost:5173/'`, so argparse's own exit 2 cannot satisfy it.
   - GREEN `ba29658` (feat): 18 passed.
3. **Task 3 (orchestrator-directed addendum): bind guard and DNS-rebinding protection**
   - RED `4eb4500` (test): 14 failed, 11 passed (unrecognized `--allow-remote-unauthenticated`, no 400 on foreign Host, no `build_transport_security`). Refusal tests stub `open_engine`, so a red run reaches an AssertionError instead of binding a socket.
   - GREEN `8ef42bb` (feat): 25 passed in the new file.

**Plan metadata:** committed after this file (docs commit).

## Files Created/Modified

- `databasise/seam/rest.py` - `InvalidCorsOriginError`, `validate_cors_origin`, `create_app(cors_origins=...)`, docstring note, exports
- `databasise/launcher/__init__.py` - `--allow-remote-unauthenticated`, `is_loopback_host`, `bracketed`, `LOOPBACK_HOST_NAMES`, the shared bind check in `check_engine_arguments`
- `databasise/launcher/serve_rest.py` - `--cors-origin`, origin validation before the lock, `TrustedHostMiddleware` in `build_app`
- `databasise/launcher/serve_mcp.py` - `build_transport_security`, passed to `server.run` for sse/streamable-http
- `databasise/tests/seam/test_rest_cors.py` - 18 RUN-08 tests (phase-created names imported inside test bodies, per the fail-first constraint)
- `databasise/tests/launcher/test_bind_guard.py` - 25 addendum tests
- `databasise/tests/launcher/test_launchers.py` - the sse/streamable-http run-kwargs assertion now also expects `transport_security` (see deviation 1)

## Decisions Made

See `key-decisions`. In short: exact-origin matching with no normalisation; CORS methods/headers limited to what the routes use; hardening placed in the launcher so `create_app` defaults and every existing TestClient test are untouched; no authentication added.

## Deviations from Plan

### Orchestrator-directed addition

**1. [Orchestrator addendum] Non-loopback bind refusal and DNS-rebinding protection**
- **Found during:** after Task 2, responding to an automated commit security review of `databasise/launcher/serve_rest.py`
- **Issue:** the unauthenticated seam could be bound to any interface, and a rebinding page could reach a loopback bind through a foreign Host header
- **Fix:** Task 3 above. Seam authentication stays an open owner decision for the CONN phases; nothing auth-related was added.
- **Files modified:** the launcher modules and tests listed above
- **Verification:** `tests/launcher` 47 passed, `tests/seam` 306 passed 1 skipped, `tests/seam/test_rest_cors.py` plus `test_rest_transport.py` pass; manual `databasise-rest --host 0.0.0.0` and `databasise-mcp --transport sse --host 0.0.0.0` exit 2 with no `.engine.lock` created
- **Committed in:** `4eb4500` (RED), `8ef42bb` (GREEN)

### Auto-fixed Issues

**2. [Rule 1 - Bug] Existing 08-06 test asserted the exact `server.run` kwargs**
- **Found during:** Task 3 verification
- **Issue:** `test_databasise_mcp_passes_each_transport_to_the_server_run_method[sse|streamable-http]` compared `{"host","port"}` exactly; the addendum legitimately adds `transport_security`
- **Fix:** the test now pops `transport_security`, asserts DNS-rebinding protection is on, and keeps the exact `host`/`port` assertion; stdio is unchanged (`{}`)
- **Files modified:** `databasise/tests/launcher/test_launchers.py`
- **Committed in:** `8ef42bb`

### Clarification of the addendum text

The addendum asked for the bound host "with and without `:port` as Starlette requires". Starlette 1.6.0's `TrustedHostMiddleware` compares the Host header only up to its first `:`, so ports are ignored and a `host:port` entry would be dead. The REST list is therefore bare names. Because of the same split, any bracketed IPv6 Host reduces to `"["`; the list contains `"["` so `[::1]:8000` works, which also admits other bracketed IPv6 literals (an IP literal cannot be rebound). The MCP SDK matches exact strings, so its lists carry both bare and `:port` forms.

**Total deviations:** 1 orchestrator addition, 1 auto-fixed (Rule 1). **Impact on plan:** none on planned behaviour; `create_app` default and all seam tests are unchanged.

## Issues Encountered

- First RED run of the addendum tests ran `main()` against `--host 0.0.0.0` before the guard existed, which started a real server and hit the tool timeout; it was killed and the tests were changed to stub `open_engine` so a refused launch can never bind. No socket from it remained (checked with `ss`).
- Plan acceptance grep `"--cors-origin"` ... `action="append"` expects one line; the `add_argument` call spans several lines, so the flag and `action="append"` are on adjacent lines of the same call.
- Repository ruff is not clean (pre-existing B008 on `Depends(...)`/`DeleteRequest()` in `rest.py`, unsorted `__all__`, format drift in untouched files); not touched.

## Known Stubs

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: residual-remote-bind | databasise/launcher/serve_rest.py | With `--allow-remote-unauthenticated --host 0.0.0.0` the Host allow-list contains `0.0.0.0` but clients reach the server by another name, so remote requests get 400 until the operator binds the specific address; seam authentication is still absent (open decision) |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ROADMAP criterion 3 holds for the REST seam. 08-10 can run the RUN-08 rows: `test_rest_cors.py` imports phase-created names inside test bodies and collects on the pre-phase tree.
- Seam authentication remains an open owner decision for the CONN phases.

## Self-Check: PASSED

- Files exist: `databasise/seam/rest.py`, `databasise/launcher/__init__.py`, `databasise/launcher/serve_rest.py`, `databasise/launcher/serve_mcp.py`, `databasise/tests/seam/test_rest_cors.py`, `databasise/tests/launcher/test_bind_guard.py`
- Commits present: `7decfc3`, `4f878d7`, `bc3a0dc`, `ba29658`, `4eb4500`, `8ef42bb` (6, measured from the plan ledger)
- Acceptance greps: `cors_origins: Sequence[str] = ()` and `allow_methods=["GET", "POST", "DELETE"]` one line each in `rest.py`; `allow_credentials` absent; `cors_origins=args.cors_origin or ()` one line in `serve_rest.py`
- Verification: `tests/seam/test_rest_cors.py` 18 passed (at least 18 required)

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*
