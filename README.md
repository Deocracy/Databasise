# Databasise 2.0 — Fully Agnostic System

The build of the **RAG Modality Swap system model** (v1.0, shipped 2026-08-28): re-cutting Databasise's engine (stock LightRAG 1.5.4 + Cozo plugin) into an agnostic machine + fitting contract + versioned components, where a modality (LightRAG, HippoRAG 2, …) is a wiring of components, not a monolith.

## What's here

- `docs/system-model/` — the frozen v1.0 governing documents, copied verbatim from the model repo (`ServerDestroyer/rag-modality-swap-system-model`, local: `~/Vibe Coding/RAG Graph Vector Raw/.planning/architectures/`):
  - `SYSTEM-MODEL.md` — entry point. §VD verdict (conditional go), §BP the four-rung build ladder, §H1 what this build inherits vs. must decide itself.
  - `CONTRACT.md` (fitting contract, 20 sections), `ANATOMY.md` (machine anatomy), `PARTS.md` (three stress-modality wirings), `CATALOG.md` (72-system snap-in catalog + porting protocol), `RIG.md` (comparison rig + versioning).
  - `MODEL-RED-TEAM.md` — adversarial record. `D-VARIANTS/SELECTION.md` — governs on any disagreement, including its spike-005 amendment.
  - Five gate scripts (`*-check.sh`, 145 checks), `rig-trace.schema.json`, `wirings/` (illustrative wiring JSON), `ARCHITECTURE-RUBRIC.md`.
- `.claude/skills/spike-findings-rag-graph-vector-raw/` — distilled spike findings (001–005) incl. `taint.py` (laundering-test validator).
- `v1/` — Databasise v1: the sourcerer-lightrag fork (stock LightRAG 1.5.4 + `lightrag/kg/cozo_impl.py` Cozo plugin, with docker/k8s/webui/tests), extracted from the 2026-06-26 archive and **sanitized for public release** (root `.env` removed; credential values in `env.docker-compose-full` blanked — see `env.example` for configuration).
- `reference/hipporag2-2502.14802.pdf` — HippoRAG 2 paper.

Not in the repo (local pointers): HippoRAG reference clone at `~/Vibe Coding/RAG Graph Vector Raw/reference/HippoRAG` (114MB; re-clone when Phase 4 needs it); the original unsanitized v1 archive at `~/Vibe Coding/Databasise/_archives/sourcerer-lightrag_nonstripped_2026-06-26.tgz` (contains live credentials — never commit it). LightRAG code-verified pin: upstream commit `b93f7c31f`.

## Build ladder (SYSTEM-MODEL.md §BP — binding order)

1. **Validator + depth machinery + falsifier gate** — Falsifiers 2 (static depth computability) and 5 (per-tier A/A null width) must run and pass here; ladder halts if either fires. Falsifier 8 survey alongside (non-gating).
2. **LightRAG query-side re-cut in parity** — ~794 lines, 17 of 18 node positions, gated on the Phase-1 A/A band.
3. **Opaque-side admission** — LightRAG's ~1,786-line ingest core as `quarantined` opaque node; codebase-memory-mcp whole-engine under §17/§8, run twice (Falsifier 4).
4. **HippoRAG 2 full decomposition + first side-by-side rig run.**

Precondition to Phase 1: owner ratification of the §VD verdict (`recommended — awaiting owner ratification`).

The query side decomposes **first**; the ingest side stays opaque longest (spike-005 binding order — do not "optimise" this back).
