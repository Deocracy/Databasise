# Phase 17 — UI Review

**Audited:** 2026-10-31
**Baseline:** 17-UI-SPEC.md (approved 2026-10-25, revision 1) plus 17-CONTEXT.md owner rulings D-06 to D-14
**Screenshots:** captured (file:// load of mockups/operator-console.html; 3 viewports x 6 screens, 1440 / 768 / 375 px). Stored under .planning/ui-reviews/17-gui-mockup-audit/ (git-ignored).
**Interaction captures:** off (`interaction_capture: false`). Experience Design findings below are code-derived, cross-checked against the existing 17-REVIEW.md code review.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Test-asserted strings present verbatim; `Submit` kept by accepted default |
| 2. Visuals | 2/4 | Ledger timeline breaks words mid-token at 1440 px; duplicated `operator route` badge in Timeline heading |
| 3. Color | 3/4 | Palette and status tokens match contract; status glyph and word present on badges |
| 4. Typography | 3/4 | Scale holds to 13/14/16/20 px and weights 400/600; wrapping defects in ledger table |
| 5. Spacing | 3/4 | No inline styles; no horizontal overflow at 375 px on any screen; mono cells in ledger cramped |
| 6. Experience Design | 2/4 | Compare Run guard bypassed; Query state views render over compare columns; pending Query timer survives mode switch |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Compare-mode Run is enabled while blockers are active, and Query states leak into Compare** — a user can run a duplicate-key comparison (two columns both keyed `default`) after using the state switcher — Fix: in `21-compare.js` `run()`, recompute blockers and return early; in `20-query.js` `showState()`, skip `setDisabled(run.submit, ...)` and hide `query.compare.columns` when `data-mode` is compare. (Source: `mockups/src/js/21-compare.js:336`, `mockups/src/js/20-query.js:52`, `:60`.)
2. **Ledger timeline unreadable at 1440 px** — `record_kind` badges wrap as `promotio / n`, `tombston / e`, `machine_muta / tion`, and the `created_at` column breaks inside the timestamp — user cannot scan the active-generation row, the focal anchor of the screen — Fix: add `white-space: nowrap` to badge and timestamp cells in `mockups/src/css/60-ledger.css`, and give the Status column a `min-width` so `target of active rollback` wraps at word boundaries; keep `.table-scroll` for narrower widths.
3. **Raw selector JSON crashes Run** — `{"capability":"reads_kv"}` throws `value.capability.join is not a function` before the running state, so Run does nothing visible — Fix: in `20-query.js` `validate()`, accept only `alias` (string), `capability` (array of strings), `harness` (string) and reject anything else with the existing `MSG.badJson` text. (Source: `mockups/src/js/20-query.js:244-246`, `mockups/src/js/10-shared.js:28`.)

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

Verified in the built file `mockups/operator-console.html`:
- Test-asserted strings present: `needs backend` (23), `operator route` (32), `stores openable / v1 reachable` (2), `not probed` (3), `not yet recorded` (1), `operator diagnostics` (10), `whole corpus, not this job` (1), `LightRAG (v1) documents` (2), `not built / gated` (5), `Keep document`, `Keep alias`, `Keep active version`, `Keep version` (1 each), `Promote this arm` (4), `promote from this result` (1), `Roll back to` (7), `Load trace` (2), `Refresh health` (1), `Open node` (8).
- No generic labels (`Cancel`, `Click here`, `Something went wrong`, `No data`) reach the DOM. `Check Health` (spec 17-UI-SPEC Copywriting) is present only as the hidden `Check health` button at `mockups/src/screens/corpus.html:28`, which is sentence case as the checker asked.
- `Submit` (12 uses) is the accepted default in the UI-SPEC decisions table, so it is not scored as a defect. It remains the weakest label in the file.
- `Cancel pipeline` (`mockups/src/screens/documents.html:137`) has no confirmation shape, although the UI-SPEC Destructive table lists the checker's flag. It is a `needs backend` control, so the defect is latent.
- Gap against spec: the Trace summary `not yet recorded` string is test-asserted; it is present once, so the sentinel branch is covered by one fixture only.

Score is 3, not 4, because the Cancel pipeline confirmation shape is missing and the checker's copy flags remain open.

### Pillar 2: Visuals (2/4)

Score 2 is driven by the ledger screen, which is the Ledger focal anchor (`ledger.timeline.region`) in the spec.

- Desktop 1440 px, Ledger, Timeline table: `record_kind` badges wrap mid-word (`promotio/n`, `tombston/e`, `rollback` wrapping). `change_origin` wraps `machine_muta/tion`. `created_at` breaks as `2026-10-12T08:30:1/1Z`. The row therefore carries no legible reading order. File: `mockups/src/css/60-ledger.css`.
- The Timeline heading carries two `operator route` badges (one for the section, one for `POST /ledger/history`), and the Promote panel carries one more beside the `Recent runs` radio. Three operator badges sit in one panel, which breaks the "one badge per wrapper" intent of D-10. Source: `mockups/src/screens/ledger.html`.
- Focal point on each screen is marked with `data-focal="true"` (seven occurrences; evidence has two on separate tabs, which the spec allows). The Query focal panel is correct; the answer panel that should follow it is not marked, so the "ask, then read" anchor is half-marked.
- Graph screen at 375 px (mobile-graph): the Node panel and Chunks table stack correctly, with the `Open node` primary action visible. This is a pass.

### Pillar 3: Color (3/4)

- Light theme only; neutrals `#FFFFFF`, `#F4F4F5`, `#E4E4E7`, text `#09090B`, muted `#52525B` match the Color table in the spec.
- Accent `#1D4ED8` is used on `Run`, `Refresh health`, `Open node`, the active nav bar and the focus ring. Ledger `Promote alias` is accent-tinted while disabled, which reads as a faded accent, not a second accent use. Pass.
- Status tokens (`ok`, `warn`, `fail`, `progress`, `neutral`, `needs-backend`, `operator route`) all appear with a glyph and a word (`✓ ok`, `✕ failed`, `● processing`, `■ pending`, `▲ rollback`). Color is never the only carrier.
- Minor: the `operator route` badge uses `#52525B`/`#F4F4F5`, the same tint as `neutral`. The spec states the separate token `.badge-op` exists "so the two never merge"; the values match but the visual distinction now rests on text alone. Recorded as a warning, not a score driver.
- Hex literals appear outside `:root` in the CSS (about 19 unique values). They are the palette values themselves, so this is acceptable for a single-file mockup.

### Pillar 4: Typography (3/4)

- CSS `font-size` declarations are 13, 16 and 20 px; body 14 px is set in the base `font` shorthand. Weights in use are 400 and 600. This matches the spec scale and the two-weight rule.
- The 13 px tier renders correctly in the Corpus KPI tiles, the Documents table and mono refs.
- Defect: `Stores` and `Engine` headings on Corpus use the Heading 16 px tier but are visually closer to the body labels than to the panel title. Read as same-weight body text at 1440 px.
- Defect: mono refs wrap at arbitrary positions in the Graph chunk table (`c-7f3a9 / 1` pattern on the mobile view), consistent with `overflow-wrap: anywhere` being applied to all mono text. Refs should break only at their dash.

### Pillar 5: Spacing (3/4)

- No `style=""` attributes exist in the built file (count 0). The `--w` bar-chart exception is not used on any screen at capture time.
- No horizontal page overflow: `scrollWidth` equals `innerWidth` for all six screens at 1440, 768 and 375 px.
- Defect: the ledger Timeline `Actions` column stacks `Roll back to` and `Retire` vertically at desktop widths, and the stacked buttons are not separated by the 8 px `sm` token (they touch). Source: `mockups/src/css/60-ledger.css`.
- Defect: the `Health fixture` strip and the `State/Fixture` mock strip sit at 16 px inset on the content column at 1440 px but flush to the rail on the Ledger screen, so the left edge of the mock strip changes between screens. Mock-only, low impact.

### Pillar 6: Experience Design (2/4)

Interaction findings are code-derived (interaction capture off). Cross-checked against 17-REVIEW.md, whose verifier confirmed each defect:

- **Compare Run guard missing** (`mockups/src/js/21-compare.js:336`): `run()` checks only query text. The disabled state is applied only in `syncRun()`, and `QueryScreen.showState` (`20-query.js:60`) re-enables Run on any state change. Two Default rows therefore run and render two columns both keyed `default`, which the spec says the server refuses.
- **Query states render over Compare columns** (`mockups/src/js/20-query.js:52`): `query.compare.columns` is hidden only by `Compare.hideColumns()`, so `setState('success')` shows the single-result panel above visible columns, breaking the one-state-visible rule.
- **Mode switch leaves a Query run pending** (`mockups/src/js/21-compare.js:415`): switching to Compare within 800 ms results in a query-mode single result appearing in compare mode, and a Query history row for a run the operator left.
- **Raw selector JSON** (`mockups/src/js/20-query.js:246`): the crash path described under Top 3 Fix 3.
- Positive: the four error shapes route through one `classifyResponse` path; Run in query mode is clickable with an inline message as the spec requires; `Keep document` takes initial focus on the Delete dialog.
- Positive: 0 console errors and 0 network requests on file:// across all three viewports.

Score is 2 because three interaction paths break the stated state contract, and one of them can present a result the spec says the server refuses.

---

## Registry Safety

Registry audit: not applicable. `components.json` does not exist and UI-SPEC lists no third-party registry.

---

## Files Audited

- /home/chris/coding/Databasise-2.0-fully-agnostic-system/.planning/phases/17-gui-mockup/17-UI-SPEC.md
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/.planning/phases/17-gui-mockup/17-CONTEXT.md
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/.planning/phases/17-gui-mockup/17-REVIEW.md (cross-check only)
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/operator-console.html (built artifact, read-only)
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/css/60-ledger.css
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/css/00-base.css
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/js/20-query.js
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/js/21-compare.js
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/js/10-shared.js
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/screens/ledger.html
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/screens/documents.html
- /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/src/screens/corpus.html
- Screenshots: /home/chris/coding/Databasise-2.0-fully-agnostic-system/.planning/ui-reviews/17-gui-mockup-audit/ (18 files)

Not audited visually: Evidence & Trace and Documents & Jobs at 768 and 375 px (captured, not individually inspected). Interaction states were not driven live.
