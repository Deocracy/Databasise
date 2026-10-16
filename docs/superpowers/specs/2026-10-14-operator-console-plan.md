# Operator Console GUI — Plan

Date: 2026-10-14
Status: plan recorded; step 1 in progress

## Goal

An operator console GUI for Databasise 2.0. The user is the operator running the engine. The console is a client of the §18 REST API ([databasise/seam/rest.py](../../../databasise/seam/rest.py)). It does not modify the seam's envelope, and swapping modalities must not change what it reads.

## Decision change

v1.0 excluded all UI ([.planning/PROJECT.md](../../../.planning/PROJECT.md) line 48, [.planning/research/FEATURES.md](../../../.planning/research/FEATURES.md) line 43). This plan changes that decision to: **an operator console is in scope as a REST client**. Databasise itself stays API-first. PROJECT.md is to be updated when the next milestone opens.

## Starting state (2026-10-14)

- The v2 engine has no GUI code, mockups, or GUI plans. It has 15 REST routes and 9 MCP tools.
- [v1/lightrag_webui/](../../../v1/lightrag_webui/) is a React 19 + Vite + Sigma.js app that calls the v1 LightRAG server, not §18. It is a reference, not a base.
- §18 has no read routes for browsing the graph or vector stores, and none for listing modalities, aliases, or ledger history.

## Scope known so far

1. Query and compare: run queries, compare modalities side by side, inspect evidence and traces.
2. Documents and jobs: upload, insert, and delete documents; watch ingest jobs; corpus counts and health.
3. Ledger actions: promote, rollback, and retire, with a view of current state.
4. Graph and vector browser: needs new read-only API routes.
5. More screens are expected once the mockup is in use. The plan allows for this: step 2 is where new needs get found.

## Steps

**Order change (2026-10-14, owner decision):** the engine defects found in the second pass ([docs/gui/CODEBASE-MAP.md](../../gui/CODEBASE-MAP.md) section 4) are fixed **before** any GUI work. The milestone order is: **defects → GUI connectors (step 3's read routes) → GUI build (mockup, then connect)**. That puts step 3 ahead of step 2.

**Tracking moved to GSD (2026-10-14):** this work now runs as GSD milestone v1.1, "Engine Fixes + Operator Console". The live plan is [.planning/ROADMAP.md](../../../.planning/ROADMAP.md) and [.planning/REQUIREMENTS.md](../../../.planning/REQUIREMENTS.md). This file is the original record.

1. **API inventory.** Document every REST route and MCP tool: what it does, its request and response fields, its refusals, and what the GUI needs for it. Then list every GUI need that has no API yet, with a proposed route and a priority. Output: [docs/gui/API-INVENTORY.md](../../gui/API-INVENTORY.md).
1b. **Engine fixes.** Fix the defects in CODEBASE-MAP.md section 4 before any GUI work. That covers the 12 blockers (M-01 to M-12) plus whatever else the owner puts in scope. Each defect becomes a BAK ledger row with its own test, and that test must fail before the fix is written. Its own spec and plans come through superpowers.
2. **Mockup GUI.** Build a clickable HTML mockup from the inventory, one screen per group in step 1. Controls whose API does not exist yet are kept and marked as needing backend work. They are never silently cut. This avoids the GUI-research finding where 13 mockup controls were dropped because their backend was never written down as a requirement. The owner uses the mockup and records new needs back into the inventory.
3. **Backend gap routes.** Add the read-only routes the mockup needs that do not exist yet: graph and vector browse, plus registry and ledger listing. Each one follows the rest.py thin-adapter rule and the §18 constraints.
4. **Connect.** Wire the mockup to the live REST API screen by screen, replacing mock data with real calls.

## Process

- Superpowers drives design: brainstorming, then this plan, then writing-plans for each step's implementation plan.
- BAK (agent-delivery-kit, from GUI-research) is used once building starts, from step 2 onward.

## Open decisions (to settle during steps 1–2)

- Where the browse routes live: on §18 itself, or on a separate admin/console surface that keeps §18's closed envelope unchanged.
- CORS and auth for a browser client. rest.py currently ships with neither.
- The build stack after the mockup. Likely React 19 + Vite + Sigma.js, so the v1 graph viewer can be reused.
