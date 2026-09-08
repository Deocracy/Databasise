# Injected-LLM-Endpoint Survey

**Date:** 2026-09-08
**Requirement:** MACH-04
**Falsifier:** Falsifier 8

**Disposition, quoted from `docs/system-model/SYSTEM-MODEL.md` (`## §RK`, the falsifier register):**
> "Narrowest of the falsifiers — a non-gating documentation pass placed in `## §BP` Phase 1
> alongside the two gating falsifiers; failure 'collapses to the shallowest-denominator problem
> the selection exists to fix' for engine comparability specifically, not a `SELECTION.md`-level
> reversal." — disposition: **`accepted-as-stated-risk`**, cost class **`cheap`**.

A failure recorded here is a **comparability finding**, not a ladder halt: nothing this survey
finds blocks Phase 5, gates a later phase, or reopens `SELECTION.md`. It narrows what a future
cross-engine token comparison may honestly claim, and nothing more.

## List Provenance

No document in `docs/system-model/` enumerates exactly five engines under a "sandbox-candidate"
label. `SYSTEM-MODEL.md` and `docs/system-model/D-VARIANTS/SELECTION.md` both refer to "the five
sandbox-candidate engines already named in the lineup" for Falsifier 8, but no single table
supplies that list. Falsifier 6 names exactly two engines by way of illustration
(`codebase-memory-mcp`: no LLM, own storage; a LightRAG server: LLM-heavy, injectable endpoint).
`CATALOG.md`'s `## §T` master table separately carries a dedicated `MC-` bucket with exactly two
MCP-hosted candidates (`postgres-mcp`, `supabase-mcp`) plus `CA-1` (code-graph-rag) and `CA-2`
(codebase-memory-mcp) as the catalog's own foreign/opaque-shaped entries.

The five engines below are therefore an **adopted recommended default**, composed from
`CATALOG.md`'s `CA-`/`MC-` opaque-shaped entries plus Falsifier 6's own named second engine — not
a verbatim list read from any source document. `05-RESEARCH.md` Assumption A2 records this same
inference and flags it Medium risk precisely because Falsifier 8 is non-gating and
`accepted-as-stated-risk`, so a wrong or incomplete list does not block this phase. Correcting the
list means editing the findings table below — a one-edit change, not a re-derivation.

## The Claim Under Test

Quoted verbatim, `docs/system-model/D-VARIANTS/SELECTION.md` line 133, `## Falsifiers` item 8:
> "**Engines refuse the injected endpoint in the common case.** Token comparability collapses to
> the shallowest-denominator problem the selection exists to fix. *Experiment:* survey the
> endpoint-injection surface of the five sandbox-candidate engines already named in the lineup; a
> documentation pass."

Quoted verbatim, `docs/system-model/SYSTEM-MODEL.md` line 158, the falsifier register's own row:
> "Engines accept an injected LLM endpoint in the common case, preserving token comparability. |
> Falsifier 8 | Survey the endpoint-injection surface of the five sandbox-candidate engines already
> named in the lineup; a documentation pass. | cheap | Narrowest of the falsifiers ... |
> accepted-as-stated-risk"

`docs/system-model/CONTRACT.md` §8 condition 3, the admission rule this claim is adjudicated
against: "The node's network namespace MUST be denied, with the machine acting as the injected LLM
provider in its place. An engine that cannot accept the injected endpoint MUST be admitted as
`unbudgetable`, and the rig MUST refuse any token comparison that would include it."

## Findings

