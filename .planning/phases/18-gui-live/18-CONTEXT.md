# Phase 18: GUI Live - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning
**Mode:** Autonomous smart discuss. The owner asked for no interactive questions, so every grey-area question below took its recommended answer. The proposal tables, with the alternatives that were not chosen, are at the end of this file for audit.

<domain>
## Phase Boundary

The operator runs the whole console against the live engine from a browser page that the launcher serves. The screens are the six from Phase 17: Query & Compare, Evidence & Trace, Documents & Jobs, Corpus & Health, Ledger, Graph/vector browser. The fixture data is replaced by calls to the live §18 REST app and the Phase 16 operator routes.

The phase delivers:
- the `mockup_freeze` write from the Phase 17 approval record (17-CONTEXT D-13);
- a live console source tree outside `mockups/`, ported from the approved mockup with every frozen `data-mock-id` kept;
- launcher serving of the built console from the same origin as the REST app;
- the live transport, streaming, error, polling and in-flight rules of LIVE-02 to LIVE-08;
- the runtime needs-backend badge rule of LIVE-09;
- fixes in the live source for the Phase 17 review findings that change live behaviour;
- a live Playwright suite and an owner click-through.

Covered requirements: LIVE-01 to LIVE-09.

**Not in this phase:**
- Any new server route. Routes that are absent today (`/selectors/resolve`, `/refusals`, `/graph/node/attrs`, `/stores/counts`, `/jobs`, `/pipeline`, `/evidence/resolve-batch`, `/documents/reprocess`, `/jobs/{job_id}/cancel`, the `/corpus` status/sort/search parameters) stay badged.
- Authentication, a reverse proxy, or remote access.
- Edits to the frozen mockup `mockups/operator-console.html` or to the mockup's sources in a way that changes its bytes.
- React, Vite, Node or any frontend toolchain.
- Dark theme.
</domain>

<decisions>
## Implementation Decisions

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
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — LIVE-01 to LIVE-09; GUI-01 to GUI-11 and CONN-01 to CONN-14, which they build on.
- `.planning/ROADMAP.md` — Phase 18 goal, success criteria and the owner decision list (open questions 2 to 6 and 8).

### Freeze and ids
- `docs/gui/MOCKUP-APPROVAL.md` — approved variant, path, sha256 and the D-13 handoff steps (D-04).
- `docs/gui/MOCK-IDS.json` — the 623 frozen ids.
- `scripts/mockup-id-check.py` — skip directories, sha256 check, MOCKUP-PORT.md mapping (D-03, D-04).
- `scripts/ledger-amend.py` — `freeze-variant` verb. Ledger files are read with the Read tool only.

### API shapes and routes
- `docs/gui/API-INVENTORY.md` §3 (bodies), §5.1 and §5.3 (proposed routes).
- `docs/gui/GAP-ROUTES.json` and `docs/gui/INVENTORY-MAP.json` — which controls map to missing or operator routes.
- `docs/gui/refusals.json` — the refusal catalogue (D-06, D-12).
- `databasise/seam/rest.py`, `databasise/seam/operator_rest.py`, `databasise/launcher/serve_rest.py` — routes, CORS, Origin guard, `--operator`, `--log-file`.
- `databasise/seam/engine.py:1104` — `stream_envelope_events` (D-10).

### Prior decisions
- `.planning/phases/16-gui-connectors/16-CONTEXT.md` — D-01 (operator flag and host rule), D-07, D-08, D-10, D-15 to D-19, F (no provider spend).
- `.planning/phases/17-gui-mockup/17-CONTEXT.md` — D-01, D-02, D-06 to D-10, D-13, D-15 and the Discretion list.
- `.planning/phases/11-lightrag-corpus-path/11-CONTEXT.md` — D-01 (M-04 option b) for D-15.

