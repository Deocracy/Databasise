---
title: MelodyScribe as a Databasise wiring — third modality on the rig
trigger_condition: milestone v1.0 closes (Phase 7 done), or the first rig measurement of a 2B-class model on any LightRAG/HippoRAG slot completes
planted_date: 2026-09-11
---

# Seed: MelodyScribe wiring

Run MelodyScribe (a micro-harness: MiniCPM5-2B class model in a sandbox, self-embedding via an LLM2Vec-style adapter, routing to graph / vector / SQL / Folios, background revise pass) as a wiring behind the §18 seam, so it sits on the rig beside LightRAG and HippoRAG 2 and is compared on the same corpus with the same envelope.

Why it belongs here: the core value is "modalities are swappable without consumers noticing". A modality whose LLM and embedder are the same 2B model, running with zero API tokens, is the strongest test of that claim, and its promotion is priced by RIG §F3 like any other.

Preconditions before planning it:
- The two rig experiments in `.planning/todos/pending/melodyscribe-spike-rig-experiments.md` have results.
- The system-model fit questions (NodeKind, effects, artifact scope for the Scriptorium, embedder-as-component admissibility) are answered; see `reference/micro-harnesses/`.

Source material: `reference/micro-harnesses/` (survey, feasibility, naming).
