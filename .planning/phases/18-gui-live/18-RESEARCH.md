# Phase 18: GUI Live - Research

**Researched:** 2026-10-31
**Domain:** Porting a frozen single-file HTML/JS operator console from fixtures to a live FastAPI app (same-origin serving, fetch/SSE transport, run-time badge rule, Playwright-driven live tests)
**Confidence:** HIGH (every API shape, wire format and harness technique below was run against the real app and the installed Chromium this session; the large unknown is effort, not feasibility)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### A. Serving, binding and build stack (LIVE-01; roadmap open questions 4 and 5)
- **D-01 (serving):** The launcher serves the built console from the same origin as the REST app. A new `databasise-rest --console` flag adds one route, `GET /console`, in the launcher's `build_app` (serve_rest.py), next to the TrustedHost and Origin guards. The route returns the single built HTML file with `include_in_schema=False`, so `/openapi.json` and the §18 surface tests do not change. Without the flag the app is unchanged (same pattern as Phase 16 D-01). No `StaticFiles` mount is needed, because the build is one file.
  - **Why:** same origin needs no `--cors-origin`, and the existing Origin guard already admits `http://127.0.0.1:<port>` and `http://localhost:<port>` (serve_rest.py `own`), so state-changing POSTs from the page pass with no CORS change.
- **D-02 (bind and auth):** `--console` with a non-loopback `--host` is a `parser.error`, the same rule as `--operator` (Phase 16 D-01 host rule), even with `--allow-remote-unauthenticated`. There is no authentication; loopback bind, TrustedHost and the Origin guard are the protections (Phase 8, Phase 16 D-10). `--console` does not imply `--operator`: without `--operator` the operator controls keep their badges (D-08), which is also how LIVE-09 is tested in both directions. The documented operator invocation is `databasise-rest --operator --console --log-file PATH` plus the usual store root, workspace and client arguments.
- **D-03 (build stack and location):** The live console is plain HTML, CSS and JavaScript, ported from the mockup sources. Its sources live in a new package directory `databasise/console/src/` (a copy of `mockups/src/` taken at the frozen commit), and the built file is `databasise/console/operator-console.html`, checked in and shipped as package data (add `databasise.console` to `[tool.setuptools] packages` and the HTML to package-data). The launcher reads it through `importlib.resources`. `mockups/build.py` gets `--src` and `--out` arguments whose defaults keep today's paths, so `mockups/build.py --check` still reproduces the approved bytes and the same script builds and `--check`s the console.
  - **Why:** `scripts/mockup-id-check.py` skips `mockups/`, `tests/`, `dist/` and `build/`, so the live source must sit elsewhere; `databasise/console/` is scanned. Once frozen, the mockup file must stay byte-identical (the checker compares its sha256), so the live source must be a separate copy that can diverge. A React port would rewrite about 4,500 lines of working JS and adds a toolchain the project does not have.
- **D-04 (freeze order, plan 1):** The first plan, in this order:
  1. checks `sha256sum mockups/operator-console.html` equals `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20` from docs/gui/MOCKUP-APPROVAL.md (verified equal on 2026-10-31 during this discussion, and `mockups/build.py --check` exited 0); a different digest stops the plan for a new owner approval;
  2. copies `mockups/src/` to `databasise/console/src/` and builds `databasise/console/operator-console.html` with no other change, so every frozen id is present;
  3. runs `python3 scripts/ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html`;
  4. runs `scripts/mockup-id-check.py` and requires exit 0.
  - **Why:** once `mockup_freeze` is set, the completion gate runs the id check, which exits 1 for every frozen id missing from a scanned UI source. Copying before freezing keeps the gate green between plans. No id is renamed, so no MOCKUP-PORT.md is created unless a later plan needs a mapping.

### B. Fixture-to-live transport and the frozen ids and badges (LIVE-02, LIVE-07, LIVE-09)
- **D-05 (transport layer):** One shared transport in the console source, `api(method, path, body, opts)`, returns `{status, body}` and is the only place that calls `fetch`. Every screen replaces its fixture lookup plus `setTimeout` with a call to it and passes the result to the existing `classifyResponse` and `renderError` (10-shared.js). Upload uses the same function with a `FormData` body. Each call takes an `AbortSignal` (D-14).
- **D-06 (mock-only controls):** The 12 `*.mock.*` ids (including `shell.mock.banner` and `shell.mock.health-fixture`) stay in the live source and are hidden in the live build (`hidden` attribute set at start-up). Their ids remain in the scanned source, so LIVE-09's "no mockup control is removed" and the id check both hold. No live screen ever renders fixture data as server data. Embedded fixtures that are real catalogues stay embedded: `refusals.json` (Phase 16 D-07, 17 D-04) and `selector-resolution.json` (Phase 16 D-08, 17 D-06).
- **D-07 (client-side state):** The run history (`{query, selector, trace_token, timestamp}` per query and per compare column, LIVE-02), the client-side job list (LIVE-05) and the client-side ledger log (LIVE-07) are kept in memory and mirrored to `sessionStorage`, wrapped in try/catch, so a reload in the same tab keeps them. The evidence cache keyed on `(namespace, ref)` (LIVE-04) is in memory only, for the page's lifetime.
- **D-08 (badge rule):** At start-up the console fetches `GET /openapi.json` once. For each element with `data-needs-backend`, the value's method and path template are matched against the spec's `paths`. When the operation is present and the control is wired, the console removes `data-needs-backend`, `data-backend-state` and the badge. A value with a parenthesised qualifier (for example `GET /corpus (status, sort, search)`) keeps its badge unless every named parameter appears in that operation's parameters. If `/openapi.json` fails to load, every badge stays. The rule runs on the live server's spec, never on GAP-ROUTES.json, so the same build is correct with and without `--operator`.
- **D-09 (absent routes):** A control whose route is absent stays visible and badged. Where the requirement names a client-side fallback, it uses it: the alias, version and trace pickers and the promote preview fall back to the client-side ledger log and run history (LIVE-07; Phase 16 open questions 2 and 3). Every other absent-route control is disabled with a tooltip naming the route. It does not show fixture data. The selector `Resolves to` preview keeps using the embedded resolution table (D-06), because `POST /selectors/resolve` does not exist.

### C. Live request semantics: streaming, errors, polling and in-flight (LIVE-02 to LIVE-06, LIVE-08)
- **D-10 (streaming):** `POST /query/stream` is read with `fetch` and a `ReadableStream` SSE parser, as LIVE-02 states. Before parsing, the parser checks `res.ok` and that the content type starts with `text/event-stream`. Otherwise it reads the JSON body and renders it through `renderError`. Lines starting with `:` are ignored, which covers `: ping`. `evidence` events append rows, and the `final` event completes the run (`stream_envelope_events`, engine.py:1104). A stream that ends without a `final` event shows the existing `q-stream-disconnected` state. The result panel shows `Run complete.` and enables Promote only after `final` (WR-JSA-05).
- **D-11 (compare parsing):** A compare sent with one selector is parsed as a bare envelope and shown as one column. With two or more it is parsed as a map keyed by the server's comparison key, and each column is filled from its own key. Each column's Open trace and Promote use that column's own `trace_token` (WR-JSA-06). `Compare.run` re-checks every blocker before it sends (WR-JSA-02, D-17).
- **D-12 (errors):** All responses go through `classifyResponse`, which branches on `refusal_type` and never on status alone (GUI-06, 17 D-09). The refusal banner prints the real HTTP status (404 for the SEAM-04 lookups, 409 for store-busy and write overlap, 422 otherwise) instead of a fixed `422` (IN-JSA-09). A rejected `fetch` (server down, connection reset) renders the generic error state with the text "server unreachable" and sets the header health to `unreachable`. On a 5xx, when `GET /log` is in `/openapi.json`, the existing `*.error.server-log` region loads `GET /log?limit=200`; otherwise that region keeps its badge (Phase 16 D-18, D-19). On the Graph screen, `StoreBusyError` renders `graph.state.store-busy` and `UnknownGraphNodeError` renders the unknown-node state (LIVE-08; Phase 16 D-15, D-16).
- **D-13 (in-flight gate and polling):** One shared in-flight registry in the console source counts calls by kind: query, compare, ingest, delete. While an ingest or delete is in flight, Query and Compare Run are disabled (LIVE-05). The Phase 17 blocking style applies (17 discretion: query Run clickable with an inline message). Header health loads `GET /health` once on page load and shows the `checking` state for up to 60 s (LIVE-01). Health polling stays off by default (17 discretion) and, when enabled, runs at the selected 30 to 60 s interval and skips any tick while any call is in flight (LIVE-06). Counts poll only while a non-terminal status count is above zero. The jobs poll runs only while the jobs drawer is open on the Documents screen and stops at a terminal status (IN-JSB-05). When `GET /info` is present, the header store-busy field reads `write_in_flight` and `graph_busy` with each health load and labels `graph_busy` "in use" (Phase 16 D-17). Writes by other clients are not predicted. The server's 409 refusal renders through D-12.
- **D-14 (cancellation):** Every call takes an `AbortController`. A new Run, a mode switch between Query and Compare, or leaving a screen aborts that screen's pending reads (WR-JSA-04). A write (ingest, upload, delete, promote, rollback, retire) is never aborted after it is sent, and a dialog's Cancel or Escape before Confirm sends nothing (WR-JSB-02, IN-JSC-04). An aborted evidence resolve restores its opener button (IN-JSB-08).
- **D-15 (LIVE-05 stores notice, roadmap open question 8):** No "different stores" notice is added. Phase 11 D-01 settled M-04 as option b, with a v1-to-v2 import after every LightRAG ingest and delete, and LRAG-02 is complete. The mockup has no such notice, so adding one would change a frozen screen. After a delete, the corpus table and counts re-fetch `GET /corpus` and `GET /corpus/counts`. The live test asserts that refresh. It also asserts that a query after ingest returns evidence from the ingested document.

### D. Phase 17 review findings and verification
- **D-16 (fixes go only into the live source):** After D-04 the mockup and `mockups/src/` stay as approved. Every Phase 17 finding that Phase 18 absorbs is fixed in `databasise/console/src/` only. Each absorbed row is then set to `fixed in Phase 18 (<plan>)` in `.planning/phases/17-gui-mockup/17-REVIEW-DISPOSITION.md`.
- **D-17 (absorbed findings: the ones that change live behaviour or real data):**
  - **Query and compare:** WR-JSA-01, WR-JSA-02, WR-JSA-03, WR-JSA-04, WR-JSA-05, WR-JSA-06, IN-JSA-07, IN-JSA-08, IN-JSA-09.
  - **Evidence, documents and corpus:** WR-JSB-01, WR-JSB-02, WR-JSB-03, WR-JSB-04, IN-JSB-05, IN-JSB-06, IN-JSB-07, IN-JSB-08.
  - **Ledger:** WR-JSC-01, WR-JSC-02, IN-JSC-04, IN-JSC-08.
  - **UI review:** Top-3 fix 2 (`white-space: nowrap` on the ledger badge and timestamp cells, plus a min-width on the Status column).

  WR-JSC-01 follows the server: `active` is true for the head row and for the target of an active rollback, and `tombstoned` is true on the tombstone record itself. The head row is the active row with the highest `generation_ordinal`. Every other active row reads `target of active rollback`.