| Engine (CATALOG id) | Hosting shape | Accepts injected LLM endpoint | Injection mechanism | Evidence class and source | §8 condition 3 consequence |
| --- | --- | --- | --- | --- | --- |
| codebase-memory-mcp (CA-2) | whole-engine opaque node, `self_storage` | Vacuous — zero LLM calls anywhere | none — no LLM call path exists in the fifteen-tool surface to inject an endpoint into | [code-verified] `PARTS.md ## §X` condition 3's already-run verdict, `mcp.c` TOOLS[] scan, `src/ui/http_server.c` — recorded as an **open question, not a clean yes**, because a loopback-bound HTTP UI server exists in the same OS process even though zero LLM/network calls appear in any of the fifteen tool handlers | Vacuous for injection itself; the denial-scope question (per-tool-call vs per-process, `PARTS.md` row `N12`) stays open for reasons unrelated to LLM injection |
| postgres-mcp (MC-1) | `external-tool` hosted opaque (§17), `self_storage` default | Vacuous — no LLM in its own declared capability closure | none — a SQL tool surface (`sql_result_set`/`derived_finding` outputs only) | [docs-verified] `CATALOG.md` MC-1 entry, `crystaldba/postgres-mcp` README's own "MCP Server API" table (nine tools, none an LLM call) | Vacuous — condition 3's denied-namespace-or-unbudgetable choice does not arise for an engine with no LLM to provide |
| supabase-mcp (MC-2) | `external-tool` hosted opaque (§17), `self_storage` default | Vacuous — no LLM in its own declared capability closure | none — thirty tools across eight categories (account/database/debugging/development/docs/edge-functions/storage/branching), none an LLM call | [docs-verified] `CATALOG.md` MC-2 entry, `supabase-community/supabase-mcp` source tree (`packages/mcp-server-supabase/src/tools/*.ts`) | Vacuous — same as MC-1 |
| code-graph-rag (CA-1) | decomposed wiring; index side fully deterministic/zero-LLM, query side LLM-centric | Unknown — this is the one catalogued candidate whose own closure calls an LLM at all | `rewriter` node (`CypherGenerator`, translating natural language into a `formal_query`) and `generator` node (answer synthesis) — CATALOG.md records these two LLM-calling positions, but no clone of code-graph-rag's own client construction was read this session to confirm it accepts a caller-supplied `base_url` the way `openai_compat.py` or v1's `lightrag/llm/openai.py` do | [inference] for the injection-acceptance judgment; the underlying "this engine calls an LLM at all" fact is [code-verified] per `CATALOG.md` CA-1's own citation (`MODALITIES-CODE-AND-ALIEN Part 1 §1`), read against a pinned clone in a prior phase, not re-read this session | Unresolved — the one row where the denied-namespace-vs-`unbudgetable` choice is a live, unsettled question; this survey does not round it up to either answer |
| a foreign-hosted LightRAG server | Falsifier-6-named LLM-heavy case, distinct from the in-process opaque ingest core Phase 5 plan 05-01 already admits | Yes — confirmed by code | `v1/lightrag/llm/openai.py`'s `base_url`/`api_key` constructor parameters (lines 138-139, 191-215) and `v1/scripts/run_parity_ingest.py`'s env-driven construction (`LLM_BINDING_HOST`/`LLM_BINDING_API_KEY`, lines 132-138), which Phase 3's parity harness already exercises as a real injection against this exact codebase; `databasise/clients/openai_compat.py`'s `OpenAICompatibleClient` is the machine's own analogous injectable client for the same purpose | [code-verified] `v1/lightrag/llm/openai.py`, `v1/scripts/run_parity_ingest.py`, `databasise/clients/openai_compat.py` — all read this session | Denied network namespace with the machine as injected provider — satisfiable by construction, the same technique Phase 3's parity harness already uses |

## Verdict

Of the five surveyed engines, three (`codebase-memory-mcp`, `postgres-mcp`, `supabase-mcp`) are
**vacuous** for Falsifier 8's own question: none calls an LLM anywhere in its declared capability
closure, so there is no endpoint for the engine to accept or refuse, and §8 condition 3's
denied-namespace-or-`unbudgetable` choice never arises for them. One (a foreign-hosted LightRAG
server) is **confirmed by code to accept the injected endpoint** — the identical `base_url`/`api_key`
injection mechanism Phase 3's own parity harness already exercises against this codebase. One
(`code-graph-rag`) is **unresolved**: `CATALOG.md`'s own prior code-verified analysis confirms its
closure calls an LLM through a `rewriter`/`generator` pair, but this pass did not itself read
code-graph-rag's client-construction source to confirm base-URL injectability, so the row is
recorded as an inference rather than a verified yes.

**Falsifier 8 did not fire on this evidence, but it is not confirmed refuted either.** Zero of the
five rows demonstrates an engine that calls an LLM and refuses the injected endpoint — the
falsifier's own failure condition. The falsifier is recorded as **surveyed**, not confirmed or
refuted: among the two LLM-calling engines this list actually contains, one accepts injection
cleanly and the other is unresolved rather than refusing. What would change this verdict: reading
code-graph-rag's own LLM-client construction against its real source, or widening this five-engine
list to include an engine that positively refuses a caller-supplied endpoint.

For the token-comparability claim Falsifier 8 exists to protect: three of five candidates carry no
token spend to compare in the first place (vacuous), one is confirmed comparable by construction,
and one row's comparability is presently unknown rather than settled either way — a future
cross-engine token comparison that included `code-graph-rag` without resolving this row would be
overstating what this survey supports.

## Method and Limits

Read this session: `docs/system-model/SYSTEM-MODEL.md` (Falsifier 8's register row),
`docs/system-model/D-VARIANTS/SELECTION.md` (`## Falsifiers` item 8), `docs/system-model/CATALOG.md`
(CA-1, CA-2, MC-1, MC-2 entries and the `## §T` master table), `docs/system-model/PARTS.md ## §X`
(codebase-memory-mcp's already-run condition-3 verdict), `docs/system-model/CONTRACT.md` §8
condition 3, `databasise/clients/openai_compat.py`, `v1/lightrag/llm/openai.py`, and
`v1/scripts/run_parity_ingest.py`. Not read this session: any clone of `postgres-mcp`,
`supabase-mcp`, or `code-graph-rag`'s own source — their rows rest on `CATALOG.md`'s own prior
citations (`[docs-verified]` for MC-1/MC-2 against published READMEs, per `CATALOG.md`'s own D-06
convention; `[code-verified]` for CA-1's LLM-calling fact against a pinned clone read in an earlier
phase). No engine other than the LightRAG case was executed for this pass — every verdict above is
a source read, not a live network probe against a running instance of any of the five engines.
