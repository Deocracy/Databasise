# Micro-harnesses — research side project (MelodyScribe)

Started 2026-09-11. Owner: Christopher. Status: collecting, not deciding.

Project name: **MelodyScribe** (decided 2026-09-11). Inside Databasise, MelodyScribe is the name of the method: a micro-harness wiring that embeds for itself, routes to graph / vector / SQL / skills, refines cyclically, and serves the frontier model through one human-authored skill. Naming rules in `NAMING.md`.

## What this folder is

A collection point for evidence on **micro-harnesses**: a small local model (1B–3B class) wrapped in a narrow task contract (prompt + output schema + deterministic validator), used as one component inside a larger system instead of routing every call to a frontier model. The working question is whether Databasise can run some of its LLM-backed nodes on such a harness without consumers noticing, and how to fine-tune the model and tune the harness once a slot is chosen.

The working definition above is a draft drawn from the owner's earlier work (see "Prior findings"); it is to be confirmed in discussion, not treated as settled.

## Contents

| File | What |
|---|---|
| `minicpm5-2b.md` | Notes on the candidate model: identity, benchmarks, training recipe (SFT → RL → OPD), deployment backends, fine-tune recipe, open questions. Every fact tagged with its source. |
| `prior-art-survey.md` | Answers: can one network be both LLM and embedder (GritLM, LLM2Vec, llama.cpp); which memory harnesses route conversations and documents into graph + vector + SQL (Cognee, MIRIX, Letta, Graphiti, Memori, Hindsight, A-MEM, Mem0, MemOS); which small models are trained to do the routing (Mem-α, Memory-R1, MemoRAG). Verdict: the intersection is unbuilt. |
| `NAMING.md` | MelodyScribe naming convention: project, method, models (`MelodyScribe-2B-v0.1`), Scriptorium, Folio, Proof, the MelodyScribe skill, seam tool names. |
| `system-model-fit.md` | MelodyScribe mapped onto CONTRACT / ANATOMY / RIG / SELECTION clause by clause: modality not harness, model as `core` client, opaque entry under §8, stores via §15 (SQL Branch 2, Folios `self_storage`), reviser as `fixpoint`, no `melodyscribe_*` seam tools, F3 pricing, four open questions. |
| `score-format-and-cache.md` | The Score: sectioned input format with per-section embed / respond / file / link directives, executed in one context via llama.cpp sequences; what the KV cache reuses exactly (prefix), approximately (shift reuse), or by isolation (Prompt Cache modules); why isolated-embedding sections double as reusable KV modules. |
| `runtime-one-pass.md` | How one prefill yields both the paragraph embedding and the tool-call generation: prompt-layout rule, three verified routes (llama.cpp C API, llama-server prompt cache, SGLang hidden states), grammar-constrained op list, adapter-vs-head decision, the efficiency claim stated precisely. |
| `runtime-and-training-stack.md` | Where PyTorch lives (training rig only), the three environments, serving on legion via Ollama with `ollama-cuda`, the causal-vs-bidirectional embed-adapter decision, training sized to a 16 GB card, what crosses the boundary. |
| `feasibility.md` | Why the intersection is unbuilt (seven reasons), capability-by-capability feasibility with evidence, the skills store and its injection gate, the two rig experiments that settle the unknowns. |
| `sources/` | Verbatim snapshots (dated) of the HF model card, the OpenBMB/MiniCPM README, and the TRL fine-tune cookbook. Re-fetch before relying on a number older than a month. |

## Prior findings (owner's earlier work, outside this repo)

The claim that motivated this folder, "in many cases a very small model was as good as or better than a frontier model", comes from the owner's dissertation workspace, not from anything in this repo. Pointers, plain text because the paths contain spaces:

- /home/chris/Vibe Coding/atomized-dissertation/wiki/research/08 Parallel Small-Model Architecture.md — compound-AI framing (Zaharia 2024), cascade/routing literature (FrugalGPT, RouteLLM, BEST-Route, cascade-routing duality, xRouter), MoA and its "single strong small model beats mixed families" caveat (arXiv 2502.00674).
- /home/chris/Vibe Coding/atomized-dissertation/.planning/spikes/027-parallel-llm-speed/MOA-PARALLELISM-MEMO.md — adversarially reviewed memo; separates speed claims from quality claims; records that a symbolic validator plays the ranker role at zero cost; cites Correlated Errors (arXiv 2506.07962) and CAPA (arXiv 2502.04313) on why same-family ensembles do not decorrelate.
- /home/chris/Vibe Coding/atomized-dissertation/wiki/synthesis/direction-execution-model.md — the microagent execution model: "Microagents build and render. Code reads, validates, and gates." Per-step small-model routing with escalation of hard steps.
- /home/chris/Vibe Coding/atomized-dissertation/wiki/research/Sources/2026-maker-implementations-debrief.md — MAKER: thousands of micro-calls to cheaper small models, gated by voting and validators; token-explosion critique.
- /home/chris/Vibe Coding/atomized-dissertation/wiki/architectures/route-llm.md — learned per-query router.

The effect-size evidence for "small ≈ frontier" lives in that workspace's spikes 001 and 017 (referenced by the memo). Those were not re-read for this snapshot; see the ledger below.

## Candidate slots in Databasise (owner analysis, for discussion)

Ranked by how narrow and verifiable the task is, which is what a 2B model needs:

1. **Index-side entity / relation extraction** (LightRAG index core; HippoRAG 2 OpenIE triples) — highest-volume LLM call in the system, schema-shaped output, validator can be graph-structural.
2. **Query-side keyword extraction** (LightRAG stage 1) — tiny output, high frequency, trivially schema-checked.
3. **Query routing / mode selection** (naive vs graph vs hybrid) — a classification, cheap to measure on the rig.
4. **Entity-description merge / summarization** — short constrained generation.
5. **Not a candidate:** the judge and falsifier roles. Phase 2 decision D-07 fixed "judge never free"; that stands.

Any promotion of a harness into one of these slots is priced against RIG §F3 per-mutation-class affordability, like every other component change. No benchmark number in `minicpm5-2b.md` settles it.

## Unresolved ledger

Claims this folder carries but cannot yet stand behind. Do not copy these into a requirement or decision as plain fact.

- "A very small model was as good as or better than a frontier model in many cases" — owner finding; source-of-record is spikes 001/017 in the dissertation workspace, not re-read here. **unverifiable in this snapshot.**
- All MiniCPM5-2B benchmark scores — vendor-reported on the model card (rows marked † from Artificial Analysis). Primary for "what the vendor reports", not independent. **non-authoritative for our tasks.**
- RL+OPD gain of +10.96 / +6.96 points — vendor-reported, same status.
- MiniCPM5-2B decode speed and quantised-checkpoint quality — not reported anywhere in the sources fetched. **no source.**

## Next

Discussion in progress via `/gsd-explore`. Outputs (notes, todos, seeds, spike) get routed into `.planning/` once the owner picks them.
