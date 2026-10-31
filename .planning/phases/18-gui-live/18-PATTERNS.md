# Phase 18: GUI Live - Pattern Map

**Mapped:** 2026-10-31
**Files analyzed:** 14 new/modified (groups)
**Analogs found:** 13 / 14
**All analog paths verified git-tracked** (`git ls-files`). Test analogs were read with Read only (edit guard).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `mockups/build.py` (add `--src/--out`) | utility (build) | batch/transform | itself (`build()`, `main()`, lines 44-111) | exact (modify) |
| `databasise/console/src/**` (copy of `mockups/src/**`) | component set | copy | `mockups/src/**` | exact (verbatim copy) |
| `databasise/console/operator-console.html` | build output | transform | `mockups/operator-console.html` | exact |
| `databasise/console/__init__.py` | config (package marker) | n/a | `databasise/launcher/__init__.py` | role-match |
| `databasise/pyproject.toml` | config | n/a | its own `[tool.setuptools] packages` + `package-data` (lines 127-177) | exact (modify) |
| `databasise/launcher/serve_rest.py` (`--console`, `GET /console`) | route/launcher | request-response | `--operator` flag + host rule, same file lines 33-37, 122-126; `build_app` 51-87 | exact (modify) |
| `console/src/js/05-api.js` (transport, `InFlight`, SSE, `applyBadges`) | service | request-response + streaming | `mockups/src/js/00-app.js` (`Console` bus), `10-shared.js` (`classifyResponse`/`renderError`) | role-match |
| `console/src/js/20..70-*.js` (screen ports) | component | request-response | same-named `mockups/src/js/*.js` (port in place) | exact (modify copy) |
| `console/src/js/00-app.js` (health, mock hiding) | component | request-response | `mockups/src/js/00-app.js` lines 39-98 | exact (modify copy) |
| `console/src/css/60-ledger.css` (nowrap) | config (style) | n/a | `mockups/src/css/60-ledger.css` | exact (modify copy) |
| `databasise/tests/gui_live/conftest.py` | test fixture | event-driven | `databasise/tests/gui/conftest.py` | role-match |
| `databasise/tests/gui_live/_corpus_fake.py` | test helper | request-response | `databasise/tests/seam/test_rest_corpus_endpoints.py` lines 118-175 | exact |
| `databasise/tests/gui_live/test_live_0N_*.py` | test | request-response | `databasise/tests/gui/conftest.py` `MockUI`; seam tests below | role-match |
| `17-REVIEW-DISPOSITION.md` rows | doc | n/a | existing rows | exact |
| wheel-contents test (new file, not edit of `test_packaging.py`) | test | batch | `test_packaging.py` lines 69-78 (per RESEARCH; not re-read, locked) | partial |

## Pattern Assignments

### `mockups/build.py` (utility, transform)

**Analog:** itself. Module globals `SRC`/`OUT` (lines 21-22) are used by `fixtures_json()` (46), `expand()` (67, 72) and `build()` (82). Thread `src` through, keep zero-arg `build()` (the Phase 17 build test calls it with no args) and keep `SHARED_FIXTURES` rooted at `ROOT`.

```python
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mockups" / "src"
OUT = ROOT / "mockups" / "operator-console.html"
...
def fixtures_json() -> str:            # -> fixtures_json(src: Path)
    for path in sorted((SRC / "fixtures").glob("*.json")):
...
def build() -> str:                    # -> build(src: Path = SRC)
    html = expand(read(SRC / "page.html", "page.html"), "page.html")
...
def main(argv: list[str]) -> int:
    if argv not in ([], ["--check"]):  # replace with argparse: --check, --src (default SRC), --out (default OUT)
```
Error text at line 100 hardcodes `mockups/operator-console.html`; make it use the `--out` path. `read()` uses `path.relative_to(ROOT)` (line 40), so `--src` must be under ROOT. Verify after edit: `build.py --check` exit 0 and sha256 `bf98e79e...` unchanged.

### `databasise/launcher/serve_rest.py` (launcher route, request-response)

**Analog:** same file, `--operator` handling.

