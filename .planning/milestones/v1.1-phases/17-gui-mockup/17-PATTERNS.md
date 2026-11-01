# Phase 17: GUI Mockup - Pattern Map

**Mapped:** 2026-10-25
**Files analyzed:** 14 (new/modified)
**Analogs found:** 8 / 14 (the rest are greenfield; 17-RESEARCH Patterns 1-5 and the Playwright skeleton in 17-RESEARCH are the templates)

All analog paths below were checked with `git ls-files` (tracked). `databasise/tests/gui/`, `mockups/` and `docs/gui/MOCK-IDS.json` / `GAP-ROUTES.json` do not exist yet.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `mockups/operator-console.html` (generated, frozen) | static UI | event-driven (client-only, fixtures) | none in repo; UI-SPEC + `v1/lightrag_webui/src/index.css` (palette only) | no analog |
| `mockups/build.py`, `mockups/src/*` (optional assembler, RESEARCH) | utility | transform / batch | `databasise/tests/seam/test_refusal_catalogue_file.py` (deterministic generate-and-compare) | partial |
| `databasise/tests/gui/__init__.py` | test pkg | - | `databasise/tests/seam/` package layout | exact |
| `databasise/tests/gui/conftest.py` | test fixtures | request-response (browser) | `databasise/tests/conftest.py` (autouse offline guard + fixtures) | role-match |
| `databasise/tests/gui/test_gui_01..11_*.py` | test | request-response | `databasise/tests/seam/test_refusal_catalogue_file.py` (module docstring, regenerate hint, set-diff assertion) | role-match |
| `databasise/tests/gui/test_playwright_smoke.py` | test | request-response | RESEARCH Pattern 1 skeleton | no analog |
| GUI-02 id test (inside `test_gui_02_*`) | test | transform | `scripts/mockup-id-check.py` `find_ids`, `variant_spans` | exact (reuse, do not reimplement) |
| GUI-03 route classification test | test | request-response | `databasise/seam/operator_rest.py` route list + `create_app(operator=True)` | exact |
| GUI-06 catalogue test | test | transform | `test_refusal_catalogue_file.py::_runtime_subclasses` | exact |
| `docs/gui/MOCK-IDS.json` | generated data | batch | `docs/gui/refusals.json` (sorted JSON, `indent=2`, trailing newline) | exact |
| `docs/gui/GAP-ROUTES.json` | generated data | batch | `docs/gui/refusals.json` | role-match |
| id-list / GAP-ROUTES generator | utility | transform | generator is the test itself in `test_refusal_catalogue_file.py` (`DATABASISE_REGENERATE=1`) | exact |
| `docs/gui/MOCKUP-APPROVAL.md`, `docs/gui/API-INVENTORY.md`, `.planning/REQUIREMENTS.md`, `17-UI-SPEC.md` | docs | - | edit in place; REQUIREMENTS "Requirement text exceptions" precedent in `13-CONTEXT.md:186-194` | n/a |
| `databasise/pyproject.toml`, `databasise/uv.lock` | config | - | `[dependency-groups].dev` block, lines 59-71 | exact |

## Pattern Assignments

### Generated-file sync test (GUI-02 MOCK-IDS, GAP-ROUTES, GUI-06)
**Analog:** `databasise/tests/seam/test_refusal_catalogue_file.py` (READ with the Read tool only; the edit-guard hook blocks Bash reads of locked checks and the file must not be modified).

