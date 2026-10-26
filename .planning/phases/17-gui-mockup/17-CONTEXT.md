# Phase 17: GUI Mockup - Context

**Gathered:** 2026-10-25
**Status:** Ready for planning
**Mode:** Interactive discuss. The owner answered every question below. Before this discussion, the UI design contract `17-UI-SPEC.md` was approved (2026-10-25, gsd-ui-checker revision 1). It remains the authority for layout, ids, copy and states. This file records the owner rulings on its "Decisions taken by default" table, plus four requirement amendments that override parts of it.

<domain>
## Phase Boundary

The deliverable is one static file, `mockups/operator-console.html`, that opens from file:// with no network access. It covers the six operator console screens:
- Query & Compare
- Evidence & Trace
- Documents & Jobs
- Corpus & Health
- Ledger
- Graph/vector browser

All data comes from inline fixtures shaped like API-INVENTORY §3. Every control and display region carries a unique `data-mock-id`. Controls whose route is missing or operator-only are badged.

The phase also delivers:
- the checked-in id list;
- a Playwright test suite;
- an owner freeze (`mockup_freeze`) after the new needs are recorded in API-INVENTORY.

Covered requirements: GUI-01 through GUI-11.

**Not in this phase:**
- Connecting to the live API (Phase 18).
- Any new server route. Proposed routes are only named and badged.
- Dark theme.
- Authentication.
</domain>

<decisions>
## Implementation Decisions

### A. Roadmap owner decisions (UI-SPEC defaults confirmed)
- **D-01 (GUI-01):** The test suite uses Playwright for Python, added to the `dev` extra in `databasise/pyproject.toml` and run under pytest. On NixOS (host legion), the browsers come from nixpkgs `playwright-driver.browsers` via `PLAYWRIGHT_BROWSERS_PATH`, not from `playwright install`. The planner must include the step that provides them. Playwright is not installed today.
- **D-02 (GUI-02):** Ids follow the grammar `<screen>.<region>.<control>`: lower case, dot separated. Screen roots are `screen-<name>`, slot suffixes are `-N`, and the reserved regions are `mock`, `state` and `error`. The list is `docs/gui/MOCK-IDS.json`, a sorted array generated from the final file, and the test asserts set equality with it. — **Reversibility:** costly — Phase 18's port plan (MOCKUP-PORT.md) and `scripts/mockup-id-check.py` key on these ids after the freeze.
- **D-03 (GUI-03):** §5.1 "later" items that have no proposed route appear in one text-only `<screen>.planned.list` per screen (a `<details>` titled `Planned (not built)`), with no controls. The item lists are in UI-SPEC "Needs-backend Registry".
- **D-04 (GUI-06):** The refusal catalogue is the generated `docs/gui/refusals.json`, carried forward from Phase 16 D-07 and not re-asked.
- **D-05 (GUI-11):** `POST /graph/node` returns references only: edges as `{src, tgt, edge_types, weight}`. Node attributes load through an explicit `Load attributes` button that calls a new proposed route, `POST /graph/node/attrs`. This follows Phase 16 D-16, which allows references plus an allowlist and defers dereference. The new route is recorded in API-INVENTORY at freeze.

### B. Requirement amendments (frozen text updated to match the engine)
The owner chose to amend all four. The amendments go into REQUIREMENTS.md and 17-UI-SPEC.md **before** the build plans. They do not go into ledger row text: `scripts/ledger-amend.py` has no verb that edits a row's `text`, per 17-RESEARCH and the Phase 12/13 precedent. The ledger is touched only for `test_ref`, `code_ref` and status. Where an amendment contradicts a row in UI-SPEC "Decisions taken by default", the UI-SPEC row is updated too.
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
  3. On approval it records the approved file's sha256 and the approval in a checked-in note (for example `docs/gui/MOCKUP-APPROVAL.md` with variant `console-a`, path `mockups/operator-console.html`, sha256, date). It does **not** write `mockup_freeze`; see D-13.

- **D-13 (amends D-12, owner ruling after research):** The ledger `mockup_freeze` write (`scripts/ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html`) moves to the **first plan of Phase 18**.
  - Reason: once `mockup_freeze` is set, `scripts/check-ledger.py` runs `scripts/mockup-id-check.py` inside the completion gate. The check exits 1 for every frozen id missing from a UI source outside `mockups/` and `tests/`, and no such source exists until Phase 18.
  - Phase 17 must not set `mockup_freeze`, and must not copy the HTML into a non-skipped directory to satisfy the checker.
  - Phase 18's first plan verifies that the file's sha256 still equals the recorded approval before freezing.

  — **Reversibility:** one-way (at the Phase 18 freeze) — after the freeze, every frozen id must appear in the Phase 18 build or be mapped in MOCKUP-PORT.md (LIVE-09), and a re-freeze needs a new ledger amendment.