**Flag** (lines 33-37):
```python
parser.add_argument(
    "--operator",
    action="store_true",
    help="mount the operator read routes (wiring names, aliases, trace tokens); loopback --host only",
)
```
**Host rule** in `main()` (lines 122-126) — copy for `--console`, same placement, before `check_engine_arguments` so no store lock is taken:
```python
if args.operator and not is_loopback_host(args.host):
    parser.error(
        "--operator needs a loopback --host, even with --allow-remote-unauthenticated: the operator "
        "routes expose wiring names and trace tokens"
    )
```
**Route placement** in `build_app` (lines 51-87): add after the `origin_guard` middleware, before `return app`. Use `getattr(args, "console", False)` (line 65 comment: protected tests hand-build a Namespace). Local imports inside the function match the style (`from fastapi.responses import JSONResponse` at line 57). Read the packaged file once at build time via `importlib.resources.files("databasise.console").joinpath("operator-console.html").read_bytes()`. `@app.get("/console", include_in_schema=False)`. Origin guard `own` set (line 77) already admits the page origin; `--port 0` is unsupported for the console.

### `databasise/seam/operator_rest.py` (reference only; not modified)

Pattern for what hidden/gated routes look like and what the badges map to: `add_operator_routes(app, engine, *, log=False)`, with `if log:` mounting `GET /log` (lines 132-145). `/openapi.json` includes these, which is what `applyBadges` matches against. `GET /console` must use `include_in_schema=False` so this surface is unchanged.

### `databasise/pyproject.toml` (config)

Add `"databasise.console"` to the `packages` list (line 127+, comment style: name it in the same commit that creates it, lines 133-134) and a package-data entry in the existing table (lines 169-177):
```toml
[tool.setuptools.package-data]
"databasise.evidence" = ["wirings/*.json"]
"databasise.wirings" = ["*.json", "lightrag/*.json", "hipporag/*.json"]
...
"databasise.console" = ["operator-console.html"]   # new
```
`package-dir = {"databasise" = "."}` means `databasise.console` is the `databasise/console/` directory. `src/` is not a package and is not shipped.

### `console/src/js/05-api.js` (transport, request-response + streaming)

**Analog:** `mockups/src/js/00-app.js` for the shared-scope conventions (one concatenated script, `"use strict"`, globals `FIX`, `$id`, `Console`; sorted-glob order so `05-api.js` loads after `00-app.js`, before `10-shared.js`). Event bus to reuse for `inflight`/`health`:

```javascript
var Console = {
  screens: {}, handlers: {}, current: null,
  register: function (name, impl) { this.screens[name] = impl; },
  on: function (event, fn) { (this.handlers[event] = this.handlers[event] || []).push(fn); },
  emit: function (event, payload) { (this.handlers[event] || []).forEach(function (fn) { fn(payload); }); },
};
```
Code style: ES5 `var`/`function`, no arrow functions, `textContent` only. Body of `api()`, `readStream()` and `applyBadges()`: copy RESEARCH Patterns 1-3 (18-RESEARCH.md lines 256-315) verbatim as the starting point. Required corrections from RESEARCH pitfalls: `/health` must not register in `InFlight` (Pitfall 12); badge removal must check `closest("[data-needs-backend]") === el` for nested wrappers and remove `title`.

**Error rendering to reuse unchanged** (`mockups/src/js/10-shared.js` 215-222):
```javascript
function classifyResponse(status, body) {
  var structured = body !== null && typeof body === "object";
  if (structured && body.refusal_type === "ForeignEngineRefusalError") return "server-failure";
  if (structured && typeof body.refusal_type === "string") return "refusal";
  if (status === 422 && structured && Array.isArray(body.detail)) return "validation";
  if (status >= 200 && status < 300) return "result";
  return "generic";
}
```
`renderError(screen, status, body, opts)` is at line 301, `wireErrors(screen)` at 320, `fillRefusal` at 245 (replace its fixed `422` footer with the real status, IN-JSA-09). `api()` returning `{status: 0, body: "server unreachable"}` already lands in `fillGeneric` (292-298) and `healthState` (`00-app.js` 43-46).

### Screen ports `console/src/js/{20-query,21-compare,30-evidence,40-documents,50-corpus,60-ledger,70-graph}.js`