### Phase 17 review
- `.planning/phases/17-gui-mockup/17-REVIEW.md`, `17-REVIEW-DISPOSITION.md`, `17-UI-REVIEW.md` — the findings listed in D-17 and D-18.
- `.planning/phases/17-gui-mockup/17-UI-SPEC.md` — layout, copy and states. It is still the authority for anything this file does not change.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mockups/src/js/10-shared.js`: `classifyResponse`, `renderError`, `fillRefusal`, `fillValidation`, `fillServerFailure`, `wireErrors`, `Picker`, `Resolution`, `selectorLabel`, `comparisonKey`, `openDialog`. The live transport feeds these directly (D-05, D-12).
- `mockups/src/js/00-app.js`: the `Console` screen registry and event bus (`on`/`emit`), plus `renderHealth`, which already has the `loading`, `ok`, `degraded` and `error` states.
- `mockups/build.py`: a deterministic stdlib assembler with `--check`. Give it `--src` and `--out` (D-03).
- `databasise/launcher/serve_rest.py`: `build_app` (the place for the `GET /console` route), `own`, the origin set, the `--operator` host rule, and `log_config_for`.
- `databasise/seam/operator_rest.py`: all ten operator routes the badges switch on.

### Established Patterns
- Launcher flags gate whole surfaces and are refused on non-loopback hosts (Phase 16 D-01).
- Operator and §18 routes are thin adapters. The console route is transport, so it sits in the launcher, outside the CONN-01 AST scope.
- Mockup JS is one concatenated script with shared globals (`FIX`, `$id`, `Console`). Screen files register through `Console.register`.
- Tests run under pytest from `databasise/`. Playwright browsers come from nixpkgs `playwright-driver.browsers` through `PLAYWRIGHT_BROWSERS_PATH` (17 D-15).

### Integration Points
- New: `databasise/console/` (package, `src/`, built `operator-console.html`), the `--console` flag and route, `databasise/tests/gui_live/`.
- Changed: `mockups/build.py` (arguments only; default output must stay byte-identical), `databasise/pyproject.toml` (package and package-data), `ledger/REQUIREMENTS.json` `mockup_freeze` (only through `ledger-amend.py freeze-variant`), `17-REVIEW-DISPOSITION.md` rows.
- Not changed: `mockups/operator-console.html`, `mockups/src/` content, `databasise/tests/gui/` (the Phase 17 suite).
</code_context>

<specifics>
## Specific Ideas

- The `operator route` badge (17 D-10) exists so this phase can drop those badges when it runs with `--operator`. D-08 does this at run time from `/openapi.json`.
- HippoRAG stays first class (17 D-07, D-08): promote and delete are offered for HippoRAG selectors in live mode as well.
- The real write paths (delete, promote, rollback, retire, retry) are where the Phase 17 dialog and targeting bugs would destroy or repoint real data. Those findings (WR-JSB-02, IN-JSB-06, IN-JSC-04, WR-JSC-01, IN-JSA-08) are mandatory, not polish.
</specifics>

<deferred>
## Deferred Ideas

- Authentication or a reverse proxy with auth for non-loopback use. Seam auth is still undecided (PROJECT.md key decisions).
- A Vite dev proxy or a React 19 + Vite + Sigma.js rebuild of the console.
- Graph visualisation (Sigma.js) on the Graph/vector browser. The screen stays a paged table browser.
- Server routes still missing: `POST /selectors/resolve`, `GET /refusals`, `POST /graph/node/attrs`, `POST /stores/counts`, `GET /jobs`, `GET /pipeline`, `POST /evidence/resolve-batch`, `POST /documents/reprocess`, `POST /jobs/{job_id}/cancel`, and the `/corpus` status/sort/search parameters.
- Fixing the Phase 17 test and build findings listed in D-18 (a Phase 17 fix round).
- Dark theme (17 Deferred).
</deferred>

---

*Phase: 18-gui-live*
*Context gathered: 2026-10-31*

## Proposal tables (auto-accepted)

### Grey Area 1/4: Serving, binding and build stack

| # | Question | ✅ Recommended | Alternative(s) |
|---|----------|---------------|-----------------|
| 1 | How is the console served to the browser? | Same origin: a launcher `--console` flag adds `GET /console` (hidden from OpenAPI) returning the one built HTML. Needs no CORS, and the Origin guard already admits the loopback origins. | `StaticFiles` mount on `create_app(console=True)`; open from file:// against an opt-in `--cors-origin` allow-list; Vite dev proxy |
| 2 | Bind and auth? | Loopback only: `--console` with a non-loopback host is a parser error, like `--operator`. No auth. `--console` does not imply `--operator`. This follows Phase 16 D-01 and D-10. | Reverse proxy with auth; `--console` implies `--operator` |
| 3 | Build stack and source location? | Plain HTML/JS ported from the mockup into `databasise/console/src/`, built by `mockups/build.py --src/--out` to a checked-in `databasise/console/operator-console.html` shipped as package data. The id check scans it, and the mockup stays byte-frozen. | React 19 + Vite + Sigma.js rewrite; single source tree with a build-time transport flag (impossible after the freeze, because mockup bytes cannot change) |
| 4 | What does the first plan do? | Verify the sha256 (matched on 2026-10-31), copy the sources into the live tree and build, run `freeze-variant`, run the id check and require exit 0. The copy comes first so the gate never fails between plans. | Freeze first, then port (gate red until the port lands); freeze in the last plan (contradicts 17 D-13) |

### Grey Area 2/4: Fixture-to-live transport, frozen ids and badges

| # | Question | ✅ Recommended | Alternative(s) |
|---|----------|---------------|-----------------|
| 1 | How do screens switch from fixtures to live calls? | One `api(method, path, body, opts)` transport returning `{status, body}`, the only `fetch` caller. Its result feeds the existing `classifyResponse`/`renderError`. | Per-screen fetch calls; a fixture/live runtime switch kept in the live build |
| 2 | What happens to the mock-only controls (`*.mock.*`, `shell.mock.banner`)? | Kept in the source and hidden in the live build. Ids stay scanned, so no control is removed. No fixture data is shown as live. | Exempt them in MOCKUP-PORT.md and delete them; keep them visible behind `?fixtures` |
| 3 | When does a badge drop? | At run time, from the live `/openapi.json`: method plus path matched, a qualifier needs its named parameters, and a failed load keeps every badge. | Build-time from GAP-ROUTES.json; drop all operator badges whenever `--operator` is set |
| 4 | What does a control with an absent route do live? | It stays visible and badged. It uses the client-side fallback where LIVE-07 names one, and is otherwise disabled with a tooltip naming the route. It never shows fixture data. | Keep serving fixture data (misleading in a live console); hide the control (violates LIVE-09) |
| 5 | Where do run history, job list and ledger log live? | In memory, mirrored to `sessionStorage` with try/catch. The evidence cache is in memory only. | In memory only (lost on reload); `localStorage` (persists across sessions and store roots) |

### Grey Area 3/4: Live request semantics

| # | Question | ✅ Recommended | Alternative(s) |
|---|----------|---------------|-----------------|
| 1 | How is the stream read? | fetch + ReadableStream SSE parser. It checks `res.ok` and `text/event-stream` first, ignores `:` lines, appends on `evidence` and completes on `final`. No `final` shows the disconnected state. `Run complete.` and Promote appear only after `final`. | `EventSource` (cannot POST a body); buffer the whole response then parse |
| 2 | How are errors shown? | `classifyResponse` on `refusal_type`, with the real status printed. A rejected fetch shows generic "server unreachable" and header `unreachable`. A 5xx loads `GET /log?limit=200` when present. StoreBusy and UnknownGraphNode go to their Graph states. | Status-code branching (contradicts GUI-06); no log tail |
| 3 | In-flight gate and polling? | A shared registry by kind. Ingest or delete disables Run. Health loads on page load, and its poll is off by default and skips while busy. Counts poll only while non-terminal > 0. The jobs poll runs only while the drawer is open. `/info` store-busy is read with health. | Server-only gating via `/info.write_in_flight` before every Run; always-on polling |
| 4 | LIVE-05 "different stores" notice? | No notice. M-04 was settled as option b in Phase 11 and LRAG-02 is done. Corpus and counts refresh after a delete, and the test also asserts query-after-ingest evidence. | Add the notice (changes a frozen screen); test the corpus path only |
| 5 | Cancellation? | AbortController per call. A new Run, a mode switch or a screen change aborts reads. Writes are never aborted once sent. Cancel before Confirm sends nothing. | No abort (stale responses land in the wrong mode); abort writes too (state unknown) |

### Grey Area 4/4: Phase 17 review findings and verification

| # | Question | ✅ Recommended | Alternative(s) |
|---|----------|---------------|-----------------|
| 1 | Where do fixes land? | In the live source only. The mockup stays frozen, and the disposition rows are marked `fixed in Phase 18`. | Fix the mockup and re-approve and re-freeze (one-way freeze, 17 D-13) |
| 2 | Which findings must Phase 18 absorb? | Every JS behaviour finding (WR-JSA-01 to 06, IN-JSA-07 to 09, WR-JSB-01 to 04, IN-JSB-05 to 08, WR-JSC-01, WR-JSC-02, IN-JSC-04, IN-JSC-08), plus the UI-review ledger nowrap fix. WR-JSC-01 follows the server's `active`/`tombstoned` semantics. | Only the three named by the orchestrator (WR-JSA-01, WR-JSA-02, WR-JSC-01); all 39 including the Phase 17 tests |
| 3 | What happens to the rest? | Fixture-only IN-JSC-05/06/07 are `n/a in live`. Test and build findings stay with Phase 17. The new live conftest adopts the IN-BLD-04 pattern and covers the IN-JSB-09 gap. | Fix the Phase 17 tests here too |
| 4 | How is live behaviour tested? | Playwright against an in-process uvicorn app on an ephemeral loopback port, with a temp store root, stub clients and a substituted corpus op. No provider spend. Store-busy comes from a raw pycozo lock. The badge test runs with and without `--operator`. The owner click-through with real clients is the last plan. | A recorded HAR replay; owner click-through only |