- **D-18 (findings not absorbed):** Three findings concern only mockup fixtures and do not apply to live data: IN-JSC-05, IN-JSC-06, IN-JSC-07. Each is recorded as `n/a in live (fixture-only)`. The test and build findings stay with the Phase 17 disposition: WR-BLD-01, WR-TST-01 to 03, WR-JSC-03 (the same as TST-03), IN-BLD-02 to 05, IN-JSB-09, IN-TST-04 to 08. Phase 18 does not edit the Phase 17 test files. One exception: the new live suite's conftest fails the test itself, not its teardown, on a page error (the IN-BLD-04 pattern), and has a test that covers the inspector's Open trace link and a confirmed delete (the IN-JSB-09 gap) on live data.
- **D-19 (live test harness):** A new pytest and Playwright module set under `databasise/tests/gui_live/` starts the REST app in-process with uvicorn on an ephemeral 127.0.0.1 port. It uses a temp store root, `--operator --console` equivalents, stub clients and the substituted corpus op used by the existing seam tests. There is no provider spend, and `-m live` is never used (Phase 16 F). Store-busy is produced by holding a raw `pycozo.Client("rocksdb", path)` (Phase 16 D-15). The LIVE-09 badge test runs the same build against an app without `--operator` and against one with it. The Phase 17 suite keeps targeting the frozen mockup unchanged. Playwright and its browsers come from 17 D-01 and D-15; no new dependency.
- **D-20 (owner verification):** The last plan is a `checkpoint:human-verify`. The owner starts the launcher bound to 127.0.0.1 with real clients and opens `http://127.0.0.1:<port>/console`. The owner then walks the five success criteria: query, stream and compare, evidence and trace, ingest/upload/delete, promote then query through the alias then rollback and retire, graph browse, and badges.

### Claude's Discretion
- How plans are split and ordered, provided D-04 is plan 1 and D-20 is last.
- The exact `GET /log` limit used in the 500 state (D-12 says 200; any value in 1..1000 is allowed).
- Whether the hidden mock-region code paths keep their demo fixtures embedded or are reduced to inert stubs, provided the ids stay in the source (D-06) and no live screen reads them.
- Whether alias rows from `GET /ledger/aliases` also feed the `Resolves to` preview for alias selectors.
- The `sessionStorage` key names and size cap for D-07.

### Deferred Ideas (OUT OF SCOPE)
- Authentication or a reverse proxy with auth for non-loopback use. Seam auth is still undecided (PROJECT.md key decisions).
- A Vite dev proxy or a React 19 + Vite + Sigma.js rebuild of the console.
- Graph visualisation (Sigma.js) on the Graph/vector browser. The screen stays a paged table browser.
- Server routes still missing: `POST /selectors/resolve`, `GET /refusals`, `POST /graph/node/attrs`, `POST /stores/counts`, `GET /jobs`, `GET /pipeline`, `POST /evidence/resolve-batch`, `POST /documents/reprocess`, `POST /jobs/{job_id}/cancel`, and the `/corpus` status/sort/search parameters.
- Fixing the Phase 17 test and build findings listed in D-18 (a Phase 17 fix round).
- Dark theme (17 Deferred).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-01 | Console served same-origin by the launcher on 127.0.0.1; fetch POST /query completes 200 with no CORS error; header health shows live GET /health on load | `GET /console` route in `build_app` (D-01); Origin guard `own` set admits the page's origin (verified serve_rest.py:77); in-process uvicorn + Chromium run produced 200/200/422 with no CORS text (Verified Point 4); `/health` shape verified |
| LIVE-02 | Live POST /query, /query/stream, /compare; SSE parser checks status+content type, ignores `: ping`, shows disconnected state; compare bare-vs-map; client history | Wire format of the stream verified (no `event:` field, `kind` inside `data:`); ping analysis (Verified Point 1); compare Default must be `{}` not `null` (Pitfall 1); truncation test technique verified |
| LIVE-03 | Real refusal 422, validation 422, 500 render through GUI-06 states on every connected screen | `classifyResponse`/`renderError` reuse; real validation shape `{detail:[{loc,msg,type}]}` with `loc` mapping to `data-field-loc` (14 values listed); real 500 via a raising engine method |
| LIVE-04 | POST /evidence/resolve with EvidenceRef copied unchanged; per-(namespace,ref) cache; POST /trace/resolve with debug re-request | The mockup emits `{id,namespace,kind}`; the server needs `{ref,namespace,kind,score,tier}` and refuses `id` as `extra_forbidden` (Pitfall 2); real record and trace shapes match the mockup fixtures key for key |
| LIVE-05 | POST /documents, /documents/upload, GET /jobs/{id}, DELETE /documents/{id}; job list; Run disabled during write; corpus+counts refresh after delete | POST /documents blocks until committed (Verified Point 2); DELETE carries `{selector}` in a body; upload progress cannot be real over fetch (Pitfall 7) |
| LIVE-06 | GET /health, /corpus, /corpus/counts; health poll 30-60 s only when enabled and idle; counts poll only while non-terminal > 0; paging by next_offset | Response shapes verified; Playwright `page.clock` exists in 1.59.0 so polls are testable without 30 s waits; `JobStatus` has no `offset`/`total` (client tracks offset) |
| LIVE-07 | POST /promote, /rollback, /retire; client-side ledger log; follow-up POST /query {alias}; pickers read aliases/history/traces/preview with fallback | Full promote -> alias query -> history -> rollback -> retire path ran offline on the HippoRAG stub; `/ledger/aliases` rows carry no arm; head-row logic for WR-JSC-01 needs the alias row, not page position (Pitfall 9) |
| LIVE-08 | POST /graph/nodes, /graph/node, /chunks with a selector; paging by next_offset; store-busy refusal while graph held | Shapes verified (no `offset` echoed); pycozo busy recipe verified in an existing test (Verified Point 5); fixed row slots must become dynamic (Pitfall 3) |
| LIVE-09 | `data-needs-backend` + badge kept exactly when route absent from live /openapi.json; no control removed; `mockup-id-check.py` exit 0 | 54 attributes in the built file (32 instances of 10 operator routes, 22 instances of 10 never-present routes; see the Badge Matrix); badge markup has two classes and several shapes; id-check mechanics verified (Pitfall 5, 6) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Project CLAUDE.md (`.claude/CLAUDE.md`): Databasise 2.0 is Python, runs on local NixOS (host legion), embeddable in-process, no external DB servers, no Docker. The §18 seam must stay modality-agnostic. Evidence standard: no benchmark number settles a decision (not engaged by this phase).
- GSD workflow enforcement: file-changing work goes through a GSD command (this phase is executed through `/gsd-execute-phase`).
- Global `~/.claude/CLAUDE.md`: file references in answers are markdown links with workspace-relative targets, no spaces in new file names; plain technical language; simple lists first.
- Project skill `spike-findings-rag-graph-vector-raw` exists; it covers the RAG system model, not the console, so it does not constrain this phase.
- Run-environment rules given for this phase: never edit `databasise/tests/` from a research or non-test plan task and never edit `ledger/` by hand (the only writer is `scripts/ledger-amend.py`); never read `.env*` or `v1/parity-env.txt`; no provider spend; no `-m live`.
- **Edit guard (verified by running into it, not by reading docs):** `/home/chris/coding/GUI-research/adapters/claude-code/hooks/check-edit-guard.py` blocks any Bash command that has shell operators (`&&`, `;`, `|`, `\|` inside quotes) and names a path that is a protected file or an ancestor folder of one, and it blocks Edit/Write on protected paths. Protected = every `test_ref` file in the rows, every `check_locks.files` entry, `check_guard` entries (empty) [VERIFIED: ledger/REQUIREMENTS.json:2376-2531]. Consequence for executors: prefer Read/Edit/Write and single read-only commands with absolute paths; `cd X && grep ... databasise/tests` fails.

## Summary

