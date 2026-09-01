# Phase 3: LightRAG Query Side - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-31
**Phase:** 3-lightrag-query-side
**Areas discussed:** Index provenance, The original arm, Model clients, Parity gate depth
(all four presented; owner declined per-area discussion and directed recommendations)

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Index provenance | Where the corpus index the query nodes read comes from; ingest core is opaque and its admission is Phase 5 scope | |
| The original arm | How the pre-decomposition LightRAG is stood up and run; v1 has no venv today | |
| Model clients | `databasise/` has no LLM/embedding/rerank client; machine primitive vs. part-internal; which providers | |
| Parity gate depth | Roadmap criteria 4+5 (eval bundle, A/A floor) vs. criterion 6 (deterministic retrieval gate); arm coverage | |

**User's choice:** Other — "no area needs coverd go with recomendations"
**Notes:** Owner handed all four areas back for Claude to settle. Every decision D-01..D-15 in
CONTEXT.md is therefore Claude's, made under stated rationale, and open to owner reversal. Recorded
explicitly in CONTEXT.md `<specifics>` so a later reader does not mistake them for owner positions.

---

## Claude's Discretion

The whole of CONTEXT.md `<decisions>` was Claude's discretion by owner direction. The four areas
resolved as:

- **Index provenance** → D-01/D-02/D-03: v1 indexes once, verbatim import into the v2 namespace
  layout with byte-identity assertions, `embedder-index` authored and validated by sample
  reproduction rather than re-embedding. Driven by PITFALLS 8 — indexing twice makes embedding drift
  indistinguishable from a decomposition bug.
- **The original arm** → D-04/D-05: v1 in its own pinned venv, invoked as a subprocess by the
  harness, never imported (Phase 1 D-14's boundary test); not an admitted opaque node, since that is
  Phase 5's MODAL-02 and Phase 1 D-08 refuses `subprocess` placement by name. Trace asymmetry between
  the two arms recorded rather than glossed.
- **Model clients** → D-06..D-09: machine-owned primitives on `NodeContext.clients`, forced by
  MACH-05's metering-at-declared-boundary rule; one OpenAI-compatible shape so v1's env-var config
  and v2's node config carry one pinned identity; Phase 2's banked models (qwen3.7-flash
  provider-pinned, local Ollama embedder); rerank authored and wired but configured off, with
  `calls_rerank` still declared under §19.9's fallback-reachability rule.
- **Parity gate depth** → D-10..D-14: criterion 6's deterministic retrieval gate is the phase gate;
  MACH-02/MACH-03 deferred a second time to Phase 6, recorded as a written amendment; `keywords`
  pinned per query so downstream is exactly comparable and measured separately as its own N-run
  band; all five arms over a `mix` base; small fixed HotpotQA-distractor corpus snapshot.
- **Storage-ownership audit** (not presented as an area; settled while scouting) → D-15:
  machine-checked from the run record, undeclared store touch is a refusal, import-boundary check
  extended.

## Deferred Ideas

- MACH-02 / MACH-03 (eval bundle + A/A calibration, Falsifier 5) → Phase 6. Second deferral.
- Rerank as a live path → whenever a provider is worth standing up.
- The original arm as an admitted opaque node → Phase 5 (MODAL-02).
- `.planning/architectures/wirings/` illustrative JSON named by PARTS §L.2 but never written →
  resolve here or fold into the HARD-01/HARD-02 doc pass.
- PARTS defects D1, D2, D7, D12 → contract-level, unrepaired; note if the port trips them, do not
  repair here.
- HARD-01 / HARD-02 → Phase 7 doc pass.
- The fact layer / DR-05 `validity` sub-capability → still open; Phase 4's frozen §18 envelope is
  its deadline.
