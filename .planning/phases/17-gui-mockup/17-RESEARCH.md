# Phase 17: GUI Mockup - Research

**Researched:** 2026-10-25
**Domain:** one static HTML/CSS/JS operator-console mockup (file://), id stamping, a pytest + Playwright-for-Python check suite on NixOS, and the BAK ledger/freeze tooling around it
**Confidence:** HIGH for tooling, routes, fixtures and BAK mechanics (read from source this session); MEDIUM for the Playwright-on-NixOS runtime path (everything except the actual browser launch was verified)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### A. Roadmap owner decisions (UI-SPEC defaults confirmed)
- **D-01 (GUI-01):** The test suite uses Playwright for Python, added to the `dev` extra in `databasise/pyproject.toml` and run under pytest. On NixOS (host legion), the browsers come from nixpkgs `playwright-driver.browsers` via `PLAYWRIGHT_BROWSERS_PATH`, not from `playwright install`. The planner must include the step that provides them. Playwright is not installed today.
- **D-02 (GUI-02):** Ids follow the grammar `<screen>.<region>.<control>`: lower case, dot separated. Screen roots are `screen-<name>`, slot suffixes are `-N`, and the reserved regions are `mock`, `state` and `error`. The list is `docs/gui/MOCK-IDS.json`, a sorted array generated from the final file, and the test asserts set equality with it. — **Reversibility:** costly — Phase 18's port plan (MOCKUP-PORT.md) and `scripts/mockup-id-check.py` key on these ids after the freeze.
- **D-03 (GUI-03):** §5.1 "later" items that have no proposed route appear in one text-only `<screen>.planned.list` per screen (a `<details>` titled `Planned (not built)`), with no controls. The item lists are in UI-SPEC "Needs-backend Registry".
- **D-04 (GUI-06):** The refusal catalogue is the generated `docs/gui/refusals.json`, carried forward from Phase 16 D-07 and not re-asked.
- **D-05 (GUI-11):** `POST /graph/node` returns references only: edges as `{src, tgt, edge_types, weight}`. Node attributes load through an explicit `Load attributes` button that calls a new proposed route, `POST /graph/node/attrs`. This follows Phase 16 D-16, which allows references plus an allowlist and defers dereference. The new route is recorded in API-INVENTORY at freeze.

### B. Requirement amendments (frozen text updated to match the engine)
The owner chose to amend all four. The amendments go into REQUIREMENTS.md and the ledger rows (through `scripts/ledger-amend.py` only, because the ledger is hook-frozen) **before** the build plans. Where an amendment contradicts a row in UI-SPEC "Decisions taken by default", the UI-SPEC row is updated too.
- **D-06 (GUI-04, GUI-05):** All six arms, including hybrid and global, are reachable. They are offered in the selector picker and as compare columns, and `Resolves to` uses the post-WIRE-01 table (`databasise/tests/fixtures/selector-resolution.json`). Remove the "unreachable" sentences. This matches the UI-SPEC default already.
- **D-07 (GUI-05, GUI-10):** Promotion from HippoRAG runs is **allowed**, because the server has accepted HippoRAG traces since Phase 14 D-05. Remove the HippoRAG pre-flight blocker, the disabled `Promote this arm` on HippoRAG columns and the disabled `promote from this result`. Partial-run blockers stay. **This overrides the UI-SPEC default.**
- **D-08 (GUI-08):** Delete is offered for **any selector the server can delete under**, LightRAG and HippoRAG alike (HIPP-16 delete wiring). The confirmation dialog still names document_id and the target selector. **This overrides the UI-SPEC default.**
- **D-09 (GUI-06):** The requirement text says "all SeamRefusalError subclasses" without a count. The pytest compares `refusals.json` against `SeamRefusalError.__subclasses__()` (51 today), so the number cannot go stale.

### C. Badging routes that exist behind `--operator`
- **D-10:** There are two badge kinds. Every control on an unbuilt or operator-only route keeps `data-needs-backend="<route>"`, which is the GUI-03 test contract.
  - Routes that Phase 16 built and mounts only under `--operator` add `data-backend-state="operator"` and show a visible `operator route` badge instead of `needs backend`. These are `/info`, `/wirings`, `/ledger/aliases`, `/ledger/history`, `/traces`, `/promote/preview`, `/chunks`, `/graph/nodes`, `/graph/node` and `/log`. The planner verifies the exact set against the Phase 16 code and API-INVENTORY §5.
  - Routes that don't exist keep the `needs backend` badge.
  - The GUI-03 test asserts on `data-needs-backend` plus the presence of one badge of either kind. LIVE-02's rule (drop the attribute once the route appears in `/openapi.json`) is unchanged.

### D. Review and freeze
- **D-11:** The owner reviews by opening `mockups/operator-console.html` from file:// in a local browser. Nothing is published, and the Playwright suite is the mechanical check.
- **D-12:** The last plan is a human-verify plan:
  1. Claude drafts the new needs into `docs/gui/API-INVENTORY.md` (at least `POST /graph/node/attrs` and any route strings the UI-SPEC chose `(default)`) and syncs `docs/gui/GAP-ROUTES.json`.
  2. The plan stops at a `checkpoint:human-verify` while the owner clicks through.
  3. Only on approval does it write `mockup_freeze {variant: "console-a", path: "mockups/operator-console.html", sha256}` through `scripts/ledger-amend.py` and confirm that `scripts/mockup-id-check.py` exits 0.

  — **Reversibility:** one-way — after the freeze, every frozen id must appear in the Phase 18 build or be mapped in MOCKUP-PORT.md (LIVE-09), and a re-freeze needs a new ledger amendment.

### Claude's Discretion
- Every other row of UI-SPEC "Decisions taken by default" is accepted as written. This covers:
  - variant `console-a`, light theme only, system fonts, 7-symbol sprite;
  - type, spacing and palette;
  - compare cap of 4 columns, 4 rows and 5 evidence slots;
  - blocking style (query Run clickable with an inline message, everything else natively disabled);
  - polling off by default, the stream mock timings, `not probed` = a key the server did not report;
  - dialog dismiss labels, and `Submit` kept on paste and upload.
- How plans are split and ordered, provided the amendment work (D-06 to D-09) lands before the screens it affects, and the freeze (D-12) is last.

### Deferred Ideas (OUT OF SCOPE)
- Publishing the mockup as a claude.ai artifact for review from other devices: not chosen, and available on request.
- Dark theme: UI-SPEC allows a `.dark` token set later without id changes.
- Reviewed todos not folded: `melodyscribe-spike-rig-experiments.md` and `melodyscribe-interface-skill.md` (MelodyScribe project, moved to DeBIOS-Foundation/MelodyScribe).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GUI-01 | Single static file, six screens, header health, zero network, inline fixtures | Playwright provisioning (Standard Stack), request-capture skeleton, file shape rules from `mockup-id-check.py` |
| GUI-02 | Unique `data-mock-id` on every control/region, `data-mock-variant`, checked-in id list, freeze | `html.parser` test skeleton, regex-vs-parser parity test, `MOCK-IDS.json` generator, `freeze-variant` verb |
| GUI-03 | `data-needs-backend` + visible badge for every missing/unbuilt route | Route classification table (operator vs missing vs field-present), `GAP-ROUTES.json` shape, code-derived classification test |
| GUI-04 | Query mode controls, state switcher, client-side blocks | UI-SPEC screen 1; resolution table from `selector-resolution.json`; D-06 amendment |
| GUI-05 | Compare mode, key rendering, duplicate warning, N columns | UI-SPEC screen 1; compare key rule verified in API-INVENTORY 3.1.3; D-06/D-07 amendments |
| GUI-06 | Four error shapes, static catalogue of all SeamRefusalError subclasses | `refusals.json` (51 entries, verified), `__subclasses__()` walk, `classifyResponse` order |
| GUI-07 | Evidence + Trace inspectors, Debug template clone | Fixture shapes (3.2.1, 3.2.2); `tier`/`feed_tier` code drift (Pitfall 9) |
| GUI-08 | Paste/upload/jobs/delete | UI-SPEC screen 3; D-08 amendment; HippoRAG delete wiring |
| GUI-09 | Corpus & Health | `HealthReport` real shape (drift from UI-SPEC fixtures, Pitfall 8); `interrupted` status |
| GUI-10 | Ledger promote form + timeline | Timeline fixture; D-07 amendment; ledger route shapes (5.1a) |
| GUI-11 | Graph/vector browser | Operator route shapes (5.1a); D-05 attrs route; `StoreBusyError` attribute `store_kind` |
| LIVE-02 / LIVE-09 | Consumers of the freeze (Phase 18) | The completion gate already runs `mockup-id-check.py` once `mockup_freeze` is set (Pitfall 2) |
</phase_requirements>

## Summary

The phase builds one HTML file and the checks around it; there is no new library choice except the test driver. The UI design contract (`17-UI-SPEC.md`) already fixes layout, ids, copy and fixtures, so the research effort went into the places where the contract meets machinery: Playwright on NixOS, the BAK scripts that will read the file, the Phase 16 route set, and drift between the approved UI-SPEC and the code it describes.

Five findings change how the planner should write plans. (1) The `dev` "extra" in `databasise/pyproject.toml` is a PEP 735 `[dependency-groups]` group, not an extra, and the pip `playwright` wheel must be pinned to the version whose Chromium revision matches nixpkgs: `playwright==1.59.0` (Chromium 1217) with `playwright-driver.browsers` from the 26.05 channel (driver 1.59.1, Chromium 1217). (2) `scripts/ledger-amend.py` has no verb that edits a row's `text`; the GUI rows' text is already a truncated summary ending in `...`, so the D-06 to D-09 amendments land in `REQUIREMENTS.md` only (plus UI-SPEC), exactly as Phases 12 and 13 recorded "Requirement text exceptions". (3) **D-12 step 3 cannot hold as written:** once `mockup_freeze` is set, `scripts/check-ledger.py` runs `scripts/mockup-id-check.py` inside the completion gate, and that script exits 1 for every frozen id that is not present in a UI source file outside `mockups/` and `tests/`. No such UI source exists until Phase 18, so the check exits 1 after the freeze unless the owner chooses otherwise (Open Question 1). (4) Every GUI row needs its own `test_ref` (`path::node`), a recorded failing run before any code exists (`record-fail`), and must fail, not skip, on the failing run; the Playwright fixtures must therefore assert the mockup file exists before they look for a browser. (5) The UI-SPEC fixtures are stale against the code in several places (health `engine` keys, `engine_reason` and `clients` already on `GET /health`, the `interrupted` status, `tier`/`feed_tier` null, a HippoRAG corpus listing); Pitfall 8 lists them.

**Primary recommendation:** Wave 0 = provision browsers + add the pinned Playwright dev dependency behind a human-verify checkpoint, write the 11 failing test nodes under `databasise/tests/gui/`, register them with `set --test-ref` and `record-fail`, and land the REQUIREMENTS.md/UI-SPEC amendments (D-06 to D-10). Build the single HTML file from per-screen source partials with a small Python assembler under `mockups/src/` (the id check skips `mockups/`), so parallel screen plans do not collide on one 100 KB file. Last plan = id list, GAP-ROUTES, API-INVENTORY drafts, then the human-verify freeze, with the exit-code expectation settled by the owner first.

## Project Constraints (from CLAUDE.md)

- Work enters through a GSD command; no direct repo edits outside a GSD workflow (`.claude/CLAUDE.md` "GSD Workflow Enforcement").
- Python tests run under pytest from `databasise/` (`.venv/bin/python -m pytest`); dev dependencies go in the `dev` group of `databasise/pyproject.toml`; ruff, target py311 in that file (`[tool.ruff] target-version = "py311"`).
- The ledger is hook-frozen: write only through `scripts/ledger-amend.py`; read with Read or one plain `cat/grep/jq/ls` command with no shell operators. Never write `ledger/` directly.
- Locked check files (listed in `check_locks.files`) cannot be edited or even read through Bash by the guard hook; use Read.
- Never read `.env*` files or `v1/parity-env.txt` (hook does not cover the symlink target).
- Global: never create files with spaces in the name; plain technical language; file references in final replies are clickable workspace-relative links.
- Runtime: local NixOS, no Docker, no external servers; the mockup needs zero network (GUI-01).
- `workflow.nyquist_validation` is true (Validation Architecture required); `security_enforcement` is false in `.planning/config.json:48`, so no Security Domain section (one XSS-hygiene pitfall is kept below).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Six screens, state views, nav, dialogs | Browser / Client | — | Static file:// page; no server involved in this phase |
| Fixture data | Browser / Client (inline JSON) | — | `<script type="application/json" id="mock-fixtures">`, shapes copied from API-INVENTORY section 3 and 5.1a |
| Client-side blocks (empty text, hash alias, 26,214,400 bytes, page size 1..100, document id pattern, duplicate keys) | Browser / Client | — | These mirror server rules the defects ledger says the server does not check |
| Error-shape classification (`classifyResponse`) | Browser / Client | — | One function used by real paths and `__mock.inject` |
| Refusal catalogue | Browser / Client (embedded copy) | Repo file `docs/gui/refusals.json` | Embedded at build time; pytest compares to `SeamRefusalError.__subclasses__()` |
| Id stamping and id list | Repo tooling (assembler + `MOCK-IDS.json`) | pytest | The check scripts read source text, not the DOM |
| Badge classification (operator vs missing) | Repo tooling (`GAP-ROUTES.json`) | pytest over `create_app(operator=True)` routes | Keeps the badge kind honest against the code |
| Freeze | BAK ledger | `scripts/mockup-id-check.py` | `freeze-variant` records sha256; the check enforces ids in UI sources |
| Test browsers | Host (NixOS, nixpkgs) | pytest fixtures | Generic Playwright downloads do not run on legion (verified below) |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `playwright` (PyPI) | pin `==1.59.0` | Headless-browser tests (D-01) | Locked by D-01. 1.59.0 expects Chromium revision 1217 [VERIFIED: raw `browsers.json` at tag v1.59.0, `"name": "chromium", "revision": "1217"`], and nixpkgs 26.05 ships Chromium 1217 [VERIFIED: `/nix/store/4fn5q60vi29f6rxmq27rln0y4zdjcc2a-nixos-26.05/nixos/pkgs/development/web/playwright/browsers.json`: `"chromium": { "revision": "1217", "browserVersion": "147.0.7727.15"`]. PyPI has 1.59.0 but no 1.59.1 wheel [VERIFIED: pypi.org/pypi/playwright/json releases `1.59.1 []`]. Latest on PyPI is 1.64.1; do not take it, its Chromium revision will not match nixpkgs. |
| `playwright-driver.browsers` (nixpkgs 26.05) | driver 1.59.1 | The browsers, via `PLAYWRIGHT_BROWSERS_PATH` | Locked by D-01. `nix-instantiate` on this host: `[ "1.59.1" "1.59.0" ... ]` for `playwright-driver.version` and `python3Packages.playwright.version`. Output path `/nix/store/35ks1vk4jj0jkqb82p5waixxzifbbsy2-playwright-browsers` is not in the local store but `nix path-info --store https://cache.nixos.org` returns it, so it substitutes from the binary cache [VERIFIED]. |
| `pytest` + `pytest-asyncio` | already in `dev` (`pytest>=8.4.2`, `pytest-asyncio>=1.2`) | Runner | `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`; Playwright tests must be plain sync functions |
| stdlib `html.parser` | — | GUI-02 element/id walk | Named in the GUI-02 requirement test text |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi` (already installed via `rest` extra) | in venv | Build `create_app(operator=True)` in the route-classification test | GUI-03 code-derived badge check |
| stdlib `importlib.util` | — | Load `scripts/mockup-id-check.py` (hyphenated name) to reuse `find_ids` / `variant_spans` | Parity test between the parser and the regex checker |
| `greenlet`, `pyee` | pulled in by playwright 1.59.0 (`pyee<14,>=13`, `greenlet<4.0.0,>=3.1.1`) [VERIFIED: pypi.org/pypi/playwright/1.59.0/json `requires_dist`] | Playwright runtime deps | Neither is in `databasise/uv.lock` today [VERIFIED: grep of `^name = ` found only `typing-extensions`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Browsers from `playwright-driver.browsers` | System `chromium` on PATH via `launch(executable_path=...)` | `/run/current-system/sw/bin/chromium` exists (Chromium 156.0.8078.47) and avoids a ~GB build, but it is not what D-01 locks and its version differs from the driver's protocol expectations; keep as a documented fallback only |
| `playwright install` browsers | — | Does not work here: `~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome --version` fails with `error while loading shared libraries: libglib-2.0.so.0: cannot open shared object file` [VERIFIED by running it] |
| `pytest-playwright` plugin | plain `playwright.sync_api` with own fixtures | The plugin adds options/fixtures and a `--browser` CLI that the repo's strict `addopts` and asyncio auto mode do not need; plain fixtures keep the skip logic in one place |
| `nix-shell`/flake dev shell | `nix-build '<nixpkgs>' -A playwright-driver.browsers -o <symlink>` | No flake or shell.nix exists in the repo; a GC-rooted symlink outside the repo is the smallest step |

**Installation (for the Wave 0 plan; I installed nothing):**
```bash
# 1. browsers (GC-rooted symlink outside the repo; substitutes from cache.nixos.org)
nix-build '<nixpkgs>' -A playwright-driver.browsers -o "$HOME/.cache/databasise/playwright-browsers"
# 2. python dependency: add to [dependency-groups].dev in databasise/pyproject.toml
#    "playwright==1.59.0",
cd databasise && uv lock && uv sync          # updates uv.lock (network)
# 3. runtime env for the tests
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/databasise/playwright-browsers"
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
export PLAYWRIGHT_NODEJS_PATH="$(command -v node)"   # only if the wheel's bundled node fails (see Pitfall 4)
```

**Version verification:** `PLAYWRIGHT_NODEJS_PATH` is honoured by playwright-python 1.59.0 [VERIFIED: `playwright/_impl/_driver.py` at tag v1.59.0: `os.getenv("PLAYWRIGHT_NODEJS_PATH", str(driver_path / "node"))`]. System node is v24.21.0 [VERIFIED: `node --version`].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| playwright | PyPI | years (1.59.0 uploaded 2026-04-29; latest 1.64.1 uploaded 2026-10-22) | not reported by the seam | github.com/Microsoft/playwright-python (PyPI `project_urls.homepage`; author "Microsoft Corporation", Apache-2.0) | SUS (`too-new`, `unknown-downloads`, `no-repository`) | Flagged. The flags come from the newest release date and missing stats, not from a doubtful project. Planner adds `checkpoint:human-verify` before install and pins `==1.59.0`. |
| greenlet | PyPI | years | not reported | python-greenlet/greenlet | SUS (`unknown-downloads`) | Transitive of playwright; include in the same checkpoint |
| pyee | PyPI | years | not reported | jfhbrook/pyee | SUS (`too-new` 2026-10-24, `unknown-downloads`, `no-repository`) | Transitive of playwright (`pyee<14,>=13`); include in the same checkpoint |

Verdicts from `gsd-tools query package-legitimacy check --ecosystem pypi playwright greenlet pyee typing-extensions` run this session. `typing-extensions` returned SUS (`unknown-downloads`, `no-repository`) but is already locked in `uv.lock` and is not new.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious [SUS]:** playwright, greenlet, pyee. Planner inserts one `checkpoint:human-verify` before `uv lock`/`uv sync`. The repo's existing precedent is the "Package legitimacy confirmed by the developer" comments in `databasise/pyproject.toml`.

No package is added for the mockup itself: `Tool: none` in the UI-SPEC, hand-written HTML/CSS/JS, no CDN, no web font.

## Architecture Patterns

### System Architecture Diagram

```
 owner / pytest
      |
      v
 file:///.../mockups/operator-console.html          (one static file, zero network)
      |
      +--> <head><style>  tokens, layout, [hidden]{display:none!important}
      |
      +--> <body>
      |      <div data-mock-id="shell.root.app" data-mock-variant="console-a">   <-- variant span
      |         header(health) | nav(6) | 6x <section hidden screen-*> | 4x <dialog> | <svg hidden> sprite
      |      </div>                                                               <-- wrapper closes
      |      <script type="application/json" id="mock-fixtures">  inline fixtures + embedded refusals catalogue
      |      <script>  store/state -> render(screen) -> classifyResponse(status, body) -> error shape component
      |                window.__mock = { show, setState, inject, loadFixture }
      |
      +--> user action / test hook
              |
              v
        client-side pre-check (empty text, hash alias, size, pattern, page size, duplicate key)
              |  blocked -> inline message, no state change
              v  allowed
        fixture lookup (screen, fixtureName)  --200--> result view (answer, badges, evidence, tokens, seam events)
              |                               --422/5xx--> classifyResponse -> refusal | validation | server-failure | generic
              v
        badges: wrapper[data-needs-backend] + ONE of  span.badge-nb "needs backend"  |  span "operator route" (data-backend-state="operator")

 repo tooling (outside the wrapper's reach)
   mockups/src/*  --assembler-->  mockups/operator-console.html --id extraction--> docs/gui/MOCK-IDS.json
   docs/gui/GAP-ROUTES.json  <--classified against-->  create_app(operator=True).routes
   scripts/ledger-amend.py freeze-variant  -->  ledger mockup_freeze {variant,path,sha256}
   scripts/check-ledger.py  -->  scripts/mockup-id-check.py (every frozen id must be in UI sources outside mockups/)
```

### Recommended Project Structure

```
mockups/
  operator-console.html        # generated output; the frozen file (sha256 binds these bytes)
  src/                         # skipped by the id check ("mockups" is in SKIP_DIRS at any depth)
    head.css  shell.html  query.html  evidence.html  documents.html  corpus.html  ledger.html  graph.html
    fixtures.json  app.js  screens/*.js
  build.py                     # deterministic assembler: concatenates partials, expands slot repeats (open-1..5 ...)
docs/gui/
  MOCK-IDS.json                # sorted array of every id (D-02)
  GAP-ROUTES.json              # route strings + kind (operator | missing | field)
databasise/tests/gui/
  __init__.py  conftest.py     # browser/page fixtures, mockup path assertion, request capture
  test_gui_01_*.py ... test_gui_11_*.py
```

Why an assembler: the UI-SPEC requires literal slot ids (`query.evidence.open-3`, `query.row2.move-up`, seven selector-picker instances), which is several hundred hand-typed ids if written as one file [ASSUMED: count not computed]. Parallel screen plans editing one 100 KB file would also conflict. The generated file is still one static file, and `build.py` output must be byte-stable because the freeze hashes it. Hand-writing remains acceptable if the planner prefers it; then sequence the screen plans, do not parallelize them.

### Pattern 1: Test-first with fail-not-skip (BAK flow)
**What:** each GUI row gets a distinct `test_ref` = `databasise/tests/gui/<file>.py::<node>`; the node must fail before the mockup exists and the failing output must name the node.
**When to use:** all 11 rows.
```python
# databasise/tests/gui/conftest.py  (new file; becomes a protected check once locked)
import os, shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]          # repo root (docs/ lives here)
MOCKUP = ROOT / "mockups" / "operator-console.html"

@pytest.fixture(scope="session")
def mockup_path() -> Path:
    # FAIL, never skip, when the file is absent: record-fail needs a non-zero exit that names the test.
    assert MOCKUP.is_file(), f"{MOCKUP} is missing (GUI mockup not built yet)"
    return MOCKUP

@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    default = Path.home() / ".cache" / "databasise" / "playwright-browsers"
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and default.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(default)
    pw = sync_api.sync_playwright().start()
    try:
        b = pw.chromium.launch()
    except sync_api.Error as exc:
        pw.stop()
        if os.environ.get("DATABASISE_REQUIRE_BROWSER") == "1":
            pytest.fail(f"browser required but unavailable: {exc}")
        pytest.skip(f"no Playwright browser: {str(exc).splitlines()[0]}")
    yield b
    b.close(); pw.stop()
```
Fixture order matters: list `mockup_path` before `browser` in the test signature so a missing file fails first.

### Pattern 2: Zero-request capture (GUI-01)
```python
# Source: Playwright Python sync API (page.on("request"), browser.new_context(offline=True))
def test_gui_01_six_screens_zero_requests(browser, mockup_path):
    ctx = browser.new_context(offline=True, viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    seen, errors = [], []
    page.on("request", lambda r: seen.append(r.url))
    page.on("pageerror", lambda e: errors.append(str(e)))        # free JS-exception check
    page.goto(mockup_path.as_uri())
    for name in ("query", "evidence", "documents", "corpus", "ledger", "graph"):
        page.locator(f'[data-mock-id="shell.nav.{name}"]').click()
        for other in ("query", "evidence", "documents", "corpus", "ledger", "graph"):
            vis = page.locator(f'[data-mock-id="screen-{other}"]').is_visible()
            assert vis == (other == name)
    external = [u for u in seen if not u.startswith(("file://", "data:", "blob:", "about:"))]
    assert external == [] and errors == []
```

### Pattern 3: GUI-02 element walk plus checker parity
```python
from html.parser import HTMLParser
class Walk(HTMLParser):
    NEED = {"button", "input", "select", "textarea", "a", "summary"}
    NEED_ROLE = {"tab", "dialog", "table", "status"}
    def __init__(self): super().__init__(); self.ids, self.missing, self.root = [], [], None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-mock-variant" in a: self.root = a
        need = tag in self.NEED or a.get("role") in self.NEED_ROLE
        mid = a.get("data-mock-id")
        if mid: self.ids.append(mid)
        elif need: self.missing.append((tag, a))
```
Then assert `len(ids) == len(set(ids))`, `missing == []`, `set(ids) == set(json.load(MOCK-IDS))`, and that the same set equals `find_ids(text of variant_spans)` loaded with `importlib.util.spec_from_file_location("mockup_id_check", "scripts/mockup-id-check.py")`. The parity assertion catches a raw `<`/`>` inside an attribute value, which `TAG_RE = [^<>]*?` mishandles (see Pitfall 3).

### Pattern 4: Code-derived badge classification (GUI-03 / D-10)
```python
from databasise.seam.rest import create_app
default = {(m, r.path) for r in create_app(store_root=tmp, workspace="w", clients={}).routes for m in getattr(r, "methods", ()) }
operator = {... create_app(store_root=tmp2, workspace="w", clients={}, operator=True, log_path=tmp2/"log.txt") ...}
operator_only = operator - default        # must equal the set of GAP-ROUTES entries with kind == "operator"
```
`GET /log` exists only when `log_path` is passed (see route table), so the test must pass one. Strings like `GET /corpus (status, sort, search)` are parsed as the first two tokens plus a parenthetical.

### Pattern 5: GUI-06 catalogue test (no dependency on a protected test module)
```python
import databasise.seam.refusals, databasise.seam.trace_store, databasise.seam.evidence, databasise.seam.tokens  # load the 4 outside-module subclasses
from databasise.seam.refusals import SeamRefusalError
def runtime_subclasses():
    seen, todo = set(), list(SeamRefusalError.__subclasses__())
    while todo:
        c = todo.pop()
        if c not in seen: seen.add(c); todo.extend(c.__subclasses__())
    return {c.__name__ for c in seen if not c.__module__.startswith("databasise.tests")}
# assert runtime_subclasses() == {e["refusal_type"] for e in json.load(open("docs/gui/refusals.json"))}
# and == the refusal types embedded in the mockup's fixture block
```
Importing the four modules matters: without them the set is smaller. 51 today, direct and recursive walks agree [VERIFIED: ran `len(S.__subclasses__())`, recursive count and non-test count: `51 51 51`].

### Anti-Patterns to Avoid
- **Creating or renaming ids from JS.** The id list and the port check read source text. Slots are literal; JS fills text and toggles `hidden`.
- **`data-mock-id="..."` text inside the wrapper's scripts or comments, or any `<`/`>` in an attribute value.** Write `&lt;`/`&gt;` (UI-SPEC Authoring Contract).
- **Skipping because the file is absent.** It hides the failing run `record-fail` needs.
- **Editing a `test_ref` file in a later plan.** Once a row's `test_ref` is set it is a protected check; `plan-gate.py --check-edits` reports `Task N edits <path> (no owner grant)` for any plan line `Create:/Modify:/Test:` naming it. Plan the whole test file in Wave 0 against the UI-SPEC ids.
- **`innerHTML` for fixture or user text.** Use `textContent`; the page renders attacker-shaped strings by design (refusal attributes, `cause`, `error_message`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser automation | A CDP/puppeteer wrapper or shell-out to `chromium --headless` | `playwright.sync_api` | D-01; handles waits, viewports, offline context |
| Refusal catalogue | A hand-typed list of 51 types | Embed `docs/gui/refusals.json` at build time | D-04; the CONN-02 sync test already keeps it equal to the code |
| Resolution table | A re-derived selector table | Embed `databasise/tests/fixtures/selector-resolution.json` rows (29 rows) plus the four documented combinations | D-06; file is regenerated by its own test |
| Id extraction for `MOCK-IDS.json` | A second regex | `find_ids` / `variant_spans` from `scripts/mockup-id-check.py` | The freeze check uses exactly that logic; two extractors can disagree |
| Freeze sha256 | A manual `sha256sum` into the ledger | `ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html` | The verb computes the digest itself (`ledger-amend.py:983-984`) |
| Modal dialogs | A div-based modal | Native `<dialog role="dialog">` + `showModal()` | UI-SPEC; `Escape`/focus trap come free |
| SSE/stream | A real stream | Timed fixture rows (200 ms apart after an 800 ms running state) | UI-SPEC; the real server has no incremental stream (API-INVENTORY 3.1.2) |

**Key insight:** the machinery that will judge this file (the id regex checker, the plan gate, the phase gate) is source-text based and unforgiving; reuse its functions in tests instead of re-implementing them.

## Operator route set (question 2, D-10)

Routes mounted by `create_app(operator=True)` [VERIFIED: `databasise/seam/operator_rest.py`, decorators at lines 80-145, quoted]:

| Decorator (verbatim) | Line |
|---|---|
| `@app.get("/info")` | 80 |
| `@app.get("/wirings")` | 85 |
| `@app.get("/ledger/aliases", responses=_FAULT_RESPONSES)` | 90 |
| `@app.post("/ledger/history", responses=_FAULT_RESPONSES)` | 95 |
| `@app.get("/traces", responses=_FAULT_RESPONSES)` | 100 |
| `@app.post("/promote/preview", ...)` (multi-line decorator) | 105 |
| `@app.post("/chunks", responses=_FAULT_RESPONSES)` | 117 |
| `@app.post("/graph/nodes", responses=_OPERATOR_STORE_RESPONSES)` | 122 |
| `@app.post("/graph/node", responses=_OPERATOR_STORE_RESPONSES)` | 127 |
| `@app.get("/log", ...)` inside `if log:` | 134 |

`create_app` mounts them only `if operator:` (`rest.py:545-549`: `add_operator_routes(app, engine, log=log_path is not None)`), so `/log` also needs `log_path`. The set equals the D-10 list exactly (10 routes) [VERIFIED].

Non-operator routes that already exist [VERIFIED: `rest.py` decorators 387-541]: `POST /query`, `/compare`, `/query/stream`, `/evidence/resolve`, `/trace/resolve`, `/documents`, `/documents/upload`, `GET /jobs/{job_id}`, `DELETE /documents/{document_id}`, `POST /documents/{document_id}/retry`, `GET /health`, `GET /corpus`, `GET /corpus/counts`, `POST /promote`, `/rollback`, `/retire`.

Absent everywhere [VERIFIED: grep of `selectors/resolve|stores/counts|/refusals|/pipeline|resolve-batch|documents/reprocess|graph/node/attrs` in `databasise/seam/*.py` found no route]: classification of the 21 UI-SPEC registry strings:

| Kind | Route strings |
|---|---|
| `operator route` (10) | `GET /ledger/aliases`, `POST /ledger/history`, `GET /traces`, `POST /promote/preview`, `GET /info`, `GET /wirings`, `GET /log`, `POST /graph/nodes`, `POST /graph/node`, `POST /chunks` |
| `needs backend` (10) | `POST /selectors/resolve`, `GET /refusals`, `POST /graph/node/attrs`, `POST /stores/counts`, `GET /jobs`, `GET /pipeline`, `POST /jobs/{job_id}/cancel`, `GET /corpus (status, sort, search)`, `POST /documents/reprocess`, `POST /evidence/resolve-batch` |
| field already on a built, non-operator route (1) | `GET /health (engine_reason)` (Open Question 2) |

`GET /corpus` exists with `limit`, `offset` and a `selector` query param but no status/sort/search [VERIFIED: `rest.py:519-527`], so that string stays `needs backend`.

## Freeze tooling (question 3)

**`scripts/mockup-id-check.py` constraints** [VERIFIED: read in full]:
- `ID_RE` matches only `data-mock-id\s*=\s*"..."` / `'...'` / `{ "..." }` forms, with `(?<![\[\w-])` so `[data-mock-id="x"]` selectors never count.
- `TAG_RE = r"<(/?)\s*([A-Za-z][A-Za-z0-9-]*)([^<>]*?)(/?)>"`; comments, `<script>` and `<style>` bodies are opaque (`OPAQUE_RE`).
- The variant span is the element carrying `data-mock-variant`, closed by depth-counting tags of the same name; only `<div>` is expected for the root, so inside the wrapper `<div>`s must balance and none may be self-closed.
- `SKIP_DIRS` includes `"mockups"` (and `"tests"`, `"test"`, `"e2e"`, `"__tests__"`, `".planning"`, `".claude"`, `"node_modules"`, `".venv"`, `"dist"`, `"build"`), and the frozen file itself is skipped by resolved path; `UI_SUFFIXES = {".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro"}`; `.spec.`/`.test.` file names are skipped. So the BAK mockup scan does skip `mockups/` (GUI-01's claim holds), and a copy of the ids elsewhere (docs, a console directory) would count as a UI source.
- `freeze` is `{variant, path, sha256}` strings or null; null prints `mockup check skipped (no frozen variant; S8-lean: gates on checkable items only)` and exits 0.
- Exit 1 lines: `mockup frozen file missing`, `mockup frozen file changed since freeze`, `mockup <id>: present in frozen mockup <rel> but missing from UI sources`.

**Setting `mockup_freeze`** [VERIFIED: `scripts/ledger-amend.py:552-554` parser and `959-989` handler]:
```
p_fv = sub.add_parser("freeze-variant")
p_fv.add_argument("--variant", required=True)
p_fv.add_argument("--path", required=True)
```
Command: `python3 scripts/ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html`. The handler resolves the path inside the root, requires the file, and stores `{"variant": variant, "path": rel, "sha256": hashlib.sha256(blob).hexdigest()}`. Any later edit of the HTML changes the digest and the check then prints `mockup frozen file changed since freeze`.

**Row verbs** (the only ones relevant to the 11 rows) [VERIFIED: parser lines 506-518]: `set --id GUI-04 --test-ref <path::node> --code-ref <path> [--spec-ref ...] [--evidence ...]`; `set-status --id GUI-04 --status done`; `record-fail --id ... --cmd "<shell command containing the check path>" [--timeout N] [--at COMMIT]`; `lock-checks --commit <sha> [--also PATH]`. There is **no verb that edits a row's `text`** (`set` accepts only `--spec-ref --test-ref --code-ref --evidence --phase`). The GUI rows' `text` is already a truncated summary ending in `...` (e.g. GUI-04: `"... a stream ..."`, read at `ledger/REQUIREMENTS.json:2135`), so ledger text cannot drift in a way a gate checks. Precedent: Phases 12 and 13 recorded "Requirement text exceptions (to record in REQUIREMENTS.md)" (`13-CONTEXT.md:186-194`) and never edited the ledger text. CONTEXT B's phrase "and the ledger rows (through `scripts/ledger-amend.py` only...)" therefore reduces to: edit REQUIREMENTS.md and UI-SPEC; the ledger is touched only for `test_ref`/`code_ref`/status/freeze.

**Plan gate** [VERIFIED: `scripts/plan-gate.py` lines 27, 102-134]: every due `open` row id must appear (regex `\b[A-Z][A-Z0-9]*-[0-9]+\b`) in at least one `*-PLAN.md` in the phase directory; frontmatter `requirements:` lists are enough. Due now: GUI-01..GUI-11 (ledger start-up output lists them as `open and due`). `--check-edits` additionally flags any plan line beginning `Create`, `Modify` or `Test` (with optional bullet/bold) that names a file in `test_ref`, `check_locks.files` or `check_guard`.

**Phase gate** [VERIFIED: `scripts/phase-gate.py:220-300`]: for a row to be `done`: non-empty `test_ref` (`missing check (empty test_ref)` today for all 11 rows), the check must be unique across rows (`each row needs its own test`), the file must exist, be locked by the owner (`check not locked ... the user reviews it and runs lock-checks`), have a recorded failing run that names the node and matches the current file hash (`check never failed`, `recorded failure never reached its test`, `recorded failure is stale`).

## Fixture shapes (question 4)

Fixture shapes for each screen are fixed in UI-SPEC "Screen Contracts" and match API-INVENTORY section 3 and 5.1a. What the planner needs beyond the UI-SPEC:

- **`docs/gui/refusals.json`**: a JSON array of 51 objects `{refusal_type, module, attribute_keys, http_status}` sorted by `refusal_type` [VERIFIED: loaded this session; first entry `{"refusal_type": "ActiveGenerationRetirementError", "module": "databasise.seam.refusals", "attribute_keys": ["alias", "version"], "http_status": 422}`; status counts 422:45, 404:4, 502:1, 409:1]. Examples the fixtures need: `StoreBusyError` attribute_keys `["store_kind"]` status 409; `UnknownGraphNodeError` `["node_id"]` 422; `ForeignEngineRefusalError` `["failure_class", "operation"]` 502; `UnknownTraceReferenceError` `["trace_reference"]` 404; `UnresolvableEvidenceReferenceError` `["ref"]` 404; `PartialRunEvidenceError` `["trace_ids"]` 422; `ActiveGenerationRetirementError` `["alias", "version"]` 422.
- **`databasise/tests/fixtures/selector-resolution.json`**: top-level keys `rows` and `reachable`; `reachable` is `{"naive": true, "bypass": true, "hybrid": true, "local": true, "global": true, "hipporag": true}`; `rows` has 29 entries `{selector, wiring, node_count, outcome}` [VERIFIED]. Selected rows (verbatim): `{"capability": ["reads_graph"]}` -> hipporag 14; `{"capability": ["calls_llm"]}` -> bypass 1; `{"capability": ["reads_vector:entities"]}` -> local 15; `{"capability": ["reads_vector:relationships"]}` -> global 15; entities+relationships -> hybrid 17; `{"capability": []}` -> `EmptyCapabilitySelectorError`; `{"harness": "hotpotqa"}` -> `UnsatisfiableSelectorError`; aliases `fixture-naive|bypass|hybrid|local|global|hipporag` resolve to their arm. The table has no row for `reads_vector:chunks` or the `reads_graph`+`calls_llm` / `reads_graph`+`calls_rerank` combinations; those come from API-INVENTORY 3.0 (the four documented combinations in UI-SPEC). `calls_rerank` and `calls_embedding` alone resolve to naive, `reads_kv` to naive.
- **Operator route bodies** (API-INVENTORY 5.1a, quoted): `GET /info` -> `{version, workspace, clients: {llm, embedding, rerank}, write_in_flight, graph_busy}`; `GET /ledger/aliases` -> `[{alias, active_version, record_kind, generation_ordinal, created_at}]`; `POST /ledger/history` -> `{records: [{generation_ordinal, created_at, record_kind, minted_version, targets_version, change_origin, promotion_trace_ids, active, tombstoned}], total, next_offset}`; `GET /traces` -> `{items: [{trace_reference, created_at, partial, degraded, stop_reason}], total, next_offset}`; `POST /promote/preview` -> `{arm, mutation_class, next_version, promotable, reason}`; `POST /chunks` -> `{refs, total, next_offset}`; `POST /graph/nodes` -> `{nodes: [{id, degree}], total, next_offset}`; `POST /graph/node` -> `{id, degree, edges: [{src, tgt, edge_types, weight}], next_offset}`; `GET /log` -> `{lines: [str]}`.
- **Existing-route bodies**: `DeletionOutcome {document_id, status: "success"|"not_found"|"not_allowed"|"fail", message, seam_events}` (`corpus.py:149-166`); `IngestJob {job_id, enqueued, seam_events}` (`corpus.py:136-146`); `PromotionResult {alias, version, record_kind, provenance, generation_ordinal}` (API-INVENTORY 3.0).

## Common Pitfalls

### Pitfall 1: The ledger cannot take the requirement-text amendments
**What goes wrong:** a plan task says "amend the ledger rows for D-06..D-09" and the executor cannot find a verb.
**Why:** `ledger-amend.py set` has no `--text`; row text is fixed at add (also the premise of `mockup-id-check.py`'s `port_overrides` comment "ledger text is fixed at add").
**How to avoid:** the amendment task edits `.planning/REQUIREMENTS.md` (GUI-04, GUI-05, GUI-06, GUI-08, GUI-10 text and the `Test:` bullets that mention hybrid/global unreachable, "HippoRAG columns", "HippoRAG trace ... blocked", "HippoRAG-resolving selector ... Delete is not offered", "all 30") and `17-UI-SPEC.md`; the ledger is only touched for `test_ref`/`code_ref`/status.
**Warning signs:** a plan action containing `ledger-amend.py set --text`.

### Pitfall 2: D-12 step 3 ("mockup-id-check exits 0") cannot be satisfied at the end of Phase 17
**What goes wrong:** after `freeze-variant`, `scripts/check-ledger.py` calls `mockup_id_violations` (`check-ledger.py:88-122`, wired at line 717) which runs `mockup-id-check.py --root <root>`; every frozen id missing from a UI source outside the skip dirs becomes a hard violation line. No file outside `mockups/` and `tests/` carries the ids until Phase 18, and there is no `MOCKUP-PORT.md` (`ls MOCKUP-PORT.md`: no such file).
**Why:** the freeze tooling is built for "the built UI must carry the frozen ids" (LIVE-09's check), but D-12 freezes before any build.
**How to avoid:** the owner decides (Open Question 1) before the last plan is written. Do not "fix" it by copying the HTML into a non-skipped directory just to satisfy the script.
**Warning signs:** the last plan's verify step says `mockup-id-check.py exits 0`.

### Pitfall 3: The regex checker and an HTML parser disagree on attribute content
**What goes wrong:** a `title="a > b"`, a raw `<` in a tooltip, or an unbalanced `<div>` inside the wrapper makes `variant_spans` end early; `want` shrinks silently and later ids look "present".
**How to avoid:** the parity assertion in Pattern 3; write `&lt;`/`&gt;`; keep `<div>` balanced; no scripts inside the wrapper (scripts are opaque to the checker but ids inside a script string would still be matched by `find_ids` if they were in the span).

### Pitfall 4: Playwright wheel and Chromium on NixOS
**What goes wrong:** the browser is downloaded and fails to start; or the wheel's bundled node driver fails; or revisions mismatch (`Executable doesn't exist at .../chromium_headless_shell-NNNN`).
**Facts:** the Playwright-downloaded Chromium in `~/.cache/ms-playwright/chromium-1243` does not start here [VERIFIED, output above]. `programs.nix-ld.enable = true` is set (`/etc/nixos/configuration.nix:411`), `/lib64/ld-linux-x86-64.so.2` exists and `NIX_LD_LIBRARY_PATH=/run/current-system/sw/share/nix-ld/lib`, so the wheel's generic bundled `driver/node` probably runs [ASSUMED, untested: nothing installed this session]; if not, `PLAYWRIGHT_NODEJS_PATH=$(command -v node)` [VERIFIED honoured].
**How to avoid:** pin `playwright==1.59.0`; set `PLAYWRIGHT_BROWSERS_PATH` to the nixpkgs browsers; a Wave 0 smoke test (`launch()`, load `data:text/html,x`, close) runs before the 11 real tests and records the exact working environment in the plan summary.
**Warning signs:** `Looks like Playwright was just installed or updated`, or a revision other than 1217 in the error text.

### Pitfall 5: Skip hides the failing run and the offline gate
**What goes wrong:** `pytest.importorskip`/browser-launch skips return exit 0, so `record-fail` reports `check passed, so it cannot prove a failure`, and a finished row can be "green" on a machine with no browser.
**How to avoid:** the file-exists assertion comes first (Pattern 1); add `DATABASISE_REQUIRE_BROWSER=1` for plan verification commands so a missing browser fails; keep plain skips only for developer machines. `databasise/tools/check_offline_suite.py` reports skipped tests but only treats `mcp`-related skip reasons as contradictory, so a new skip reason will not fail that gate on its own.

### Pitfall 6: Offline guard and the sync API
**Facts:** `databasise/tests/conftest.py` has an autouse fixture that patches `socket.socket.connect` to refuse non-loopback addresses [VERIFIED: lines 107-135]. Playwright drives the node driver over pipes, and Chromium is a separate process, so neither is affected. `asyncio_mode = "auto"` only wraps `async def` tests; keep every Playwright test synchronous (the sync API refuses to run inside a running asyncio loop) [ASSUMED: confirm in the Wave 0 smoke test].

### Pitfall 7: Protected check files
`check_locks.files` locks ~110 existing test files (read from `ledger/REQUIREMENTS.json`), and the edit-guard hook refuses even `sed -n` reads of them through Bash (it blocked `test_refusal_catalogue_file.py`); use the Read tool, and never modify them. New test files are not locked until the owner runs `lock-checks`; after that they are. Put anything reusable (id constants, helpers) in files that are not a `test_ref` and be aware that `lock-checks --also` can extend the lock to helpers.

### Pitfall 8: UI-SPEC fixtures drift from the code they copy
Each item below was checked against source this session.

| UI-SPEC says | Code says | Recommendation |
|---|---|---|
| `health-degraded` engine `{interpreter_present, working_dir_present, storages_initialized}` | `engine_report` keys are `"interpreter_present"`, `"working_dir_present"`, `"v1_reachable"` (`engine.py:2066-2070`); `HealthReport.engine: dict[str, bool]` (`corpus.py:340`) | Use `v1_reachable` in fixtures; the `v1 engine reachable` row reads `v1_reachable`; amend API-INVENTORY 3.4.1 at freeze (it still says `storages_initialized`) |
| `corpus.health.reasons` and `corpus.health.clients` are needs-backend (`GET /health (engine_reason)`, `GET /info`) | `GET /health` already returns `clients` and `engine_reason` (`corpus.py:341-342`, `engine.py:2114-2120`), with `engine_reason` text like `v1 not configured: missing EMBEDDING_DIM`, `model clients not configured`, `v1 interpreter missing`, `environment digest unavailable` | Open Question 2; fixtures should carry these fields either way |
| Status colors list no `interrupted` | `_INTERRUPTED = "interrupted"` (`engine.py:757`); `GET /corpus` reports a document left in `parsing`/`analyzing`/`processing` as `interrupted` in rows and `counts` when no write holds the gate (`engine.py:1961-1998`) | Add `interrupted` to the warn status set; consider a `corpus.kpi.interrupted` tile hidden at 0, like `preprocessed` (UI-SPEC addendum; ids are not frozen yet) |
| Trace node table prints `T3` for `tier`/`feed_tier` | `tier: str | None = None`, `feed_tier: str | None = None` (`runner/trace.py:115-116`); docstring says they are `None` (D-14) | Fixture `null`; render the neutral `placeholder` badge for null (and for `T3`); GUI-07 only requires "marked as placeholders" |
| Corpus: "HippoRAG documents are not listed" | `GET /corpus` takes a `selector`; a HippoRAG selector lists per-document manifests (`engine.py:1968-1980`) | Keep the frozen title `LightRAG (v1) documents` (GUI-09 text); optional: note the selector param in the API-INVENTORY drafts |
| Ingest/upload failure text | `POST /documents/{document_id}/retry` exists (`rest.py:508`) | Out of requirement scope; add to the screen's `planned` list only if the owner wants it surfaced |
| Server-failure body shows `cause` | Real bodies withhold `cause` (UI-SPEC row "Server-failure `cause`" and Phase 9 D-04) | Already handled: details panel works with or without it |
| GUI-06 text "all 30" | 51 [VERIFIED] | D-09 already removes the count |
| Dependency "dev extra" | `[dependency-groups] dev = [...]` (`pyproject.toml`), not `[project.optional-dependencies]` | Add `playwright==1.59.0` to the `dev` group; `uv sync` installs it without a flag |

### Pitfall 9: D-07/D-08 touch more than the sentences they name
D-07 removes: pre-flight blocker `Trace <short> is from a HippoRAG run...`, `Promote this arm` disabled on HippoRAG columns, `promote from this result` disabled for HippoRAG, the `cmp-3col` fixture note "(hipporag, success, `Promote this arm` disabled)", the string `Promotion from HippoRAG runs is blocked in this console.`, and the REQUIREMENTS `Test:` clauses for GUI-05 and GUI-10. D-08 removes `documents.delete.not-offered`, the string `Delete is offered only for LightRAG selectors.`, the "Delete is not offered" clause of the GUI-08 test, and the HippoRAG-hidden behaviour of `documents.delete.*` and `documents.jobs.delete-N`. The delete dialog body in UI-SPEC is written for LightRAG ("removes it from the v1 corpus ... The query stores are not changed; the deleted document's chunks can stay resolvable"); for a HippoRAG-resolving selector the body needs a different sentence. Ids not yet frozen may be dropped or added freely before the freeze.

### Pitfall 10: The new `operator route` badge has no design token
UI-SPEC reserves the needs-backend violet (`#5B21B6` on `#EDE9FE`) "never reused". D-10 adds a second badge kind. Recommended: the neutral status pair (`#52525B` on `#F4F4F5`, glyph plus the words `operator route`), and a title `Mounted only with --operator` (`--operator --log-file` for `/log`). Add the row to the UI-SPEC Color table in the amendment task.

### Pitfall 11: Rendering untrusted-shaped text
Refusal attributes, `message`, `cause`, `error_message`, trace values and graph attributes are rendered. Use `textContent`/`createTextNode`; wrap trace ids in `<mark>` by constructing nodes, not by string concatenation.

## Code Examples

### Viewport check (GUI-05)
```python
ctx = browser.new_context(viewport={"width": 375, "height": 800})
page = ctx.new_page(); page.goto(mockup_path.as_uri())
page.locator('[data-mock-id="shell.nav.query"]').click()
assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
```

### Test hooks (from the UI-SPEC Authoring Contract)
```python
page.evaluate("window.__mock.setState('query', 'partial')")
page.evaluate("window.__mock.inject('query', {status: 422, body: {refusal_type: 'ForeignEngineRefusalError', message: 'x', cause: 'c'}})")
assert page.locator('[data-mock-id="query.error.server-failure"]').is_visible()
assert not page.locator('[data-mock-id="query.error.details-toggle"]').get_attribute("aria-expanded") == "true"
```

### Freeze (last plan, after the owner approves)
```
python3 scripts/ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html
python3 scripts/mockup-id-check.py --root .
```

### Row registration (Wave 0, per row)
```
python3 scripts/ledger-amend.py set --id GUI-04 --test-ref "databasise/tests/gui/test_gui_04_query_mode.py::test_gui_04_query_mode" --code-ref "mockups/operator-console.html"
python3 scripts/ledger-amend.py record-fail --id GUI-04 --cmd "cd databasise && .venv/bin/python -m pytest tests/gui/test_gui_04_query_mode.py::test_gui_04_query_mode -q"
```
The `--cmd` must contain the check path (`record-fail needs --cmd containing the check path`); the test file must exist; the output must name the node.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GUI-04/05 list hybrid and global as unreachable | All six arms reachable by capability tokens (`reads_vector:entities` -> local, `:relationships` -> global, both -> hybrid) | Phase 13 D-01 (WIRE-01) | Picker, compare columns, resolves-to table |
| Promotion from HippoRAG blocked | Accepted by the server | Phase 14 D-05 | D-07 |
| Delete LightRAG only | HippoRAG delete wiring exists | HIPP-16 | D-08 |
| `tier`/`feed_tier` `T3` placeholder | `None` | Phase 13 D-12/D-14 | Pitfall 8 |
| Health: booleans only, no reasons | `engine_reason`, `clients`, `v1_reachable` | Phase 11 plan 09 | Pitfall 8 |
| Operator surface absent | Ten routes behind `--operator` | Phase 16 | D-10 badges |

**Deprecated/outdated:** API-INVENTORY 3.4.1 (`storages_initialized`, "no failure reason") and 3.4.2 ("No selector parameter"); both are corrected by the freeze-time inventory update.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The wheel's bundled generic `driver/node` runs under nix-ld; otherwise `PLAYWRIGHT_NODEJS_PATH` fixes it | Pitfall 4 | Wave 0 smoke test fails; the fallback env var is already specified |
| A2 | `playwright-driver.browsers` provides `chromium_headless_shell-1217` that `chromium.launch()` (headless) uses with `playwright==1.59.0` | Standard Stack | Launch error naming the missing directory; fallback `executable_path` to system chromium |
| A3 | Sync Playwright tests run fine under `asyncio_mode = "auto"` when the test function is not `async` | Pitfall 6 | Switch the fixtures to a thread or set a per-module `pytest.mark` override |
| A4 | The mockup will hold several hundred ids (rough estimate, not counted) | Architecture | Only affects the choice of assembler vs hand-writing |
| A5 | `ledger-amend.py freeze-variant` is not blocked by the ledger-verify hook (the hook text lists approve, reject, drop, acknowledge-handoff, set-status into deferred-approved/dropped) | Freeze tooling | The freeze step becomes an owner-run command |
| A6 | Full Playwright suite for 11 files runs in about a minute | Validation | Longer suite; keep the per-file quick command |
| A7 | `nix-build '<nixpkgs>' -A playwright-driver.browsers` works as a normal user and substitutes from cache.nixos.org | Installation | Use `nix-store --realise` or ask the owner to add it to `configuration.nix` |

## Open Questions

1. **How is D-12 step 3 satisfied?** (blocking for the last plan)
   - What we know: after `freeze-variant`, the completion gate runs `mockup-id-check.py`, which exits 1 for every frozen id absent from UI sources outside `mockups/`/`tests/`; no Phase 17 deliverable provides such a source (Pitfall 2).
   - What's unclear: whether the owner wants (a) to freeze at the end of Phase 17 and accept hard `mockup ...: missing from UI sources` lines in the gate until Phase 18 ports the ids, (b) to move the `freeze-variant` write to the start of Phase 18 (the sha256 is the same file), or (c) something else.
   - Recommendation: (b) keeps every gate clean and still satisfies LIVE-09; if the owner insists on (a), change D-12 step 3 to "run the check and record the expected exit 1 and its line count" so the plan does not assert something false.

2. **Badge for fields that already exist on a non-operator route** (`corpus.health.clients`, `corpus.health.reasons`: both fields are on `GET /health`)
   - What we know: GUI-03 and GUI-09 text name "health reasons, client presence" as needs-backend fields; `GET /health` returns `clients` and `engine_reason` today; `write_in_flight`/`graph_busy` are operator-only on `GET /info`.
   - What's unclear: whether these two keep `data-needs-backend` (frozen text) or take the D-10 treatment for "route exists".
   - Recommendation: keep all ids unchanged. D-10 defines only two badge kinds, so this needs an owner ruling. Default if none is given: the `busy` chips (operator `GET /info`) get the `operator route` badge; `clients` and `reasons` lose `data-needs-backend` and the badge, but only in the same task that amends the GUI-03 and GUI-09 text in REQUIREMENTS.md (otherwise the frozen text and the markup disagree). The safe alternative is to leave both as `needs backend` and fix them in Phase 18 (LIVE-09 drops the badge once the route is in `/openapi.json`, which is already true for `/health`).

3. **Where the 11 test nodes live and how many assertions each carries.**
   - What we know: each row needs one distinct `path::node`; the REQUIREMENTS `Test:` bullets are single narratives.
   - Recommendation: one file per requirement under `databasise/tests/gui/`, the ledger node being the narrative test, extra focused tests in the same file for diagnosis. Fix the files fully in Wave 0.

4. **API-INVENTORY drafts** (D-12 step 1) need the owner's wording for the new `POST /graph/node/attrs` row (request `{selector, node_id}`, response attrs map with allowlist question from Phase 16 D-16) and for corrections listed in Pitfall 8.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 venv | tests | yes | `databasise/.venv` Python 3.12.13 | — |
| pytest, pytest-asyncio, fastapi | tests, route-classification test | yes | in venv (3060 tests collected) | — |
| `playwright` Python package | GUI tests | no | not installed (`ModuleNotFoundError`) | add pinned dev dependency after the legitimacy checkpoint |
| Playwright browsers | GUI tests | no | nixpkgs `playwright-driver.browsers` substitutable (cache.nixos.org returned the path) | system `chromium` (156.0.8078.47) via `executable_path` |
| `nix`, `nix-build` | provisioning | yes | `/run/current-system/sw/bin/nix`; NixOS 26.05.12658 | — |
| nix-ld | wheel's generic node driver | yes | `programs.nix-ld.enable = true` (`configuration.nix:411`) | `PLAYWRIGHT_NODEJS_PATH` + system node v24.21.0 |
| `uv` | `uv lock` / `uv sync` | yes | 0.11.21 | `pip` is not on PATH |
| `node` | fallback driver | yes | v24.21.0 | — |
| `gsd-tools` | packages check | yes | `~/.claude/gsd-core/bin/gsd-tools.cjs` | — |
| Network (PyPI, cache.nixos.org) | one-time install | yes (read access confirmed this session) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** playwright package and browsers (steps above).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2+ with pytest-asyncio (auto mode); Playwright for Python 1.59.0 (sync API) |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = '-m "not live"'`); no new config needed |
| Quick run command | `cd databasise && DATABASISE_REQUIRE_BROWSER=1 .venv/bin/python -m pytest tests/gui/test_gui_0N_<name>.py -q -x` |
| Full suite command | `cd databasise && .venv/bin/python -m pytest -q` then `.venv/bin/python databasise/tools/check_offline_suite.py` (run from repo root as that module's docstring shows) |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUI-01 | six screens switch, header health on every screen, zero external requests, no page errors | browser | `pytest tests/gui/test_gui_01_shell.py -q` | Wave 0 |
| GUI-02 | every interactive/region element has a unique id, variant on root, id set equals `MOCK-IDS.json`, parser set equals regex-checker set | unit (html.parser) | `pytest tests/gui/test_gui_02_ids.py -q` | Wave 0 |
| GUI-03 | every `GAP-ROUTES.json` route string appears as `data-needs-backend`; each such element holds a visible badge (`needs backend` or `operator route`); operator-only routes equal the code-derived set | unit + app routes | `pytest tests/gui/test_gui_03_needs_backend.py -q` | Wave 0 |
| GUI-04 | blocks for `'   '`, empty capability, 64-hex alias, multi-member JSON; 8 state views; Open trace disabled on null token; `promote from this result` disabled on partial | browser | `pytest tests/gui/test_gui_04_query_mode.py -q` | Wave 0 |
| GUI-05 | duplicate-key warning blocks Run (alias `default` vs Default, `a+b` vs `a`,`b`); removing a row re-enables; 3-column fixture partial only in column 2; HippoRAG column promotable (D-07); 375 px tabs and no horizontal scroll | browser | `pytest tests/gui/test_gui_05_compare.py -q` | Wave 0 |
| GUI-06 | four injected shapes render distinctly (type banner with `<mark>` trace id, server failure with cause hidden until toggle, field error on selector input, generic); catalogue equals `__subclasses__()` walk | browser + unit | `pytest tests/gui/test_gui_06_errors.py -q` | Wave 0 |
| GUI-07 | evidence row opens with content/chips/key-value; lookup namespace select has exactly `chunks`, `hipporag-chunks`; non-debug trace has no node table; Debug adds identity panel and table with halted row highlighted; `sentinel:` renders `not yet recorded` | browser | `pytest tests/gui/test_gui_07_evidence_trace.py -q` | Wave 0 |
| GUI-08 | id `a b` blocked; 0-byte and 26,214,401-byte files blocked; page size 0 and 101 rejected; `next_offset` null disables Next; Delete dialog names document_id and selector; Delete offered for HippoRAG selectors (D-08) | browser | `pytest tests/gui/test_gui_08_documents.py -q` | Wave 0 |
| GUI-09 | degraded fixture: badge text `stores openable / v1 reachable`, state degraded, vector row `not probed`; no `preprocessed` tile at 0; failed tile filters; total 0 empty state links to Paste text | browser | `pytest tests/gui/test_gui_09_corpus.py -q` | Wave 0 |
| GUI-10 | partial trace blocked (HippoRAG trace not blocked, D-07); empty and 64-hex alias blocked; no default `change_origin`; Retire disabled on rows W and V and tombstoned row, enabled on the remaining row; typing the version required | browser | `pytest tests/gui/test_gui_10_ledger.py -q` | Wave 0 |
| GUI-11 | prefix filter; node detail with paged edges; chunk Open shows the ref in Evidence Inspector; store-busy state; no input/label/id/aria-label/placeholder contains `namespace` | browser + unit | `pytest tests/gui/test_gui_11_graph.py -q` | Wave 0 |
| (support) | assembler output is byte-stable and equals the checked-in HTML | unit | `pytest tests/gui/test_mockup_build.py -q` (only if an assembler is used) | Wave 0 |
| (support) | Playwright smoke: launch, load `data:` page, close | smoke | `pytest tests/gui/test_playwright_smoke.py -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** the single test file for the screen being built, with `DATABASISE_REQUIRE_BROWSER=1`.
- **Per wave merge:** `cd databasise && DATABASISE_REQUIRE_BROWSER=1 .venv/bin/python -m pytest tests/gui -q`.
- **Phase gate:** full suite green (`.venv/bin/python -m pytest -q`, also `python -m pytest`, via `tools/check_offline_suite.py`), `python3 scripts/plan-gate.py --plans .planning/phases/17-gui-mockup`, `python3 scripts/phase-gate.py` (each row: unique `test_ref`, locked, recorded failure), then the owner click-through and freeze.

### Wave 0 Gaps
- [ ] `databasise/tests/gui/__init__.py`, `conftest.py` (fixtures in Pattern 1) and 11 requirement test files plus the smoke test (none exist)
- [ ] Framework install: `playwright==1.59.0` in `[dependency-groups].dev`, `uv lock`, behind the legitimacy checkpoint
- [ ] Browsers: `nix-build '<nixpkgs>' -A playwright-driver.browsers -o ~/.cache/databasise/playwright-browsers`
- [ ] `docs/gui/MOCK-IDS.json` generator (reuse `find_ids`) and `docs/gui/GAP-ROUTES.json` (initial 21 strings with kind)
- [ ] REQUIREMENTS.md and UI-SPEC amendments D-06..D-10 (before the screen plans)
- [ ] For each of GUI-01..11: `set --test-ref/--code-ref`, then `record-fail`; owner runs `lock-checks` later

## Security Domain

Omitted: `security_enforcement` is `false` in `.planning/config.json:48`. The one relevant control (render untrusted-shaped strings with `textContent`) is Pitfall 11.

## Sources

### Primary (HIGH confidence, read or executed this session)
- `/home/chris/coding/Databasise-2.0-fully-agnostic-system/.planning/phases/17-gui-mockup/17-CONTEXT.md`, `17-UI-SPEC.md` (read in full)
- `scripts/mockup-id-check.py`, `scripts/plan-gate.py`, `scripts/phase-gate.py`, `scripts/check-ledger.py` (lines 84-125, 628-730), `scripts/ledger-amend.py` (lines 1-1750)
- `databasise/seam/operator_rest.py`, `databasise/seam/rest.py` (350-551), `databasise/seam/engine.py` (1955-2120), `databasise/seam/corpus.py`, `databasise/runner/trace.py`, `databasise/pyproject.toml`, `databasise/tests/conftest.py`, `databasise/tests/seam/test_refusal_catalogue_file.py`, `databasise/tools/check_offline_suite.py`
- `docs/gui/API-INVENTORY.md` (lines 1-370, 486-560, 686-845), `docs/gui/refusals.json`, `databasise/tests/fixtures/selector-resolution.json`
- `.planning/REQUIREMENTS.md` (GUI/LIVE rows and their `Test:` bullets), `.planning/ROADMAP.md` Phase 17, `.planning/STATE.md`, `.planning/phases/13-selectors-wiring-runner/13-CONTEXT.md:186-194`
- `/etc/nixos/configuration.nix:411` (nix-ld); `nix-instantiate` evaluation of `playwright-driver.version` (1.59.1) and `python3Packages.playwright.version` (1.59.0); nixpkgs `pkgs/development/web/playwright/browsers.json`; `nix path-info --store https://cache.nixos.org` for the browsers output
- raw GitHub `microsoft/playwright` `packages/playwright-core/browsers.json` at v1.59.0; `microsoft/playwright-python` `playwright/_impl/_driver.py` at v1.59.0; PyPI JSON for playwright (latest 1.64.1; 1.59.0 `requires_dist`)
- `gsd-tools query package-legitimacy check` (pypi: playwright, greenlet, pyee, typing-extensions)

### Secondary (MEDIUM confidence)
- none

### Tertiary (LOW confidence)
- Behaviour of the wheel's bundled node under nix-ld, sync API under pytest-asyncio auto mode, run-time estimate (A1, A3, A6): not exercised because installs were out of scope.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH on versions and revision match; MEDIUM on the launch path until the Wave 0 smoke test.
- Architecture: HIGH (the UI-SPEC fixes it; research verified the tooling constraints).
- Pitfalls: HIGH (each cites file and line or a command run this session).

**Research date:** 2026-10-25
**Valid until:** 2026-11-08 for Playwright/nixpkgs versions (channel may bump); the BAK script findings hold until those scripts change.
