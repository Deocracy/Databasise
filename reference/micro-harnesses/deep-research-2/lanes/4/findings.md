# Lane 4 findings: hybrid models — one small model that embeds and generates

Scope: unified embed+generate training, mode-switching adapters, weight merging of an
embed-tuned model with its generative base, MoE variants, measured generation
degradation, and single-forward-pass reuse. Screened 33, admitted 28 (27 papers with
PDFs on disk + the mergekit tool). Every admitted paper was opened at its arXiv abs
page (title, authors, dates, abstract verified from the fetched page); full-text
numbers live in the downloaded PDFs and were not re-extracted here.

## (a) Admitted items

**GritLM (2402.09906).** Generative Representational Instruction Tuning trains one LLM
on generative and embedding tasks jointly, distinguishing them by instruction; GritLM 7B
set the MTEB state of the art at release while matching or beating same-size models on
generative tasks. Take: this is the reference recipe for question 2 — instruction
switching, not architecture surgery, is what makes one weight set do both jobs, and it
directly shapes the MelodyScribe skill/embedding-marker design. Careful: 7B scale with
full joint training is far above a 16 GB single-GPU budget; the transferable part is
the instruction-conditioning pattern, and small-scale replication needs LoRA-scale
confirmation. Repo: https://github.com/ContextualAI/gritlm (700 stars, MIT).

**OneGen (2409.05152, EMNLP 2024).** Retrieval tokens and generation tokens are emitted
in one forward pass, so retrieval and generation share the same rollout with no
separate retriever call. Take: the closest published analogue of MelodyScribe's
one-pass section handling — marker tokens that switch the head between modes — and the
paper to copy the training/eval setup from for Spike 006. Careful: results are at 7B
and on RAG/entity-linking tasks, not on graph-op emission; the retrieval-token
vocabulary trick must be re-proven next to a grammar-constrained op decoder.
Repo: https://github.com/zjunlp/OneGen (148 stars, MIT).

**LLM2Vec (2404.05961).** Any decoder LLM becomes an embedder in three steps —
bidirectional attention, masked next-token prediction, unsupervised contrastive
learning — with a LoRA path that leaves the generative base weights untouched. Take:
this is the cheapest credible route to a hybrid small model: freeze MiniCPM-scale base,
train only the embedding adapter, keep generation intact by construction. Careful:
bidirectional attention breaks KV-cache reuse for the embedding pass, which interacts
with lane 8's prefix-caching plans; and the contrastive step still needs pair data
(the labelled pairs Spike 004 lacked). Repo: https://github.com/McGill-NLP/llm2vec
(1714 stars, MIT).

**LLM2Vec-Gen (2603.10913).** Successor from the same group: trainable special tokens
compress the frozen LLM's own potential response into a fixed-length embedding in
output space, guided by an unsupervised teacher plus reconstruction, on unlabeled
queries only. Take: removes LLM2Vec's contrastive-pair requirement — the exact blocker
Spike 004 hit — while keeping the backbone frozen, so generation cannot degrade.
Careful: 2026 paper, low citation history so far; the unsupervised teacher's quality
bounds everything, and the [EMB]-marker idea in MelodyScribe is a special case worth
comparing head-to-head. Repo: https://github.com/McGill-NLP/llm2vec-gen (77 stars, MIT).

