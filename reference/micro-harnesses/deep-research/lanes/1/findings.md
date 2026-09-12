# Lane 1 findings: Unified embedding and generation in one model

Screened 27, admitted 17. All admitted items were opened at their arXiv abs page;
all 17 PDFs were downloaded from `https://arxiv.org/pdf/<id>` and verified to start
with `%PDF`. Repo facts (stars, push date, license) were read from the GitHub API
on 2026-09-12 unless noted. Star counts for monorepo-hosted code (unilm,
FlagEmbedding) are repo-level, not model-level.

## (a) Admitted items

**GritLM (2402.09906).** The reference joint-training recipe: one LLM handles
generative and embedding tasks, switched by instruction, with causal attention for
generation and bidirectional attention for embedding. Take: the exact training
mix MelodyScribe wants (representational + generative instruction tuning), the
attention-switching implementation pattern, and the RAG-latency argument (>60%
speedup by co-locating retriever and generator). Careful: unification is per-task
switching, NOT one forward pass doing both — embedding a paragraph and generating
from it remain two passes; and the "no performance loss" claim is at 7B/8x7B, far
above the 1-3B target. MIT, weights + code released.

**LLM2Vec (2404.05961).** Three-step conversion of any decoder-only LLM into an
encoder: enable bidirectional attention, masked-next-token pretraining, then
contrastive tuning — parameter-efficient, applied down to 1.3B, SOTA-unsupervised
on MTEB at release. Take: the cheapest known path to turn MiniCPM5-2B into a
strong embedder, plus its pooling/attention ablations for the last-token-vs-
bidirectional question. Careful: step 1 breaks causal generation in the converted
weights, so the embedder and the generator diverge unless MelodyScribe keeps
separate adapters; and MNTP pretraining costs extra compute before any payoff.
MIT, code + 1.3B-8B checkpoints released.

**NV-Embed (2405.17428).** ICLR 2025 Spotlight; Mistral-based generalist that held
MTEB #1. Two results matter: a latent-attention pooling head consistently beats
mean pooling and last-EOS pooling, and removing the causal mask during
contrastive training improves representations. Take: the pooling-head design
(MelodyScribe should not assume raw last-token hidden states are sufficient) and
the two-stage retrieval-then-non-retrieval instruction tuning. Careful: no GitHub
repo exists (weights only, on Hugging Face) and the license is CC-BY-NC-4.0 —
usable for research, not for a commercial Databasise. No generation is preserved;
it is embed-only.

**E5-Mistral (2401.00368).** ACL 2024; fine-tunes a decoder-only LLM with contrastive
loss on synthetic data alone (<1k steps) using last-token pooling, then sets SOTA
with a synthetic+labeled mix. Take: proof that a decoder becomes a top embedder
with surprisingly little contrastive data, and the synthetic-data pipeline behind
it. Careful: relies on a proprietary LLM to author the synthetic data (distillation
dependency), and generation quality after embedding fine-tune is unmeasured.
MIT via microsoft/unilm.

**Echo / Repetition Improves Language Model Embeddings (2402.15449).** ICLR 2025.
Repeating the input and pooling from the second occurrence gives a causal decoder
bidirectional-like context with zero architecture change and zero training (+5%
zero-shot, matching bidirectional-converted models). Take: the fallback if
MelodyScribe must embed with a strictly frozen causal model — no weights change at
all. Careful: it doubles the token cost of every embedding pass, which directly
taxes the "near-zero token cost" hypothesis, and no official code or checkpoints
were found.

**Qwen3-Embedding (2506.05176).** The most on-scale public recipe: decoder-based
embedders at 0.6B/4B/8B with multi-stage unsupervised-then-supervised training and
model merging, Apache-2.0. Take: the 0.6B variant is the closest existing artefact
to a MiniCPM5-2B embedder — copy its data mix and merging strategy. Careful: it is
embed-only (no generation-preservation results), and the 0.6B model's absolute
quality trails its larger siblings, so expect a scale tax at 2B too.

**OneGen (2409.05152).** EMNLP 2024 Findings; the only admitted work that truly does
generation and retrieval in ONE forward pass: autoregressively emitted retrieval
tokens double as embedding queries, reusing the live KV cache. Reports no
generation degradation with retrieval gains (+1.5pt single-hop, +3.3 F1 multi-hop).
Take: the architectural pattern closest to MelodyScribe capability 1 — file-while-
generating instead of GritLM's switch-and-re-encode. Careful: demonstrated only at
7B (Llama2/Qwen2-1.5B appears only as a baseline retriever, not as a OneGen host),
and retrieval tokens still consume generation budget. MIT, code + HF models.

**PromptEOL (2307.16645).** EMNLP 2024 Findings; the "in one word" prompt template
plus the only scaling study in the lane (OPT/LLaMA 125M-66B): a 2.7B model with
this template beats a prior 4.8B SOTA. Take: the zero-training embedding baseline
for a 2B model and evidence that small models can carry sentence semantics.
Careful: STS-only evaluation (not retrieval), and the repo has no license listed.
Also note the template consumes prompt tokens on every pass.

**KaLM-Embedding (2501.01028).** Qwen2-0.5B-based multilingual embedder, SOTA among
<1B models, via persona-based synthetic data, ranking-consistency filtering, and
semi-homogeneous batching. Take: direct existence proof that a 0.5B decoder makes
a competitive embedder, and a data-quality recipe (filtering > volume) that ports
to any 2B effort. Careful: embed-only; generation behavior of the base model after
conversion is unreported. MIT, code + weights.

