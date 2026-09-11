# Feasibility: one small model that embeds for itself, routes to graph / vector / SQL / skills, refines cyclically, and answers from all of it

Date: 2026-09-11. Companion to `prior-art-survey.md`. Owner analysis unless a source is named.

## Why nobody has built the intersection

1. **Two communities, two objectives.** Embedding work (GritLM, LLM2Vec) optimises MTEB. Memory-layer work (Mem0, Cognee, Letta, Graphiti) optimises conversational recall benchmarks and assumes a hosted frontier LLM plus a hosted embedding API, because that is the fastest way to ship a product. Unifying weights is a training project; memory-layer vendors do not train models.
2. **Separate models are cheaper at index time.** A dedicated embedder is 0.1–0.6B and embeds thousands of chunks per second; a 2B generator embeds at generator cost. GritLM's >60% RAG speedup comes from reusing the KV cache of a document that is both embedded and generated over at query time (README: `model.encode(..., get_cache=True)` then `generate(past_key_values=cache)`). Bulk corpus ingest never generates over most chunks, so unification wins at query time and loses at index time. Structural, not accidental.
3. **Small models fail structured output.** Graphiti's README says so outright: "particularly problematic when using smaller models." Routing to typed stores needs strict schemas, so every memory layer defaults to a frontier model. Grammar-constrained decoding (llama.cpp GBNF, Outlines ★15,782, XGrammar ★1,880) makes syntax a sampler property rather than a model property, so the residual problem is semantic (wrong store, wrong entity), not syntactic. Most memory layers predate wide use of constrained decoding and have not revisited the assumption.
4. **No benchmark rewards the intersection.** LoCoMo and LongMemEval grade recall from chat; MTEB grades embeddings; SWE-bench grades agents. Nothing grades "one small model builds and queries a multi-store memory with no frontier model in the loop", so no lab optimises for it.
5. **Routing training data is schema-specific.** Mem-α and Memory-R1 each had to construct their own dataset (both abstracts say so). Which store a fact belongs in depends on the product's schema, so the data does not transfer between products, and vendors keep the decision in a prompt to a frontier model instead of fine-tuning.
6. **Vendor incentive.** Letta, Mem0, Zep, Cognee, Hindsight monetise a hosted layer. A self-contained on-device small model removes the need for the service.
7. **Timing.** The parts matured at different times: GritLM Feb 2024, Graphiti 2024, Mem-α Sep 2025, MiniCPM5-2B Sep 2026. A 2B-class model with usable tool-calling and long-context numbers is weeks old. The intersection was not cheaply feasible until now.

## Is it possible? Capability by capability

| Capability | Status | Evidence | What it costs us |
|---|---|---|---|
| One set of weights embeds and generates | **Proven at 7B**; adapter route proven on Llama-architecture bases | GritLM-7B (MTEB 66.8, gen 55.5, README table); LLM2Vec ships LoRA adapters over Llama-3-8B (README) | MiniCPM5-2B is standard `LlamaForCausalLM`, so LLM2Vec's recipe applies without model code. Open: quality at 2B |
| Small model routes extracted pieces to typed stores | **Proven at 4–8B with RL**; unmeasured at 2B | Mem-α, Memory-R1 abstracts (learned store/update/retrieve decisions) | Fine-tune target. MiniCPM's own OPD recipe fits: frontier teacher on our schema, on-policy distillation into the 2B |
| Graph + vector + SQL stores, linked | **Engineering, already owned** | Databasise machine primitives: Cozo graph, Faiss vector, SQLite KV/ledger | None new. The harness is a wiring over existing primitives |
| Skills store: model reads and writes `.md` procedures | **Proven pattern** | Voyager (2023, ★7,193): LLM-written skills retrieved by embedding. Letta MemFS: git-backed memory files the agent inspects and edits (docs). Anthropic Agent Skills spec (agentskills.io): `SKILL.md` with frontmatter, progressive disclosure. MIRIX procedural memory; Hindsight knowledge pages | A fourth store: a directory of `SKILL.md` files indexed by the same embedder and by name. Two skill kinds the owner named: documentation-making, advanced-searching (query procedures over the other three stores) |
| Cyclical refinement (re-link, re-embed after graph changes) | **Proven at note scale**; cost scales with corpus | A-MEM memory evolution; Letta sleep-time compute (arXiv 2504.13171); Hindsight consolidation | Budgeted background pass. Must be gated: this project's own history includes a model destroying the wiki layer (memory: lost-fact-layer). The promote/rollback ledger in the contract vocabulary is the guard |
| Query-side routing across stores | **Library pattern exists** | LlamaIndex SQLAutoVectorQueryEngine (docs); §18 seam selectors | Engineering |
| Token savings | **Follows from locality** | Frontier model sees only distilled memory; all ingest tokens are local | Measured on the rig, priced per RIG §F3 |

