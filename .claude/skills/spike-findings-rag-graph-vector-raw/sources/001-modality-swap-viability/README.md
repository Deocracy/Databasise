---
spike: 001
name: modality-swap-viability
type: standard
validates: "Given the archived Databasise engine (sourcerer-lightrag tgz), when its source is inspected against upstream LightRAG, then the RAG modality is separable from the machine without loss of designed features"
verdict: VALIDATED
related: [002]
tags: [lightrag, cozo, databasise, viability, read-only]
---

# Spike 001: Modality Swap Viability

Read-only inspection spike, run 2026-08-10, regularized into the manifest retroactively (it predates the spike structure).

## What This Validates

**Given** the archived Databasise engine (`sourcerer-lightrag_nonstripped_2026-06-26.tgz`), **when** its source is inspected and compared against the vendored upstream LightRAG copy, **then** the RAG modality is separable from the machine (storage + clients) without losing any built feature.

## How to Run

Extract the tgz to scratchpad; diff against `Databasise/upstream-venv/Lib/site-packages/lightrag`; grep for custom code and feature markers. No code written, no repos modified.

## Results

**Verdict: VALIDATED ✓** — full findings in [FINDINGS.md](FINDINGS.md). Key results:

1. The "fork" is stock LightRAG 1.5.4 + one plugin file (`cozo_impl.py`, 977 lines, `BaseGraphStorage` impl); zero core-file deltas
2. The machine/fitting seam already exists one level low: `kg_query(...)` receives storages as arguments; LLM/embed/rerank injected as fields; ~no concrete-backend leakage in 5,995 lines
3. **Correction to the brief:** time-shift + contradiction detection are designed-but-unbuilt (Cozo schema shaped for additive `Validity` column, deferred "Phase 6") — nothing to preserve, only to not-foreclose
4. Query path is already a named 4-stage component pipeline; index side is entangled (~1,786 lines, ontology-welded)
5. A working storage-parity harness (same corpus, isolated dirs, structural diffs, JSON out) exists to generalize into the modality comparison rig

Limits: vendored copy not verified-clean upstream (api_version 0313 vs 0312); HippoRAG 2 not read (led to the 24-system survey and spike 002).
