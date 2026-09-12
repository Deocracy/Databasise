# Lane 5 findings: prompts and instructions for embeddings

Scope: instruction-following embedders, prompt-based decoder embeddings, sensitivity of
wording, query-side versus document-side prefixes, chat-template effects, marker-token
approaches, and anything measuring how much MRR moves with the instruction. 18 admitted,
7 abstained, 25 screened. All figures below come from pages opened during this lane
(arXiv abs/HTML/PDF, ACL Anthology, Hugging Face, GitHub, vendor project pages).

## (a) Admitted items

**INSTRUCTOR (2212.09741).** One encoder trained with a natural-language instruction
concatenated to every input over 330 tasks (MEDI), evaluated on 70 embedding tasks with
+3.4% average gain over the previous best at matched size. MelodyScribe takeaway: this is
the reference recipe for task-conditioned embeddings — "Represent the X for Y; Input:"
style prefixes on both sides plus contrastive multitask training. Caution: the
robustness-to-paraphrase claim on the project page is contradicted by later
instance-level benchmarks (see refutations); treat the +3.4% as task-prefix conditioning,
not general instruction following.

**E5-Mistral (2401.00368).** Decoder-only Mistral fine-tuned with contrastive loss on
synthetic-plus-labeled data, reaching SOTA on BEIR/MTEB with under 1k training steps on
synthetic data alone. MelodyScribe takeaway: the production-critical convention is the
**one-sided prefix** — instructions go on queries only ("Given a web search query,
retrieve relevant passages..."), documents are encoded bare so the corpus index is built
once and reused across tasks (confirmed in the HF usage docs and the Linq report).
Caution: the synthetic-data pipeline depends on proprietary LLMs; the transferable part
is the prefix convention, not the data.

**NV-Embed (2405.17428).** Mistral-7B with a trainable latent-attention pooling layer,
causal mask removed during contrastive training, and two-stage instruction tuning; MTEB
69.32 and No. 1 in May and August 2024. Two design facts matter: the latent pooler beats
mean pooling 69.32 to 68.98 in their ablation, and instruction tokens are **masked out of
the pooled output** (they still affect states through attention) with **no instruction
prefix on documents**. MelodyScribe takeaway: copy the masking rule for the [EMB]-marker
design — the marker/prefix shapes the state but must not leak into the pooled vector —
and keep document-side inputs bare. Caution: latent attention adds parameters and was
validated at 7B; the gain may not survive at 0.6B.

**PromptEOL / Scaling Sentence Embeddings (2307.16645).** The "This sentence: [X] means
in one word:" template plus in-context demonstrations, evaluated training-free from
125M to 66B parameters; a fine-tuned 2.7B OPT with the prompt beats a 4.8B ST5 on STS.
MelodyScribe takeaway: this is the cheapest baseline for Spike 007 — wrap the section in
a one-word-compression prompt and read the last-token state, before training anything.
Caution from the paper itself: scaling past tens of billions of parameters *hurts* STS,
so bigger is not better for this trick, and the one-word constraint is a zero-shot
device, not necessarily a fine-tuning template.

**Echo embeddings (2402.15449).** Repeating the input and pooling from the second
occurrence fixes a proven failure mode: causal last-token states overweight late tokens
and early-token states never see later context. Zero-shot gain is ~5% and matches
bidirectional-conversion-plus-MLM; compute-matched fine-tuning matches or beats
bidirectional conversion. MelodyScribe takeaway: directly relevant to Spike 004's
anisotropy diagnosis — the untrained last-token state is weak partly because it is
causally blind to later tokens, and echo is the no-architecture-change fix to test in
Spike 007. Caution: repetition doubles sequence length and compute; the repo
(jakespringer/echo-embeddings, 168 stars, Apache-2.0) also bakes instructions into echo
templates, so isolate repetition effects from instruction effects when measuring.

**MetaEOL (2402.18458).** Eight GPT-4-written meta-task prompts (classification,
sentiment, paraphrase, extraction) each with one-word limitation, embeddings averaged
with no training; LLaMA2-13B improves 6.73% over PromptEOL and beats contrastive-trained
models on STS. MelodyScribe takeaway: prompt *diversity plus averaging* is a free,
training-independent quality lever — test multi-prompt averaging for the Score-section
embedding in Spike 007. Caution: eight forward passes per section is an 8x serving cost;
the repo (12 stars, code only, no checkpoint) is a research script, not a component.

**Qwen3-Embedding (2506.05176).** Instruction-aware decoder embedders at 0.6B/4B/8B with
Matryoshka support, Apache-2.0, built on Qwen3 with a chat-template input
(`<|im_start|>user: {Instruction} : {Query} : {Document}`). The vendor reports
instructions beat no-instructions by 1–5% on most tasks and advises English instructions
even for multilingual retrieval. MelodyScribe takeaway: this is the closest public
analogue of the harness goal — a sub-billion instruction-aware embedder with a scored
MRR delta for the instruction itself — and the 0.6B checkpoint is the distillation
teacher candidate for lane 3. Caution: the 1–5% figure is vendor-reported, not
independently replicated; verify it on our corpus before budgeting quality to it.

**Promptriever (2409.11136).** The first bi-encoder that is genuinely promptable: ~500k
MS MARCO instances augmented with per-query instructions **and instruction negatives**
(passages relevant to the query but wrong under the instruction). Results: +14.3 p-MRR /
+3.1 nDCG-MAP on FollowIR, +12.9 Robustness@10 on InstructIR, +1.4 BEIR average when
prompted, 44% lower cross-instruction variance. MelodyScribe takeaway: the recipe that
makes instructions actually move retrieval is instruction negatives, not just
instructions — any Spike 007 training phase must mine negatives that share the query but
violate the instruction. Caution: gains are demonstrated on retrieval with relevance
instructions; transfer to CLS/clustering-style section instructions is unproven.

**InstructIR (2402.14334).** 9,906 instance-wise user-aligned instructions with a
Robustness@10 (minimum nDCG over paraphrases) metric. Headline result: retrievers tuned
on task-style instructions (e.g. INSTRUCTOR) can *underperform* their non-tuned
counterparts — evidence of overfitting to coarse task prefixes. MelodyScribe takeaway:
adopt Robustness@10-style evaluation for Spike 007; a single canned instruction per
section type will overstate quality. Caution: GPT-4-generated instructions may flatter
models distilled from similar LLMs.

**FollowIR (2403.15246).** TREC-narrative benchmark with a p-MRR metric (−100 to +100)
measuring whether the ranking actually changes with the instruction, plus training data.
Finding: essentially only 3B+ models, or instruction-tuned LMs never trained for
retrieval, follow instructions; their FollowIR-7B doubles Mistral-7B (71.5 vs 35.3
Robustness@10). MelodyScribe takeaway: expect a 2B embedder to *ignore* subtle
instructions unless trained with instruction negatives (cf. Promptriever); sizeurate the
instruction (short, imperative, criteria-first) rather than relying on nuance. Caution:
TREC narratives are long professional-assessor texts, unlike short Score prefixes.

**InBedder (2402.09642).** Reframes the instruction as a question and embeds the
*expected answer* (first-token hidden states over generated answers, stopwords
stripped, mean answer 2.89 tokens) after fine-tuning only on ~200k abstractive QA
triplets; beats concatenation-style instruction embedders on instruction-awareness and
robustness tests. MelodyScribe takeaway: an alternative harness design worth one Spike
007 arm — instead of pooling the [EMB] marker over the section, pool over a short
generated answer to a fixed per-task question. Caution: requires a generative forward
pass *plus* answer pooling, which conflicts with the one-forward-pass budget.

**bge-en-icl (2409.15700).** Trains the embedder with 0–5 randomly sampled in-context
query–passage examples prepended to queries (few-shot 71.67 vs zero-shot 71.24 MTEB;
plain ICL on a conventionally tuned embedder *hurts*, cf. GritLM). MelodyScribe
takeaway: few-shot examples are viable query-side augmentation, but only with dedicated
random-count training; do not paste examples into prompts of a conventionally tuned
model. Caution: document-side stays bare and examples inflate query length — account
KV cost in Spike 009.

**TART / BERRI (2211.09260).** ~40 retrieval datasets with ~3.5 expert instructions each;
dual-encoder score s(t,q,d) = E([t;q])ᵀE(d) — again query-side-only instructions with
documents encoded bare — plus instruction-unfollowing negatives, a precursor of
Promptriever's recipe. MelodyScribe takeaway: independent confirmation of the one-sided
prefix plus instruction-negative pattern from 2022. Caution: base scale is 110M
Contriever-era; absolute numbers are stale, only the pattern transfers.

**PromptBERT (2201.04337).** Prompt templates with *template denoising* (subtract the
template-only bias vector) gain +2.29/+2.58 over SimCSE unsupervised on BERT/RoBERTa.
MelodyScribe takeaway: any fixed marker/prefix ([EMB], instructions) injects a
template bias into the state — measure the marker-only state and subtract or center it
as a cheap anisotropy/offset control in Spike 007. Caution: encoder/[MASK] machinery;
the principle transfers, the code does not.

**Gecko (2403.20327).** Two-step LLM distillation (generate task+query pairs, then
LLM-relabel retrieved positives/hard negatives into FRet): 256-dim Gecko beats all
768-dim entries, 768-dim reaches 66.31 MTEB, matching 7x-larger models.
MelodyScribe takeaway: the strongest evidence that *task-description generation plus
LLM-judged negatives* — both prompt-design artifacts — drive small-model quality;
FRet-style synthesis is the data recipe for the 16 GB-GPU training plan. Caution: no
open repo URL was located in the opened pages, so reproducibility rests on the paper
alone.

**mE5-large-instruct (2402.05672).** 150k unique synthetic instructions across 93
languages lift English MTEB 61.5 to 64.4 at fixed encoder size. MelodyScribe takeaway:
instruction *diversity* (150k distinct) matters more than instruction length — generate
a large paraphrase pool for Score section-type prefixes rather than hand-tuning one.
Caution: encoder backbone; diversity effect size on decoders is unmeasured.

**Instruction sensitivity (2605.22544).** 6 models (≤0.6B), 11 datasets, 15 prompts each:
single-prompt scores misrepresent the plausible-prompt distribution in both directions,
and any model can be ranked first under favorable prompt selection. MelodyScribe
takeaway: Spike 007 must report distributions over prompt paraphrases, never a single
prompt's MRR — and the harness should pin exact instruction strings in versioned
config, since wording is a silent quality variable. Caution: 2026 preprint, small-model
scope only; sensitivity profile of 7B+ instruction embedders may differ.

**Linq-Embed-Mistral (2412.03223).** E5-Mistral fine-tune to 68.2 MTEB / 60.2 retrieval
with task-tailored data crafting; explicitly documents the E5-style one-sided prefix as
a *serving* decision (documents encoded once, cached, reused). MelodyScribe takeaway:
third independent source for query-only instructions, with serving-cache rationale that
feeds Spike 009's prefix-caching design. Caution: vendor tech report; training data
synthesis details are coarser than E5-Mistral/NV-Embed.

## (b) Refutations

**R1 — "Instruction-tuned embedders are robust to instruction wording."** The
INSTRUCTOR project page claims robustness to paraphrase. Contradicted by 2605.22544
(rankings not robust; any model promotable to first place by prompt selection) and by
InstructIR (2402.14334), where instruction-tuned retrievers underperform non-tuned ones
on instance-wise instructions. Status: the robustness claim does not survive
instance-level evaluation.

**R2 — "Adding an instruction prefix helps (or at least never hurts)."** Qwen3's
vendor figure (+1–5%) holds only for instruction-trained models. Promptriever (2409.11136)
shows prompts *hurt* standard-trained RepLLaMA (−0.1) and BM25 (−5.0) on BEIR while
helping only the instruction-negative-trained model (+1.4); FollowIR (2403.15246) shows
near-zero instruction sensitivity for standard retrievers. Status: an instruction prefix
on an untrained model is as likely to hurt as to help — Spike 007's zero-shot arms must
include a no-instruction control.

**R3 — "Document-side prefixes are needed for task conditioning."** E5-Mistral,
NV-Embed, TART, and Linq-Embed-Mistral all independently converge on bare documents with
instructions query-side only (NV-Embed additionally masks instruction tokens from
pooling). Status: any harness design prefixing stored sections can drop the document
prefix with precedent — and should, for index reuse.

## (c) Unresolved ledger

- **Chat-template effects on embedding quality.** No study found isolating chat-template
  wrappers (`<|im_start|>` etc.) versus raw concatenation; Qwen3 uses them, E5-Mistral
  does not. Reason: gap in the literature as screened.
- **Marker-token ([EMB]-style) pooling.** No paper found training or evaluating a
  dedicated marker token for decoder embeddings; closest analogues are echo templates
  and PromptBERT's [MASK] pooling. Reason: gap; Spike 007 will be primary evidence.
- **Controlled query-vs-document prefix MRR delta.** The one-sided convention is
  documented three times over but always as a design decision, never as an ablation with
  an MRR number. Reason: no ablation found.
- **Independent replication of Qwen3-Embedding's +1–5% instruction figure.**
  Vendor-reported only. Reason: single source.
- **SFR-Embedding recipe.** Frequently cited, no paper found; blog + HF card only.
  Reason: secondary sources, abstained.
- **PTEB, EPIC, KV-Embedding, ICLR-2024 robustness paper.** Screened but not verifiable
  at a primary landing page within lane budget. Reason: abstained per lane rules, see
  inventory.

## (d) Security findings

No security-relevant findings. Instruction prefixes in this lane are model *inputs*,
not executable directives; none of the screened papers describe an instruction channel
that crosses a trust boundary (no tool use, no store writes, no privilege change).
Requirement for the harness: treat Score section-type instruction strings as
versioned configuration, not as untrusted user input — pinning them avoids both silent
quality drift (per 2605.22544) and any future prompt-injection confusion between
config-authored and user-supplied instructions.