**MetaEOL (2402.18458).** ACL 2024; averages embeddings from 8 meta-task prompts on
a frozen decoder, beating PromptEOL and Echo and matching LLM2Vec-7B on STS with
no training. Take: the strongest frozen-backbone result — relevant if Folios must
be embedded without touching weights. Careful: 8 forward passes per text (the
opposite of one-pass), STS-only, 12-star repo with no license.

**EmbeddingGemma (2509.20354).** 308M decoder-derived (Gemma 3 -> T5Gemma encoder
init -> Gemini-Embedding distillation), SOTA under 500M, robust to 4-bit/128-d
compression. Take: the compression and distillation recipe for on-device 2B
embeddings. Careful: encoder-only output — it discards generation entirely, so it
informs the embedding half only; weights are gated under the Gemma license.

**BGE-M3 (2402.03216).** One encoder serving dense + sparse + multi-vector retrieval
via self-distillation, 100+ languages, 8k context. Take: precedent that one set of
weights can serve multiple retrieval modalities — the closest analogue to filing
one paragraph into several stores. Careful: encoder-only (XLM-R-based), no
generation. MIT, code + weights.

**SGPT (2202.08904).** The original decoder-as-bi-encoder (position-weighted mean
pooling + BitFit), from the same first author as GritLM. Take: the pooling result
that still holds — weighted-mean beats last-token — and BitFit as the cheapest
adaptation method tried. Careful: 5.8B scale, 4096-d embeddings (5x storage), and
largely superseded by the above. MIT.

**Gemini Embedding (2503.07891).** Google's report on converting Gemini into a
generalist embedder (filtering + synthetic data + model soup), SOTA on MMTEB.
Take: the frontier-vendor recipe, and confirmation that even Gemini needs the full
data-curation pipeline — embeddings are not free at any scale. Careful: API-only,
no weights or code; treat all numbers as vendor-reported.

**Gecko (2403.20327).** Two-step LLM distillation (FRet synthetic queries + LLM
relabeling of positives/negatives) letting 1B-class models rival 7B ones. Take:
the distillation recipe for compressing a frontier teacher into a 2B embedder.
Careful: no public weights; the teacher LLM calls are the expensive hidden input.

**E5 (2212.03533).** The weakly-supervised contrastive recipe (CCPairs) every later
work inherits; first to beat BM25 zero-shot. Admitted at relevance 1 as the recipe
predecessor, not as lane evidence (encoder-only). MIT via unilm.

**AnglE (2309.12871).** ACL 2024; angle-over-cosine loss fixing saturation zones,
with ablations over 5 pooling strategies and an AnglE-LLaMA variant. Admitted at
relevance 1 for the pooling/loss evidence only. MIT.

## (b) Refutations (admitted sources only)

1. **"One forward pass does both" is not demonstrated by GritLM.** GRIT switches
   attention modes per task type (2402.09906: causal for generation, bidirectional
   for embedding), so embedding a paragraph and generating from it are separate
   passes. Only OneGen (2409.05152) unifies in a single pass, and only by emitting
   retrieval tokens mid-generation at 7B — not by emitting a paragraph embedding
   and constrained store-operations simultaneously at 1-3B. MelodyScribe capability
   1 as stated has no admitted precedent.
2. **"Embeddings from own hidden states are free" is contradicted.** NV-Embed
   (2405.17428) shows last-token causal embeddings underperform a learned pooling
   head and require removing the causal mask; LLM2Vec (2404.05961) requires
   bidirectional enablement + MNTP to reach SOTA; SGPT (2202.08904) needs
   position-weighted pooling; MetaEOL (2402.18458) trails contrastive-trained
   models despite 8 prompts. Production-quality embeddings cost architecture
   change, extra tokens (Echo 2x, MetaEOL 8x), or contrastive training — or all
   three.
3. **The 1-3B joint embed+generate claim is unsupported, not refuted.** Every
   admitted unifier is >=7B (GritLM 7B/8x7B, OneGen 7B, NV-Embed/E5-Mistral 7B).
   Every admitted sub-1B decoder-embedder is embed-only (Qwen3-0.6B, KaLM-0.5B,
   EmbeddingGemma-308M). No admitted paper measures generation degradation from
   embedding duty at 1-3B, so the motivating hypothesis stands unrefuted — and
   unevidenced — at target scale.

## (c) Unresolved ledger

- SFR-Embedding-Mistral: abstain — vendor blog + model card only, no paper.
- Seed1.5-Embedding: abstain — vendor blog only; API-only, no weights/code.
- Arctic-Embed 2.0 (2412.04506): abstain — verified but encoder-only, out of scope.
- Jina-Embeddings-v3 (2409.10173): abstain — verified but encoder-only; task-LoRA
  modularity flagged for lane 6.
- BGE-Multilingual-Gemma2: abstain — no paper found, model card only; 9B out of scale.
- GTE-Qwen2 (1.5B/7B): abstain — weights only, no method paper found.
- Google text-embedding-004: abstain — proprietary, known only via citations.
- LLM2Vec-Gen (2603.10913): abstain — Mar-2026 preprint, frozen-backbone idea
  relevant to capability 1 but unverified.
- Hydra (2603.28554): abstain — single-author Mar-2026 preprint; its claim that
  GritLM-style joint training collapses generation is exactly the measurement the
  lane needs, but authority is unverified — do NOT cite as refutation.
- Contriever (2112.09118): abstain — verified baseline but encoder-only, out of scope.

## (d) Security findings

None in this lane. No admitted paper addresses memory/skill integrity; the
prompt-based methods (PromptEOL, MetaEOL, Echo) expand prompt-attack surface by
construction (embedding prompts are themselves injectable text), which the Folio
gate design should note, but no paper was found that measures this — record as a
gap, not a requirement.