Verdict: possible. It is an integration plus fine-tune project with two genuine unknowns, not a research breakthrough.

The two unknowns, each a rig experiment:

1. **2B self-embedding quality.** LLM2Vec adapter on MiniCPM5-2B versus a dedicated embedder (Qwen3-Embedding-0.6B or MiniCPM-Embedding-Light) on the Phase 3 parity corpus. Pass condition: retrieval parity within a stated margin.
2. **2B routing accuracy.** Given extracted pieces, does the model pick graph / vector / SQL / skill correctly against a frontier-labelled set? Constrained decoding on; measure semantic accuracy only.

## Skills store: one requirement that is not optional

A skill is an instruction the frontier model will follow. If the harness writes skills from ingested documents, a document becomes a channel into the frontier model's instructions. That is a prompt-injection path, and it is worse than ordinary injection because it persists. The write path for skills therefore needs a gate that the write paths for graph, vector, and SQL do not: schema validation is not enough; a model-written skill must be reviewed (human, or a separate validator with no access to the source document) or run only in a sandboxed capacity before the frontier model can read it. The project's `taint.py` laundering-test validator is the right shape of tool.

## What Databasise already has that makes this buildable here

- The three stores as machine-owned primitives, behind a fitting contract, with a wiring format. The harness is a wiring.
- An LLM-client seam that already speaks OpenAI-compatible endpoints, so a local 2B behind Ollama or SGLang is config.
- A rig with a 20-document parity corpus and side-by-side comparison, so "as good as frontier on this slot" is a measurement the project already runs.
- A promote/rollback ledger and validators, which is what cyclical self-refinement needs to be safe.
- The MiniCPM repo ships Claude Code skills for deploy and fine-tune, so the fine-tune path is scripted.

## Decision 2026-09-11: skill trust boundary

Owner decision: **micro-written skills run sandboxed, for the micro only. The frontier model gets one complementary, human-authored skill that tells it how to talk to the micro.**

```
 documents ──► micro harness (sandbox) ──► graph / vector / SQL / skills(micro-only)
                     ▲          │
   interface skill   │          │ answers = data, fenced
   (human-authored,  │          ▼
    frontier reads)  └──── frontier model ──── user
```

What this closes:

- Micro-written skills never enter the frontier's instruction set. The persistent injection channel named above does not exist.
- The frontier's only instructions about the micro are in one versioned `SKILL.md` the micro cannot write to. In Databasise terms that skill is the consumer-side guide to the §18 REST/MCP envelope: which tools exist (recall, store, graph search, SQL lookup, list skills), the response shape, and the rule that every returned value is data.
- Skill sandboxing is a property of the micro's runtime, not of each skill: the micro loads skills only from its own store, and its skill scripts execute with no path to the frontier's context.

What it does not close, stated so it is not forgotten: answers returned to the frontier are still data that can carry instructions, the ordinary RAG injection surface. The seam's fenced envelope is the existing mitigation; nothing new is needed for this design.

Cost: near zero. The MCP surface already exists (Phase 4 and 5), so the interface skill is documentation of tools that are already there, in the same shape the MiniCPM repo uses for its own skills.

## Ledger

- GritLM's KV reuse crosses an attention-mask boundary (bidirectional embedding pass, causal generation). The README code shows it works; the accuracy cost of the mismatch is in the paper body, not read here. **unverifiable here**
- LLM2Vec at ~1B (Sheared-LLaMA) is in the paper from memory; the README fetched shows only the 8B example. **unverifiable here**
- Mem-α and Memory-R1 base model sizes. **unverifiable here** (carried from prior-art-survey)