**Header and regenerate hint** (lines 1-29): docstring names the requirement and decision, then:
```python
_CATALOGUE = Path(__file__).resolve().parents[3] / "docs" / "gui" / "refusals.json"
_REGENERATE_HINT = (
    "regenerate with: DATABASISE_REGENERATE=1 databasise/.venv/bin/python -m pytest -q "
    "databasise/tests/seam/test_refusal_catalogue_file.py -p no:cacheprovider"
)
```
**Runtime subclass walk** (lines 33-38): filter `cls.__module__.startswith("databasise.tests")`.
**Regenerate-then-compare core** (lines 56-77):
```python
if os.environ.get("DATABASISE_REGENERATE") == "1":
    _CATALOGUE.parent.mkdir(parents=True, exist_ok=True)
    _CATALOGUE.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
assert _CATALOGUE.is_file(), f"{_CATALOGUE} is missing; {_REGENERATE_HINT}"
...
missing = sorted(set(expected_by_name) - set(actual_by_name))
extra = sorted(set(actual_by_name) - set(expected_by_name))
assert actual == expected, f"... missing={missing} extra={extra} ...; {_REGENERATE_HINT}"
```
Copy for MOCK-IDS.json: expected = `sorted(find_ids(variant text))`, write with `indent=2` + newline; assert set equality and no duplicates. Caveat from RESEARCH: a new `test_ref` module is locked later, so the regenerate path must live in the Wave 0 test file, planned in full up front.

**GUI-06 specifics:** this analog imports `_REFUSAL_FACTORIES`/`_all_seam_refusal_subclasses` from `databasise.tests.seam.test_rest_transport` (a protected module). RESEARCH Pattern 5 avoids that dependency by walking `SeamRefusalError.__subclasses__()` recursively after importing `databasise.seam.refusals`, `.trace_store`, `.evidence`, `.tokens`. Compare to `docs/gui/refusals.json` and to the refusal types embedded in the mockup fixture block (D-09: no hard-coded count).

### Id extraction and parity (GUI-02)
**Analog:** `scripts/mockup-id-check.py` (hyphenated filename: load with `importlib.util.spec_from_file_location`).
Reuse, do not rewrite: `find_ids(text)` (lines 38-51), `variant_spans(text, variant)` (116-149), `frozen_want_ids`. Constraints the HTML must respect: `TAG_RE = <(/?)\s*([A-Za-z][A-Za-z0-9-]*)([^<>]*?)(/?)>` (no raw `<`/`>` in attribute values; use `&lt;`/`&gt;`); comments, `<script>`, `<style>` are opaque; the `data-mock-variant` root `<div>` must be balanced with no self-closed `<div>`; `SKIP_DIRS` contains `mockups` and `tests`, so ids in `mockups/` and tests never count as UI sources. Test selectors like `[data-mock-id="x"]` are safe (lookbehind `(?<![\[\w-])`).

### Route classification (GUI-03, D-10)
**Analog:** `databasise/seam/operator_rest.py` lines 76-145. Decorators are the ground truth for the 10 operator routes: `@app.get("/info")` (80), `/wirings` (85), `/ledger/aliases` (90), `POST /ledger/history` (95), `/traces` (100), `POST /promote/preview` (105), `/chunks` (117), `/graph/nodes` (122), `/graph/node` (127), `GET /log` (134, only `if log:`).
```python
def add_operator_routes(app: FastAPI, engine: Any, *, log: bool = False) -> None:
    @app.get("/info")
    async def get_info() -> dict[str, Any]: ...
```
Test shape: build `create_app(store_root=tmp, workspace="w", clients={})` and again with `operator=True, log_path=...`; `operator_only = operator_routes - default_routes` must equal the `GAP-ROUTES.json` entries with kind `operator`. Mounting happens at `databasise/seam/rest.py:545-549`. Pass `log_path` or `/log` will be missing.

### Browser fixtures (`databasise/tests/gui/conftest.py`)
**Analog:** `databasise/tests/conftest.py` lines 109-131 (autouse `_offline_unless_live` socket guard). It patches `socket.socket.connect` in the test interpreter only; Playwright's node driver and Chromium run in other processes, so the guard does not interfere. Keep every Playwright test a plain sync `def` (pyproject uses `asyncio_mode = "auto"`).
No in-repo Playwright analog. Use 17-RESEARCH Pattern 1 (`mockup_path` fixture asserts the file exists and FAILS, never skips; `browser` fixture sets `PLAYWRIGHT_BROWSERS_PATH` default `~/.cache/databasise/playwright-browsers`, honours `DATABASISE_REQUIRE_BROWSER=1`) and Pattern 2 (offline context, `page.on("request")`, `page.on("pageerror")`). Fixture order in test signatures: `mockup_path` before `browser`.

