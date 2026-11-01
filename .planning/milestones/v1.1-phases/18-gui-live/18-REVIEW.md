---
phase: 18
status: issues_found
depth: standard
files_reviewed: 29
findings:
  critical: 0
  warning: 6
  info: 9
  total: 15
reviewed: 2026-10-31
method: single adversarial reviewer (gsd-code-reviewer); every file in scope read in full; mockups/build.py --check run for both default and console paths (both exit 0, built console file is in sync with its sources); no tests run
files_reviewed_list:
  - databasise/launcher/serve_rest.py
  - mockups/build.py
  - databasise/console/__init__.py
  - databasise/console/src/page.html
  - databasise/console/src/parts/errors.html
  - databasise/console/src/screens/corpus.html
  - databasise/console/src/screens/documents.html
  - databasise/console/src/screens/evidence.html
  - databasise/console/src/screens/graph.html
  - databasise/console/src/screens/ledger.html
  - databasise/console/src/screens/query.html
  - databasise/console/src/dialogs/delete.html
  - databasise/console/src/dialogs/promote.html
  - databasise/console/src/dialogs/retire.html
  - databasise/console/src/dialogs/rollback.html
  - databasise/console/src/js/00-app.js
  - databasise/console/src/js/05-api.js
  - databasise/console/src/js/10-shared.js
  - databasise/console/src/js/20-query.js
  - databasise/console/src/js/21-compare.js
  - databasise/console/src/js/30-evidence.js
  - databasise/console/src/js/40-documents.js
  - databasise/console/src/js/50-corpus.js
  - databasise/console/src/js/60-ledger.js
  - databasise/console/src/js/70-graph.js
  - databasise/console/src/js/90-start.js
  - databasise/tests/gui_live/conftest.py
  - databasise/tests/gui_live/_corpus_fake.py
  - databasise/tests/gui_live/_opened.py
---

# Phase 18: Code Review Report

**Reviewed:** 2026-10-31
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

No critical findings. The security-sensitive pieces hold up.

- `console_csp()` hashes the one executable inline script and the one style block, rejects any other count, and emits no inline-allow keyword. The built page has no `style=` attribute, no `on*=` handler and no `javascript:` URL, so the hash policy does not break it. The JSON fixture block is `type="application/json"` and needs no hash.
- `/console` returns bytes read once from the packaged file at start-up. It takes no caller-supplied path, so there is no traversal surface. It is registered after the TrustedHost and Origin middleware, so both cover it.
- `--console` is refused on a non-loopback host and on `--port 0`. The Origin guard rejects `Origin: null` and foreign origins on every non-GET method.
- No `innerHTML`, `insertAdjacentHTML`, `outerHTML`, `eval` or `document.write` in any console source. Every server string (refusal attributes, validation messages, log tail, trace fields, SSE evidence) reaches the DOM through `textContent` or `createTextNode`.
- `sessionStorage` content is only parsed as JSON and then rendered through the same `textContent` paths. SSE frames are routed by `kind`, with non-JSON frames dropped.

The defects found are state-handling and robustness problems in the live screens. Six warnings are worth fixing before the owner click-through. Nine items are info.

### 17-REVIEW-DISPOSITION check ("fixed in Phase 18" rows)

All 23 rows were re-read against the live source. 22 are fixed as described. One is only partly fixed and is reported as R18-01.