**Analog:** the same file in `mockups/src/js/` (the copy is edited in place). Seam map per file is in 18-RESEARCH.md lines 399-413. Representative fixture seam to replace (`20-query.js` 255-300):
```javascript
function pickFixture() { ... }          // delete live
function finish(name) {                 // fixture lookup + later(200*i) streaming simulation
  var fx = FIX.query[name];
  ...
  rows.forEach(function (ref, i) { later(200 * (i + 1), function () { fillEvidence(i + 1, ref); }); });
```
becomes `api("POST","/query/stream",...,{raw:true,signal,kind:"query"})` then `readStream`, then existing `renderResult`/`fillEvidence`/`remember`. Cross-cutting edits required in every screen: (a) delegation + `ensureRows` instead of per-slot `ID("x.open-"+n)` loops (RESEARCH Pattern 4, Pitfall 3); (b) evidence body is the envelope `EvidenceRef` unchanged, never `{id,...}` (Pitfall 2, sites 20-query.js:374, 21-compare.js:491, 70-graph.js:454); (c) compare Default selector `null` maps to `{}` (Pitfall 1); (d) keep requested offset in screen state since `next_offset` only is returned (Pitfall 4); (e) no remaining `FIX.*` reads except `FIX.refusals` and `FIX.resolution`.

### `databasise/tests/gui_live/conftest.py` (test fixture, event-driven)

**Analog:** `databasise/tests/gui/conftest.py`. Copy the module-scoped `browser` fixture (lines 39-67) as is — the module scope is load-bearing (comment lines 39-40):
```python
BROWSERS = Path.home() / ".cache" / "databasise" / "playwright-browsers"
@pytest.fixture(scope="module")
def browser():
    if BROWSERS.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS))
    os.environ.setdefault("PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS", "1")
    require = os.environ.get("DATABASISE_REQUIRE_BROWSER") == "1"
    ...
    pw = sync_playwright().start()
    try:
        instance = pw.chromium.launch()
    ...
    yield instance
    instance.close()
    pw.stop()
```
Copy the `MockUI` shape (lines 70-84: `el(mock_id)` -> `[data-mock-id="..."]`, `expect(target)`, `nav`) as `LiveUI`, minus the `window.__mock` helpers. Differences from the analog: `new_context(...)` is online (analog uses `offline=True`, line 122), navigate to `http://127.0.0.1:{port}/console` (analog uses `file://`), record `pageerror`, and fail the **test** not teardown: analog does `assert errors == []` after `yield` (line 139), which is the IN-BLD-04 defect; use a `pytest_runtest_call` hookwrapper or fail in the call phase. Do not assert on console `error` messages (Chromium logs every 4xx/5xx). Fail on any non-loopback request.

**Server fixture** (module-scoped; RESEARCH Pattern 5, lines 320-340): pre-bound socket, `serve_rest.build_parser().parse_args([... "--console", "--port", str(port)])`, `serve_rest.build_app(args, clients)`, `uvicorn.Server(...).run(sockets=[sock])` in a daemon thread, wait on `server.started`, stop with `should_exit`. Per-module `OPERATOR` flag selects the three launch modes for LIVE-09. Never `@pytest.mark.live` (addopts `-m "not live"`).

### `databasise/tests/gui_live/_corpus_fake.py` (test helper)

**Analog:** `databasise/tests/seam/test_rest_corpus_endpoints.py` (lines 118-175). Import `_make_registry` and `_patch_status_and_health`-style closure; do not rewrite. Registry swap (118-142):
```python
base = default_registry()
registry = PartRegistry(seed_tracer_parts=False)
for name in base.keys():
    candidate = base.get(name)
    registry.register(swapped.get(candidate.name_at_version, candidate))
```
Status/health fake patched on `databasise.seam.engine.run_corpus_op` (145-175): closure over a mutable `documents` list delegating to the stub driver's `_run_status`/`_run_health`. `monkeypatch` is function-scoped, so use `pytest.MonkeyPatch()` inside module-scoped fixtures. Also patch `databasise.seam.engine.default_registry` for the stub registry (RESEARCH Pattern 5).

**Offline stub clients (HippoRAG path)** — `databasise/tests/seam/test_hipporag_write_path.py` lines 31-116:
```python
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]
class _StubEmbeddingClient:  # embed() -> EmbeddingResult(vectors=[[1.0,0.0,0.0]...], tokens=TokenAccounting(...))
class _StubIngestQueryLLMClient:  # chat() dispatches on prompt content ("---Candidate Facts---", "---Recognised Entities---")
def _make_engine(store_root, *, workspace=_WORKSPACE):
    return Databasise(store_root=store_root, workspace=workspace,
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()})
```
Import them (cross-test imports of private helpers already occur, per RESEARCH) rather than copying. `_StubIngestQueryLLMClient` forces the dpr-fallback so evidence resolves to real text; use it for query-after-ingest (D-15, Open Question 1) and the whole promote -> alias query -> rollback -> retire flow.