### Dependency edit (`databasise/pyproject.toml`)
**Analog:** `[dependency-groups] dev` block, lines 59-71. It is a PEP 735 group, not an extra. Add with the same comment convention (decision reference plus "Package legitimacy confirmed by the developer"):
```toml
    # Phase 17 (GUI-01, D-01, D-15): Playwright for Python. Pinned to 1.59.0 to match nixpkgs 26.05
    # playwright-driver (chromium revision 1217). Owner approved playwright, greenlet, pyee in 17-CONTEXT D-15.
    "playwright==1.59.0",
```
Then `cd databasise && uv lock`. D-15 records the approval, so no legitimacy checkpoint is needed for these three packages.

### Fixture sources to embed (build-time copy, do not retype)
- `docs/gui/refusals.json` (51 entries `{refusal_type, module, attribute_keys, http_status}`)
- `databasise/tests/fixtures/selector-resolution.json` (`rows` 29, `reachable` all true)
- API-INVENTORY §3 / §5.1a for response bodies; follow the code where UI-SPEC drifts (CONTEXT "Claude's Discretion": `v1_reachable`, `interrupted`, `tier` null, `GET /corpus` takes `selector`, retry route exists).

## Shared Patterns

### Fail, never skip, on the absent mockup
**Apply to:** every `test_gui_*` node. The BAK `record-fail` flow needs a non-zero failing run naming the node. Assert `MOCKUP.is_file()` first (RESEARCH Pattern 1).

### One test_ref per row, whole file planned in Wave 0
**Apply to:** all 11 GUI rows. A `test_ref` file becomes a protected check after `lock-checks`; later plans must not list it under `Create:/Modify:/Test:` (plan-gate `--check-edits`). Set via `scripts/ledger-amend.py set --id GUI-NN --test-ref <path::node>`; there is no `--text` verb, so requirement text amendments go in REQUIREMENTS.md and UI-SPEC only.

### Deterministic generated JSON
**Source:** `test_refusal_catalogue_file.py:60` (`json.dumps(..., indent=2) + "\n"`, sorted). **Apply to:** MOCK-IDS.json, GAP-ROUTES.json, and `mockups/build.py` output (byte-stable because the freeze hashes it).

### Untrusted text rendering
**Apply to:** all JS in the HTML. `textContent`/`createTextNode` only, never `innerHTML` (RESEARCH Pitfall 11).

### Freeze ordering (D-13)
**Apply to:** the last plan. Write `MOCKUP-APPROVAL.md` (variant `console-a`, path, sha256, date). Do NOT run `ledger-amend.py freeze-variant` in Phase 17 (moves to Phase 18 plan 1), and do not copy the HTML outside `mockups/`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `mockups/operator-console.html` | static UI | event-driven | No static mockup or `mockups/` dir exists; use 17-UI-SPEC and its Authoring Contract. `v1/lightrag_webui/src/index.css` is a palette source only |
| `databasise/tests/gui/test_playwright_smoke.py` and browser fixtures | test | request-response | Playwright not installed; no browser tests exist. Use 17-RESEARCH Patterns 1-3 |
| `mockups/build.py` assembler (optional) | utility | transform | No HTML assembler exists. Closest idea is the regenerate-and-compare test above |

## Metadata

**Analog search scope:** `databasise/tests/`, `databasise/seam/`, `scripts/`, `docs/gui/`, `databasise/pyproject.toml`
**Files read:** test_refusal_catalogue_file.py, mockup-id-check.py (1-175), tests/conftest.py (95-145), operator_rest.py (70-100), 17-CONTEXT.md, 17-RESEARCH.md (1-470; lines 471-629 not read; 17-UI-SPEC.md not read)
**Pattern extraction date:** 2026-10-25
