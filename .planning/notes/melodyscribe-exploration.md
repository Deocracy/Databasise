---
title: MelodyScribe exploration — micro-harness memory method
date: 2026-09-11
context: /gsd-explore session on micro-harnesses; reference material collected in reference/micro-harnesses/
---

# MelodyScribe exploration

**What MelodyScribe is.** A micro-harness: a small local model (MiniCPM5-2B class) in a sandbox that embeds for itself, routes what it reads into graph / vector / SQL / skills stores, refines those stores in a background pass, and serves a frontier model through one human-authored skill. Inside Databasise it is a wiring over the machine's existing primitives, not a new engine. Naming: `reference/micro-harnesses/NAMING.md`.

**Thesis.** Every piece exists somewhere (self-embedding: GritLM, LLM2Vec; multi-store memory: Cognee, MIRIX, Letta, Graphiti, Memori, Hindsight, A-MEM; learned routing in a small model: Mem-α, Memory-R1), but no project combines them in one small model. Seven reasons why, and a capability-by-capability feasibility verdict, are in `reference/micro-harnesses/feasibility.md`. Verdict: possible; integration plus fine-tune, with two unknowns that are rig experiments (2B self-embedding quality; 2B routing accuracy).

**Decisions made in the session.**

- D-MS-01: model-written skills (Folios) run sandboxed inside the Scriptorium and are loaded only by MelodyScribe. The frontier model never reads them.
- D-MS-02: the frontier model gets exactly one human-authored skill (the MelodyScribe skill) describing the §18 REST/MCP tools; the model cannot write to that path. This closes the persistent-injection channel a model-written skill would otherwise open.
- D-MS-03: judge and falsifier roles are not MelodyScribe candidates (Phase 2 D-07, "judge never free", stands).
- D-MS-04: naming convention per NAMING.md; models are `MelodyScribe-{size}-v{version}`.

**Evidence status.** The owner's motivating finding ("a very small model was as good as or better than a frontier model in many cases") is held in the dissertation workspace (spikes 001/017) and was not re-read; it stays unverified until reproduced on this rig. MiniCPM5-2B numbers are vendor-reported. See the ledgers in the reference folder.

**Next.** Owner wants to go over the system model (`docs/system-model/`) with MelodyScribe in hand: which NodeKinds, effects, artifact scopes, and budget rules govern it, and whether a component that is its own embedding client is admissible under the contract.
