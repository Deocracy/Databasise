---
spike: 007
idea: melodyscribe
name: embedding-prompt-sensitivity
type: comparison
validates: "Given the corpus and the shared query set, when documents and queries are embedded under different instruction, prefix, and marker designs on the dedicated 0.6B embedder and on the 2B [EMB] state, then recall@k, MRR, and anisotropy per design on identical inputs"
verdict: PENDING
related: [002, 004]
tags: [embeddings, prompts, instructions, doc-prefix]
---

# Spike 007: embedding-prompt-sensitivity

## What This Validates

Does the prompt around a text change its embedding enough to matter, and which design should the Score's `doc_prefix` and query prefix use. Spike 004 found the `Passage:` versus bare prefix insensitive on the 0.6B embedder, on two gold queries. This spike measures it properly on the shared query set, on both the trained embedder and the generative path. Read `.claude/skills/spike-findings-melodyscribe/references/score-io-contract.md` (token policy, `doc_prefix` default) and `model-size-and-training.md` first.

## Plan

Data: `.planning/spikes/shared/queries-v1.json`, all splits (no training happens here), plus the two HotpotQA gold queries. Passages: the corpus documents.

Models: Qwen3-Embedding-0.6B (GGUF, `.models/`) and MiniCPM5-2B (GGUF) with the `⟦EMB⟧` marker policy from spike 002, both through llama_cpp in `.venv`. Identical texts per design across models.

Designs (each applied to the query side, the document side, or both, as stated):

1. None: bare text on both sides.
2. The vendor's documented instruction format for Qwen3-Embedding on the query side only, with a generic retrieval instruction.
3. A task-specific instruction on the query side ("retrieve the passage that answers this question about films and the people who made them").
4. A wrong-domain instruction on the query side (code search) as a control.
5. Instruction on both sides.
6. Document title as a prefix versus bare document text.
7. Generative path: the chat-template system turn as `doc_prefix` (the v0.1 default) versus no template versus a task instruction.
8. Generative path: marker placement, `⟦EMB⟧` at the end versus a PromptEOL-style prompt ("This passage means in one word:") versus "The passage is about".
9. Query form: the keyword-style queries versus the natural-language queries in the set (a data-side split, no new embeddings).

Metrics per design and model: recall@1, @3, @10, MRR; mean pairwise document cosine; query-to-document cosine gap (mean gold cosine minus mean non-gold cosine); milliseconds per text. Three repetitions where timing matters; embeddings are deterministic (check one design byte-identical on re-run).

Pass conditions, stated before the run: a design is "material" if it moves MRR by 0.05 or more on the full query set. Report the best design per model, whether the v0.1 `doc_prefix` default holds, and whether the wrong-domain control hurts (if it does not, the embedder ignores instructions on this corpus and the spike says so).

Environment: `.venv` and `env.sh`; every model load under the GPU lock; one model per process (two processes, one per model, run one after the other).

## Research

(to fill: docs read, approaches compared)

## How to Run

(to fill)

## What to Expect

(to fill)

## Investigation Trail

(to fill: every iteration with its log)

## Results

(to fill: verdict with sub-claims and the head-to-head table)