### E. Owner rulings after research (2026-10-25)
- **D-14 (GUI-09 amendment):** Client presence (`clients`) and failure reasons (`engine_reason`) already exist on `GET /health`, so they are treated as existing fields. They get no badge, and the `GET /health (engine_reason)` registry row is removed. Amend the GUI-09 text in the same way as D-06 to D-09 (REQUIREMENTS.md and UI-SPEC only). Store-busy stays an `operator route` field, because it is on `GET /info`.
- **D-15 (GUI-01 dependencies):** The owner approves adding `playwright==1.59.0` and its dependencies `greenlet` and `pyee` to `[dependency-groups].dev` in `databasise/pyproject.toml`, followed by `uv lock`. No mid-execution legitimacy checkpoint is needed for these three packages; the approval is recorded here.
  - Version 1.59.0 is pinned to match nixpkgs 26.05 `playwright-driver` (chromium revision 1217).
  - Browsers come from `nix-build '<nixpkgs>' -A playwright-driver.browsers`, through the binary cache, with `PLAYWRIGHT_BROWSERS_PATH` set. They do not come from `playwright install`.
  - GUI tests fail rather than skip when the mockup file is absent (17-RESEARCH).

### Claude's Discretion
- Every other row of UI-SPEC "Decisions taken by default" is accepted as written. This covers:
  - variant `console-a`, light theme only, system fonts, 7-symbol sprite;
  - type, spacing and palette;
  - compare cap of 4 columns, 4 rows and 5 evidence slots;
  - blocking style (query Run clickable with an inline message, everything else natively disabled);
  - polling off by default, the stream mock timings, `not probed` = a key the server did not report;
  - dialog dismiss labels, and `Submit` kept on paste and upload.
- How plans are split and ordered, provided the amendment work (D-06 to D-09, D-14) lands before the screens it affects, and the approval (D-12) is last.
- UI-SPEC drift against the code found by 17-RESEARCH: **follow the code**, and record each change in the UI-SPEC in the same plan.
  - The health engine keys are `v1_reachable`.
  - The `interrupted` corpus status gets a status colour and a KPI tile.
  - `tier` and `feed_tier` render as `—` with the placeholder badge, because the code returns `None`.
  - `GET /corpus` takes a `selector`, so HippoRAG corpus listing moves out of the Planned list.
  - `POST /documents/{id}/retry` exists, so retrying one document is not badged.
  - The `operator route` badge uses the neutral status token pair.
  - Apply the D-07 and D-08 knock-on string and id edits listed in 17-RESEARCH Pitfall 9.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design contract
- `.planning/phases/17-gui-mockup/17-UI-SPEC.md` — the approved design contract: file shape, id grammar, per-screen controls, error shapes, needs-backend registry, verbatim strings. Where it conflicts with D-07, D-08 or D-10, this file wins.

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — GUI-01 to GUI-11 (amend per D-06 to D-09), LIVE-02 and LIVE-09 (freeze consumers).
- `.planning/ROADMAP.md` — Phase 17 goal, success criteria and the owner decision list.
- `ledger/REQUIREMENTS.json` — the GUI rows and `mockup_freeze` (currently null). Change it only with `scripts/ledger-amend.py`.

### API shapes and catalogues
- `docs/gui/API-INVENTORY.md` §3 (request and response bodies the fixtures copy), §3.0 (resolves-to table), §5.1 and §5.3 (proposed routes and later rows).
- `docs/gui/refusals.json` — the generated refusal catalogue (D-04).
- `databasise/tests/fixtures/selector-resolution.json` — the post-WIRE-01 arm resolution (D-06).
- `docs/gui/CODEBASE-MAP.md`, `docs/gui/DEFECTS.json` — the defects behind the client-side pre-checks.

### Prior decisions
- `.planning/phases/16-gui-connectors/16-CONTEXT.md` — D-07 (catalogue), D-08 (resolution fixture), D-16 (graph references and allowlist), D-17 (store-busy on /info), D-18 (GET /log gating), D-01 (operator routes behind `--operator`).

### Freeze tooling
- `scripts/mockup-id-check.py` — the regex constraints on the file shape (UI-SPEC "Authoring Contract").

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/gui/refusals.json`: embed it inline (or copy it at build time) as the static catalogue.
- `databasise/tests/fixtures/selector-resolution.json`: the source of the inline `Resolves to` table.
- `v1/lightrag_webui/src/index.css`: the palette source cited in UI-SPEC Color.

### Established Patterns
- Tests run under pytest from `databasise/`. Dev dependencies go in the `dev` extra of `databasise/pyproject.toml`.
- The ledger is frozen by a PreToolUse hook. Every ledger write goes through `scripts/ledger-amend.py`, and reads use plain read-only commands.

### Integration Points
- New files: `mockups/operator-console.html` (directory does not exist yet), `docs/gui/MOCK-IDS.json`, `docs/gui/GAP-ROUTES.json` (does not exist yet), and the Playwright test module(s).
- Phase 18 consumes the frozen file, MOCK-IDS.json and the badge attributes.

</code_context>

<specifics>
## Specific Ideas

- The `operator route` badge exists so that Phase 18 can see at a glance which badges it can drop as soon as it runs with `--operator`.
- Treat HippoRAG as first-class in the console (D-07, D-08). Per the core value, both modalities stand behind one seam, and the console should not be stricter than the server.

</specifics>

<deferred>
## Deferred Ideas

- Publishing the mockup as a claude.ai artifact for review from other devices: not chosen, and available on request.
- Dark theme: UI-SPEC allows a `.dark` token set later without id changes.

### Reviewed Todos (not folded)
- `melodyscribe-spike-rig-experiments.md` and `melodyscribe-interface-skill.md` matched on keywords only. They belong to the MelodyScribe project, which moved to DeBIOS-Foundation/MelodyScribe.

</deferred>

---

*Phase: 17-gui-mockup*
*Context gathered: 2026-10-25*