**MAGNET (2501.08648).** Three self-supervised objectives plus a modified attention
mechanism adapt decoder-only LLMs to produce robust representations and infill spans
while remaining generative. Take: a second, independent unified-training recipe beside
GRIT, with infilling as a bonus third mode relevant to evidence-quote repair (Spike
003's validator failures). Careful: abstract-level screening only; the attention change
may complicate serving-engine compatibility (lane 8 must check).

**GRC (2605.09100).** Meta latent tokens plus unified generative/representational/
compressive tuning unify generation, text representation and context compression in one
forward pass. Take: the only work found that trains all three modes MelodyScribe needs
(embed, generate, compress-for-KV-reuse) together — the natural training target if
Spike 006's cheap versions work. Careful: brand-new (May 2026), no independent
replication; compression-quality numbers must be read in the PDF before depending on it.

**GEM (2608.13200).** One model reasons over the query in generation mode, then appends
an embedding token encoding the enriched context for retrieval; evaluated on
reasoning-intensive retrieval. Take: evidence that generation-first-then-embed beats
embed-only on reasoning-heavy queries — supports letting the small model "think" before
emitting the section embedding. Careful: extra reasoning tokens cost latency per query;
the trade-off curve in the PDF decides whether it fits the serving budget.

**RetroLLM (2412.11919, ACL 2025).** Retrieval and generation fused in a single
process: the LLM directly generates fine-grained corpus evidence under constrained
decoding, eliminating the separate retriever and its deployment cost. Take: the
existence proof that constrained decoding can serve retrieval inside the generation
pass — directly licences MelodyScribe's grammar-constrained op emission sharing a pass
with the embedding read-out. Careful: constrained generation of evidence still needs
the Proof validator (generated evidence can be fluent but wrong); joint optimisation
details are in the PDF. Repo: https://github.com/sunnynexus/RetroLLM (116 stars, MIT).

**Hydra (2603.28554).** A single retrieval-only LoRA on a vision-language model is
toggled at inference: on gives ColBERT-style multi-vector embeddings, off recovers
base generation with all 426 language-model tensors byte-identical to the base
checkpoint. Take: the cleanest adapter-switch measurement found — zero generation
degradation by construction, and a template for Spike 006 (train retrieval LoRA, diff
tensors, report the count). Careful: single author, vision modality, August-2026-era
base (Qwen3.5-4B per abstract); verify the byte-identical claim in the full text
before citing it as fact.

**Task Arithmetic (2212.04089).** Task vectors (fine-tune minus base) can be added or
subtracted to steer behaviour without retraining. Take: the primitive behind
merge-the-embedder-home — add a scaled embedding task vector to the generative base
and sweep the coefficient against generation benchmarks. Careful: scaling coefficients
are empirical per pair; expect a sweep, not a default.

**TIES-Merging (2306.01708).** Trim small deltas, elect per-parameter sign, average
only agreeing parameters — cuts interference when fusing same-base fine-tunes. Take:
the default merge to try first for embed-tuned + generative-base fusion. Careful:
needs both parents from the same base checkpoint, which constrains which public
embedders qualify.

**DARE / Super Mario (2311.03099).** Drop most delta parameters at random, rescale the
rest, then merge — homologous models absorb abilities with no retraining or GPU.
Take: sparsified deltas preserve more of each parent, which is exactly the "what does
the generative side lose" lever; combine DARE with TIES in the merge sweep. Careful:
drop rates interact with adapter rank; LoRA deltas may already be sparse enough that
DARE adds little — measure, don't assume.

**LM-Cocktail (2311.13534).** Merging a fine-tuned model back toward its base recovers
general-task performance while keeping target gains. Take: the paper that names the
generation-degradation pattern and its fix — fine-tune-then-merge-home should be the
baseline protocol for any MelodyScribe embedder that touches base weights. Careful:
weights for the merge (e.g. 0.5-style blends) are task-dependent; the PDF's ablations
set the starting grid.

**Model Soups (2203.05482).** Plain averaging of same-base fine-tunes improves accuracy
at zero inference cost. Take: the floor every fancier merge (TIES/DARE/AIM/SLERP) must
beat in the Spike 006 merge comparison. Careful: averaging dilutes task-specific peaks;
it is a robustness move, not a capability-union move.

**Activation-Informed Merging / AIM (2502.02421).** Folds activation-space information
into any merging method to protect critical base weights. Take: use as a guard layer on
top of TIES/DARE when the merge must provably preserve generation — the closest thing
found to a "what merging preserves" guarantee. Careful: needs calibration activations,
i.e. representative generative prompts, which must be curated, not scraped.

**Bagging-Based Model Merging (2602.05787).** Systematic comparison of multi-task
embedding training schedules versus merging for general-purpose embeddings and domain
adaptation. Take: merging is positioned as an alternative to joint multi-task training
— if MelodyScribe needs domain-specific embedding behaviour, train per-domain and
merge rather than re-running joint training. Careful: 2026, abstract-screened; the
scheduling-vs-merging numbers are in the PDF.

**Merging for task-conflict embedders (2410.15035).** Joint multi-task embedding
training suffers gradient interference (task conflict); merging per-task models beats
joint training for general embedders. Take: second independent vote for
train-separate-then-merge, with the interference analysis explaining why the unified
GRIT-style joint run may underperform a merge at small scale. Careful: embedder-only
models; the generation side is out of scope here.

**SLERP geometry study (2511.21703).** Asks whether SLERP merging cures LoRA
over-specialisation in embedding space. Take: the only SLERP-for-embeddings geometry
evidence found; include SLERP in the merge sweep for completeness. Careful:
single-author, synthetic numerical-sequence eval only — treat geometry claims as
suggestive, not general; low weight until replicated.

**SGPT (2202.08904).** Contrastive fine-tuning of GPT decoders with biased/weighted-mean
pooling for symmetric and asymmetric search. Take: the original proof that decoders
embed without architecture change, and the pooling-ablation template Spike 007 should
reuse. Careful: full fine-tune overwrites generation; useful as the embed-quality
ceiling, not as a hybrid. Repo: https://github.com/Muennighoff/sgpt (872 stars, MIT).

**E5-Mistral (2401.00368).** Full fine-tune of Mistral-7B on synthetic instructions;
high embed quality from a decoder with the generative side overwritten. Take: the
synthetic-data recipe (the data side Spike 004 lacked) and the cautionary example —
without a frozen base or merge-home step, the generator is gone. Careful: sub-1k-step
claim depends on their synthetic pipeline; reproduce the data step, not just the
contrastive step.

**Embedder's Dilemma (2608.12875).** Controlled cost-aware test of 10 LLMs vs 26
embedding models on 37 tasks: aggregate tie (0.4 pts), LLMs win reasoning-heavy
retrieval, embedders win classification, and parity costs substantially more. Take: the
fair head-to-head template (fixed tasks, cost reported) that Spike 004's comparison
should be re-run against, and a cap on "competitive" claims for small hybrids.
Careful: headline numbers are from large models; the small-model corner of the
trade-off is exactly what Spike 006 must fill in.

**Attention-Values pooling (2602.01572).** Value Aggregation pools attention value
vectors across layers/tokens and reportedly beats hidden-state pooling with no
training. Take: a concrete cheap version for Spike 006 alongside last-token and mean
pooling — values are less next-token-optimised than hidden states. Careful: single
comparison claim needs replication on our corpus before trusting; abstract-screened.

**Mid-token pooling (2605.09969).** Mean pooling across autoregressively generated
tokens beats any single token as a representation (kernel-alignment evidence across
language, vision, protein). Take: if MelodyScribe ever embeds from generated text
rather than the Score pass, pool across the generation, not the last token.
Careful: evidence is alignment-based, not retrieval-MRR-based; confirm on MRR.

**Layer Dynamics / LRD (2605.12714).** Framework measuring how representations drift
across layers, applied to 31 embedders and base LLMs on 30 MTEB tasks. Take: the
measurement toolkit for "how far did our embed-tune drift from base" — run LRD-style
checks (or at minimum neighbourhood-retention) whenever base weights move. Careful:
descriptive framework, not a training method; value is diagnostic.

**Unified on-device RAG (2604.14403).** Unified model+document representation for fully
local RAG over private documents. Take: the deployment-shape precedent for a small
unified MelodyScribe model serving private corpora on one GPU — cite for the serving
configuration recipe. Careful: on-device constraints differ from server-GPU batching;
take the representation idea, not the systems numbers.

**EPIC (2605.01372).** Replaces discrete in-context demonstrations with trained
embedding-based prompts to keep ICL gains for embeddings while cutting token overhead.
Take: if few-shot graph-extraction prompts (lane 7) bloat the Score context, EPIC-style
soft prompts are the compression route that stays inside the embedding model.
Careful: abstract-screened; overhead numbers are in the PDF.

**mergekit (tool, https://github.com/arcee-ai/mergekit, 7347 stars, LGPL-3.0,
pushed 2026-09-12).** YAML-driven SLERP/TIES/DARE/task-arithmetic merges. Take: run
every Spike 006 merge through mergekit recipes so merges are reproducible artefacts,
not one-off scripts. Careful: LGPL-3.0 — fine as a tooling dependency, check policy
before vendoring code.

## (b) Refutations

No admitted primary source contradicts a directly stated brief claim. Closest tensions,
stated precisely so the integrator does not overclaim:

1. Against "one small model hosts a competitive embedder" as a cheap win: the
Embedder's Dilemma (2608.12875) finds LLM–embedder parity only in aggregate and at
substantially higher cost, with embedders still winning classification. A small hybrid
should be claimed as competitive only per task family with cost attached, not in
general. Partial tension, not a refutation.
2. Four recalled arXiv ids from memory were contradicted at the abs page and are
recorded as abstains in the inventory (2311.16402 is QCD/TMD work, not DARE;
2311.10913 is phylogeny, not LM-Cocktail; 2304.10491 is Collatz dynamics, not
RepLLaMA; 2304.01982 is a ColBERT token-retrieval analysis, not LLaRA). The correct
DARE paper is 2311.03099 and the correct LM-Cocktail is 2311.13534, both verified.
RepLLaMA's and LLaRA's correct ids were not established — see ledger.

## (c) Unresolved ledger

- Correct arXiv ids for RepLLaMA (dense retrieval from LLaMA) and LLaRA (LLM adaptation
for retrieval) not established; two plausible recalls both resolved to unrelated
papers. Reason: memory unreliable, arXiv API throttled during the session; needs a
fresh search round.
- NV-Embed (2405.17428, latent-attention pooling, generative base) and Nomic MoE /
BGE-ICL / echo-embedding ids were candidate guesses never verified. Reason: lane
boundary — architecture/pooling detail belongs to lanes 1–3/5; listed here so the
integrator can cross-check rather than re-screen blind.
- BadMerging (backdoor attacks against model merging, id unverified, title seen in an
arXiv search snippet) not screened. Reason: surfaced late, security-relevant; needs
its own verification round before any claim.
- Full-text figures (MTEB deltas, generation-benchmark deltas, merge coefficients,
Hydra's byte-identical tensor count, SLERP geometry statistics) not extracted; all
admits here rest on verified abs-page abstracts plus the downloaded PDFs. Reason:
per-lane scope; the integrator owns number extraction.
- 2026 single-author or thin-history claims (Hydra byte-identical recovery,
SLERP-geometry generalisation, Attention-Values superiority) carry replication risk.
Reason: no citing literature yet; Spike 006 replication is the check.
- Venue fields left as "arXiv preprint" except OneGen (EMNLP 2024, repo-verified) and
RetroLLM (ACL 2025, repo-tag-verified). Reason: abs pages show no journal-ref; venues
not claimed without a source.

## (d) Security findings (as requirements)

- R1 (weight provenance): every model entering a merge (base, embed-tune, LoRA) must
be pinned by checkpoint hash from a trusted publisher; merging executes arbitrary
weight arithmetic, so an untrusted parent silently becomes the child. (Requirement
from the merge-heavy recipe set: 2212.04089, 2306.01708, 2311.03099, mergekit.)
- R2 (generated evidence is untrusted input): single-pass retrieval-inside-generation
designs (RetroLLM 2412.11919, OneGen 2409.05152) can emit fluent but false evidence;
no generated string may reach graph/SQL stores without passing the Proof validator,
and validator failures must be logged with the source span. (Extends the brief's
Spike 003 evidence-failure rate, 30–50%.)
- R3 (unverified 2026 claims quarantined): Hydra/SLERP/Attention-Values replication
claims must not gate release decisions until Spike 006 reproduces them locally.