The port is feasible with the stack already in the repo and no new dependency. The mockup is a single-script, global-scope program in which every screen funnels its rendering through a small number of functions (`applyResponse`, `renderError`, `renderTimeline`, `showPage`, ...) and drives fixtures through `setTimeout` plus a `mock.outcome` select. Replacing the fixture source with the shared `api()` transport (D-05) is mechanical for rendering. The real cost is in four places the context file does not name: fixed row slots (every table has 3 to 8 pre-built rows while the live page size defaults to 50), per-slot event binding that must become delegation, the evidence request body shape (the mockup invents `{id,...}`; the server needs the envelope's `EvidenceRef`), and the compare Default selector (`{}`, not `null`).

Both open points are answered from code. (1) `: ping` is a FastAPI keep-alive that fires only after 15 s of idle between yielded items; `/query/stream` resolves the whole envelope before the response starts and then yields all events back to back, so a ping is not emitted in practice, but the parser must still skip comment lines. (2) `POST /documents` and `POST /documents/upload` await the full run and the store commit and return the `IngestJob` afterwards, so D-13's assumption holds: the fetch is in flight for the whole write. Playwright 1.59.0 drives an in-process uvicorn app fine when uvicorn runs in a daemon thread on a pre-bound socket (uvicorn skips signal handlers off the main thread). The raw `pycozo.Client("rocksdb", path)` lock produces a real HTTP 409 `StoreBusyError` with `store_kind: "graph"`; the existing test shows the recipe, and starting busy before the engine's first graph read avoids touching private attributes.

The whole flow for LIVE-02/04/05/07/08 can be exercised offline using the HippoRAG path with the stub clients from `test_hipporag_write_path.py` (ingest, query, evidence, trace, promote, alias query, history, graph nodes, chunks all ran green in a scratch script). The LightRAG-default path (Corpus table, counts, jobs, health) needs the same monkeypatched `run_corpus_op` fake that the seam tests use. One LightRAG-specific requirement in D-15 ("query after ingest returns evidence from the ingested document") cannot be met offline on the default path; it is met on the HippoRAG selector.

**Primary recommendation:** build the shared core first (transport, in-flight registry, openapi badge pass, health, dynamic-row helper, event delegation, mock hiding), then port screens one plan each in sequence (they all rebuild the same checked-in HTML), with the live Playwright harness (pre-bound-socket uvicorn thread, module-scoped Chromium, failing-on-page-error) landing before any screen plan so each screen plan is fail-first.

## Answers to the open points the discuss step left unchecked

### 1. Does `/query/stream` emit `: ping` lines?

Only when the stream has been idle for 15 s, and in this app it effectively never does. Evidence:

- `KEEPALIVE_COMMENT = b": ping\n\n"` and `_PING_INTERVAL: float = 15.0` [VERIFIED: .venv/lib/python3.12/site-packages/fastapi/sse.py:236-241].
- The inserter wraps `await receive_stream.receive()` in `anyio.fail_after(_PING_INTERVAL)` and sends `KEEPALIVE_COMMENT` on `TimeoutError` [VERIFIED: fastapi/routing.py:589-602].
- The route resolves the whole envelope first: `async def _resolve_streamed_envelope(body: QueryRequest) -> ResponseEnvelope: ... return await engine.query(body.query, body.selector)`, used as `envelope: ResponseEnvelope = Depends(_resolve_streamed_envelope)`, then `for event in stream_envelope_events(envelope): yield event` [VERIFIED: databasise/seam/rest.py:404-433]. So the response headers only arrive after the query has finished, and the events are yielded without any await between them.
- Consequences for the plan: (a) the "streaming" UI is cosmetic, time-to-first-byte equals full query latency, and the in-flight gate must cover the whole `fetch`; (b) the parser still must ignore any line starting with `:` (spec comment), tolerate `\r\n`, split on a blank line, join multiple `data:` lines, and decode with `TextDecoder({stream: true})`.
- **Wire format** [VERIFIED by running it, scratch probe 3 and 5]: `data: {"kind": "evidence", "evidence": {"ref": "...", "namespace": "hipporag-chunks", "kind": "text_chunk", "score": 0.14285714285714285, "tier": null}}` then a blank line, then `data: {"kind": "final", "answer": ..., "trace_token": ..., ...}`. There is **no `event:` line**; dispatch on `JSON.parse(data).kind` [VERIFIED: fastapi/routing.py:545-551 plain objects go through `format_sse_event(data_str=...)` with no event name; engine.py:1114-1115 `yield {"kind": "evidence", "evidence": ref.model_dump()}` and `yield {"kind": "final", **envelope.model_dump(exclude={"evidence"})}`]. Content type is `text/event-stream; charset=utf-8`, so check with `startsWith`.
- A refusal on `/query/stream` is raised before the first byte, so it arrives as a normal JSON 4xx body, not an SSE frame; this is why D-10 checks `res.ok` and content type first.

### 2. Does POST /documents block until the write finishes?

Yes. `Databasise.ingest` builds the run, calls `_run_corpus_ingest`, which holds the gate through `_run_wiring`, `_commit_all` and `_narrow_sync_manifest`, and only then constructs `IngestJob(job_id=..., enqueued=...)` and returns it [VERIFIED: databasise/seam/engine.py:1530-1636; the `async with contextlib.AsyncExitStack() as gate:` block spans the run and commit, and `job = IngestJob(` is reached after `_commit_all(stores, "ingest", self.store_root)` at line 1592]. The REST route is `return await engine.ingest(body.document, body.selector)` [VERIFIED: rest.py:443-445]. `POST /documents/upload` reads the file bytes, builds the `IngestDocument` and makes the same awaited call [VERIFIED: rest.py:447-489]. `delete_document` and `retry_document` follow the same shape (gate entered at engine.py:1817-1824).

Practical consequences:
- The `fetch` promise settles only after the commit; the in-flight registry entry for kind `ingest` or `delete` is exactly the write window. No polling is needed to know when it ended.
- The write gate is a refuse-at-once lock for LightRAG (`StoreBusyError(store_kind="corpus")` 409 when another write holds it, engine.py:859-884) and a queue for HippoRAG (waits up to 900 s, engine.py:891-911). A second ingest sent from another client during an ingest either 409s (LightRAG) or waits (HippoRAG); the UI must render the 409 through the refusal banner.
- A query that overlaps a write can get a graph-level `StoreBusyError` 409 (the writer holds the RocksDB lock). That is the reason for the LIVE-05 gate, and also why the 409 must render cleanly when another client caused it.
- The returned `job_id` is already terminal in practice (the HippoRAG probe: `GET /jobs/{id}` returned `{"counts":{"processed":1}}` immediately). The LightRAG card note ("enqueued is not a success signal; check the job row status") still applies.

### 3. Playwright for Python 1.59.0 driving an in-process uvicorn app (D-20 harness)

Verified end to end this session (scratch probes 2, 3 and 5; the browsers are present at `~/.cache/databasise/playwright-browsers`: chromium-1217, chromium_headless_shell-1217, ffmpeg-1011, firefox-1511, webkit-2272):

1. Bind a socket first: `sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen(); port = sock.getsockname()[1]`. This removes the free-port race and gives the real port **before** the app is built, which is mandatory because `build_app` computes the Origin-guard set from `args.port` (serve_rest.py:77, `own = {f"http://{name}:{args.port}" ...}`). `--port 0` through the launcher would put `:0` into `own` and 403 every browser POST; the live console does not support `--port 0`.
2. Parse real args: `serve_rest.build_parser().parse_args(["--no-clients" | clients, "--store-root", root, "--workspace", "ws", "--operator", "--console", "--port", str(port)])`, then `app = serve_rest.build_app(args, clients)`. Pass stub clients as the second argument.
3. Run uvicorn in a daemon thread: `server = uvicorn.Server(uvicorn.Config(app, log_level="warning")); threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()`; wait on `server.started`; stop with `server.should_exit = True` then `join`. uvicorn installs signal handlers only on the main thread [VERIFIED: uvicorn/server.py:323-326 `if threading.current_thread() is not threading.main_thread():`]. uvicorn 0.52.4, fastapi 0.141.1, starlette 1.6.0 [VERIFIED: `.venv` import].
4. Browser: reuse the Phase 17 recipe (module-scoped `sync_playwright().start()`, `pw.chromium.launch()`, env `PLAYWRIGHT_BROWSERS_PATH` and `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1`) [VERIFIED: databasise/tests/gui/conftest.py:39-67]. Module scope matters: "a live sync_playwright keeps its event loop registered, which breaks every async test that runs after tests/gui in the same session" (conftest.py:39-40). `new_context()` with the default online mode (Phase 17 used `offline=True`; live must not).
5. Result of the scratch run: a page served by the launcher app at `/console` fetched `/health`, `/info` and `POST /query` and received `200 200 422` with no CORS failure. Chromium logs a console `error` for every 4xx/5xx response ("Failed to load resource: the server responded with a status of 422"), so a live test must not assert "no console errors"; assert **no `pageerror`** and no console text containing `CORS` or `Access-Control`.
6. Time control: `page.clock` exists in 1.59.0 with `install`, `fast_forward`, `run_for`, `pause_at`, `set_fixed_time`, `set_system_time` [VERIFIED: `playwright.sync_api._generated.Clock` attributes]. Use `page.clock.install()` before `goto` and `fast_forward` to fire the 30-60 s polls without waiting.
7. Stream edge cases against the real server: `page.route("**/query/stream", handler)` where the handler calls `route.fetch()` and `route.fulfill(response=resp, body=<first frame only>)`. Run against the live app this produced `kinds: ['evidence']` (no `final`) for the truncated case and `['evidence', 'final']` untouched [VERIFIED scratch probe 5]. This gives the "early-closed stream shows disconnected" criterion a real-server test.
8. Real error shapes without fakes: refusal 422 = ordinary bad input (empty capability, unknown alias `{"alias": "x"}` gives `UnsatisfiableSelectorError`); validation 422 = rewrite the request body in a `page.route` handler with `route.continue_(post_data=...)` so the real server answers `{"detail":[{"loc":["body","query","text"],...}]}`; real 500 = replace `app.state.engine.query` with an async function that raises, which makes Starlette answer `500 Internal Server Error` text.

### 4. How a raw pycozo lock produces the store-busy state

The existing test does it and passes: build the graph, `finalize()` the store, then `held = pycozo.Client("rocksdb", str((root / "ws" / "chunk_entity_relation" / "graph.cozo").resolve()), dataframe=False)`, call `POST /graph/nodes`, and observe `409` with `refusal_type == "StoreBusyError"` and `store_kind == "graph"`; `held.close()` releases it [VERIFIED: databasise/tests/seam/test_console_graph.py:75-90]. The test also releases the engine's own earlier read-hold first: `for key in client.app.state.engine._graph_holds: _ClientRegistry.release(key)` then `.clear()` (lines 79-82), because an engine that already read the graph holds its own client. Two ways for the live suite:

- Preferred: hold the raw client **before the engine's first graph read** in that module's app (fresh `store_root` per module or per test), click Load, assert `graph.state.store-busy` is shown, then `held.close()` and click `graph.state.retry`; no private attribute is touched.
- Fallback: copy the release dance (touches `engine._graph_holds` and `databasise.stores.graph._ClientRegistry`, both private).

HippoRAG's graph namespace is `hipporag-graph` (`.../ws/hipporag-graph/graph.cozo`); the default LightRAG one is `chunk_entity_relation`. `GET /info` `graph_busy` does **not** see a raw client (it is "in use in this process" via the registry only: engine.py:2124-2140), so the header "in use" label is not reachable through a raw client; the 409 banner is.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Serving the console HTML | Frontend Server (launcher `build_app`) | Package data (`importlib.resources`) | Same-origin, one file, loopback only; a launcher concern outside the §18 thin-adapter AST scope |
| Origin / Host protection of state-changing calls | API / Backend (launcher middleware) | Browser (sends `Origin`) | Already exists (serve_rest.py:68-87); the console relies on it, must not add CORS |
| Request transport, abort, in-flight registry, polling | Browser / Client | — | Pure client state; the server has no cancel or queue |
| SSE parsing | Browser / Client | API (FastAPI `EventSourceResponse`) | Server emits plain `data:` frames; client dispatches on `kind` |
| Badge rule (`data-needs-backend`) | Browser / Client | API (`/openapi.json`) | Decided at run time from the live spec so the same build serves both launch modes |
| Selector `Resolves to` preview | Browser / Client (embedded table) | — | `POST /selectors/resolve` does not exist (D-09) |
| Run history, job list, ledger log | Browser / Client (`sessionStorage`) | API (`GET /traces`, `GET /ledger/aliases`, `POST /ledger/history` when present) | Client log is the fallback and the label source (selector per trace) |
| Head-of-alias determination for the timeline | API (`GET /ledger/aliases` row) | Browser | Page position is unreliable when the timeline is paged (Pitfall 9) |
| Write gating (single graph lock) | API (engine write gate, 409) | Browser (disable Run while in flight) | Browser gate is a courtesy; the server remains the authority |
| Live test harness | Test (in-process uvicorn thread + Chromium) | — | D-19; no provider spend |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Plain HTML/CSS/JS (browser-native `fetch`, `ReadableStream`, `AbortController`, `TextDecoder`, `sessionStorage`, `<dialog>`) | n/a | The live console | Locked by D-03; no toolchain; matches the mockup |
| `mockups/build.py` (stdlib) | repo | Assembles the single file from `src/` | Locked by D-03; add `--src/--out` only |
| FastAPI | 0.141.1 | Existing REST app; `GET /console` is one route in the launcher | [VERIFIED: .venv `fastapi.__version__`] |
| Starlette | 1.6.0 | TrustedHost / middleware (existing) | [VERIFIED: .venv] |
| uvicorn | 0.52.4 | Serves the app (launcher and the test thread) | [VERIFIED: .venv] |
| `importlib.resources` | stdlib | Read `databasise/console/operator-console.html` as package data | Locked by D-03 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| playwright (Python) | 1.59.0 | Live browser tests | Already a dev dependency (pyproject.toml:73 `"playwright==1.59.0"`); chromium-1217 on disk |
| pytest / pytest-asyncio | existing (`asyncio_mode = "auto"`) | Test runner | Live tests are plain sync functions; never use `@pytest.mark.live` (addopts `-m "not live"` would deselect them) [VERIFIED: pyproject.toml:112-116] |
| pycozo | existing | Raw RocksDB lock for the store-busy test | Recipe in Verified Point 4 |
| httpx | existing (`.venv/bin/httpx`) | Seed data / readiness poll from the test thread | Used by test_console_log.py:114-145 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Daemon-thread uvicorn with a pre-bound socket | `subprocess` running `databasise-rest` (test_console_log.py:114-151 pattern) | Subprocess cannot receive stub clients, the stub registry or a patched `run_corpus_op`; it is right for the one "real launcher flag" test only |
| `fetch` upload | `XMLHttpRequest` for real upload progress | Violates D-05 (single `fetch` caller); LIVE-05 does not require progress; use an indeterminate state |
| Dynamic row growth | Clamp page size to the slot count | Contradicts the visible 1..100 page-size control; reject |

**Installation:** none. No package is added (D-19).

**Version verification:** `playwright 1.59.0` via `importlib.metadata.version('playwright')`; fastapi/starlette/uvicorn via the venv, all read this session.

## Package Legitimacy Audit

No external package is installed or recommended in this phase. Playwright 1.59.0 (with greenlet and pyee) was approved by the owner in 17-CONTEXT D-15 and is already in `pyproject.toml`; nothing else is new. The legitimacy gate is therefore not applicable.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 operator's browser (127.0.0.1)
   |  GET /console  (one built HTML, same origin)         GET /openapi.json (once) --> badge pass
   v                                                                 |
 +-------------------- console page (single script) -----------------v----------------+
 | Console shell: nav, hash routing, header health chip, mock-only controls hidden     |
 |   api(method, path, body, {signal})  -- the ONLY fetch caller --> {status, body}    |
 |   InFlight registry {query, compare, ingest, delete}  --> Run gating, poll skipping |
 |   classifyResponse -> renderError (refusal | validation | server-failure | generic) |
 |   AliasCatalog / RunHistory / JobList / LedgerLog (memory + sessionStorage)         |
 |   Screens: Query+Compare | Evidence+Trace | Documents | Corpus+Health | Ledger | Graph|
 +--------+----------------------------------------------------------------------------+
          | JSON / multipart / SSE over same-origin fetch
          v
 launcher app (databasise.launcher.serve_rest.build_app)
   TrustedHost(localhost,127.0.0.1,[,bound host) -> Origin guard (non-GET needs own origin)
   +-- GET /console (include_in_schema=False)           [new, --console only]
   +-- create_app routes: /query /query/stream /compare /evidence/resolve /trace/resolve
   |      /documents /documents/upload /jobs/{id} /documents/{id} (DELETE, retry) /health
   |      /corpus /corpus/counts /promote /rollback /retire
   +-- operator routes (--operator): /info /wirings /ledger/aliases /ledger/history /traces
   |      /promote/preview /chunks /graph/nodes /graph/node  (+ /log with --log-file)
          v
 Databasise engine (one per process)  --> stores (RocksDB graph, Faiss, sqlite), ledger.db,
                                           trace store, v1 corpus driver subprocess (LightRAG)
```

Test harness path: pytest (sync) -> pre-bound socket -> `build_app` + daemon-thread uvicorn -> module-scoped Chromium -> `page.goto(f"http://127.0.0.1:{port}/console")`.

### Recommended Project Structure
```
databasise/console/
├── __init__.py                 # makes databasise.console a package (D-03)
├── operator-console.html       # built, checked in, package data
└── src/                        # copy of mockups/src at the frozen commit (D-04), then diverges
    ├── page.html  css/  dialogs/  fixtures/  parts/  screens/
    └── js/  00-app.js 10-shared.js [new: 05-api.js] 20-query.js ... 70-graph.js
databasise/tests/gui_live/
├── __init__.py
├── conftest.py                 # server thread, browser (module scope), LiveUI, page-error-fails-the-test
├── _corpus_fake.py             # stateful run_corpus_op fake + stub registry (reuse seam helpers)
└── test_live_0N_*.py           # one per LIVE row
mockups/build.py                # gains --src/--out only; default bytes unchanged
```
Note `js/*.js` are concatenated in sorted glob order (`<!--@glob js/*.js-->`, build.py:71-73), so a new transport file must sort before the screens (for example `05-api.js`) and after `00-app.js` only if it needs `FIX`/`$id`.

### Pattern 1: The single transport (D-05)
**What:** one function, one `fetch`, always resolves (never throws) so every caller feeds `classifyResponse`.
```javascript
// Source: designed for this phase; behaviour checked against the live app (scratch probes 2-5).
var InFlight = { counts: {}, begin: function (kind) { this.counts[kind] = (this.counts[kind] || 0) + 1; Console.emit("inflight"); return function () { InFlight.counts[kind] -= 1; Console.emit("inflight"); }; }, any: function () { return Object.keys(this.counts).some(function (k) { return InFlight.counts[k] > 0; }); } };
function api(method, path, body, opts) {
  opts = opts || {};
  var init = { method: method, headers: {}, signal: opts.signal };
  if (body instanceof FormData) init.body = body;                     // never set Content-Type: the browser adds the boundary
  else if (body !== undefined && body !== null) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  var done = opts.kind ? InFlight.begin(opts.kind) : function () {};
  return fetch(path, init).then(function (res) {
    if (opts.raw) return { status: res.status, res: res };            // the stream reader needs the Response
    return res.text().then(function (text) { var parsed = text; try { parsed = JSON.parse(text); } catch (e) {} return { status: res.status, body: parsed }; });
  }, function (err) { return err && err.name === "AbortError" ? { status: -1, aborted: true } : { status: 0, body: "server unreachable" }; })
    .then(function (r) { done(); return r; });
}
```
`status: 0` with a string body already renders the generic state (`fillGeneric`, 10-shared.js:292-298 prints "No response from the server." for status 0 unless `opts.text` is given) and `healthState` maps a numeric `status` to `error` (00-app.js:43-46).

### Pattern 2: SSE reader (D-10)
```javascript
function readStream(res, onEvidence, onFinal) {          // res.ok and content type were already checked
  var reader = res.body.getReader(), dec = new TextDecoder(), buf = "", sawFinal = false;
  function frame(text) {
    var data = text.split(/\r?\n/).filter(function (l) { return l.indexOf("data:") === 0; }).map(function (l) { return l.slice(5).replace(/^ /, ""); }).join("\n");
    if (!data) return;                                   // comment-only frame (": ping") or empty
    var ev = JSON.parse(data);
    if (ev.kind === "evidence") onEvidence(ev.evidence); else if (ev.kind === "final") { sawFinal = true; onFinal(ev); }
  }
  return (function pump() {
    return reader.read().then(function (r) {
      if (r.done) { if (buf.trim()) frame(buf); return sawFinal; }   // false => render the disconnected state
      buf += dec.decode(r.value, { stream: true });
      var m; while ((m = buf.match(/\r?\n\r?\n/))) { frame(buf.slice(0, m.index)); buf = buf.slice(m.index + m[0].length); }
      return pump();
    });
  })();
}
```
A `final` payload has the envelope fields minus `evidence`; rebuild the envelope as `Object.assign({}, final, {evidence: collected})` before `renderResult` and drop `kind`.

### Pattern 3: Run-time badge rule (D-08)
```javascript
function applyBadges(spec) {                              // spec === null when /openapi.json failed: change nothing
  if (!spec) return;
  Array.prototype.forEach.call(document.querySelectorAll("[data-needs-backend]"), function (el) {
    var m = /^(GET|POST|PUT|DELETE)\s+(\S+)(?:\s*\(([^)]*)\))?\s*$/.exec(el.getAttribute("data-needs-backend"));
    if (!m) return;
    var op = spec.paths && spec.paths[m[2]] && spec.paths[m[2]][m[1].toLowerCase()];
    if (!op) return;                                       // absent: keep attribute and badge (and apply D-09 disabling)
    if (m[3]) { var names = (op.parameters || []).map(function (p) { return p.name; });
      if (!m[3].split(",").every(function (n) { return names.indexOf(n.trim()) >= 0; })) return; }
    if (!WIRED[el.getAttribute("data-needs-backend")]) return;      // present but not wired in this build: keep
    el.removeAttribute("data-needs-backend"); el.removeAttribute("data-backend-state"); el.removeAttribute("title");
    Array.prototype.forEach.call(el.querySelectorAll(".badge-nb, .badge-op"), function (b) { b.remove(); });
  });
}
```
Notes: (1) `/openapi.json` path keys use the same template names (`/jobs/{job_id}`, `/documents/{document_id}`) [VERIFIED scratch probe 1 path list]. (2) The qualifier `GET /corpus (status, sort, search)` is satisfied only if the operation lists parameters named `status`, `sort` and `search`; today `/corpus` has `limit`, `offset`, `selector` (rest.py:519-527), so that badge stays. (3) Badges are not uniform markup: a `<span class="badge badge-op">operator route</span>` child (selector.html:14), a `<span class="badge badge-nb">needs backend</span>` child (errors.html:8), a badge nested in a `<summary>` inside a child panel (corpus.html:187), and a `<div>` wrapper that contains a whole panel (corpus.html:74, 172, 185). Removing only the wrapper's direct badge leaves nested ones; use `querySelectorAll(".badge-nb, .badge-op")` scoped to the wrapper, but do not remove badges that belong to a different, nested wrapper that must keep its own badge (check `closest("[data-needs-backend]") === el`). (4) The `title` attribute ("Mounted only with --operator", "Not implemented yet: ...") must also go or it contradicts the removed badge.

### Pattern 4: Dynamic rows and delegation (needed everywhere)
Every table has fixed slots: query evidence 5 (query.html:196), query history 3 (:295), compare per-column evidence 5 (:263) and columns 4 (:233,238), documents jobs rows 5 and session jobs 3 (documents.html:130,155), corpus rows 6 (corpus.html:153), ledger aliases 3, traces 6, timeline 5 (ledger.html:38,72,138), graph nodes 8, edges 6, chunks 8 (graph.html:85,142,184). Live pages default to 50. Add one helper, `ensureRows(tbody, n)`, that clones the last slot, rewrites its `data-mock-id` numeric suffix, and appends; and replace the per-slot `ID("x.open-" + n).addEventListener` loops with a single delegated listener on the table (`event.target.closest("button")` plus the row index). Cloned ids (`...-9`) are not in the frozen set and are never in static source, so the id check is unaffected [VERIFIED: ID_RE needs a literal `data-mock-id="..."` (mockup-id-check.py:10-15); `setAttribute("data-mock-id", x)` does not match].

### Pattern 5: In-process server fixture
```python
# Source: verified by scratch probes 2, 3, 5 (this research); mirrors databasise/tests/gui/conftest.py browser fixture.
@pytest.fixture(scope="module")
def live_app(tmp_path_factory, request):
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); sock.listen()
    port = sock.getsockname()[1]
    root = tmp_path_factory.mktemp("store")
    argv = ["--store-root", str(root), "--workspace", "ws", "--console", "--port", str(port)]
    argv += ["--operator"] if getattr(request.module, "OPERATOR", True) else []
    args = serve_rest.build_parser().parse_args(argv)
    app = serve_rest.build_app(args, {"embedding": StubEmbedding(), "llm": StubLLM()})
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True); thread.start()
    deadline = time.monotonic() + 30
    while not server.started and time.monotonic() < deadline: time.sleep(0.05)
    assert server.started, "uvicorn did not start"
    yield SimpleNamespace(app=app, port=port, base=f"http://127.0.0.1:{port}", root=root)
    server.should_exit = True; thread.join(15)
```
`default_registry` substitution for ingest/delete without provider or v1 interpreter: `monkeypatch.setattr("databasise.seam.engine.default_registry", lambda: stub_registry)` works because `Databasise.__init__` resolves `registry if registry is not None else default_registry()` at call time [VERIFIED: engine.py:215, 1215]. `monkeypatch` is function-scoped, so use `pytest.MonkeyPatch()` in a module-scoped fixture. Patch `databasise.seam.engine.run_corpus_op` with a closure over a mutable document list for `status`/`health`, exactly as `_patch_status_and_health` does [VERIFIED: test_rest_corpus_endpoints.py:145-170], and import the helpers (`_make_registry`, the stub driver `_run_status`/`_run_health`) rather than re-writing them; importing private helpers across test modules is already done (test_bind_guard.py:106 imports `_patch_health`).

### Pattern 6: Fail the test itself on a page error (D-18 / IN-BLD-04)
Record `page.on("pageerror")` into a list, and check it in a `pytest_runtest_call` hookwrapper (or an autouse fixture finalised in the call phase) so the failure is a test failure, not a teardown ERROR. Do not assert on console `error` messages (see Verified Point 3.5).

### Anti-Patterns to Avoid
- **Reading fixtures in a live path.** The mockup reads `FIX.query`, `FIX.documents`, `FIX.shell.info`, `FIX.aliases`, `FIX.ledger`, `FIX.graph`, `FIX.corpus`, `FIX.health` all over (grep: 20-query.js:28, 30-evidence.js:38,98-104, 40-documents.js:45,247,369-408, 50-corpus.js:137,283,331-387, 60-ledger.js:2,571, 70-graph.js:34,129,137). A leftover read silently shows fiction as data.
- **Wrapping the rejected-fetch case in `try/catch` per screen.** `api()` resolves `{status: 0}`; screens never see an exception (D-12).
- **`innerHTML` with server text.** Evidence content is arbitrary document text. Keep the Pitfall-11 rule (10-shared.js:1: "Text only ever reaches the DOM through textContent").
- **Parallel screen plans that each commit the built HTML** (Pitfall 10).
- **Changing `mockups/build.py`'s default escaping** (IN-BLD-03) in this phase: it would change the frozen mockup's bytes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error shape rendering | A second banner system | `classifyResponse`, `renderError`, `fillRefusal`, `fillValidation`, `fillServerFailure`, `wireErrors` (10-shared.js:196-340) | They already branch on `refusal_type`, map `loc` to `data-field-loc`, and print real status in the footer |
| Refusal catalogue | A fetch of `/refusals` | The embedded `refusals.json` (D-06) | Route absent; catalogue is generated and already embedded |
| Selector resolution preview | Client logic that guesses arms | Embedded `Resolution` table (10-shared.js:48-102) | `POST /selectors/resolve` absent; for aliases show version, not arm (Pitfall 8) |
| Upload multipart | Manual boundary building | `FormData` + `fetch` without a Content-Type header; fields `file`, `document_id`, `selector` (JSON string) | rest.py:447-489 |
| Waiting 30-60 s in tests | `time.sleep` | `page.clock.install()` + `fast_forward` | Verified present in 1.59.0 |
| Timers for in-flight UI | `setTimeout` simulation | the real promise from `api()` | The fixture timers (`LOAD_MS`, `FLIGHT_MS`, `CONFIRM_MS`) must disappear from live paths |
| Free port selection | `bind(0)`, close, reuse | keep the bound socket and pass it to uvicorn (`sockets=[sock]`) | No race; port known before `build_app` |
| Package-data file lookup | `Path(__file__).parent / ...` string paths | `importlib.resources.files("databasise.console").joinpath("operator-console.html")` | Works from a wheel (D-03) |
| Unique ids on cloned rows | Hand-numbered copies in HTML | `ensureRows` clone-and-renumber | Keeps frozen ids 1..N and adds only N+1... |

**Key insight:** the mockup already contains the rendering half of every screen; the work is replacing its simulated data source and its fixed-size, slot-bound structure, not redesigning the UI.

## Live API contract (verified by running the app, scratch probes 1-5)

| Call | Request body | Response (live) | Notes |
|------|--------------|-----------------|-------|
| `POST /query` | `{"query": {"text": "..."}, "selector": null \| {...}}` | envelope: `answer, evidence[{ref,namespace,kind,score,tier}], trace_token, depth_label, partial, degraded, stop_reason, degradation_reason, token_accounting[], seam_events[]` | [VERIFIED: envelope.py:80-99] empty text -> 422 `EmptyQueryObjectError` |
| `POST /query/stream` | same | SSE, see Point 1 | refusal arrives as JSON before any byte |
| `POST /compare` | `{"query": {...}, "selectors": [ {...}, ... ]}` | 1 selector: bare envelope; >=2: map keyed by comparison key | **Default selector = `{}`**; `null` in the list is a 422 `model_attributes_type`; two `{}` -> 422 `DuplicateComparisonKeyError` key `default` |
| `POST /evidence/resolve` | the envelope's EvidenceRef: `{ref, namespace, kind, score?, tier?}` | record: HippoRAG `{id, document_id, ordinal, content}`; LightRAG `{id, full_doc_id, content, file_path}` | `{id,...}` -> 422 `extra_forbidden`+`missing ref`; unknown ref -> 404 `UnresolvableEvidenceReferenceError` |
| `POST /trace/resolve` | `{"trace_reference": t, "debug": false\|true}` | non-debug: `arm_execution_order, bundle_ref, concurrency_setting, corpus_snapshot_hash, degradation_reason, degraded, determinism_setting, executor_version, partial, stop_reason`; debug adds `arm_id, nodes[], run_id, wiring_id, wiring_instance_hash` | node keys equal the mockup fixture's: `allowance, budget_state, cache_hit, cross_process_failure_cause, depth, effective_depth, execution_mode, feed_tier, guards_fired, instance_hash, node_id, realised_budget_share, resumable, spent, status, tier, tokens, wall_clock_ms`; unknown -> 404 `UnknownTraceReferenceError` |
| `POST /documents` | `{"document": {"text": ..., "document_id"?: ...}, "selector"?: ...}` | `{job_id, enqueued, seam_events[]}` after the commit | blocks |
| `POST /documents/upload` | multipart: `file`, `document_id?`, `selector?` (JSON string) | `IngestJob` | selector blank/`null` = none |
| `GET /jobs/{job_id}?limit&offset` | — | `{job_id, documents[{document_id,status,updated_at,error_message}], counts{}, next_offset}` | **no `offset` or `total`** [VERIFIED: corpus.py:273-284] |
| `DELETE /documents/{id}` | optional `{"selector": ...}` | `{document_id, status: success\|not_found\|not_allowed\|fail, message, seam_events[]}` | no selector reaches LightRAG: a HippoRAG doc returns `not_found` (probe 3) |
| `POST /documents/{id}/retry` | optional `{"selector"}` | `IngestJob` | exists, not a gap route |
| `GET /health` | — | `{status: ok\|degraded, stores{"kv:text_chunks": ok\|absent\|corrupted\|busy, ...}, engine{interpreter_present, working_dir_present, v1_reachable}, clients{llm,embedding,rerank}, engine_reason}` | 10 store keys [VERIFIED: probe 4]; HippoRAG-only root reads `degraded` |
| `GET /corpus?limit&offset&selector=<json>` | — | `{documents[], counts{}, total, next_offset}` | selector is a JSON string |
| `GET /corpus/counts?selector=<json>` | — | `{by_status{}, total}` | |
| `POST /promote` `/rollback` `/retire` | `{alias, trace_ids[], change_origin, verb?}` / `+version` | `{alias, version, record_kind, provenance, generation_ordinal}` | `change_origin`: `human_edit` or `machine_mutation` |
| `GET /info` (operator) | — | `{version, workspace, clients{}, write_in_flight, graph_busy}` | |
| `GET /wirings` (operator) | — | rows with `name, wiring_id, wiring_version, title, node_count, effects, provides, harnesses, default_eligible, is_default, reachable` | engine.py:2147-2174 |
| `GET /ledger/aliases` (operator) | — | `[{alias, active_version, record_kind, generation_ordinal, created_at}]` | **no arm** [VERIFIED: test_console_ledger.py:22 `_ALIAS_KEYS`] |
| `POST /ledger/history` (operator) | `{alias, limit, offset}` | `{records[{generation_ordinal, created_at, record_kind, minted_version, targets_version, change_origin, promotion_trace_ids, active, tombstoned}], total, next_offset}`, ascending by ordinal | page bounds -> 422 `PageBoundsError` (limit 0) / `PageSizeExceededError` (101) |
| `GET /traces?limit&offset` (operator) | — | `{items[{trace_reference, created_at, partial, degraded, stop_reason}], total, next_offset}` | newest first |
| `POST /promote/preview` (operator) | same as promote | `{arm, mutation_class, next_version, promotable, reason}` | `reason` = refusal name when not promotable |
| `POST /chunks` (operator) | `{selector, limit, offset}` | `{refs[{ref,namespace,kind,score,tier}], total, next_offset}` | refs can go straight to `/evidence/resolve` |
| `POST /graph/nodes` (operator) | `{selector, prefix, limit, offset}` | `{nodes[{id, degree}], total, next_offset}` | 409 StoreBusy possible |
| `POST /graph/node` (operator) | `{selector, node_id, limit, offset}` | `{id, degree, edges[{src,tgt,edge_types,weight}], next_offset}` | unknown -> 422 `UnknownGraphNodeError` `node_id` |
| `GET /log?limit=1..1000` (operator+`--log-file`) | — | `{lines: [...]}` | redacted |

HTTP status map [VERIFIED: rest.py:124-155]: 409 `StoreBusyError`; 404 for `UnknownTraceReferenceError`, `UnknownJobError`, `UnresolvableEvidenceReferenceError`, `UnknownGenerationVersionError`; 502/503 `ForeignEngineRefusalError` (503 when `failure_class` in `MissingV1InterpreterError, CorpusOpTimeoutError, DriverUnavailable, V1NotConfigured, EnvironmentDigestUnavailable`); 422 for every other refusal. A launcher transport guard answers `403 {"detail": "origin not allowed"}` (serve_rest.py:80-85) and a TrustedHost `400`; both are `generic` shapes in `classifyResponse` because `detail` is a string, not an array.

## Fixture-to-live seam map (what each screen file must change)

| File (lines) | Fixture/simulation seams | Live replacement |
|--------------|--------------------------|------------------|
| `00-app.js` (106) | `FIX.shell.info` chip (line 65); `renderHealth(fixtureName)` reads `FIX.health`; `shell.mock.health-fixture` change handler; `Console.health()` | `/info` or `info.version` from `/openapi.json` for the chip; `renderHealth(report)` fed by `api("GET","/health")` with a 60 s abort; keep `window.Console`; keep or inert `window.__mock` |
| `10-shared.js` (364) | `Picker` fills aliases from `FIX.aliases` (116-120) with `arm`; `Resolution` merges `FIX.aliases` arms (80-82); `REFUSAL_HINTS`, `classifyResponse` (reuse unchanged); `copyText` | `AliasCatalog` shared loader (fed by `GET /ledger/aliases`, refreshed after promote/rollback/retire); alias option label `alias (active_version)`; `Resolution` alias branch -> "alias <name>, active version <v>; the server resolves the arm at run time" |
| `20-query.js` (420) | `history` from `FIX.query.history` (28); `pickFixture`/`finish`/`later(800)` (264-308); `STATE_FIXTURE`; `mock.*` handlers | `run()` -> `api("POST","/query"...)`; streaming via Pattern 2; history entries `{query, selector, trace_token, timestamp}` (the mockup stores `{time, selector, trace_token, partial}`); one `syncRun()` deciding disabled from running / write in flight / compare blockers (WR-JSA-02) |
| `21-compare.js` (517) | `Compare.run` uses `FIX.query["q-success"].body` for every column (366); `bad` detection via `Resolution` text | `api("POST","/compare", {query, selectors: model.map(sel => sel || {})})`; 1 selector -> envelope, else map by `comparisonKey` |
| `30-evidence.js` (473) | `find()` reads `FIX.evidence` (96-107); `TRACE_OF` scan of `FIX.query/compare` (24-38); `resolve()`/`loadTrace()` timers; `emit open-evidence {ref:{id,...}}` from query/compare/graph | `api("POST","/evidence/resolve", ref)` with the envelope EvidenceRef; cache `ns\u0001ref`; `api("POST","/trace/resolve",{trace_reference, debug})`; debug toggle re-requests |
| `40-documents.js` (629) | `sessionJobs` from `FIX.documents` (45); `finishIngest` -> `ingest-success`; `fixtureFor`/`loadJob`; `FIX.documents.pipeline.text` (573); simulated upload progress (276-291); `finishDelete` | `POST /documents`, `POST /documents/upload` (FormData), `GET /jobs/{id}?limit&offset`, `DELETE /documents/{id}` with `{selector}`; track `offset` client-side; `documents.pipeline.*` and `jobs.all` stay badged and disabled |
| `50-corpus.js` (522) | `FIX.corpus[name]` pages (283); `Console.health()` fixture; `fillBusy`/`fillInstance`/`fillWirings` from `FIX.shell.info` / `FIX.corpus.wirings`; `fillLog` from `FIX.corpus.log`; `retryDocument` timer | `GET /corpus?limit&offset`, `GET /corpus/counts`, `GET /info`, `GET /wirings`, `GET /log?limit`, `POST /documents/{id}/retry`; filter/sort/search controls disabled while the `/corpus` qualifier badge is present; KPI-tile filter stays client-side on the current page |
| `60-ledger.js` (640) | `L = FIX.ledger` (2); `traceByRef`; `renderTimeline`/`statusOf` (421-483); `loadAlias` (499); `showPreview` timer; dialogs `finish()` timers | `POST /promote`, `/rollback`, `/retire`; `GET /traces` + run history for the trace list; `POST /ledger/history`; `POST /promote/preview`; `GET /ledger/aliases`; client ledger log |
| `70-graph.js` (477) | `fix()`, `allNodes`, `edgesOf`, `attrsOf` (51-93); `failure()` mock outcomes; `later()` timers; `EDGE_PAGE = 6` | `POST /graph/nodes`, `/graph/node`, `/chunks`; edge paging uses server `next_offset`; `POST /graph/node/attrs` and `POST /stores/counts` are absent, so attrs panel and count tiles stay badged and disabled (no fixture counts) |

Mock outcome selects (`*.mock.outcome`), fixture selects, state switchers: hidden, code paths inert (discretion item 3).

## Badge Matrix (built file, 54 `data-needs-backend` attributes) [VERIFIED: grep of mockups/operator-console.html]

| Route | Count | Present with `--operator`? | Wired in this phase by |
|-------|------:|:---:|------------------------|
| `GET /ledger/aliases` | 10 | yes | AliasCatalog feeding every Picker (query, compare rows, documents, graph) and the Ledger aliases panel |
| `GET /log` | 7 | only with `--operator --log-file` | per-screen `*.error.server-log` (6) + Corpus log panel (1) |
| `GET /info` | 3 | yes | header chip, `corpus.health.busy`, `corpus.instance.panel` |
| `POST /graph/nodes` / `POST /graph/node` | 3 / 3 | yes | Graph screen wrappers |
| `GET /traces` | 2 | yes | Ledger trace list, evidence/trace picker |
| `POST /promote/preview`, `POST /ledger/history`, `POST /chunks`, `GET /wirings` | 1 each | yes | Ledger preview, timeline, chunk browser, Corpus wirings panel |
| `POST /selectors/resolve` | 7 | never | stays badged (embedded table) |
| `GET /refusals` | 7 | never | stays badged (embedded catalogue) |
| `GET /corpus (status, sort, search)`, `GET /jobs`, `GET /pipeline`, `POST /jobs/{job_id}/cancel`, `POST /documents/reprocess`, `POST /evidence/resolve-batch`, `POST /stores/counts`, `POST /graph/node/attrs` | 1 each | never | stay badged, controls disabled with a tooltip naming the route |

Counts (built file): 32 instances belong to the 10 operator routes and 22 to the 10 never-present routes. Expected badges left per launch mode: no `--operator` -> all 54; `--operator` without `--log-file` -> 22 + 7 (`GET /log`) = 29; `--operator --log-file` -> 22. The per-element rule is "badge iff the route is absent from the live `/openapi.json`". `GET /log` needs `--log-file` too: `add_operator_routes(app, engine, log=log_path is not None)` mounts it only then [VERIFIED: operator_rest.py:132-145, rest.py:545-549], so the third configuration (operator without log file) must keep the 7 `GET /log` badges; the LIVE-09 test should cover all three launch modes. The UI-visible exception: in a no-operator launch `GET /info` is absent, so the header chip has no workspace; show `version` from `/openapi.json` `info.version` ("0.1.0", probe 1) and nothing fabricated for the workspace.

## Common Pitfalls

### Pitfall 1: `null` Default selector in `/compare`
**What goes wrong:** the mockup models Default as `null` (`selectorLabel(null)`, `comparisonKey(null)`). Sending `[null, {...}]` returns a 422 *validation* error (`model_attributes_type`, `loc ["body","selectors",0]`), which the user sees as a field error on a row.
**Why:** `CompareRequest.selectors: list[Selector]` has no `None` (rest.py:205-210); `Selector` with every member unset is the default (selectors.py:115-131).
**How to avoid:** map `null` to `{}` for compare only; `/query` keeps `selector: null`. Alias row: `{"alias": a}`; capability: `{"capability": [...]}`; send arrays (a bare string is also legal but the mockup picker yields arrays).
**Warning signs:** compare with a Default row always 422.

### Pitfall 2: The evidence request body
**What goes wrong:** `Console.emit("open-evidence", {ref: {id: ref.ref, namespace, kind}, score})` (20-query.js:374, 21-compare.js:491, 70-graph.js:454) sends `{id,...}`; the server answers 422 `missing ref` + `extra_forbidden id`.
**How to avoid:** keep the envelope's evidence object (or the `/chunks` ref object) unchanged and pass it as the body (LIVE-04: "EvidenceRef copied unchanged"); keep `score` separately for the inspector's score line; `EvidenceRef` also has `tier`.

### Pitfall 3: Fixed slots, per-slot handlers
See Pattern 4. Symptoms: only the first 5/6/8 rows render, or the 9th row has no click handler. Real query results exceed 5 evidence rows on LightRAG. Delegation plus `ensureRows` is a prerequisite for every table, so it belongs in the shared core plan.

### Pitfall 4: Page offset is not echoed
`/graph/nodes`, `/chunks`, `/jobs/{id}` (and `/ledger/history`, `/corpus`) return `next_offset` (and `total` on some) but no `offset`; the mockup `pager()` reads `page.offset` (70-graph.js:178-185, 50-corpus.js:277-279, 40-documents.js:377-378). Keep the requested offset in the screen state and set `page.offset = requestedOffset`. `Prev` offset = `max(0, offset - limit)`; `JobStatus` has no `total`, so "Showing x to y of z" must omit `of z` for jobs.

### Pitfall 5: The id check scans more than you expect and nothing it finds is mockup-specific
`scripts/mockup-id-check.py` walks the project root, skips `mockups`, `tests`, `test`, `e2e`, `.planning`, `build`, `dist`, `out`, `.venv` and others [VERIFIED: mockup-id-check.py:16-20] and counts `.html/.js/...` text with a literal `data-mock-id="..."` [VERIFIED: :10-15, :21-22]. Facts for the plan: (a) `databasise/console/` is scanned, so the id set is satisfied by `operator-console.html` and by `src/screens/*.html`; ids produced by `<!--@repeat-->` (`{{n}}`) exist only in the built file, so the built file must be committed and current when the gate runs; (b) the frozen file is `rp == frozen` excluded, so the check cannot pass by finding ids in the mockup itself; (c) with `mockup_freeze` null the script prints "mockup check skipped" and exits 0 (verified: ran it this session); (d) after the freeze, a stale `databasise/console/operator-console.html` that lost an id fails with `mockup <id>: present in frozen mockup ... but missing from UI sources`; (e) `variant_spans` takes ids only inside the `data-mock-variant="console-a"` element (`shell.root.app`), 623 ids [VERIFIED: docs/gui/MOCK-IDS.json length 623].

### Pitfall 6: The freeze must not change mockup bytes, and `build.py` must keep a zero-argument `build()`
`databasise/tests/gui/test_mockup_build.py` loads `mockups/build.py` and calls `module.build()` with no arguments, comparing to the checked-in mockup [VERIFIED: test_mockup_build.py:14-20]; the sha256 recorded by `freeze-variant` is the digest of `mockups/operator-console.html` [VERIFIED: ledger-amend.py:983-984]. So: add `build(src=SRC)`, thread `src` through `expand`/`fixtures_json`/`read`, add `--src/--out` to `main`, keep `SHARED_FIXTURES` rooted at the repo root. Currently `expand`/`fixtures_json` use the module-global `SRC` (build.py:21, 46, 67, 72). Re-run `build.py --check` and `sha256sum` after editing; both must still show `bf98e79e...` and exit 0 (verified today: digest equal and `--check` exit 0).

### Pitfall 7: Upload progress cannot be real over `fetch`
`submitUpload` animates 20% steps (40-documents.js:276-291). With `fetch` there is no upload progress event. Show an indeterminate `<progress>` (no `value`) or the spinner while the request is in flight; do not keep the scripted percentages (they would be invented data).

### Pitfall 8: Alias rows carry no arm
`GET /ledger/aliases` rows are `{alias, active_version, record_kind, generation_ordinal, created_at}`; the mockup's `FIX.aliases` also has `arm` and uses it for the Picker label and for `Resolution` (10-shared.js:80-82, 117). Live label: `alias (active_version)`. `POST /promote/preview` returns the real `arm` for a trace set and may be used to enrich the Ledger preview only.

### Pitfall 9: Timeline head row (WR-JSC-01) when the timeline is paged
Server semantics, verified by test and by probe: on a promote(v1), promote(v2), rollback(->v1 gives v3), retire(v2) history, `active` is true for both the promotion of v1 and the rollback record, and `tombstoned` is true for the retired promotion and for the tombstone record itself [VERIFIED: test_console_ledger.py:126-131]. D-17 says the head is the active row with the highest `generation_ordinal`, which is correct only if that row is on the loaded page. Records are ascending and the head is usually on the **last** page. Safer rule: take the head from the alias row (`GET /ledger/aliases`: `generation_ordinal` and `active_version` of the alias) and treat an `active` record as `active` iff its `generation_ordinal` equals that value, otherwise `target of active rollback`; fall back to highest active ordinal on the page when the alias list is unavailable. `statusOf`'s current rollback-target branch (60-ledger.js:421-426) assumes a single active row and must be replaced.

### Pitfall 10: Parallel plans and one generated file
All screens compile into `databasise/console/operator-console.html`. Two plans that rebuild and commit it in separate worktrees conflict on merge in a 370 KB single line-ish file. Either run the JS-touching plans sequentially (they also share `00-app.js` and `10-shared.js` edits), or make only the closing plan commit the built file and have conftest build into a tmp path for the screen plans. The `GET /console` route test needs the packaged file, so a sequential order is simpler.

### Pitfall 11: Guards that fire on executors
(a) The BAK edit guard (see Project Constraints) protects every file named by a ledger `test_ref` and every `check_locks.files` entry; the LIVE rows currently have empty `test_ref`/`code_ref` [VERIFIED: ledger/REQUIREMENTS.json:2246-2370]. New `tests/gui_live/*` files are creatable until a row names them; after `ledger-amend set --test-ref ...` they are protected and later edits need `grant-check-edit` (the precedent grant is for `databasise/tests/gui/conftest.py`, ledger/REQUIREMENTS.json:2532-2537). So write every live test file first, link `test_ref` last, and expect to ask for a grant for any post-link fix. (b) `python3 scripts/ledger-amend.py freeze-variant ...` is the only writer; the run environment for this research forbids the word "ledger" in a Bash command, so if the executor hits the same hook the freeze step needs the orchestrator or the owner. (c) `scripts/size-gate.py` rejects a plan with more than 20 items, 20 cited ledger IDs or 500 lines [VERIFIED: size-gate.py:29-31, 70-76]; `scripts/plan-gate.py` fails a plan set that drops a due ledger ID.

### Pitfall 12: Header health vs a slow `/health`
`GET /health` calls the v1 driver in a subprocess with a wall-clock ceiling (engine.py:2073-2079) and probes stores in a worker thread, so it can take seconds. D-13 allows `checking` for up to 60 s: abort the fetch at 60 s and render `error`. A health tick must be skipped (not queued) while `InFlight.any()` is true; the `/health` call itself must not register in the registry or it would skip itself.

### Pitfall 13: sessionStorage shape and size
Mirror only small JSON (history cap, for example 50 entries, jobs cap 50, ledger log cap 50); wrap every `sessionStorage` call in try/catch (storage can throw). Never store response bodies or document text.

### Pitfall 14: Hash routing and `/console` URL
`Console.show` writes `location.hash` and listens to `hashchange` (00-app.js:26, 80-83); that works unchanged under `/console#evidence`. Do not add a `<base>` tag or absolute fetch URLs; use root-relative paths so the page works on `localhost` and `127.0.0.1` alike (the Origin guard admits both).

## Phase 17 findings: how each absorbed row lands in live code (D-17)

| Finding | Live-source fix |
|---------|-----------------|
| WR-JSA-01 | `validate()` accepts only `{alias:string}`, `{capability:string[]}`, `{harness:string}`; `{}`/all-null -> Default or `badJson`; never hand an unchecked object to `selectorLabel` |
| WR-JSA-02 / 03 / 04 | one `syncRun()`; `QueryScreen.showState` never touches Run in compare mode; Compare re-checks blockers at the top of `run`; mode switch calls both screens' cancel and aborts the pending `AbortController`; hide `query.compare.columns` for non-compare renders |
| WR-JSA-05 | streaming keeps `query.state.running` (or no banner) and Promote/Compare disabled until `final` |
| WR-JSA-06 | columns filled from the map entry keyed by `comparisonKey`; `trace_token` per column |
| IN-JSA-07 / 08 / 09 | uncheck other boxes on promote event; `setDisabled(promote, partial \|\| !trace)`; refusal state text without a fixed `422` (fill from status) |
| WR-JSB-01 | `originLink = null` in lookups; disable `evidence.inspector.trace-link` when no token |
| WR-JSB-02 / IN-JSC-04 | while a confirm is in flight disable cancel and `preventDefault` the dialog `cancel` event; the delete/promote/rollback/retire request is sent only on Confirm and is never aborted afterwards (D-14) |
| WR-JSB-03 | restore pager from the retained page record after a failed load; restore the job-id input |
| WR-JSB-04 | health error gets its own region or is re-painted after `hideErrors` |
| IN-JSB-05 | poll only while the drawer is open and stop at a terminal state; clear on `jobs.close` and on screen leave |
| IN-JSB-06 | find the retry target row by `document_id` when the response arrives |
| IN-JSB-07 | show `Open in Corpus` for LightRAG records keyed on `full_doc_id` (and prefill search is a disabled control: the `/corpus` search is badged), or hide for HippoRAG; pick one and record it |
| IN-JSB-08 | `busy(false)` beside every `abort()` |
| WR-JSC-01 | Pitfall 9; fixture JSON is not used live |
| WR-JSC-02 | recompute selected traces at response time, disable trace boxes while the preview is pending |
| IN-JSC-08 | call `checkSize()` at the end of `hideErrors`/`showError` |
| UI-review top-3 fix 2 | CSS `white-space: nowrap` on ledger badge and timestamp cells, `min-width` on the Status column (60-ledger CSS: `mockups/src/css/60-ledger.css`) |

## Code Examples

### `--console` flag and route (D-01, D-02)
```python
# Source: designed against databasise/launcher/serve_rest.py:22-87, 114-156 (read this session).
parser.add_argument("--console", action="store_true",
    help="serve the operator console at GET /console; loopback --host only (D-01, D-02)")
# main(): next to the --operator host rule
if args.console and not is_loopback_host(args.host):
    parser.error("--console needs a loopback --host, even with --allow-remote-unauthenticated: "
                 "the console drives every route without authentication")
# build_app(): after the Origin guard is installed
if getattr(args, "console", False):        # getattr: protected tests hand-build a Namespace
    from importlib.resources import files
    page = files("databasise.console").joinpath("operator-console.html").read_bytes()
    from fastapi.responses import Response
    @app.get("/console", include_in_schema=False)
    async def console() -> Response:
        return Response(page, media_type="text/html; charset=utf-8", headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                       "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})
```
Reading the file once at build time makes a missing package file fail at startup, not on the first request. The `is_loopback_host` import is already in serve_rest.py (line 16). The existing remote-host refusal test shape (test_console_surface.py:237-252) is the template for the new refusal test: `main([... "--console", "--host", "192.168.1.5", "--allow-remote-unauthenticated", "--no-clients", "--store-root", root])` must raise `SystemExit(2)` with `--console` and `loopback` in stderr and no `.engine.lock` created.

### `build.py` arguments, default bytes unchanged
```python
# Source: designed against mockups/build.py:21-22, 44-111 (read this session).
def build(src: Path = SRC) -> str:           # zero-arg call in test_mockup_build.py:19 must keep working
    html = expand(read(src / "page.html", "page.html"), "page.html", src)
    ...
def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    ap.add_argument("--src", type=Path, default=SRC); ap.add_argument("--out", type=Path, default=OUT)
```

### Package data (D-03)
```toml
# pyproject.toml [tool.setuptools] packages: add "databasise.console"
[tool.setuptools.package-data]
"databasise.console" = ["operator-console.html"]
```
`databasise/console/src/` is not a package and is not shipped. `test_packaging.py` builds a wheel from a temp copy and only asserts the tools, bundles and fixtures [VERIFIED: test_packaging.py:69-78]; add a live check that the wheel RECORD lists `databasise/console/operator-console.html` as a new test, not an edit of that file (it is locked).

### Early-closed stream test
```python
def test_early_closed_stream_shows_disconnected(live_ui):
    def truncate(route):
        resp = route.fetch()
        route.fulfill(response=resp, body=resp.text().split("\n\n")[0] + "\n\n")
    live_ui.page.route("**/query/stream", truncate)
    # type text, tick "Stream the response", click Run
    live_ui.expect("query.state.error-500").to_be_visible()      # SHAPE_STATE generic -> error-500 view
    assert "The stream closed before the final event." in live_ui.el("query.error.generic").inner_text()
```
(ids `query.state.error-500` and the generic region text are from 20-query.js:14-15 and 10-shared.js:292-298.)

## State of the Art

| Old (mockup) | Current (live) | Impact |
|--------------|----------------|--------|
| Fixture + `setTimeout` per screen | One `api()` + real promises | Timers for LOAD/FLIGHT/CONFIRM disappear; the confirm race (WR-JSB-02) must be fixed by gating cancel, not by clearing timers |
| `new_context(offline=True)` | online context to loopback only | Live conftest must also fail on any non-loopback request |
| `EventSource` (cannot POST a body) | `fetch` + `ReadableStream` | LIVE-02; the server emits plain `data:` frames with no `event:` |
| Phase 17 `ui` fixture asserts page errors in teardown | assert in the call phase | IN-BLD-04 pattern in the new conftest only |

**Deprecated/outdated:** nothing in the toolchain; `pytest-asyncio` `asyncio_mode = "auto"` only wraps `async def`, so sync Playwright tests are unaffected.

## Runtime State Inventory

Not a rename/refactor/migration phase. The only persisted runtime state this phase adds is browser `sessionStorage` (tab-scoped, not shared with the server). The ledger write is a single `mockup_freeze` field through `ledger-amend.py` (D-04 step 3).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `databasise/.venv/bin/python` | everything | yes | 3.12 | — |
| fastapi / starlette / uvicorn | launcher, test thread | yes | 0.141.1 / 1.6.0 / 0.52.4 | — |
| playwright (Python) | live suite | yes | 1.59.0 | — |
| Chromium for Playwright | live suite | yes | chromium-1217 at `~/.cache/databasise/playwright-browsers` (also headless shell, firefox, webkit present) | `DATABASISE_REQUIRE_BROWSER` unset -> tests skip, set to `1` -> fail |
| pycozo (RocksDB) | store-busy test | yes (imported in probes) | repo-pinned | — |
| httpx | readiness poll | yes | in `.venv/bin` | — |
| Node/Bun/npm | none needed (D-03) | not required | — | — |
| `python3` + `scripts/ledger-amend.py` | freeze step | yes (script read) | — | orchestrator/owner if the Bash hook blocks the call |
| Real model clients / v1 interpreter | D-20 owner walkthrough only | owner machine | — | stub clients + fake `run_corpus_op` for automated tests |

**Missing dependencies with no fallback:** none for automated work. The D-20 walk needs the owner's real env file and a populated store; agents must not read `.env*` or `v1/parity-env.txt`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`) + Playwright for Python 1.59.0 (sync API); live tests are plain sync functions |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = '-m "not live"'`) |
| Quick run command | `DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q databasise/tests/gui_live/test_live_0N_*.py -p no:cacheprovider` |
| Full phase command | `DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q databasise/tests/gui_live databasise/tests/gui databasise/tests/launcher databasise/tests/seam/test_console_surface.py databasise/tests/seam/test_rest_transport.py -p no:cacheprovider` (the orchestrator runs the whole suite; do not) |
| Build/freeze checks | `databasise/.venv/bin/python mockups/build.py --check`; `databasise/.venv/bin/python mockups/build.py --src databasise/console/src --out databasise/console/operator-console.html --check`; `python3 scripts/mockup-id-check.py`; `sha256sum mockups/operator-console.html` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-01 | `--console` serves `/console`, absent without the flag; remote host refused; page POST /query is 200 with no CORS text; header health shows live result | launcher unit + Playwright | `pytest databasise/tests/gui_live/test_live_01_serving.py` | no, Wave 0 |
| LIVE-02 | query, stream (evidence rows then final), compare one-selector bare and two-selector map, early-closed stream, history entry shape | Playwright | `pytest .../test_live_02_query_compare.py` | no, Wave 0 |
| LIVE-03 | real refusal (409/404/422), real validation field error, real 500 on query, evidence, documents, corpus, ledger, graph | Playwright with real server errors | `pytest .../test_live_03_errors.py` | no, Wave 0 |
| LIVE-04 | one `/evidence/resolve` request per ref per session; Debug toggle re-requests with `debug: true`; inspector Open trace targets the originating result | Playwright with request counting | `pytest .../test_live_04_evidence_trace.py` | no, Wave 0 |
| LIVE-05 | paste ingest, upload, job load, confirmed delete; Run disabled while a write is in flight; corpus+counts refetched after delete; query after HippoRAG ingest returns that document's evidence | Playwright + stateful corpus fake | `pytest .../test_live_05_documents.py` | no, Wave 0 |
| LIVE-06 | health one call on load; poll only when enabled and idle (clock); counts poll only while non-terminal > 0; next_offset paging | Playwright + `page.clock` | `pytest .../test_live_06_corpus_health.py` | no, Wave 0 |
| LIVE-07 | promote -> client log -> query `{alias}` returns 200; rollback; retire; head/target/tombstoned statuses per server semantics; cancel before Confirm sends nothing | Playwright, HippoRAG stub path | `pytest .../test_live_07_ledger.py` | no, Wave 0 |
| LIVE-08 | nodes/node/chunks by selector, paging by next_offset, store-busy banner while a raw pycozo client holds the graph, unknown node | Playwright + pycozo | `pytest .../test_live_08_graph.py` | no, Wave 0 |
| LIVE-09 | badge iff route absent, in three launch modes (no operator; operator; operator+log-file); all 623 frozen ids present in the page; `mockup-id-check.py` exit 0; mock-only controls hidden but present | Playwright + subprocess script | `pytest .../test_live_09_badges_ids.py` | no, Wave 0 |

### Sampling Rate
- **Per task commit:** the screen's `build.py` rebuild + `--check` for the console, plus that screen's single test file (under 30 s each in the probes: server start about 1 s, Chromium start about 1-2 s).
- **Per wave merge:** all of `databasise/tests/gui_live` + `databasise/tests/gui` (Phase 17 suite, still against the frozen mockup) + `databasise/tests/launcher` + `test_console_surface.py` + `test_rest_transport.py` + `mockup-id-check.py`.
- **Phase gate:** the orchestrator's full suite green, `mockups/build.py --check` exit 0, `sha256sum mockups/operator-console.html` equals `bf98e79e...`, `scripts/mockup-id-check.py` exit 0 with `mockup_freeze` set, then the D-20 owner checkpoint before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `databasise/tests/gui_live/__init__.py`, `conftest.py` (server thread on a pre-bound socket, module-scoped Chromium, `LiveUI` with `el/expect`, loopback-only request guard, page-error-fails-the-test hook)
- [ ] `_corpus_fake.py` (stateful `run_corpus_op` closure + stub registry swap via `databasise.seam.engine.default_registry`), reusing the helpers in `test_rest_corpus_endpoints.py`
- [ ] one `test_live_0N_*.py` per row, written failing first; `test_ref` linked only after they exist
- [ ] `mockups/build.py --src/--out`, `databasise/console/{__init__.py,src/,operator-console.html}`, `pyproject.toml` package + package-data
- [ ] a wheel-contents test for the console file that does not edit the locked `test_packaging.py`
- [ ] Framework install: none (Playwright 1.59.0 and Chromium 1217 present)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (out of scope, D-02: no auth) | loopback bind only; `--console` refused on non-loopback even with `--allow-remote-unauthenticated` |
| V3 Session Management | no server session | `sessionStorage` holds only small JSON, tab-scoped, no secrets |
| V4 Access Control | yes | TrustedHost + Origin guard (serve_rest.py:68-87) already in front of every route; operator routes mounted only with `--operator` |
| V5 Input Validation | yes | server-side Pydantic is authoritative; client prechecks mirror it (document_id `^[A-Za-z0-9_-]+$`, 26,214,400 byte cap, page size 1..100); raw selector JSON accepts only the three known members (WR-JSA-01) |
| V6 Cryptography | no | none introduced |
| V8/V14 Data protection / config | yes | `GET /console` response headers: CSP (inline script/style only, `connect-src 'self'`, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| V12/V13 API and web service | yes | no new route besides `GET /console`; `include_in_schema=False` keeps `/openapi.json` unchanged |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS from evidence text, answers, log lines, error bodies | Tampering / Info disclosure | `textContent` only (10-shared.js:1 rule), no `innerHTML`, `fillGeneric` slices to 500 chars; CSP blocks external script even if one slipped through |
| CSRF / cross-site writes to the loopback API | Tampering | existing Origin guard returns 403 for a non-listed Origin on non-GET; the page is same-origin so its own POSTs carry an admitted `Origin`; do not add CORS |
| DNS rebinding | Spoofing | existing TrustedHost middleware; `--console` adds none |
| Clickjacking of Delete/Retire/Rollback | Tampering | `frame-ancestors 'none'` + `X-Frame-Options: DENY` on the console response; destructive dialogs keep the safe default focus (`openDialog`, 10-shared.js:343-348) |
| Exposure of paths and tracebacks through the log tail | Info disclosure | `GET /log` is server-redacted and only with `--operator --log-file` (loopback); render with `textContent` in a `<pre>` |
| Unauthenticated destructive ops if exposed beyond loopback | Elevation | `parser.error` for any non-loopback `--host` with `--console` |
| Stale or forged page served after a rebuild | Tampering | read the packaged file at startup; build output verified by `build.py --check` in a test |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The non-terminal status set for counts polling is `pending, parsing, analyzing, processing, preprocessed` and `interrupted`/`processed`/`failed` are terminal. The status vocabulary is `[VERIFIED: mockups/src/js/50-corpus.js:14]` but which of them v1 still advances is `[ASSUMED]`; engine.py:756 `_MID_PIPELINE = frozenset({"parsing", "analyzing", "processing"})` is verified | Phase Requirements LIVE-06 | Counts polling stops too early or never stops |
| A2 | A CSP of `script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'` is acceptable for the one-file inline page and does not block `fetch`, `<dialog>`, `sessionStorage` or the clipboard call | Security Domain, Code Examples | Page renders blank or fetch blocked; first Playwright run would show it. Not run with the header in this session |
| A3 | Playwright's `route.fetch()` + `route.fulfill(response=..., body=...)` truncation is a faithful "stream closed early" for a `ReadableStream` reader. Verified that the reader gets only the first frame; whether Chromium reports it as a clean EOF versus a network error for every case is `[ASSUMED]` | Verified Point 3 | The disconnected state might see a rejected read instead of `done`; treat a rejected `reader.read()` after at least one chunk as the same "disconnected" state |
| A4 | A long LightRAG ingest that exceeds the browser's/Chromium's idle fetch limits never occurs on loopback (no intermediary) | LIVE-05 | A multi-minute `fetch` could be dropped; the UI would show server unreachable while the write continues. No evidence of a Chromium cap on loopback was gathered |
| A5 | Showing `Open in Corpus` for LightRAG records keyed on `full_doc_id` (IN-JSB-07) is the intended fix; the alternative (hide for HippoRAG, amend UI-SPEC line 318) is equally allowed by D-17 | Findings table | Owner click-through objects; low cost to flip |
| A6 | The owner's D-20 walkthrough has a populated default store (`DEFAULT_STORE_ROOT`) and client env file; not inspected (secret files are off limits) | Environment | Walkthrough steps may need a seeded store |

## Open Questions (RESOLVED)

1. **Query-after-ingest on the LightRAG default path (D-15).**
   - What we know: the offline stub driver does not populate the v2 stores, so `v1-index-sync` has nothing to mirror; the HippoRAG selector path ingests and queries entirely offline with stub clients and returned the ingested text as evidence (probe 3).
   - What's unclear: whether the owner expects the automated assertion on the LightRAG default selector.
   - Recommendation: assert D-15's "query after ingest returns the document's evidence" on the HippoRAG selector in the automated suite and leave the LightRAG default path to the D-20 owner walkthrough; record this in the plan so it is a conscious scope reading.
   - RESOLVED: asserted on the HippoRAG selector (`test_query_after_hipporag_ingest_returns_that_documents_evidence`); the LightRAG default path is checked in the owner walkthrough. Decided in the 18-08 plan and its truth (Open Question 1), with the walkthrough step in 18-11 Task 2. The matching LIVE-07 substitution is the named deviation in 18-09.

2. **Run disabled vs "clickable with an inline message" for the in-flight write gate.**
   - What we know: 17-CONTEXT discretion says "query Run clickable with an inline message, everything else natively disabled"; LIVE-05 and success criterion 3 say Run is disabled while a write is in flight.
   - Recommendation: natively disabled (`setDisabled(true)`, which also sets `aria-disabled`) plus a visible reason in `query.run.message`; keep the "clickable with message" style only for validation blockers. Playwright `to_be_disabled` accepts both.
   - RESOLVED: natively disabled with the visible reason, and LIVE-05 governs. Decided in the 18-CONTEXT D-13 amendment of 2026-10-31 (plan-check ruling), mirrored in the 18-UI-SPEC Run blockers row, and implemented by 18-08 Task 3 with its truth.

3. **Timeline head determination when the alias list is missing.**
   - Recommendation: fall back to the highest-ordinal active record on the loaded page and label the status conservatively; the aliases and history routes are both operator routes, so they are present together in practice.
   - RESOLVED: the head is the active row with the highest generation_ordinal (D-17), read from the GET /ledger/aliases row, with the highest active ordinal on the loaded page as fallback. Decided in the 18-09 plan (Task 2, WR-JSC-01) and its truth.

4. **Which badges count as "wired" when a route is present.** `GET /ledger/aliases` has 10 instances; if any one Picker is not wired in this build its badge would be dropped wrongly. Recommendation: a `WIRED` set keyed by route string, populated by each screen plan as it finishes, with the LIVE-09 test enumerating all 54 elements per launch mode.
   - RESOLVED: `WIRED` keys are `"<scope> <data-needs-backend value>"`, where the scope is the screen, `dialog` or `shell`. Each screen file declares its own keys, and the LIVE-09 matrix checks all 54 elements in three launch modes. Decided in the 18-03 plan (objective and Task 2) and its truth, and closed in 18-11 Task 1.

5. **Whether to keep `window.__mock`.** Inert and harmless; removing it changes nothing for the live suite. Keeping it keeps the ported files closer to the approved source.
   - RESOLVED: not installed in the live build, following the 18-UI-SPEC Live Shell; the mock-only controls stay in the source, hidden. Decided in the 18-03 plan (objective, Task 1) and its truth, and tested by `test_mock_only_controls_are_hidden_but_present`.

6. **Roadmap open question 8: the LIVE-05 "different stores" notice.** The ROADMAP and LIVE-05 mark it "Owner decision first", and D-15 had defaulted it to no notice.
   - DEFERRED to owner at 18-11: the frozen mockup's notice `documents.notice.store-split` is kept, visible and unchanged, until the owner decides at the 18-11 click-through between keeping it and removing it on the basis of Phase 11 D-01 option b. Decided in the 18-CONTEXT D-15 amendment of 2026-10-31 (plan-check ruling); 18-08 Task 3 keeps and tests the notice, and 18-11 Task 2 asks the question.

## Suggested plan shape (Claude's discretion; D-04 first, D-20 last)

1. **Freeze and copy (D-04):** sha check, `build.py --src/--out` (default bytes unchanged), copy `mockups/src` -> `databasise/console/src`, build, `__init__.py`, pyproject package + package-data, `freeze-variant`, id check exit 0.
2. **Launcher `--console` (LIVE-01):** flag, host rule, route with headers, tests (flag present/absent, remote refused, `/openapi.json` unchanged).
3. **Live harness (fail-first):** `tests/gui_live` conftest, corpus fake, one failing skeleton per LIVE row.
4. **Shell core:** `05-api.js` transport + `InFlight`, health with 60 s abort, `applyBadges`, mock hiding, `ensureRows` + delegation, `sessionStorage` helpers, AliasCatalog, title/banner copy (LIVE-01/03/09).
5. **Query & Compare** incl. SSE and WR-JSA-01..06, IN-JSA-07..09 (LIVE-02, LIVE-03).
6. **Evidence & Trace** incl. WR-JSB-01, IN-JSB-07/08 (LIVE-04).
7. **Documents** incl. WR-JSB-02/03, IN-JSB-05 (LIVE-05) and **Corpus & Health** incl. WR-JSB-04, IN-JSB-06 (LIVE-06), possibly two plans.
8. **Ledger** incl. WR-JSC-01/02, IN-JSC-04/08, nowrap CSS (LIVE-07).
9. **Graph** (LIVE-08).
10. **Closure:** badge matrix in three launch modes, disposition rows updated in `17-REVIEW-DISPOSITION.md`, `ledger-amend set --test-ref/--code-ref` for LIVE-01..09 (after test files exist), final id check, wheel contents test.
11. **Owner checkpoint (D-20), `checkpoint:human-verify`.**

Plans 4-9 touch the same generated file and shared globals; schedule them in separate waves (Pitfall 10).

## Sources

### Primary (HIGH confidence)
- Local source read this session: `databasise/launcher/serve_rest.py`, `databasise/seam/rest.py`, `databasise/seam/operator_rest.py`, `databasise/seam/engine.py` (ingest 1354-1636, stream 1104-1115, corpus/health/info 1955-2145, gates 855-912, trace 2697-2711), `databasise/seam/corpus.py`, `envelope.py`, `evidence.py`, `selectors.py`, `mockups/build.py`, `mockups/src/**` JS and HTML, `scripts/mockup-id-check.py`, `scripts/ledger-amend.py` (freeze-variant 959-989), `scripts/size-gate.py`, `scripts/plan-gate.py`, `ledger/REQUIREMENTS.json` (rows, `check_locks`, `check_edit_grants`), `docs/gui/MOCKUP-APPROVAL.md`, `docs/gui/MOCK-IDS.json` (623), Phase 17 `17-REVIEW.md`, `17-REVIEW-DISPOSITION.md`, `17-CONTEXT.md` line 83-84, existing tests `test_console_graph.py`, `test_console_ledger.py`, `test_console_log.py`, `test_console_surface.py`, `test_bind_guard.py`, `test_rest_corpus_endpoints.py`, `test_rest_cors.py`, `test_hipporag_write_path.py`, `tests/gui/conftest.py`, `test_mockup_build.py`, `test_packaging.py`, `test_removed_stores_absent.py`.
- Installed libraries: `.venv/.../fastapi/sse.py` and `routing.py` (keep-alive and SSE serialisation), `uvicorn/server.py` (signal handling), `playwright.sync_api` (Clock API, version 1.59.0).
- Run in this session (scratchpad probes 1-5): compare null vs `{}`, openapi path list, empty-text and unknown-alias refusals, full HippoRAG offline flow (ingest, query, evidence, trace, traces, graph nodes, chunks, promote, preview, alias query, history, health, info, jobs, corpus with selector, stream wire format, delete), in-process uvicorn thread + Chromium fetch, SSE parsing in Chromium, `route.fetch`/`route.fulfill` truncation. `mockups/build.py --check` exit 0, mockup sha256 `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20`, `mockup-id-check.py` exit 0 (skipped, no freeze).

### Secondary (MEDIUM confidence)
- none used; no external web sources were needed.

### Tertiary (LOW confidence)
- Items tagged `[ASSUMED]` in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new; versions read from the venv.
- Architecture: HIGH for serving, transport, harness and API shapes (executed); MEDIUM for effort split across plans (estimate).
- Pitfalls: HIGH for Pitfalls 1-4, 6, 8-9 (reproduced or read in source); MEDIUM for 10-14 (process and behaviour judgments).

**Research date:** 2026-10-31
**Valid until:** 2026-11-30 (stable; revisit if FastAPI's SSE internals, the operator route set or the mockup freeze digest change)