### `databasise/tests/gui_live/test_live_08_graph.py` (store-busy)

**Analog:** `databasise/tests/seam/test_console_graph.py` lines 75-90 (raw pycozo lock -> 409):
```python
import pycozo
path = root / "ws" / _NAMESPACE / "graph.cozo"
from databasise.stores.graph import _ClientRegistry
for key in client.app.state.engine._graph_holds:
    _ClientRegistry.release(key)
client.app.state.engine._graph_holds.clear()
held = pycozo.Client("rocksdb", str(path.resolve()), dataframe=False)
try:
    busy = client.post("/graph/nodes", json={})
finally:
    held.close()
assert busy.status_code == 409 ...  # refusal_type == "StoreBusyError", store_kind == "graph"
```
Graph seeding (lines 33-40): `CozoGraphStore(_NAMESPACE, "ws", store_root)`, `upsert_node`/`upsert_edge`, `index_done_callback()`, `finalize()` (releases the registry entry so a raw client can hold the path). Preferred live variant: hold the raw client before the engine's first graph read to avoid touching `_graph_holds`. HippoRAG graph namespace is `hipporag-graph`. `GET /info` `graph_busy` does not see a raw client; assert the 409 banner only.

### `--console` launcher tests (LIVE-01), new file under `databasise/tests/launcher/` or `gui_live/`

**Analog:** `databasise/tests/seam/test_console_surface.py` lines 237-252 (remote host refusal) and 225-234 (route set diff):
```python
main(["--operator", "--host", "192.168.1.5", "--allow-remote-unauthenticated", "--no-clients",
      "--store-root", str(root)])   # -> SystemExit code 2, "--operator" and "loopback" in stderr
assert not (root / ".engine.lock").exists()
```
Replace `--operator` by `--console`. Add: `/openapi.json` identical with and without `--console`; `GET /console` 200 with the CSP headers when set, 404 without.

## Shared Patterns

### Text-only DOM and shared scope
**Source:** `mockups/src/js/10-shared.js` line 1 rule and `00-app.js` line 1-2 (`"use strict"`, one concatenated script). Apply to all console JS: `textContent` only, no `innerHTML` with server text, ES5 style, files sorted by name.

### Error classification
**Source:** `mockups/src/js/10-shared.js` 197-340. Apply to every screen: all responses through `classifyResponse` then `renderError`; never branch on status alone.

### Frozen ids
**Source:** `scripts/mockup-id-check.py` (ID regex needs literal `data-mock-id="..."`; skips `mockups/`, `tests/`, `.planning`, `build`, `dist`). Cloned rows via `setAttribute("data-mock-id", ...)` do not trip it. Mock-only controls stay in source with `hidden`.

### Test guard conventions
**Source:** project hooks. `Bash` commands naming `databasise/tests` files are blocked when they use shell operators; use Read/Edit/Write. Write all `gui_live` files before linking `test_ref` (linked files become protected).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `console/src/js/05-api.js` SSE reader (`fetch` + `ReadableStream`) | service | streaming | The mockup simulates streaming with `setTimeout`; use RESEARCH Pattern 2 (verified against the live wire format: no `event:` line, dispatch on `kind`) |
| wheel-contents test for `databasise/console/operator-console.html` | test | batch | Closest is `test_packaging.py`, which is locked and was not re-read; write a new file following its wheel-build approach |
| uvicorn-thread server fixture | test fixture | event-driven | No existing in-process uvicorn fixture; `test_console_log.py` uses a subprocess (cannot take stub clients). Use RESEARCH Pattern 5 |

## Metadata

**Analog search scope:** `mockups/`, `databasise/launcher/`, `databasise/seam/operator_rest.py`, `databasise/tests/gui/`, `databasise/tests/seam/` (named files), `databasise/pyproject.toml`
**Files read:** 12 (CONTEXT, RESEARCH, serve_rest.py, build.py, operator_rest.py, gui/conftest.py, test_console_graph.py, test_hipporag_write_path.py (1-130), test_rest_corpus_endpoints.py (100-175), test_console_surface.py (225-265), 00-app.js, 10-shared.js excerpts)
**Not scanned:** graph-MCP (coverage unavailable for these files), 20-70 JS bodies beyond the cited excerpts (line seams taken from RESEARCH)
**Pattern extraction date:** 2026-10-31