| 17 ID | Result |
|-------|--------|
| WR-JSA-01 | fixed: `memberOk` and the one-member rule are enforced in `validate()`, 20-query.js:225-273 |
| WR-JSA-02 | fixed: `Compare.run` re-runs `update()` and the in-flight checks, 21-compare.js:377; `showState` no longer re-enables Run in compare mode, 20-query.js:60 |
| WR-JSA-03 | partly fixed: states and columns no longer show together, but the Run spinner stays visible next to the compare columns. See R18-01 |
| WR-JSA-04 | fixed: `setMode` cancels both, and Compare's `show` handler cancels both on leaving, 21-compare.js:520-524 |
| WR-JSA-05 | fixed: `syncTraceControls(null, "streaming")` keeps Promote and Compare disabled until `final` |
| WR-JSA-06 | fixed: each column carries its own `trace_token` |
| WR-JSB-01 | fixed: `origin` is captured per opened row, 30-evidence.js:94-109, 431-434 |
| WR-JSB-02 | fixed: the request is built in `confirmDelete` only, from the captured `pending` |
| WR-JSB-03 | fixed: `restoreJob()` repaints the last good page |
| WR-JSB-04 | fixed with the documented shortcut: `repaintHealthError()` after every clear |
| WR-JSC-01 | fixed: matches the server flags (`active` is lineage membership, head is the alias row's ordinal, tombstone records read `—`) |
| WR-JSC-02 | fixed: boxes locked while the preview waits, and the answer is dropped when none is checked |
| IN-JSA-07 | fixed: `checked = {}` before pinning |
| IN-JSA-08 | fixed: Promote needs `done && !partial && lastTrace` |
| IN-JSA-09 | fixed: the real status is printed |
| IN-JSB-05 | fixed: `leaveJobs()` on drawer close and on leaving the screen |
| IN-JSB-06 | fixed for row targeting by id, but the `retrying` map breaks for some valid ids. See R18-03 |
| IN-JSB-07 | fixed: `full_doc_id` gates the link |
| IN-JSB-08 | fixed: `abortResolve()` restores the opener |
| IN-JSC-04 | fixed: Cancel and Escape send nothing, and Confirm locks both until the answer |
| IN-JSC-08 | fixed: `checkSize()` after every `renderError` |
| UI-review top-3 fix 2 | fixed: nowrap and a min-width are in 60-ledger.css |

## Warnings

### R18-01: Compare Run leaves the Run spinner visible after a successful multi-column compare (17 WR-JSA-03, partial)

**File:** `databasise/console/src/js/21-compare.js:388-398` (also 150-156) and `databasise/console/src/js/20-query.js:58`
**Issue:** `Compare.run` calls `QueryScreen.showState("running")` (line 388), which shows `query.run.spinner`. On a 2xx with two or more selectors it then calls `hideStates()` and `showColumns()`. `hideStates()` hides the state views, the result panel and the error box, but not the spinner. Only `QueryScreen.showState` ever hides the spinner, so it keeps spinning beside an enabled Run button for as long as the columns are on screen. It clears only on the next mode switch or the next query. The mockup did not have this: it used per-column spinners and never called `showState("running")`. This is a state shown next to the compare columns, the exact class of bug WR-JSA-03 recorded.
**Fix:**
```js
function hideStates() {
  STATES.forEach(function (s) { ID("state." + s).hidden = true; });
  ID("result.panel").hidden = true;
  ID("run.spinner").hidden = true;   // the running state is over
  errorsBox.hidden = true;
}
```

### R18-02: Ledger "partial run" pre-flight blocker can never fire for the browser-history source

**File:** `databasise/console/src/js/20-query.js:220` and `databasise/console/src/js/60-ledger.js:129, 202`
**Issue:** `remember()` stores only `{query, selector, trace_token, timestamp}`. `historyEntries()` in the Ledger reads `partial: !!e.partial` and `degraded: !!e.degraded` from those entries, and both fields are always absent. So under the default "History" source, `refreshPreflight()` never blocks a partial trace and the trace list never shows the partial or degraded chips. The operator can select a partial run and press Promote. Only the server's `PartialRunEvidenceError` refusal stops it. The "Recent runs (server)" source gets the flags from `GET /traces`, so only the browser-history path is dead. The partial blocker is guaranteed UI-SPEC behaviour, and it is dead code on the path the operator uses most.
**Fix:** Record the flags when the run is remembered, and pass them through the compare path too:
```js
runLog.add({ query: body.query.text, selector: body.selector, trace_token: env.trace_token,
             partial: !!env.partial, degraded: !!env.degraded, timestamp: new Date().toISOString() });
```

### R18-03: Plain-object registries keyed by server or user ids break for ids such as `constructor` and `__proto__`

**File:** `databasise/console/src/js/50-corpus.js:45, 256, 409-414`; `databasise/console/src/js/10-shared.js:115, 141, 159`
**Issue:** `retrying = {}` is indexed by `document_id`. The document-id grammar `^[A-Za-z0-9_-]+$` (40-documents.js:6) admits `constructor`, `toString`, `valueOf`, `hasOwnProperty` and `__proto__`. For those ids `retrying[id]` is already truthy, so `retryDocument` returns silently and `fillRows` paints the row "Sending. A request that has been sent cannot be cancelled." forever. The Retry button is dead for that document. `Resolution`'s `aliases = {}` has the same flaw: an alias named `constructor` resolves to `Object`, and `describe()` prints "Resolves to: not satisfiable (undefined)". The `Resolution` map is the display-only half; `retrying` is the functional half.
**Fix:** Use maps with no prototype:
```js
var retrying = Object.create(null);   // 50-corpus.js:45
var aliases = Object.create(null);    // 10-shared.js:115 (also arms, caps, def lookups)
```

### R18-04: A 2xx with an unexpected body throws mid-render and leaves the screen in `running` with Run disabled

**File:** `databasise/console/src/js/20-query.js:175-197, 358-363`; `databasise/console/src/js/21-compare.js:260-281, 351-366, 395-397`
**Issue:** `classifyResponse` returns `"result"` for any 2xx. `renderResult` then dereferences `env.evidence.length`, `env.token_accounting` and `env.seam_events` without a shape check, and the stream path does the same with the `final` event. `fillBody` and `columnsOf` do the same for compare. If a body is not an envelope (for example a 200 with text from an intermediary, a `final` event without `token_accounting`, or a compare column that is not an envelope), the exception is thrown before `showState` runs. In the stream path it is thrown inside the success handler of `.then(ok, lost)`, which `lost` does not catch. The view stays "running", `run.submit` stays disabled, and only a reload recovers. The Documents, Ledger and Corpus screens already guard with `typeof body === "object"` plus a field check and fall back to a "The server answered without X" error. Query and Compare do not.
**Fix:** Add a shared guard and use it before rendering:
```js
function isEnvelope(b) {
  return b && typeof b === "object" && Array.isArray(b.evidence) &&
         Array.isArray(b.token_accounting) && Array.isArray(b.seam_events);
}
// applyResponse: if (shape === "result" && !isEnvelope(body)) { renderError("query", 0, null, { text: "The server answered without a result." }); showState("error-500"); return "generic"; }
```
Apply the same check to the stream `final` event and to each compare column.

### R18-05: Alias selectors are always treated as LightRAG, so the delete confirmation can state the wrong consequence

**File:** `databasise/console/src/js/40-documents.js:25-28, 103-105, 473-476`; `databasise/console/src/js/10-shared.js:157-158`
**Issue:** `family()` returns `"hipporag"` only when `picker.arm() === "hipporag"`. For an alias in the catalogue, `Resolution.resolve` deliberately returns `arm: null` (the arm is unknown client-side), so `family()` reports `"lightrag"`. For an alias that resolves to HippoRAG, the destructive Delete dialog says "removes it from the v1 corpus ... The query stores are not changed; the deleted document's chunks can stay resolvable." That is false for HippoRAG. The paste card note, the "Target: LightRAG" label and the post-delete `corpus-changed` refresh are also wrong. The file-upload pane is not blocked either, so the server refusal is the only guard. The dialog names the selector label, but the consequence text is the part the operator relies on before a delete that cannot be undone.
**Fix:** When the arm is unknown (an alias), give the dialog neutral wording instead of a LightRAG claim. For example, add a third `DELETE_TAIL.unknown`: "This removes it from the stores the alias resolves to and cannot be undone." Drive `family()` from `arm === null && selector.alias !== undefined` to `"unknown"`.

### R18-06: Graph lists from the previous selector stay on screen when the new selector's read fails

**File:** `databasise/console/src/js/70-graph.js:218-239, 270-277`
**Issue:** `loadAll()` starts a read for a changed selector but keeps `nodes` and `chunks` from the old selector. `run()` repaints with the old data while loading, and again after a failure, with the failure banner above it. The "last good page stays" rule fits a same-selector retry or page change, not a selector change. After switching from Default to an alias that is refused (or to a busy store), the tables still list the old selector's nodes and chunks under the new selector's controls. Clicking a node row then opens it with the new selector against ids from the old store.
**Fix:** Clear the cached pages when the selector key changes:
```js
function loadAll() {
  loaded = true;
  lastKey = JSON.stringify(sel());
  cancel("node"); node = null;
  nodes = null; chunks = null;       // pages belong to the previous selector
  paint();
  loadNodes(0);
  loadChunks(0);
}
```

## Info

### R18-07: A streamed query leaves `InFlight` as soon as the response headers arrive

**File:** `databasise/console/src/js/05-api.js:40-63` and `databasise/console/src/js/20-query.js:329`
**Issue:** With `opts.raw`, `api()` resolves `{status, res}` and runs `done()` right away, so the `query` call stops counting before the SSE body is read. LIVE-06 says the health poll never runs "while a query ... is in flight". The server resolves the whole envelope before the first header (`_resolve_streamed_envelope`), so the uncovered window is only the event replay, which is short. It is still a spec gap.
**Fix:** For a raw call, let the caller release it: return `done` on the result, or have `runStream` hold its own `InFlight.begin("query")` until `readStream` settles.

### R18-08: Health poll tick does not skip while the previous health load is still pending

**File:** `databasise/console/src/js/50-corpus.js:189-196` and `databasise/console/src/js/00-app.js:97-116`
**Issue:** `healthTick` skips only when `InFlight.any()`. `Console.loadHealth` registers no kind, so with a hung server (the case where health matters most) a 30 s poll starts a second load while the first waits for its 60 s timeout. The older call's "timed out" report can overwrite the newer call's loading state.
**Fix:** Keep a `healthPending` flag, or register the health call as kind `"health"` and have `healthTick` skip when it is set.

### R18-09: Evidence cache is never invalidated after a write

**File:** `databasise/console/src/js/30-evidence.js:12, 155-156`
**Issue:** The `(namespace, ref)` cache is kept for the page's lifetime (LIVE-04). After a successful delete, `corpus-changed` refreshes Corpus but not this cache, so Open on a deleted document's chunk shows the cached record instead of `UnresolvableEvidenceReferenceError` ("record no longer present"). This is within the stated rule, but it hides the very refusal the screen has a view for.
**Fix:** `Console.on("corpus-changed", function () { cache = {}; });` (use `Object.create(null)`, see R18-03).

### R18-10: Raw selector JSON bypasses the picker blockers, and an empty capability list reports "not valid JSON"

**File:** `databasise/console/src/js/20-query.js:260-275`
**Issue:** `{"alias": ""}` and hash-shaped aliases in the raw box are never run through `picker.blockers()` (`pickMsg` is skipped whenever `raw !== ""`). They go to the server and come back as a validation or refusal banner. `{"capability": []}` fails `memberOk` and shows `MSG.badJson`, which is the wrong message; `SELECTOR_MSG.noCapability` already exists.
**Fix:** After building `override`, run it through the same `blockerOf` logic Compare uses, and map an empty capability list to `SELECTOR_MSG.noCapability`.

### R18-11: `Picker.attach` and its callers shadow the global `api` transport

**File:** `databasise/console/src/js/10-shared.js:201` and `databasise/console/src/js/40-documents.js:525`
**Issue:** `var api = {...}` inside `Picker.attach`, and the `function (api)` callback parameter, shadow the one transport the design says is the only place that calls `fetch`. Nothing breaks today. Any later `api("POST", ...)` added inside either scope would hit the picker object and throw.
**Fix:** Rename to `selectorApi` (or `view`) in both places.

### R18-12: `mockups/build.py` raises `ValueError` for paths outside the repo and writes non-atomically

**File:** `mockups/build.py:41, 104-105, 110`
**Issue:** `path.relative_to(ROOT)` and `out.relative_to(ROOT)` raise `ValueError` for a `--src` or `--out` outside the repository (a temp directory), so the intended "missing file" and "is stale" messages become tracebacks. `out.write_bytes` is not atomic, so an interrupted build leaves a truncated packaged console file, which `console_csp()` would then refuse at start-up.
**Fix:** Format with a helper that falls back to the absolute path, and write to `out.with_suffix(".tmp")` then `os.replace`.

### R18-13: Launcher start-up failure for a bad console page is a traceback, and the script-type regex is loose

**File:** `databasise/launcher/serve_rest.py:76, 217`
**Issue:** `console_csp()` raises `RuntimeError` inside `build_app`, which `main()` calls after the engine and store lock are open. The `finally` closes the fd, but the operator gets a traceback rather than a `refuse()` message. The `type=` detection regex `\btype\s*=` also matches `data-type=`, so a future tag such as `<script data-type="x">` would be misclassified. The `X-Content-Type-Options` and other hardening headers are on `/console` only, not on the JSON routes.
**Fix:** Catch `RuntimeError` around `build_app` and `return refuse(exc)`. Anchor the regex with `(?<![\w-])type`. Optionally add `nosniff` in the launcher's HTTP middleware.

### R18-14: Query text is stored unbounded in `sessionStorage` and nothing reads it

**File:** `databasise/console/src/js/20-query.js:220` and `databasise/console/src/js/05-api.js:141-147`
**Issue:** LIVE-02 asks for `{query, selector, trace_token, timestamp}`, but no screen reads `query` back. A large pasted query, times 50 entries, can exceed the storage quota. `save()` then fails silently and the same quota loss also stops the job list and the ledger log from persisting.
**Fix:** Store `query.text.slice(0, 200)` (enough for a label), or give each `SessionLog` its own size cap.

### R18-15: IN-BLD-03 is still open in the shipped build

**File:** `mockups/build.py:52`
**Issue:** `fixtures_json` escapes `</` but not `<!--`. The embedded JSON block is read by the same HTML tokenizer as scripts, and the live page's CSP hash is computed by regex over the page. The built file currently contains no `<!--` (checked), so nothing breaks, but a future refusal or resolution catalogue entry containing `<!--` followed by `<script` would break the page.
**Fix:** `text.replace("</", "<\\/").replace("<!--", "<\\!--")`.

---

_Reviewed: 2026-10-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
