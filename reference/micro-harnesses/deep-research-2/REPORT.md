# Deep-research round 2: how the best embedding models are built, and how MelodyScribe gets one

Integrator report. Inputs: `lanes/<n>/findings.md` and `lanes/<n>/method.md` (10 lanes),
`merged/INVENTORY.tsv` (191 unique screened candidates, 153 admitted, 38 abstained),
`merged/papers/` (150 staged PDFs). No item below comes from memory; every figure traces to a lane
finding or an inventory row, with the arXiv id or URL inline. Vendor benchmark figures are labelled
as vendor-reported throughout: they are primary only for "what the vendor reports".

Scope notes: `merged/SUMMARY.md` records 287 lane rows deduplicated to 191 unique items
(150 admitted PDFs staged). No candidate carries a `refute` disposition in the inventory;
refutations in part 3 are claim-level (a primary source contradicting a stated claim), each with
its source. Lane PDFs were verified to start with `%PDF`; most lane claims rest on verified
arXiv abs pages plus the staged PDFs, and shallow-verification limits are flagged where the lanes
flagged them (notably lane 6 title-record admits).

## 1. Verdict

**Q1 — How the best embedders are built, and what transfers to 0.3–2B on one 16 GB GPU.**
The evidence supports a two-stage recipe — large-scale weakly-supervised or synthetic
contrastive pretraining, then supervised fine-tuning on high-quality triplets — with an
InfoNCE-family objective, in-batch plus mined hard negatives, explicit false-negative
handling, and instruction conditioning (E5 2212.03533; Qwen3-Embedding 2506.05176;
E5-Mistral 2401.00368). What separates the top from the middle is data curation and
negatives (ANN-mined hard negatives, ANCE 2007.00808; LLM relabelling of positives and
hard negatives, Gecko 2403.20327; consistency filtering, InPars 2202.05144), learned
pooling over last-token readout (latent attention, NV-Embed 2405.17428), and nested
training for serving-time truncation (MRL 2205.13147). What transfers to one 16 GB GPU:
synthetic-only pair generation plus a short contrastive run under 1k steps (E5-Mistral
2401.00368), adapter training on a frozen 4-bit base (LLM2Vec 2404.05961; QLoRA
2305.14314), cross-batch negatives to simulate large batches (RocketQA 2010.08191), and
the sentence-transformers stack for experimentation (huggingface/sentence-transformers).
Sub-0.5B models are competitive on retrieval when the data recipe is right (Arctic-Embed
2405.05374; Qwen3-Embedding-0.6B 2506.05176; EmbeddingGemma-300M 2509.20354).

**Q2 — Can one small generative model host a competitive embedder, and what does the
generative side lose?** Yes, conditionally. GritLM (2402.09906) proves instruction-switched
joint generative-plus-embedding training matches single-mode training with no loss to
either side — but at 7B with full joint training, not at 0.3–2B. The cheap routes Spike 006
should test are: a frozen generative base plus a retrieval-only LoRA toggled at inference
(LLM2Vec 2404.05961; Hydra 2603.28554, which reports all base tensors byte-identical with
the adapter off), unsupervised special-token compression needing no pairs (LLM2Vec-Gen
2603.10913 — the direct answer to Spike 004's missing-pairs blocker), and fine-tune-then-
merge-home with TIES/DARE plus LM-Cocktail rebalancing (2306.01708; 2311.03099; 2311.13534).
Measured generation degradation at small scale is the gap: the Embedder's Dilemma
(2608.12875) finds LLM–embedder parity only in aggregate and at substantially higher cost,
with embedders still winning classification. The closest existing system to the whole
thesis is GritLM (unified weights, instruction switching) combined with a KGGen-style
(2502.09956) extraction pipeline; what it lacks is proof below 7B, a grammar-constrained
op-emission head with a mechanical validator, KV-cache-compatible attention under
bidirectional conversion, and any 16 GB serving numbers.

**Q3 — Does the prompt change the embedding, and how should the marker be designed?**
Yes, measurably: vendor-reported +1–5% for instructions over no instructions (Qwen3-Embedding
2506.05176), +5% zero-shot for echo repetition (2402.15449), +3.4% for task prefixes
(INSTRUCTOR 2212.09741), +14.3 p-MRR with instruction negatives (Promptriever 2409.11136),
+6.73% for averaged meta-task prompts (MetaEOL 2402.18458). The supported design is:
instructions on the query side only, documents encoded bare so the index is built once
(E5-Mistral 2401.00368; NV-Embed 2405.17428; TART 2211.09260; Linq-Embed-Mistral 2412.03223);
instruction tokens masked out of the pooled output while still shaping states through
attention (NV-Embed 2405.17428) — the rule to copy for the `[EMB]` marker; template-bias
subtraction for any fixed marker (PromptBERT 2201.04337); and pinned, versioned instruction
strings, because single-prompt scores misrepresent the prompt distribution and rankings are
gameable by prompt selection (2605.22544). Caution: on an untrained model a prefix can hurt
rather than help (Promptriever 2409.11136; FollowIR 2403.15246), so Spike 007 needs a
no-instruction control.

**Q4 — What prompt is best for graph extraction with small models?** Schema-as-code
annotation guidelines with definitions (GoLLIE 2310.03668), two-step entities-then-relations
over one-step emission (KGGen 2502.09956; iText2KG 2409.03284), open extraction followed by
post-hoc canonicalization instead of stuffing the schema into the prompt (EDC 2404.03868),
a cheap filter-after-extract pass mapping onto Proof's evidence check (HippoRAG 2 2502.14802),
marker-token copy plus self-verification for verbatim spans (GPT-NER 2304.10428), and
constraints in the decoder rather than the prompt (GenIE 2112.08340; XGrammar 2411.15100)
— with the BoostCD warning (2506.14901) that constrained decoding alone substitutes
wrong-but-valid entities, so syntax enforcement and semantic verification are
non-substitutable layers. Accuracy is a training result: distill a frontier teacher on broad
unlabeled text (UniversalNER 2308.03279), synthesize in the easy reverse direction
(SynthIE 2303.04132), confirm Spike 003's flat-before-fine-tuning reading (Han et al.
2305.14450; GoLLIE 2310.03668). The closest pipeline is KGGen; what it lacks is small-model
extraction numbers, date normalisation, and verbatim-quote adherence rates.

**Q5 — How to serve thousands of parallel small-model workers on one GPU with maximal KV
sharing?** Continuous batching plus paged KV blocks is the substrate (Orca, OSDI 2022,
doi:10.5555/3542929.3542970; PagedAttention 2309.06180); place the entire human-authored
skill and schema first in every prompt so one hash chain covers all workers (vLLM automatic
prefix caching, docs.vllm.ai); prefer a radix-tree KV layer when the shared unit is a
forked program (SGLang/RadixAttention 2312.07104); schedule by shared prefix with
decode-ratio-first reordering for offline batches (BatchLLM 2412.03594; Preble 2407.00023);
chunk prefills so long sections never stall decodes (SARATHI 2308.16369; Sarathi-Serve
2403.02310); reuse non-prefix chunks with selective recompute when order varies
(CacheBlend 2405.16444); consider frozen-head or no-retraining speculative drafting
(Medusa 2401.10774; EAGLE-2 2406.16858) only after measuring acceptance under
grammar-constrained decoding. Hard limit: every throughput multiple above was measured on
datacenter GPUs with 7B+ models; no primary source reports 0.3–2B concurrency on a 16 GB
card, so Spike 009 is primary evidence, not replication.

**Q6 — How to order the harness pieces, and what do pipelines do at scale?** The supported
order is extract-offline, embed everything (chunks and triples), dense-seed, graph-walk,
LLM-filter (HippoRAG 2 2502.14802); never run an LLM reasoning loop per query on the serving
path (IRCoT 2212.10509 is the cost baseline HippoRAG beats 10–30x). Incremental updates are
union-merge, never rebuild (LightRAG 2410.05779); idempotency is content-hash chunk keys
(nano-graphrag, https://github.com/gusye1234/nano-graphrag); resolution is clustering after
extraction, not during (KGGen 2502.09956), with definition-then-LLM-verify as the precision
guard (EDC 2404.03868); communities are Leiden, not Louvain (1810.08473); streaming is
episode-first with invalidate-don't-delete bi-temporal edges (Zep/Graphiti 2501.13956);
retrieval payloads place the strongest evidence last (PathRAG 2502.14902). Retrieval is HNSW
by default (1603.09320) with an IVF fallback armed (ANN-Benchmarks 1807.05614), a sparse arm
that still wins zero-shot (SPLADEv2 2109.10086; BGE-M3 2402.03216), Matryoshka truncation at
query time (2205.13147), anisotropic quantization for MIPS storage (1908.10396), and a
distilled 0.3–1B reranker with ranking losses (MiniLM 2002.10957; RankT5 2210.10634).
The gap: no primary source reports documents-per-hour with hardware for any extraction
pipeline, and no paper measures incremental index-update costs — Spike 010 owns both numbers.

## 2. Top twenty

Ranked by leverage for MelodyScribe (size-band fit × transferability to the rig × cost of
being wrong). Each entry: what it is, what to take, what to be careful about.

1. **GritLM (2402.09906).** Joint generative-plus-embedding training of one LLM switched
by instruction; GritLM 7B set open-model MTEB SOTA while matching generative baselines,
with joint training matching single-mode training (repo ContextualAI/gritlm, MIT). Take:
the reference recipe for Q2 and the design authority for switching the Score pass between
embedding and op-emission by instruction/marker rather than by architecture surgery.
Careful: the no-loss claim is 7B full-training evidence; small-scale and adapter-only
confirmation is exactly Spike 006.
2. **Qwen3-Embedding (2506.05176).** 0.6B/4B/8B decoder-embedder series with unsupervised
pretraining, supervised fine-tuning on model-synthesized data, and merging; Apache-2.0,
0.6B artefact at 8.3M downloads (repo QwenLM/Qwen3-Embedding). Take: the in-band training
template and the distillation teacher/baseline for Spike 006 — copy the loss (hard negatives
plus false-negative masking), the two-stage schedule, and the synthetic-data flywheel.
Careful: the 0.6B keeps a decoder backbone (costlier than a 30M BERT), numbers are
vendor-reported, and stage costs live in the PDF, not the abstract.
3. **LLM2Vec (2404.05961).** Three-step decoder-to-encoder conversion (bidirectional
attention, masked next-token pretraining, unsupervised contrastive tuning) with a LoRA path
leaving base weights untouched; 1.3B–8B (repo McGill-NLP/llm2vec, MIT). Take: the cheapest
route to a hybrid small model — freeze the MiniCPM-class base, train only the embedding
adapter, keep generation intact by construction. Careful: bidirectional attention breaks
KV-cache reuse for the embedding pass (interacts with the serving plan), and unsupervised
contrastive tuning alone reproduces the Spike 004 anisotropy regime — supervised follow-up
is still required.
4. **E5-Mistral (2401.00368).** Decoder-only LLM fine-tuned into an embedder on synthetic
data alone in under 1k steps, no labels, across 93 languages, reaching SOTA. Take: the
minimal decoder-embedder recipe and the direct answer to Spike 004's missing-pairs problem,
plus the production-critical one-sided-prefix convention (instructions on queries, documents
bare, index built once). Careful: the pairs were GPT-4-generated (frontier-API dependency
with license/cost terms), and the headline run is 7B, not sub-2B.
5. **Gecko (2403.20327).** Two-step LLM-to-compact distillation: generate diverse synthetic
pairs, then retrieve candidates and LLM-relabel positives and hard negatives into a 1.2B
(and 256-dim) retriever at 66.31 MTEB. Take: the generate-then-relabel pattern plus
MRL-style short vectors is the quality-per-byte winner and the data recipe for the 16 GB
training plan (FRet-style synthesis). Careful: no public weights or training code — distill
the method, not the model — and relabelling doubles LLM API cost.
6. **NV-Embed (2405.17428).** Mistral-7B embedder with latent-attention pooling (beats mean
and last-token pooling 69.32 to 68.98 in ablation), causal mask removed for contrastive
training, two-stage instruction tuning; MTEB 69.32. Take: the pooling verdict — do not
default to last-token — plus the masking rule (instruction tokens shape states but are
excluded from pooling) to copy for `[EMB]`. Careful: no public training repo (paper-only
recipe), added pooler parameters to train, and released weights are CC-BY-NC-4.0
(non-commercial — do not ship).
7. **OneGen (2409.05152).** Retrieval tokens and generation tokens emitted in one forward
pass sharing a rollout, via retrieval-token markers; EMNLP 2024 (repo zjunlp/OneGen, MIT).
Take: the closest published analogue of MelodyScribe's one-pass section handling — copy its
training/eval setup for Spike 006. Careful: results are 7B on RAG/entity-linking, not on
graph-op emission; the marker vocabulary must be re-proven next to a grammar-constrained
op decoder.
8. **Echo embeddings (2402.15449).** Repeating the input inside the prompt gives causal-LM
tokens full context access: +5% zero-shot, nearly matching bidirectionally-converted models,
no training (repo jakespringer/echo-embeddings, Apache-2.0). Take: the no-architecture-change
fix for the causal blindness behind Spike 004's anisotropy — the floor for training-free
decoder states and the first Spike 007 arm. Careful: echo doubles sequence length and
compute; supervised fine-tuning still beats it.
9. **Promptriever (2409.11136).** Per-instance instruction training with instruction
negatives (passages relevant to the query but wrong under the instruction): +14.3 p-MRR on
FollowIR, +12.9 Robustness@10 on InstructIR, 44% lower cross-instruction variance. Take: the
recipe that makes instructions actually move retrieval is instruction negatives, not
instructions alone — any Spike 007 training phase must mine them. Careful: demonstrated on
retrieval with relevance instructions; transfer to section-type instructions is unproven.
10. **GoLLIE (2310.03668).** Code-LLaMA models fine-tuned to follow annotation guidelines
rendered as Python classes with docstrings, generalizing to unseen schemas; detailed
guidelines, not label names, carry the gain (repo hitz-zentroa/GoLLIE, Apache-2.0). Take:
the most transferable extraction-prompt discovery — schema-as-code — and the mandate that
guideline-following be fine-tuned in, since even large models fail at it out of the box.
Careful: checkpoints are 7B–34B (too large for the harness); distill the pattern with
anti-memorization noise, not the weights.
11. **EDC (2404.03868).** Extract-Define-Canonicalize: few-shot open extraction with no
schema in the prompt, then relation definitions, then post-hoc canonicalization with a
trained schema retriever (repo clear-nus/edc, MIT). Take: the ordering insight — keep the
op vocabulary in Proof/grammar, not in the prompt — plus the schema-retriever fallback if
the vocabulary outgrows context. Careful: refinement iterations multiply per-section cost;
shipped code canonicalizes relations only.
12. **KGGen (2502.09956).** Two-stage DSPy extraction (entities, then relations given text
plus entities) with iterative LM clustering for resolution, plus the MINE fidelity benchmark
(repo stair-lab/kg-gen). Take: the stage-two template (entities-then-relations beats one-step)
and the concrete cross-worker resolution recipe — cluster after extraction — with the
sparsity-vs-length scaling test as MelodyScribe's merge acceptance test. Careful: reference
numbers use Gemini 2.0 Flash (needs a small-model rerun in Spike 008); MINE measures
retention, not triple F1.
13. **BoostCD (2506.14901).** Boosted fusion of constrained and unconstrained decoding
drafts; documents that constrained-only decoding corrupts entities (wrong-but-valid
substitutions) while fixing formatting. Take: the error model for grammar-constrained ops —
syntax enforcement and semantic verification are non-substitutable layers — justifying
Proof's evidence-quote and date checks plus keeping the unconstrained draft as cross-check
signal. Careful: the booster is a second trained model (second forward pass); use
diagnostically unless serving allows two passes.
14. **Matryoshka Representation Learning (2205.13147).** Nested coarse-to-fine vectors
truncatable at query time with no retraining: up to 14x smaller embeddings, 14x retrieval
speedups (repo RAIVNLab/MRL, MIT). Take: the highest-leverage storage/QPS trick — train
once at full width, serve truncated widths per latency budget — and combine with
anisotropic quantization (1908.10396) for compressed MIPS storage. Careful: the
quality-vs-dims curve is model- and task-dependent; calibrate truncation on the private
eval, since MRL does not fix anisotropy by itself.
15. **ANCE (2007.00808).** Async-refreshed ANN index mining corpus-representative hard
negatives during training, fixing the train/test mismatch of in-batch sampling (repo
microsoft/ANCE, MIT). Take: the single highest-leverage change over DPR-style sampling —
refresh the negative index during MelodyScribe trainer runs — plus cross-batch negatives
(RocketQA 2010.08191) and false-negative filtering for the 16 GB batch limit. Careful:
async refresh is real infra (periodic corpus re-encoding) that a 20-document rig does not
need but a real corpus does.
16. **BGE-M3 (2402.03216).** One model serving dense, multi-vector, and sparse retrieval
over 100+ languages and 8k tokens via self-knowledge distillation across heads (repo
FlagOpen/FlagEmbedding, 12153 stars, MIT; BAAI/bge-m3 weights, MIT). Take: the existence
proof that one backbone hosts all three retrieval functions with cross-head distillation,
plus the native 8k-context design for long Score sections. Careful: three heads mean three
index paths to serve; verify each head helps before adopting all three.
17. **vLLM / PagedAttention (2309.06180; docs.vllm.ai).** OS-paged KV-cache blocks with
near-zero fragmentation and hash-chained automatic prefix caching (`enable_prefix_caching`,
`cache_salt` tenant isolation); 2–4x over prior serving. Take: the serving substrate for
the harness decoder — hundreds of section-workers coexisting in 16 GB — with the
skill-plus-schema-first ordering rule so one hash chain covers all workers. Careful:
identical-prefix blocks only; per-section tokens placed before the shared region break the
chain, and sections differ per document, so sharing comes from the skill prompt.
18. **SGLang / RadixAttention (2312.07104).** Radix tree over KV pages reusing shared
prefixes across forked programs with a cache-aware scheduler and compressed-FSM structured
decode; up to 6.4x on agentic/structured workloads. Take: the closest serving analogue of
MelodyScribe (one skill, many forked section calls) — prefer it when the shared unit is a
program, and standardise on its FlashInfer kernel substrate (2501.01005) including the
shared-prefix path. Careful: tree management pays off only with deep shared prefixes.
19. **BatchLLM (2412.03594).** Offline-batch serving with a global prefix tree, prefix-group
scheduling, and decode-ratio-first reordering; 1.3–10.8x over vLLM/SGLang (MLSys 2026).
Take: the Spike 009/010 recipe — sort section jobs by shared prefix, schedule
high-decode-ratio groups first, batch by memory-centric token budgets. Careful: newest item
here (v3 April 2026); re-verify against the MLSys version before depending on multiples.
20. **HippoRAG 2 (2502.14802).** OpenIE KG with passage nodes, embedding-seeded
Personalized PageRank, and an online LLM triple filter; +7% associative over the best
embedder (repo OSU-NLP-Group/HippoRAG, MIT). Take: the stage-ordering answer for Q6 —
embeddings serve retrieval (seed PPR), not indexing — and the filter-after-extract pattern
for Proof. Careful: reference runs use 70B-class extraction; the pattern transfers, the
scores do not, and the online filter is a per-query LLM call to budget.

## 3. Refutations

Every entry is a claim in our working vocabulary contradicted (or qualified) by a primary
source the lanes verified. Vendor tables are cited only for "what the vendor reports".

1. "One architecture is best at everything." Refuted by MTEB (2210.07316): "no particular
text embedding method dominates across all tasks."
2. "A decoder must be made bidirectional to embed well." Challenged by echo embeddings
(2402.15449): repetition matches bidirectionally-converted models with no architecture change.
3. "One model cannot embed and generate without losing something." Refuted at 7B by GritLM
(2402.09906): joint GRIT training "matches training on only generative or embedding data."
Small-scale confirmation is still open (Spike 006).
4. "Last-token state is an adequate embedding readout." Challenged by NV-Embed (2405.17428):
latent-attention pooling "consistently improves" over mean and last-`<EOS>` pooling. Supports
the Spike 004 suspicion that the untrained last-token state, not the hidden size, is the problem.
5. "In-batch negatives are sufficient." Refuted by ANCE (2007.00808): training negatives must
represent test-time irrelevants; ANN-mined hard negatives close the gap.
6. "A better teacher always distills a better student." Refuted by PROD (2209.13335): the
teacher–student capacity gap means a stronger teacher can yield a worse student; progression
(teacher first mid-size, or progressive signal) is required. Calibrates Spike 006 expectations
when distilling Qwen3-scale teachers into a 0.6B student.
7. "Top embedders require billion-pair weak-supervision pipelines." Qualified by E5-Mistral
(2401.00368): synthetic-only data with under 1k contrastive steps reaches SOTA (with a
frontier-API dependency replacing the crawl cost).
8. "LLM embedders require full fine-tuning." Qualified by LLM2Vec (2404.05961, LoRA-compatible
conversion) and QLoRA (2305.14314, 4-bit plus adapters at 16-bit quality): adapter training
suffices, which is what fits 16 GB.
9. "Contrastive training is blocked for lack of labelled query–passage pairs" (Spike 004
rationale). Refuted by E5-Mistral (2401.00368, purely synthetic data) and Gecko (2403.20327,
LLM generate-then-relabel): synthetic pairs are the established substitute; the blocker is
generator diversity and filtering, not labels.
10. "2506.07900 is the MiniCPM embedding reference." Refuted by the primary source: 2506.07900
is MiniCPM4, an efficient end-side generative LLM, not an embedding paper. MiniCPM-Embedding
(OpenBMB, Apache-2.0) links no paper on its verified HF card. Do not cite 2506.07900 as an
embedding recipe.
11. "Instruction-tuned embedders are robust to instruction wording." Contradicted by the
instruction-sensitivity study (2605.22544: any model promotable to first place by prompt
selection) and InstructIR (2402.14334: task-instruction-tuned retrievers underperform
non-tuned ones on instance-wise instructions).
12. "Adding an instruction prefix helps (or at least never hurts)." Contradicted by
Promptriever (2409.11136: prompts hurt standard-trained RepLLaMA −0.1 and BM25 −5.0 on BEIR
while helping only the instruction-negative-trained model +1.4) and FollowIR (2403.15246:
near-zero instruction sensitivity for standard retrievers).
13. "Document-side prefixes are needed for task conditioning." Contradicted by four
independent convergences on bare documents with query-side-only instructions: E5-Mistral
(2401.00368), NV-Embed (2405.17428), TART (2211.09260), Linq-Embed-Mistral (2412.03223).
14. "Raw cosine of an untrained decoder state is a fair untrained-embedder baseline."
Refuted in combination by Ethayarajh (1909.00512), BERT-flow (2011.05864), and Representation
Degeneration (1907.12009): likelihood-trained geometry is anisotropic, so raw cosine confounds
representation quality with cone effects. Spike 004's 0.31 gap is uninterpretable without a
whitened/centred control (Whitening 2103.15316; ABTT 1702.01417).
15. "No linear head helps" (over-reading of Spike 004's ridge result). Qualified refutation:
the ridge head was supervised on tiny data, while Whitening (2103.15316) and ABTT (1702.01417)
show unsupervised linear repairs help. "Supervised ridge on 20 documents helps" stands;
"no linear repair helps" is contradicted.
16. "Naive cross-dataset averaging ranks models reliably." Refuted by Brewing BEIR
(2306.07471): collapsing heterogeneous BEIR scores into one average is hard to interpret;
per-dataset effect sizes are the sound comparison.
17. "Evaluation requires human labels at scale." Refuted in its strong form by AIR-Bench
(2412.13102, automated benchmarks) together with ARES (2311.09476, synthetic judgments plus
human-anchored intervals): a small human audit calibrates synthetic labels.
18. "A grammar constraint makes extraction output trustworthy." Contradicted by BoostCD
(2506.14901): constrained-only decoding substitutes wrong-but-schema-valid entities. Syntax
enforcement (XGrammar 2411.15100; GenIE 2112.08340) and semantic verification (evidence
quotes, date checks in Proof) are non-substitutable layers.
19. "Prompting a frontier model suffices for extraction quality." Contradicted by Han et al.
(2305.14450: GPT-4 shows a visible gap to supervised SOTA across 14 IE subtasks) and GoLLIE
(2310.03668: even the largest models fail to follow annotation guidelines out of the box).
Corroborates Spike 003 ("accuracy is a training result").
20. "The schema must be in the extraction prompt." Contradicted by EDC (2404.03868): open
extraction plus post-hoc canonicalization handles schemas larger than the context window.
21. "Triplex is citable literature." No primary publication found: Triplex is a vendor
Phi-3-3.8B finetune (SciPhi, Hugging Face `SciPhi/Triplex`, blog/cookbook secondaries).
Its "beats GPT-4 at 1/60th cost" is vendor-reported and unverified.
22. "A graph index (HNSW) is the safe default everywhere." Qualified by ANN-Benchmarks
(1807.05614): on Rand-Euclidean, HNSW/SWG fail where PANNG/KGraph/NND succeed, and graph
builds are slow on hard query sets. Default HNSW with an IVF fallback armed.
23. "Compression/truncation of embeddings is approximately free." Refuted in detail by
ColBERTv2 (2112.01488): 1-bit codes cost 36.2% → 35.5% MRR@10 even with residual centroids;
naive binarization without centroids is worse (34.8%). Truncation needs nested MRL training
(2205.13147), not slicing.
24. "Dense first-stage retrieval has made sparse signals redundant." Contradicted by SPLADEv2
(2109.10086: distilled sparse "clearly outperforming recent dense models on zero-shot
evaluation") and BGE-M3 (2402.03216, whose cross-functionality distillation exists because
each arm contributes). Keep a sparse arm.
25. "Orca can be cited by arXiv id." It cannot: Orca (OSDI 2022) has no arXiv id (verified);
cite the USENIX page/DOI (doi:10.5555/3542929.3542970). Four recalled ids in lane 4 (DARE,
LM-Cocktail, RepLLaMA, LLaRA) and several in lanes 1/6/8 similarly resolved to unrelated
papers at their abs pages; the corrected DARE paper is 2311.03099 and LM-Cocktail is
2311.13534, both verified. RepLLaMA's and LLaRA's correct ids remain unestablished.

## 4. Per-lane findings

Lane scopes follow BRIEF.md section 3. Counts in headings are unique-inventory rows that list
the lane (cross-listed items appear under each lane once in the merged inventory but are
tabled under every lane they serve; per-lane screened/admitted minimums — 20/8 — are met in
all ten lanes; see part 10). One-line descriptions are the lanes' verified summaries.

### Lane 1 — Embedding model architectures (screened 24, see part 10)

Bi-encoders from encoders and decoders, pooling, bidirectional conversion, Matryoshka,
multi-vector late interaction, learned sparse, inference cost, and which architectures top
MTEB/MMTEB/BEIR. Core result: no architecture dominates all tasks (MTEB 2210.07316); the
decoder-embedder path runs through last-token pooling (E5-Mistral 2401.00368), echo
repetition as the training-free floor (2402.15449), bidirectional conversion plus MNTP
(LLM2Vec 2404.05961), or learned latent pooling (NV-Embed 2405.17428); multi-vector and
sparse arms (ColBERT 2004.12832; ColBERTv2 2112.01488; SPLADEv2 2109.10086) and Matryoshka
truncation (2205.13147) complete the serving picture; GritLM (2402.09906) is the unification
precedent and Qwen3-Embedding (2506.05176) the in-band recipe.

Admitted in lane 1 (19 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | 2007.00808 | Async-refreshed ANN index mines corpus-representative hard negatives during training. |
| ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | 2004.12832 | Token-level late-interaction (MaxSim) over BERT encodings; per-pair NN cost avoided. |
| ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction | 2112.01488 | Residual compression plus denoised supervision shrinking late-interaction footprint. |
| Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. |
| Generative Representational Instruction Tuning | 2402.09906 | Instruction-switched joint generative+embedding training at no loss to either. |
| Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. |
| M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | 2402.03216 | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. |
| MMTEB: Massive Multilingual Text Embedding Benchmark | 2502.13595 | 500+ tasks, 250+ languages; LLM-embedders lead some languages, not uniformly. |
| MTEB: Massive Text Embedding Benchmark | 2210.07316 | 58 datasets x 8 tasks; no single method dominates all tasks. |
| Matryoshka Representation Learning | 2205.13147 | Nested coarse-to-fine representation; truncate dims at query time, no retraining. |
| NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling beats mean/last-token; causal mask removed for contrastive train; 2-stage instruction tuning. |
| Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 |
| Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. |
| Repetition Improves Language Model Embeddings | 2402.15449 | Repeat-input prompting gives causal LMs bidirectional-like embeddings, +5% zero-shot, no training. |
| SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval | 2109.10086 | MLM-head sparse expansion with FLOPS regularization; inverted-index retrieval. |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| C-Pack: Packed Resources For General Chinese Embeddings | 2309.07597 | BGE-family training resources: data, small-model baselines, C-MTEB evaluation |

Not admitted in lane 1 (5):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| Jina Embeddings 2: 8192-Token General-Purpose Text Embeddings for Long Documents | 2310.19923 | Verified; long-doc architecture relevant but BGE-M3 covers 8k context among admits. |
| Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference | 2412.13663 | Verified; efficient-encoder counterpoint, but no head-to-head vs decoder-embedders fetched; thin for verdict. |
| Analysis of Local Anisotropy Fluctuations in Compact Objects | 2310.01730 | Wrong id from memory; GTE-line coverage deferred to Qwen3-Embedding row (successor series). |
| Multi-view Intent Learning and Alignment with Large Language Models for Session-based Recommendation | 2402.13840 | Wrong id from memory; correct echo-embeddings id resolved separately (2402.15449). |
| When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset | 2104.08671 | Wrong id from memory; correct BEIR paper id not resolved. BEIR coverage deferred to MTEB/MMTEB rows. |

Unresolved ledger (lane 1): current MTEB/MMTEB/BEIR top-table numbers not fetched (no
leaderboard or Papers-with-Code page opened; all figures are vendor-reported abstracts) —
leaderboard scraping is open work. BEIR and GTE paper ids unresolved after recalled ids
fetched as unrelated papers (2104.08671 = law pretraining; 2310.01730 = compact-object
physics; 2402.13840 = session recommendation). Per-architecture inference-cost numbers
(FLOPs, latency, bytes/vector) not extracted — abstracts rarely carry them; the staged PDFs
contain them. NV-Embed training code not found (weights-only posture); Qwen3-Embedding repo
license field returned null via API. ANCE (2007.00808), ModernBERT (2412.13663), Nomic
(2402.01613), Jina-v2 (2310.19923), C-Pack (2309.07597) abs-verified but not admitted
(training-recipe scope, deprioritized, or subsumed — see inventory reasons).

### Lane 2 — Training recipes for embedders (screened 29)

Contrastive objectives, negatives, false-negative handling, two-stage pretraining then
fine-tuning, synthetic query generation, instruction tuning, single-16GB-GPU fit. Core
result: the E5 two-stage shape (weak pretrain → supervised finetune, 2212.03533) with
ANN-mined negatives (ANCE 2007.00808), cross-batch sharing (RocketQA 2010.08191),
false-negative filtering, synthetic-only short runs (E5-Mistral 2401.00368; Promptagator
2209.11755; InPars 2202.05144), label-free domain adaptation (GPL 2112.07577), LLM
relabeling distillation (Gecko 2403.20327), balanced sampling plus MarginMSE into a small
student (TAS-B 2104.06967), progressive distillation across the capacity gap (PROD
2209.13335), and QLoRA/LoRA fitting 1–10B training into 16 GB (2305.14314).

Admitted in lane 2 (21 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | 2007.00808 | Async-refreshed ANN index mines corpus-representative hard negatives during training. |
| Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models | 2405.05374 | Efficiency-first recipe: data filtering and long-context handling; 22M to 334M models, SOTA-for-size on MTEB Retrieval. |
| Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. |
| Efficiently Teaching an Effective Dense Retriever with Balanced Topic Aware Sampling | 2104.06967 | Topic-aware balanced sampling plus MarginMSE distillation from cross-encoder into 6-layer DistilBERT. |
| GPL: Generative Pseudo Labeling for Unsupervised Domain Adaptation of Dense Retrieval | 2112.07577 | Query generation plus cross-encoder pseudo-labels plus hard negatives for label-free domain adaptation. |
| Gecko: Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. |
| Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| InPars: Data Augmentation for Information Retrieval using Large Language Models | 2202.05144 | GPT-3 generated synthetic queries per document with consistency filtering, then standard finetune. |
| LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. |
| M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | 2402.03216 | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. |
| NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling beats mean/last-token; causal mask removed for contrastive train; 2-stage instruction tuning. |
| Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 |
| Promptagator: Few-shot Dense Retrieval From 8 Examples | 2209.11755 | Few-shot prompted LLM writes per-task synthetic queries, then task-specific dual-encoder training. |
| QLoRA: Efficient Finetuning of Quantized LLMs | 2305.14314 | Frozen 4-bit base with LoRA adapters; 65B fine-tunable on one 48GB GPU at full 16-bit quality. |
| Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. |
| RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering | 2010.08191 | Cross-batch negatives, denoised hard negatives, and data augmentation for dual-encoders. |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| SimCSE: Simple Contrastive Learning of Sentence Embeddings | 2104.08821 | Dropout-as-augmentation unsupervised positives; supervised NLI entailment/contradiction variant. |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| Unsupervised Dense Information Retrieval with Contrastive Learning | 2112.09118 | Unsupervised contrastive pretraining with ICT and cropping augmentations. |
| PROD: Progressive Distillation for Dense Retrieval | 2209.13335 | Teacher-progressive distillation bridging the teacher-student capacity gap. |

Not admitted in lane 2 (8):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| Document Expansion by Query Prediction | 1904.08375 | Abs verified at primary source; mechanism covered by admitted synthetic-data items (Promptagator, InPars, GPL, E5-Mistral). |
| LoRA: Low-Rank Adaptation of Large Language Models | 2106.09685 | Abs verified at primary source; covered via admitted QLoRA which builds on it. |
| Representation Learning with Contrastive Predictive Coding | 1807.03748 | Abs verified at primary source; objective background only, no training recipe per se. |
| Towards General Text Embeddings with Multi-stage Contrastive Learning | 2308.03281 | Verified relevant via arXiv API; deprioritized under lane budget, subsumed by admitted two-stage items (E5, Qwen3-Embedding). |
| AnglE-optimized Text Embeddings | 2309.12871 | Verified relevant via arXiv API; objective variant, deprioritized under lane budget. |
| BiXSE: Improving Dense Retrieval via Probabilistic Graded Relevance Distillation | 2508.06781 | Screened via arXiv API title search only; abs page not opened under lane budget. |
| Curriculum Learning for Dense Retrieval Distillation | 2204.13679 | Screened via arXiv API title search only; abs page not opened under lane budget. |
| Pairwise Relevance Distillation for Dense Retrieval | 2410.01383 | Screened via arXiv API title search only; abs page not opened under lane budget. |

Unresolved ledger (lane 2): GTE (2308.03281), Nomic-Embed (2402.01613), AnglE (2309.12871)
verified relevant but budget-deprioritized/subsumed. Doc2Query (1904.08375), LoRA
(2106.09685), InfoNCE/CPC (1807.03748) abs-verified but background-only. PairDistill
(2410.01383), CL-Distill (2204.13679), BiXSE (2508.06781) title-search-only, abs pages
unopened. Per-stage compute (GPU-hours, batch sizes, temperatures, steps) for Qwen3/BGE-M3/
NV-Embed/Gecko/Arctic not extracted — abstracts do not carry them and no PDF text toolchain
was available in-lane; the staged PDFs are the input for that pass. Instruction-tuning
ablations belong to lane 5. Semantic Scholar chaining throttled (429); forward-chaining
incomplete.

### Lane 3 — Small embedders and distillation into them (screened 21)

Best 0.1–0.6B embedders, what made them good, distillation into small models, long-document
behaviour. Core result: Qwen3-Embedding-0.6B (2506.05176) is the in-band recipe and teacher;
Nomic (2402.01613) is the only small long-context recipe with every artefact open;
Gecko (2403.20327) is the distillation method; MRL (2205.13147) is the serving-vector
mechanism; E5-Mistral (2401.00368) answers the missing-pairs blocker; EmbeddingGemma
(2509.20354) is the closest public analogue of the one-small-model goal; Arctic
(2405.05374) is the sub-0.5B data playbook; Granite (2502.20204) sets the ~125M floor;
jina-v3 (2409.10173) demonstrates task-LoRA asymmetry (NC-licensed, do not ship).

Admitted in lane 3 (16 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models | 2405.05374 | Efficiency-first recipe: data filtering and long-context handling; 22M to 334M models, SOTA-for-size on MTEB Retrieval. |
| EmbeddingGemma: Powerful and Lightweight Text Representations | 2509.20354 | 300M decoder-derived embedder; closest public analogue to MelodyScribe one-model goal |
| Gecko: Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. |
| Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | 2402.03216 | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. |
| Matryoshka Representation Learning | 2205.13147 | Nested coarse-to-fine representation; truncate dims at query time, no retraining. |
| Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 |
| Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| jina-embeddings-v3: Multilingual Embeddings With Task LoRA | 2409.10173 | 570M multilingual model with task-specific LoRA adapters; long-context retrieval |
| mergekit: tools for merging pretrained large language models | n/a | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with its generative base. |
| C-Pack: Packed Resources For General Chinese Embeddings | 2309.07597 | BGE-family training resources: data, small-model baselines, C-MTEB evaluation |
| Embedding And Clustering Your Data Can Improve Contrastive Pretraining | 2407.18887 | Cluster-aware sampling for contrastive pretraining data; quality over quantity |
| Granite Embedding Models | 2502.20204 | 125M RoBERTa-style embedder family with enterprise retrieval focus |
| Training Sparse Mixture Of Experts Text Embedding Models | 2502.07972 | Sparse-MoE embedder: capacity without proportional inference cost |

Not admitted in lane 3 (2):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| MiniCPM-Embedding (no paper; HF model card only) | none | Verified HF card carries no paper link; method claims unverifiable. Secondary source only. |
| MiniCPM4: efficient end-side LLM | 2506.07900 | Generative base model, not an embedder; background only. |

Unresolved ledger (lane 3): MiniCPM-Embedding method — no paper, HF card only
(secondary-only). model2vec paper id unverified (repo MinishLab/model2vec verified, MIT).
GTE/Contriever ids unverified (early guesses returned zero entries; API throttled).
Per-model MTEB/BEIR numbers not re-fetched from the leaderboard (paper/abstract-reported
only; lane 6 owns evaluation). Per-stage GPU-hours mostly absent from surveyed papers.
Long-document score tables (LoCo, chunking vs 8k native) not extracted (no PDF text
tooling in-lane).

### Lane 4 — Hybrid models: one small model that embeds and generates (screened 33)

Unified training, mode-switching adapters, weight merging with the generative base, MoE
variants, measured generation degradation, single-forward-pass reuse. Core result: GRIT
joint training (GritLM 2402.09906), one-pass retrieval+generation tokens (OneGen 2409.05152),
LoRA conversion leaving the base untouched (LLM2Vec 2404.05961), unsupervised special-token
compression on unlabeled queries only (LLM2Vec-Gen 2603.10913), retrieval-inside-generation
under constrained decoding (RetroLLM 2412.11919), inference-toggled retrieval LoRA with
byte-identical base recovery (Hydra 2603.28554), MAGNET/GRC/GEM unified recipes (2501.08648;
2605.09100; 2608.13200), task arithmetic/TIES/DARE/LM-Cocktail/AIM merges (2212.04089;
2306.01708; 2311.03099; 2311.13534; 2502.02421), Model Soups floor (2203.05482), mergekit
tooling (https://github.com/arcee-ai/mergekit, LGPL-3.0), and the cost-aware parity cap
(Embedder's Dilemma 2608.12875).

Admitted in lane 4 (29 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| GRC: Unifying Reasoning-Driven Generation, Retrieval and Compression | 2605.09100 | Meta latent tokens plus unified generative/representational/compressive tuning unify generation, text representation and context compression in one forward pass. |
| Generative Representational Instruction Tuning | 2402.09906 | Instruction-switched joint generative+embedding training at no loss to either. |
| Hydra: Unifying Document Retrieval and Generation in a Single Vision-Language Model | 2603.28554 | Single LoRA trained only for retrieval is toggled at inference: on gives ColBERT-style multi-vector embeddings, off recovers base generation with 426/426 LM tensors byte-identical; the cleanest adapter-switch measurement found. |
| Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| LLM2Vec-Gen: Generative Embeddings from Large Language Models | 2603.10913 | Trainable special tokens compress the frozen LLM's own potential response into a fixed-length embedding in output space, trained on unlabeled queries only; backbone stays frozen. |
| LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. |
| MAGNET: Augmenting Generative Decoders with Representation Learning and Infilling Capabilities | 2501.08648 | Three self-supervised objectives plus a new attention mechanism adapt a decoder-only LLM to emit robust representations and infill spans while staying generative. |
| OneGen: Efficient One-Pass Unified Generation and Retrieval for LLMs | 2409.05152 | One forward pass emits retrieval tokens and generation tokens together via retrieval-token markers; single-pass RAG/EL without a separate retriever call. |
| Rethinking the Role of Token Retrieval in Multi-Vector Retrieval (XTR) | 2304.01982 | Retrieve-top-tokens objective; +2.8 nDCG@10 on BEIR; scoring stage 4000x fewer FLOPs |
| RetroLLM: Empowering Large Language Models to Retrieve Fine-grained Evidence within Generation | 2412.11919 | One LLM integrates retrieval and generation in a single process, generating fine-grained evidence from the corpus via constrained decoding; removes the separate retriever. |
| mergekit: tools for merging pretrained large language models | n/a | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with its generative base. |
| A Unified Model and Document Representation for On-Device Retrieval-Augmented Generation | 2604.14403 | Unified model+document representation so the whole RAG pipeline runs on-device for private local querying; small-model unified relevance. |
| Activation-Informed Merging of Large Language Models | 2502.02421 | AIM folds activation-space information into any merging method to preserve critical base weights; a guard against generation degradation when merging an embed-tuned model home. |
| Bagging-Based Model Merging for Robust General Text Embeddings | 2602.05787 | Systematic study of multi-task embedding training (scheduling) vs model merging for general embeddings and domain adaptation; merging as an alternative to joint training. |
| Editing Models with Task Arithmetic | 2212.04089 | Add/subtract task vectors (fine-tune minus base) to steer one set of weights toward combined behaviours without joint retraining. |
| GEM: A Generative Embedding Model Bridging Reasoning and Retrieval | 2608.13200 | One model reasons over the query in generation mode, then appends an embedding token encoding the enriched context for retrieval; evaluated on reasoning-intensive retrieval. |
| Giga-Embeddings: Mixture-of-Experts Encoders for High-Throughput Text Embeddings | 2608.23806 | Sparse 10B MoE encoder (1.8B active/token) tops its family on four MTEB suites and reports 114.5k tok/s in vLLM at 1024-token inputs; MoE embedder evidence with throughput numbers. |
| Improving General Text Embedding Model: Tackling Task Conflict and Data Imbalance through Model Merging | 2410.15035 | Joint multi-task embedding training shows task-conflict gradient interference; merging per-task models beats joint training for general embedders. |
| LLM-based Embeddings: Attention Values Encode Sentence Semantics Better Than Hidden States | 2602.01572 | Value Aggregation pools attention value vectors across layers/tokens and reportedly beats hidden-state pooling training-free; a cheap-version candidate reusing generative states. |
| LM-Cocktail: Resilient Tuning of Language Models via Model Merging | 2311.13534 | Merge a fine-tuned model back toward its base to recover general ability while keeping target-task gains; directly measures the generation side of the trade-off. |
| Language Models are Super Mario: Absorbing Abilities from Homologous Models as a Free Lunch | 2311.03099 | DARE drops most delta parameters then rescales, so merged homologous models keep abilities with no retraining or GPU; sparsified merges preserve more of each parent. |
| Merging: Resolving Interference When Merging Models | 2306.01708 | Trim low-magnitude deltas, elect per-parameter sign, merge disjoint means; reduces interference when fusing models tuned from one base. |
| SGPT: GPT Sentence Embeddings for Semantic Search | 2202.08904 | Contrastive fine-tune of GPT decoders (biased + weighted-mean pooling) for symmetric/asymmetric search; earliest proof decoders embed without architecture change. |
| The Embedder's Dilemma: LLMs Are Better, but at What Cost? | 2608.12875 | Controlled cost-aware comparison of 10 LLMs vs 26 embedding models on 37 tasks: tied in aggregate (0.4 pts), LLMs lead reasoning-heavy retrieval, embedders lead classification, parity costs more. |
| The Truth Lies Somewhere in the Middle (of the Generated Tokens) | 2605.09969 | Mean pooling across autoregressively generated tokens beats any single token as a representation (kernel-alignment evidence); generated-state pooling carries distributed semantics. |
| Embedding-based In-Context Prompt Training for Enhancing LLMs as Text Encoders | 2605.01372 | EPIC replaces discrete demonstration tokens with trained embedding-based in-context prompts to keep ICL gains for embeddings while cutting token overhead. |
| Evaluating Embedding Generalization: How LLMs, LoRA, and SLERP Shape Representational Geometry | 2511.21703 | Tests whether SLERP merging mitigates LoRA over-specialisation in embedding space; single-author study on synthetic numerical-sequence clustering/classification only. |
| Layer-wise Representation Dynamics: An Empirical Investigation Across Embedders and Base LLMs | 2605.12714 | LRD framework (subspace motion, neighbourhood retention, final-layer alignment) applied to 31 models on 30 MTEB tasks; measurement toolkit for how far an embedder drifts from its base. |
| Model soups: averaging weights of multiple fine-tuned models improves accuracy without increasing inference time | 2203.05482 | Plain weight averaging of same-base fine-tunes improves accuracy at zero inference cost; baseline every fancier merge must beat. |

Not admitted in lane 4 (4):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| A Dual-Task Paradigm to Investigate Sentence Comprehension Strategies in Language Models | 2604.26351 | Abs page opened; off-lane. Recorded so the miss is not silently dropped. |
| n/a (recalled id actually a Collatz paper) | 2304.10491 | Abs page contradicts recall. Correct RepLLaMA id not established this session. |
| n/a (recalled id actually a QCD paper) | 2311.16402 | Could not verify as merging work; abs page contradicts recall. Correct DARE paper admitted as SuperMario-DARE 2311.03099. |
| n/a (recalled id actually a phylogeny paper) | 2311.10913 | Abs page contradicts recall. Correct LM-Cocktail admitted as 2311.13534. |

Unresolved ledger (lane 4): RepLLaMA and LLaRA correct arXiv ids unestablished (recalls
resolved to unrelated papers). NV-Embed/Nomic-MoE/BGE-ICL/echo ids listed as lane-boundary
candidates for cross-check, not re-screened. BadMerging (backdoor attacks on merging,
security-relevant) surfaced late, unverified, needs its own round. Full-text figures (MTEB
deltas, generation deltas, merge coefficients, Hydra tensor counts, SLERP statistics) not
extracted — abs-page abstracts plus staged PDFs only. 2026 single-author/thin-history claims
(Hydra, SLERP-geometry 2511.21703, Attention-Values 2602.01572) carry replication risk;
Spike 006 is the check.

### Lane 5 — Prompts and instructions for embeddings (screened 25)

Instruction-following embedders, prompt-based decoder embeddings, wording sensitivity,
query- vs document-side prefixes, chat-template effects, marker tokens, measured MRR moves.
Core result: INSTRUCTOR task prefixes +3.4% (2212.09741); E5-Mistral one-sided prefix plus
short synthetic run (2401.00368); NV-Embed latent pooler and instruction masking
(2405.17428); PromptEOL one-word template (2307.16645); echo +5% (2402.15449); MetaEOL
averaging +6.73% (2402.18458); Qwen3 instructions +1–5% vendor-reported (2506.05176);
Promptriever instruction negatives +14.3 p-MRR (2409.11136); InstructIR/FollowIR
robustness metrics and overfitting warnings (2402.14334; 2403.15246); bge-en-icl few-shot
training (2409.15700); TART/BERRI query-side pattern (2211.09260); PromptBERT template
denoising (2201.04337); Gecko FRet synthesis (2403.20327); mE5 instruction diversity
61.5→64.4 (2402.05672); sensitivity distributions over paraphrases (2605.22544);
Linq-Embed-Mistral serving-cache rationale (2412.03223); InBedder answer-embedding
alternative (2402.09642).

Admitted in lane 5 (21 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| FollowIR: Evaluating and Teaching Information Retrieval Models to Follow Instructions | 2403.15246 | TREC-narrative instruction benchmark with p-MRR metric plus training data that teaches instruction following. |
| Gecko: Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. |
| Generative Representational Instruction Tuning | 2402.09906 | Instruction-switched joint generative+embedding training at no loss to either. |
| INSTRUCTIR: A Benchmark for Instruction Following of Information Retrieval Models | 2402.14334 | Instance-wise user-aligned instructions with Robustness@10 metric; instruction-tuned retrievers can underperform. |
| Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. |
| Making Text Embedders Few-Shot Learners | 2409.15700 | Train with 0-5 sampled in-context examples prepended to queries so the embedder gains few-shot ability without losing zero-shot. |
| Meta-Task Prompting Elicits Embeddings from Large Language Models | 2402.18458 | Average embeddings over eight meta-task prompts with explicit one-word limitation, no training. |
| NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling beats mean/last-token; causal mask removed for contrastive train; 2-stage instruction tuning. |
| One Embedder Any Task: Instruction-Finetuned Text Embeddings | 2212.09741 | Concatenate a natural-language task instruction to every input and contrastive-train one encoder on 330 tasks. |
| One prompt is not enough: Instruction Sensitivity Undermines Embedding Model Evaluation | 2605.22544 | Fifteen prompts per task over 6 models and 11 datasets show single-prompt scores misrepresent the distribution and rankings are gameable. |
| Promptriever: Instruction-Trained Retrievers Can Be Prompted Like Language Models | 2409.11136 | Per-instance instruction training with instruction negatives makes a bi-encoder promptable like an LM. |
| Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. |
| Repetition Improves Language Model Embeddings | 2402.15449 | Repeat-input prompting gives causal LMs bidirectional-like embeddings, +5% zero-shot, no training. |
| Scaling Sentence Embeddings with Large Language Models | 2307.16645 | The This-sentence-means-in-one-word template plus in-context demonstrations for training-free decoder embeddings. |
| Answer is All You Need: Instruction-following Text Embedding via Answering the Question | 2402.09642 | Embed the expected answer to the instruction-as-question instead of the instruction-text concatenation, trained on abstractive QA only. |
| Linq-Embed-Mistral Technical Report | 2412.03223 | E5-Mistral fine-tune with task-tailored data crafting and one-sided instruction prefixes; documents encoded once and cached. |
| Multilingual E5 Text Embeddings: A Technical Report | 2402.05672 | Instruction tuning with 150k unique synthetic instructions over 93 languages on an encoder backbone. |
| PromptBERT: Improving BERT Sentence Embeddings with Prompts | 2201.04337 | Manual and continuous prompt templates with template-denoised contrastive learning for encoder embeddings. |
| Task-aware Retrieval with Instructions | 2211.09260 | BERRI multi-task instruction tuning with query-side-only instructions and instruction-unfollowing negatives. |
| Embedding-based In-Context Prompt Training for Enhancing LLMs as Text Encoders | 2605.01372 | EPIC replaces discrete demonstration tokens with trained embedding-based in-context prompts to keep ICL gains for embeddings while cutting token overhead. |

Not admitted in lane 5 (3):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| Evaluating the Zero-Shot Robustness of Instruction-Tuned Models | https://proceedings.iclr.cc/paper_files/paper/2024/file/d3221cdb27e49d9c1cd35ad254feccfe-Paper-Conference.pdf | Proceedings PDF excerpt fetched but arXiv id and authorship not verified at a primary landing page. |
| KV-Embedding: Training-free Text Embedding via Internal KV Re-routing in Decoder-only LLMs | 2601.01046 | Seen only as a citing excerpt inside another fetched page; abs page never opened and numbers not verified. |
| SFR-Embedding-Mistral: Enhance Text Retrieval with Transfer Learning | unverified | Secondary sources only (vendor blog plus HF card fetched); no paper or primary recipe found, so nothing quotable on instruction design. |

Unresolved ledger (lane 5): chat-template effects on embedding quality — no isolating
study found. `[EMB]`-style marker-token pooling — no paper found; echo templates and
PromptBERT `[MASK]` are the closest analogues; Spike 007 is primary evidence.
Controlled query-vs-document prefix MRR ablation — documented as convention three times
over, never as an ablation with a number. Qwen3 +1–5% unreplicated (vendor-only).
SFR-Embedding recipe — blog plus HF card only, abstained. PTEB, EPIC, KV-Embedding,
ICLR-2024 robustness paper — not verifiable at a primary landing page in budget, abstained.

### Lane 6 — Evaluating "best" and fixing anisotropy (screened 32)

MTEB/MMTEB/BEIR and domain eval, private-corpus eval sets with synthetic queries,
anisotropy/isotropy fixes, fair head-to-heads, small-query metric pitfalls. Core result:
MTEB task diversity as the definition of best (2210.07316); MMTEB downsampling and
hard-negative small splits for iteration (2502.13595); BEIR generalisation gate with BM25
baseline (2104.08663); per-dataset effect sizes replacing mean scores (Brewing BEIR
2306.07471); contrastive uniformity mechanism, dropout positives needing no labels
(SimCSE 2104.08821; Alignment/Uniformity 2005.10242); whitening as the cheapest Spike 004
follow-up (2103.15316) with flow (2011.05864) and ABTT (1702.01417) controls; IsoScore as
the fix metric (2108.07344); private-corpus recipes — 8-example Promptagator (2209.11755),
InPars-v2 (2301.01820), GPL pseudo-labels (2112.07577), AIR-Bench automation (2412.13102),
ARES human-anchored intervals (2311.09476); DPR top-k protocol (2004.04906); MS MARCO
query-distribution reference with sparse-label warning (1611.09268). Several admits are
title-record-verified only (BIRCO, AIR-Bench, ABTT, Ethayarajh, RepDeg, IsoScore, E5,
Promptagator, InPars-v2, GPL, ARES, Gecko, DPR, MS MARCO) — read those PDFs before quoting
numbers.

Admitted in lane 6 (26 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| All-but-the-Top: Simple and Effective Postprocessing for Word Representations | 1702.01417 | Removes dominant common directions to repair degenerate word-embedding geometry (per title). |
| BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | 2104.08663 | 18-dataset zero-shot retrieval benchmark; BM25 robust, late-interaction/rerank best, dense often lags. |
| ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | 2004.12832 | Token-level late-interaction (MaxSim) over BERT encodings; per-pair NN cost avoided. |
| Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. |
| GPL: Generative Pseudo Labeling for Unsupervised Domain Adaptation of Dense Retrieval | 2112.07577 | Query generation plus cross-encoder pseudo-labels plus hard negatives for label-free domain adaptation. |
| Gecko: Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. |
| How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings | 1909.00512 | Compares the geometry of BERT, ELMo and GPT-2 embeddings (per title), the only admitted study covering a causal decoder. |
| InPars: Data Augmentation for Information Retrieval using Large Language Models | 2202.05144 | GPT-3 generated synthetic queries per document with consistency filtering, then standard finetune. |
| IsoScore: Measuring the Uniformity of Embedding Space Utilization | 2108.07344 | A score for how uniformly an embedding space is utilised (per title). |
| MMTEB: Massive Multilingual Text Embedding Benchmark | 2502.13595 | 500+ tasks, 250+ languages; LLM-embedders lead some languages, not uniformly. |
| MTEB: Massive Text Embedding Benchmark | 2210.07316 | 58 datasets x 8 tasks; no single method dominates all tasks. |
| On the Sentence Embeddings from Pre-trained Language Models | 2011.05864 | Diagnoses anisotropic BERT sentence space, fixes it with unsupervised normalising flows. |
| Promptagator: Few-shot Dense Retrieval From 8 Examples | 2209.11755 | Few-shot prompted LLM writes per-task synthetic queries, then task-specific dual-encoder training. |
| Representation Degeneration Problem in Training Natural Language Generation Models | 1907.12009 | Diagnoses why likelihood training degenerates token-embedding geometry (per title). |
| Resources for Brewing BEIR: Reproducible Reference Models and an Official Leaderboard | 2306.07471 | Reproducible BEIR baselines plus effect-size meta-analysis replacing naive cross-dataset averaging. |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| SimCSE: Simple Contrastive Learning of Sentence Embeddings | 2104.08821 | Dropout-as-augmentation unsupervised positives; supervised NLI entailment/contradiction variant. |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere | 2005.10242 | Contrastive loss asymptotically optimises alignment of positives plus uniformity on the hypersphere. |
| Unsupervised Dense Information Retrieval with Contrastive Learning | 2112.09118 | Unsupervised contrastive pretraining with ICT and cropping augmentations. |
| Whitening Sentence Representations for Better Semantics and Faster Retrieval | 2103.15316 | Closed-form whitening (mean-subtract + PCA-whiten + truncate) fixes anisotropy and speeds retrieval. |
| AIR-Bench: Automated Heterogeneous Information Retrieval Benchmark | 2412.13102 | Automated heterogeneous IR benchmark (per title); the closest public recipe for private-corpus eval sets. |
| ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | 2311.09476 | Automated RAG-system eval over synthetic queries and judgments (per title). |
| BIRCO: A Benchmark of Information Retrieval Tasks with Complex Objectives | 2402.14151 | Retrieval tasks with complex objectives (per title). |
| InPars-v2: Large Language Models as Efficient Dataset Generators for Information Retrieval | 2301.01820 | Efficient LLM synthetic query-generation recipe for retrieval datasets. |
| MS MARCO: A Human Generated MAchine Reading COmprehension Dataset | 1611.09268 | Large-scale human-generated queries for passage ranking and comprehension (per title). |

Not admitted in lane 6 (5):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| Document Expansion by Query Prediction | 1904.08375 | Abs verified at primary source; mechanism covered by admitted synthetic-data items (Promptagator, InPars, GPL, E5-Mistral). |
| RAGAs: Automated Evaluation of Retrieval Augmented Generation | no-arXiv-id | Could not verify at a primary source: no arXiv id, ACL Anthology page not fetched, and GitHub API was rate-limited when resolving the code repo. Secondary source only. |
| Augmented SBERT: Data Augmentation Method for Improving Bi-Encoders for Pairwise Sentence Scoring Tasks | 2010.08240 | Abs page opened for title/authors but abstract not read; abstaining regardless as training augmentation (lane 2 scope). |
| InPars-Light: Cost-Effective Unsupervised Training of Efficient Rankers | 2301.02998 | Verified at abs page but abstaining: reranker training is lane 10 scope. |
| TSDAE: Using Transformer-based Sequential Denoising Auto-Encoder for Unsupervised Sentence Embedding Learning | 2104.06979 | Verified at abs page but abstaining: training method is lane 2 scope; GPL (admitted) covers private-corpus adaptation for this lane. |

Unresolved ledger (lane 6): SBERT, ColBERT, Contriever, TSDAE, Doc2Query, AugSBERT,
InPars-v1, InPars-Light abstained as scope (other lanes) or superseded; RAGAS unverifiable
(no arXiv record; GitHub API rate-limited); SIF/Arora no arXiv record (ICLR 2017 venue via
OpenAlex, secondary); TREC DL overview unscreened (MS MARCO + BEIR cover the sparse-label
warning); rank-stability statistics for n ≤ 50 query sets not screened to a primary source
(pitfall evidenced via BEIR tiny sets plus Brewing BEIR, but no dedicated power/significance
reference verified).

### Lane 7 — Prompting small models for knowledge-graph extraction (screened 25)

Extraction prompts and pipelines of GraphRAG/LightRAG/HippoRAG/KGGen/EDC/iText2KG and the
IE literature; few-shot vs schema-only; two-step vs one-step; constrained decoding; error
analyses; prompt placement. Core result: GraphRAG one-shot-plus-gleaning (2404.16130);
LightRAG single-pass-plus-dedup (2410.05779); HippoRAG 2 filter-after-extract (2502.14802);
KGGen entities-then-relations plus clustering (2502.09956); EDC open-then-canonicalize
(2404.03868); iText2KG blueprint device (2409.03284); ChatIE decompose-before-extract
ceiling (2302.10205); GoLLIE schema-as-code (2310.03668); UniversalNER entity distillation
(2308.03279); GPT-NER markers plus self-verification (2304.10428); MiniRAG SLM-easy rule
(2501.06713); Graphiti streaming discipline (2501.13956); Text2KGBench metric split
(2308.02357); GenIE decoder constraints (2112.08340); SynthIE reverse synthesis
(2303.04132); InstructUIE instruction format plus auxiliary tasks (2304.08085); BoostCD
corruption model (2506.14901); DoG live-graph masking (2410.18415); Papaluca size-vs-prompt
study (2312.01954); Han error taxonomy (2305.14450); Carta minimal baseline (2307.01128);
XGrammar enforcement engine (2411.15100); JSONSchemaBench coverage testing (2501.10868);
UIE SEL/SSI linearization (2203.12277).

Admitted in lane 7 (25 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| An Empirical Study on Information Extraction using Large Language Models (v1: Is Information Extraction Solved by ChatGPT?) | 2305.14450 | GPT-4 vs SOTA gap plus soft-matching, robustness and dominant-error-type analysis over 14 IE subtasks |
| Combining Constrained and Unconstrained Decoding via Boosting: BoostCD and Its Application to Information Extraction | 2506.14901 | Boosted model fuses constrained and unconstrained drafts; constrained-only output shown to corrupt entities |
| Exploiting Asymmetry for Synthetic Training Data Generation: SynthIE and the Case of Information Extraction | 2303.04132 | Reverse-direction synthesis (triples to text) yields 1.8M pairs training 220M/770M extractors |
| Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | 2404.03868 | Open few-shot extraction first, then schema definition and post-hoc canonicalization |
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2404.16130 | LLM extracts entity/relation graph with one-shot gleaning prompt, then community summaries |
| From RAG to Memory: Non-Parametric Continual Learning for Large Language Models | 2502.14802 | OpenIE NER plus query-to-triple generation and LLM triple filtering before PageRank |
| GPT-NER: Named Entity Recognition via Large Language Models | 2304.10428 | @@## marker-token copy formulation plus self-verification QA to suppress NULL-input hallucinations |
| GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction | 2310.03668 | Models fine-tuned to follow code-formatted annotation guidelines (Python classes) on unseen schemas |
| InstructUIE: Multi-task Instruction Tuning for Unified Information Extraction | 2304.08085 | Instruction+options+text in, structured sentence out, with auxiliary span/typing subtasks |
| KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | 2502.09956 | Two-stage DSPy extraction (entities then relations) plus iterative LM clustering for resolution |
| LightRAG: Simple and Fast Retrieval-Augmented Generation | 2410.05779 | Single-pass LLM extraction of entities/relations plus keyword profiling and dedup |
| MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | 2501.06713 | SLM-friendly design: entity extraction (not abstract summarization) as the small-model task |
| Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | 2308.02357 | Ontology-guided fact extraction task with 7 metrics for extraction, conformance, hallucination |
| Unified Structure Generation for Universal Information Extraction | 2203.12277 | SEL linearization plus structural schema instructor (spot/associate/generate control) |
| UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recognition | 2308.03279 | ChatGPT-distilled open NER via mission-focused instruction tuning on diverse web text |
| Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2501.13956 | Episodic ingest with entity/fact/temporal extraction, edge dedup and bi-temporal invalidation |
| Zero- and Few-Shots Knowledge Graph Triplet Extraction with Large Language Models | 2312.01954 | Head-to-head triplet-extraction prompts across LLM sizes in zero- and few-shot settings |
| Zero-Shot Information Extraction via Chatting with ChatGPT | 2302.10205 | Two-stage multi-turn QA: find candidate types first, then chain-extract per type |
| iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models | 2409.03284 | Four-module zero-shot pipeline separating entity and relation extraction with matcher-based resolution |
| mergekit: tools for merging pretrained large language models | n/a | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with its generative base. |
| Decoding on Graphs: Faithful and Sound Reasoning on Knowledge Graphs through Generation of Well-Formed Chains | 2410.18415 | KG-topology token mask forces well-formed triplet chains during generation |
| GenIE: Generative Information Extraction | 2112.08340 | Autoregressive closed IE with bi-level trie-constrained beam search over KB schema |
| Generating Structured Outputs from Language Models: Benchmark and Studies | 2501.10868 | 10K real-world JSON schemas comparing 6 constrained-decoding frameworks on efficiency/coverage/quality |
| Iterative Zero-Shot LLM Prompting for Knowledge Graph Construction | 2307.01128 | Iterative zero-shot prompts per graph component without examples or external resources |
| XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models | 2411.15100 | Byte-level PDA with token-mask cache and GPU-overlapped grammar execution, ~100x faster |

Not admitted in lane 7 (0):

| title | arxiv_id_or_doi | reason |
|---|---|---|

Unresolved ledger (lane 7): Triplex run details — no paper, abstained (secondary only).
Full prompt texts of GraphRAG/LightRAG/HippoRAG2/KGGen live in repos, not papers — prompt
claims rest on paper text, not prompt diffs. Date normalisation — no dedicated primary
source screened (Spike 003 date failures lack a literature answer). Prompt placement
(instruction before/after document; marker position) — no direct study found. Evidence-quote
failure rates — only indirect evidence (MINE, Text2KGBench hallucination metrics, GPT-NER
NULL-hallucination). Per-size extraction tables in 2312.01954 not extracted — Spike 008 must
read them. Six repo URLs (GPT-NER, BoostCD, DoG, Papaluca-TE, Han-study, Carta) uncaptured
(API quota-exhausted), marked unverified. KGGen/GoLLIE licenses unchecked before vendoring.

### Lane 8 — Batched serving and KV sharing on one GPU (screened 39)

Continuous batching, prefix caching, prompt/output ordering, speculative decoding,
single-GPU throughput/VRAM scaling, multi-agent shared-prefix serving. Core result:
Orca iteration batching (OSDI 2022, doi:10.5555/3542929.3542970); PagedAttention
(2309.06180); vLLM automatic prefix caching docs (docs.vllm.ai); RadixAttention
(2312.07104); SARATHI/Sarathi-Serve chunked scheduling (2308.16369; 2403.02310);
SplitFuse/Dynamic SplitFuse (2401.08671); Splitwise/DistServe phase-split evidence
(2311.18677; 2401.09670); Mooncake cache-centric scheduling (2407.00079); MemServe/MemPool
(2406.17565); LMCache tiering (2510.09665); HydraGen prefix batching (2402.05099);
Preble exploit/explore routing (2407.00023); BatchLLM prefix-group scheduling (2412.03594);
Prompt Cache modules (2311.04934); CacheBlend non-prefix reuse (2405.16444); Llumnix
migration (2406.03243); NanoFlow compute-bound finding (2408.12757); FlashAttention lineage
(2205.14135); FlashInfer substrate (2501.01005); SpecInfer/Medusa/EAGLE/EAGLE-2 drafting
(2305.09781; 2401.10774; 2401.15077; 2406.16858); llama.cpp slots plus GGUF quantisation,
TensorRT-LLM baseline, TGI archived (engine repos, see inventory).

Admitted in lane 8 (25 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| BatchLLM: Optimizing Large Batched LLM Inference with Global Prefix Sharing and Throughput-oriented Token Batching | 2412.03594 | Global prefix tree + prefix-group scheduling + decode-ratio-first reorder; 1.3-10.8x vs vLLM/SGLang |
| CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | 2405.16444 | Selective recompute fuses non-prefix cached chunks; TTFT 2.2-3.3x lower, 2.8-5x throughput vs full recompute |
| DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving | 2401.09670 | Co-optimised prefill/decode placement; 4.48x more requests / 10.2x tighter SLO vs SOTA |
| Efficient Memory Management for Large Language Model Serving with PagedAttention | 2309.06180 | OS-style paging of KV cache blocks; near-zero fragmentation; 2-4x throughput vs FasterTransformer/Orca |
| FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving | 2501.01005 | JIT attention templates + block-sparse KV formats + StreamK scheduling; 29-69% inter-token-latency cut; cascade attention for shared prefixes |
| Hydragen: High-Throughput LLM Inference with Shared Prefixes | 2402.05099 | Prefix/suffix attention decomposition; inter-sequence batching; up to 32x CodeLlama-13B throughput vs vLLM |
| LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | 2510.09665 | Engine-independent KV layer: chunked offload, PD disaggregation, CacheBlend non-prefix reuse; up to 15x vLLM throughput |
| MemServe: Context Caching for Disaggregated LLM Serving with Elastic Memory Pool | 2406.17565 | MemPool unifying context caching + disaggregated inference; global prompt-tree routing; JCT/TTFT cuts up to 53%/85% |
| Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | 2407.00079 | KVCache-centric disaggregation + Conductor scheduler + early rejection; Kimi +75% requests; TE 87-190 GB/s |
| Orca: A Distributed Serving System for Transformer-Based Generative Models | doi:10.5555/3542929.3542970 (no arXiv) | Iteration-level (continuous) batching + selective batching; 36.9x throughput vs FasterTransformer on GPT-3 175B |
| Preble: Efficient Distributed Prompt Scheduling for LLM Serving | 2407.00023 | E2 exploit/explore scheduler co-optimising KV reuse + load balance; 1.5-14.5x avg latency, 2-10x p99 |
| Prompt Cache: Modular Attention Reuse for Low-Latency Inference | 2311.04934 | Schema-declared prompt modules with position-correct KV reuse; 8x GPU / 60x CPU TTFT cuts |
| SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills | 2308.16369 | Chunked prefills + decode-maximal batching; decode piggybacking; up to 10x decode throughput (LLaMA-13B/A6000) |
| SGLang: Efficient Execution of Structured Language Model Programs | 2312.07104 | RadixAttention tree-structured KV reuse across forked programs; compressed FSM for structured decode; up to 6.4x throughput |
| Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | 2403.02310 | Stall-free chunked-prefill scheduler; 2.6x capacity vs vLLM (Mistral-7B/1xA100), up to 5.6x with pipeline parallelism |
| vLLM serving engine (repo + docs) | - | APC via enable_prefix_caching with hash-chained KV blocks + cache_salt tenant isolation; chunked prefill + continuous batching built in |
| DeepSpeed-FastGen: High-throughput Text Generation for LLMs via MII and DeepSpeed-Inference | 2401.08671 | Dynamic SplitFuse token-budget batching; 2.3x effective throughput, 2x avg latency vs vLLM |
| EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees | 2406.16858 | Confidence-driven dynamic draft trees, no extra training over EAGLE; 3.05-4.26x, 20-40% over EAGLE |
| EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty | 2401.15077 | Feature-level autoregression + shifted tokens; 2.7-3.5x latency cut on LLaMA2-Chat 70B, 2x throughput |
| FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | 2205.14135 | IO-aware tiled exact attention; 15% BERT-large e2e, 3x GPT-2 train speedups; basis of all serving kernels |
| Llumnix: Dynamic Scheduling for Large Language Model Serving | 2406.03243 | Live migration of requests + KV state across instances; 10x tail-latency cut, 36% cost saving |
| Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads | 2401.10774 | Extra decoding heads + tree attention; Medusa-1 2.2x lossless frozen, Medusa-2 2.3-3.6x with joint tuning |
| NanoFlow: Towards Optimal Large Language Model Serving Throughput | 2408.12757 | Intra-device parallelism via nano-batches; serving is compute-bound at scale; 1.91x vs vLLM/FastGen/TRT-LLM |
| SpecInfer: Accelerating Generative LLM Serving with Tree-based Speculative Inference and Verification | 2305.09781 | Small-model draft trees verified in parallel by target LLM; 1.5-2.8x distributed, 2.6-3.5x offloading |
| Splitwise: Efficient Generative LLM Inference Using Phase Splitting | 2311.18677 | Split prefill/decode onto different machines; 1.4x throughput at 20% lower cost, 2.35x same budget |

Not admitted in lane 8 (4):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| WRONG ID probe: A Communication Theory Perspective on Prompting Engineering Methods | 2310.18358 | Opened arxiv abs: mismatch. FastGen admitted separately as 2401.08671. |
| WRONG ID probe: Blow-up of solutions for semilinear parabolic equation | 2402.05040 | Opened arxiv abs: mismatch. HydraGen admitted separately as 2402.05099. |
| WRONG ID probe: Drag-guided diffusion models for vehicle image generation | 2306.09935 | Opened arxiv abs: title/authors do not match. Recorded to prevent re-screening; Orca admitted separately via USENIX. |
| WRONG ID probe: Statistical Guarantees for Link Prediction using GNNs | 2402.02692 | Opened arxiv abs: mismatch. DistServe admitted separately as 2401.09670. |

Unresolved ledger (lane 8): consumer-GPU concurrency numbers (16 GB, 0.3–2B,
hundreds/thousands of workers) — no primary source found; vendor blogs excluded as
secondary. Output ordering (which finished outputs to surface first) — no paper found;
SARATHI covers prefill/decode interleaving only. llama.cpp slot-sizing/cache-reuse
measurements — repo verified, numbers not fetched from docs. SGLang scheduling-policy
details beyond the paper — docs not fetched. TensorRT-LLM KV/prefix specifics — closed
source, docs not fetched. Preble code — release unconfirmed. EAGLE/Medusa acceptance under
grammar-constrained decoding — intersection unstudied in the fetched set; Spike 009 must
measure.

### Lane 9 — Pipeline orchestration for extraction at scale (screened 22)

How GraphRAG/LightRAG/HippoRAG/nano-graphrag/Cognee/Graphiti parallelise ingestion; entity
resolution across workers; idempotent/batched writes; stage ordering; incremental and
streaming indexing; documents-per-hour with hardware. Core result: GraphRAG five-stage batch
design with gleaning loop (2404.16130); LightRAG union-merge incremental plus the legal-corpus
cost table (610k retrieval tokens vs <100; 1399×2×5000 incremental tokens avoided)
(2410.05779); HippoRAG offline-extract/online-PPR split at 10–30x vs IRCoT (2405.14831);
HippoRAG 2 passage nodes plus dense-seeded PPR plus LLM filter (2502.14802); RAPTOR
cluster-summarize tree (2401.18059); MiniRAG SLM-shaped ingestion at 25% storage
(2501.06713); PathRAG prune-plus-reliability-ordered payloads (2502.14902); KGGen iterative
clustering resolution (2502.09956); Graphiti episode-first streaming with bi-temporal
invalidation (2501.13956); IRCoT cost baseline (2212.10509); EDC definition-then-verify
dedup (2404.03868); Cognee per-corpus tuning (2505.24478); Leiden guarantees (1810.08473);
nano-graphrag single-node orchestrator pattern (https://github.com/gusye1234/nano-graphrag).

Admitted in lane 9 (15 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | 2404.03868 | Open few-shot extraction first, then schema definition and post-hoc canonicalization |
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2404.16130 | LLM extracts entity/relation graph with one-shot gleaning prompt, then community summaries |
| From RAG to Memory: Non-Parametric Continual Learning for Large Language Models | 2502.14802 | OpenIE NER plus query-to-triple generation and LLM triple filtering before PageRank |
| HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | 2405.14831 | Two-step OpenIE plus embedding synonym edges, single-step PPR retrieval; 10-30x cheaper / 6-13x faster than IRCoT |
| KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | 2502.09956 | Two-stage DSPy extraction (entities then relations) plus iterative LM clustering for resolution |
| LightRAG: Simple and Fast Retrieval-Augmented Generation | 2410.05779 | Single-pass LLM extraction of entities/relations plus keyword profiling and dedup |
| MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | 2501.06713 | SLM-friendly design: entity extraction (not abstract summarization) as the small-model task |
| Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2501.13956 | Episodic ingest with entity/fact/temporal extraction, edge dedup and bi-temporal invalidation |
| mergekit: tools for merging pretrained large language models | n/a | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with its generative base. |
| From Louvain to Leiden: guaranteeing well-connected communities | 1810.08473 | Leiden community detection with connectivity guarantees; faster and better partitions than Louvain |
| Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions | 2212.10509 | Alternate CoT-reason and retrieve steps; the expensive iterative baseline HippoRAG beats 10-30x on cost |
| LazyGraphRAG: Setting a new standard for quality and cost | n/a (https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) | Deferred-LLM indexing (NLP noun phrases + co-occurrence); indexing cost 0.1% of GraphRAG, query budget scales quality |
| Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning | 2505.24478 | Hyperparameter sweep over Cognee chunking/graph/retrieval/prompting on HotPotQA/2Wiki/MuSiQue; tuning gains real but uneven |
| PathRAG: Pruning Graph-Based Retrieval Augmented Generation with Relational Paths | 2502.14902 | Flow-based pruning of relational paths with reliability-ascending prompt ordering to cut retrieval tokens |
| RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive SBERT-embed, UMAP+GMM-cluster (BIC), LLM-summarize tree; collapsed-tree retrieval |

Not admitted in lane 9 (2):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| IMAGINE: An Integrated Model of Artificial Intelligence-Mediated Communication Effects | 2212.08658 | Recalled as IRCoT id from memory; abs page shows it is a different paper. Correct IRCoT id is 2212.10509. |
| On Pruning State-Space LLMs | 2502.18886 | Recalled as PathRAG id from memory; abs page shows it is a different paper. Recorded to prevent re-screening. |

Unresolved ledger (lane 9): no primary source anywhere reports documents-per-hour with
hardware for any system — the lane's main unresolved item, not filled by estimation.
Incremental index-update/write-amplification costs unmeasured (open in lane 10 too).
FastGraphRAG/HiRAG/mini-adjacent HKUDS variants noted via repo lists, not screened.
LangChain indexing docs URL redirected to overview — abstained rather than citing recall.
LazyGraphRAG admitted as vendor-blog secondary-only
(https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/).

### Lane 10 — High-speed retrieval and vector storage (screened 37)

Index choices, quantised/binary embeddings, Matryoshka truncation at query time, hybrid
sparse+dense, small rerankers and latency, graph+vector fusion at query time, QPS/recall
trade-offs. Core result: HNSW default (1603.09320); Faiss GPU design and library
(1702.08734; https://github.com/facebookresearch/faiss); ANN-Benchmarks protocol
(1807.05614); ScaNN anisotropic quantization (1908.10396); DPR floor (2004.04906);
ColBERT quality ceiling (2004.12832) with ColBERTv2 compression+distillation
(2112.01488) and PLAID CPU-viable serving (2205.09707); monoT5 generative-reranker
template (2003.06713); MiniLM 0.3B-class distillation recipe (2002.10957); ANCE training
loop (2007.00808); SPLADEv2 sparse arm (2109.10086); SPANN RAM/SSD scaling path
(2111.08566); XTR cheapest multi-vector objective, +2.8 BEIR (2304.01982); BGE-M3 hybrid
fusion (2402.03216); RAPTOR summary-tree fusion (2401.18059); RankT5 ranking losses
(2210.10634); DiskANN/hnswlib/ann-benchmarks/USearch artefacts (repos, see inventory).

Admitted in lane 10 (24 rows counting cross-lane listings):

| title | arxiv_id_or_doi | one_line |
|---|---|---|
| ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms | 1807.05614 | Standard recall-vs-QPS harness; graph methods win high recall but fail some datasets |
| Accelerating Large-Scale Inference with Anisotropic Vector Quantization | 1908.10396 | Loss penalizing parallel residual component for MIPS; SOTA on ann-benchmarks |
| Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | 2007.00808 | Async-refreshed ANN index mines corpus-representative hard negatives during training. |
| Billion-scale similarity search with GPUs | 1702.08734 | GPU k-selection at 55% of peak, 8.5x faster than prior GPU SOTA; IVF-PQ on GPU |
| ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | 2004.12832 | Token-level late-interaction (MaxSim) over BERT encodings; per-pair NN cost avoided. |
| ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction | 2112.01488 | Residual compression plus denoised supervision shrinking late-interaction footprint. |
| Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. |
| Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs | 1603.09320 | Log-layered proximity-graph ANN index with neighbor-selection heuristic |
| M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | 2402.03216 | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. |
| Matryoshka Representation Learning | 2205.13147 | Nested coarse-to-fine representation; truncate dims at query time, no retraining. |
| MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers | 2002.10957 | Distill last-layer attention + value relations; 6-layer student 2.0x faster at >99% accuracy |
| Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 |
| PLAID: An Efficient Engine for Late Interaction Retrieval | 2205.09707 | Centroid interaction + pruning engine: 2.5-6.8x GPU / 9.2-45x CPU speedups at 140M passages |
| Rethinking the Role of Token Retrieval in Multi-Vector Retrieval (XTR) | 2304.01982 | Retrieve-top-tokens objective; +2.8 nDCG@10 on BEIR; scoring stage 4000x fewer FLOPs |
| SPANN: Highly-efficient Billion-scale Approximate Nearest Neighbor Search | 2111.08566 | Memory-disk hybrid inverted index; 2x faster than DiskANN at 90% recall, ~1ms, 32GB |
| SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval | 2109.10086 | MLM-head sparse expansion with FLOPS regularization; inverted-index retrieval. |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| jina-embeddings-v3: Multilingual Embeddings With Task LoRA | 2409.10173 | 570M multilingual model with task-specific LoRA adapters; long-context retrieval |
| vLLM serving engine (repo + docs) | - | APC via enable_prefix_caching with hash-chained KV blocks + cache_salt tenant isolation; chunked prefill + continuous batching built in |
| C-Pack: Packed Resources For General Chinese Embeddings | 2309.07597 | BGE-family training resources: data, small-model baselines, C-MTEB evaluation |
| Document Ranking with a Pretrained Sequence-to-Sequence Model | 2003.06713 | Relevance labels as target words; T5-base MRR@10 0.363, T5-large 0.383 on MS MARCO |
| RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive SBERT-embed, UMAP+GMM-cluster (BIC), LLM-summarize tree; collapsed-tree retrieval |
| RankT5: Fine-Tuning T5 for Text Ranking with Ranking Losses | 2210.10634 | Listwise losses beat monoT5 by +1.8% MRR@10 (MARCO) / +2.8% (NQ), better zero-shot |

Not admitted in lane 10 (7):

| title | arxiv_id_or_doi | reason |
|---|---|---|
| Document Expansion by Query Prediction | 1904.08375 | Abs verified at primary source; mechanism covered by admitted synthetic-data items (Promptagator, InPars, GPL, E5-Mistral). |
| DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node | no-arXiv-found | No arXiv id found via fetched title search; repo admitted instead |
| Llama2Vec: Unsupervised Adaptation of Large Language Models for Dense Retrieval | 2312.15503 | Abs page verified; belongs to lanes 2/4 - screened for dedupe only |
| Product quantization for nearest neighbor search | no-arXiv | No arXiv PDF available; covered indirectly via admitted Faiss paper which builds on it |
| Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods | no-arXiv-DOI-only | Could not verify at primary source (no arXiv PDF per lane rules); do not cite numbers |
| SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking | 2107.05720 | Abs page verified; not separately filed - content subsumed by admitted SPLADEv2, recorded for dedupe |
| uniCOIL: Unified and Effective Weighting for Contextualized Inverted Lists | unresolved | Could not resolve a verified arXiv id from fetched search results; will not cite |

Unresolved ledger (lane 10): dense+sparse+graph fusion weights (RRF has no arXiv PDF,
abstained; BGE-M3 fuses at train time, not query time) — measure linear/RRF fusion on our
corpus. PQ-2011 foundations — no arXiv PDF (Faiss usage suffices). DiskANN paper numbers —
no arXiv id found; SPANN's 2x-over-DiskANN is single-source, needs replication before
choosing SPANN over DiskANN. uniCOIL reference unresolved. Consumer-GPU QPS for 0.3–1B
rerankers with batching — unreported (quality in monoT5/RankT5; speedups on GLUE/SQuAD in
MiniLM) — Spike 010 must produce it. ANN recall shootout on Qwen3-Embedding-0.6B vectors
with cosine/IP unmeasured — Spike 010 item.

## 5. The recipe

Three plans, each step traced to a verified paper or documented system. "Vendor-reported"
marks figures resting on vendor claims only. All training fits a single 16 GB card via
quantized frozen bases plus adapters (QLoRA 2305.14314; LLM2Vec LoRA path 2404.05961) and
the sentence-transformers stack (Apache-2.0).

### 5A. MelodyScribe embedder on one 16 GB GPU

1. **Baseline and eval first.** Stand up the private-corpus eval before training: 8
exemplar query–passage pairs per retrieval intent generate the synthetic query set
(Promptagator 2209.11755), checked for query-length/type sanity against MS MARCO
statistics (1611.09268); calibrate synthetic labels with a small human audit plus
statistical intervals (ARES 2311.09476); compare models with per-dataset effect sizes,
never a mean (Brewing BEIR 2306.07471); track alignment/uniformity (2005.10242) and
IsoScore (2108.07344) next to MRR so noisy 20-document MRR cannot mislead.
2. **Cheapest controls before training.** Whiten the MiniCPM5 last-token states on a
large unlabeled sample and re-run MRR (Whitening 2103.15316); add all-but-the-top
(1702.01417) and mean-centering controls; subtract the marker-only template bias
(PromptBERT 2201.04337). Only if unsupervised linear repairs fail is training justified —
Spike 004's ridge result does not contradict these controls (lane 6 refutation 15).
3. **Prompt arms (training-free).** Echo repetition (2402.15449), PromptEOL one-word
compression (2307.16645), multi-prompt averaging (MetaEOL 2402.18458), and a
no-instruction control (required by Promptriever 2409.11136 and FollowIR 2403.15246),
reporting distributions over paraphrases, never single-prompt MRR (2605.22544). Query-side
instructions only; documents bare (E5-Mistral 2401.00368; NV-Embed 2405.17428).
4. **Data engine.** Generate synthetic query–passage pairs with an open self-hosted
generator (terms logged per pair; E5-Mistral pattern 2401.00368 without the proprietary
dependency), consistency-filter every pair (InPars 2202.05144), LLM-relabel positives and
hard negatives (Gecko FRet 2403.20327), add instruction negatives sharing the query but
violating the instruction (Promptriever 2409.11136), diversify instructions toward ~150k
unique paraphrases rather than hand-tuning one (mE5 2402.05672), and cluster-sample the
pretraining data (2407.18887). Dedup every eval split by n-gram overlap first
(decontamination requirement, lane 6).
5. **Training.** Two stages — weak/synthetic contrastive pretraining, then supervised
fine-tuning on high-quality triplets (E5 2212.03533; Qwen3-Embedding 2506.05176) — with
improved InfoNCE plus in-batch and K mined hard negatives plus false-negative masking
(Qwen3-Embedding 2506.05176), ANN-refreshed hard negatives (ANCE 2007.00808), cross-batch
negatives for the 16 GB batch ceiling (RocketQA 2010.08191), dropout positives for the
first unsupervised pass (SimCSE 2104.08821), topic-aware balanced sampling (TAS-B
2104.06967), MarginMSE distillation from a cross-encoder into the small student (TAS-B
2104.06967), progressive teacher signal across the capacity gap (PROD 2209.13335), and a
merge-home step for robustness (Qwen3-Embedding 2506.05176; EmbeddingGemma 2509.20354).
Pool with latent attention, not last-token (NV-Embed 2405.17428); train nested Matryoshka
dims from the start (2205.13147). Expected cost: E5-Mistral-class runs complete the
contrastive phase in under 1k steps on synthetic data (2401.00368, vendor-reported) atop a
4-bit frozen base (QLoRA 2305.14314); the dominant budget is synthetic generation plus
relabeling (Gecko 2403.20327), not GPU-hours. Per-stage GPU-hours are otherwise unreported
in the surveyed abstracts — extract them from the staged PDFs before committing the plan.
6. **Hybrid decision (Spike 006 order).** Frozen base plus retrieval LoRA first (LLM2Vec
2404.05961; Hydra 2603.28554, diff tensors to verify byte-identical recovery); unsupervised
special-token compression as the no-pairs arm (LLM2Vec-Gen 2603.10913); TIES/DARE merge
sweep with Model Soups floor and LM-Cocktail rebalancing, mergekit YAML recipes
(2306.01708; 2311.03099; 2203.05482; 2311.13534; mergekit); generation benchmarks at every
coefficient (Embedder's Dilemma protocol 2608.12875); LRD-style drift checks when base
weights move (2605.12714).
7. **Retrieval stack.** HNSW default (1603.09320) built with Faiss or hnswlib; sparse arm
on a plain inverted index (SPLADEv2 2109.10086); Matryoshka truncation per query budget
(2205.13147); anisotropic PQ codes for MIPS storage (1908.10396); reranker distilled via
MiniLM attention relations (2002.10957) trained with ranking losses (RankT5 2210.10634);
fusion weights measured on-corpus (open: RRF has no primary source).

### 5B. Graph-extraction prompt and training (Spike 008 conditions)

1. **Prompt shape.** Schema-as-code: annotation guidelines as typed classes with
docstrings and definitions (GoLLIE 2310.03668); instruction plus candidate options plus
text as the tested alternative arm (InstructUIE 2304.08085); SEL-style linearization for
the op language (UIE 2203.12277); instruction placement fixed and versioned (placement
unresolved — record the choice; lane 7 ledger).
2. **Staging.** Two prompts — entities first, relations given text plus entities (KGGen
2502.09956; iText2KG 2409.03284) — against a one-step arm and a ChatIE multi-turn
quality-ceiling arm (2302.10205); open extraction with the schema outside the prompt,
canonicalize after (EDC 2404.03868); one gleaning re-prompt ("were entities missed"),
capped at one (GraphRAG 2404.16130); cheap filter pass over emitted triples mapping to
Proof (HippoRAG 2 2502.14802); marker-token verbatim spans plus self-verification
(GPT-NER 2304.10428) with Proof's substring check staying mechanical.
3. **Constraints.** Op grammar enforced in the decoder (GenIE 2112.08340) via XGrammar
(2411.15100) after coverage-testing the grammar against JSONSchemaBench's failing
classes (2501.10868); constraints derived from the incrementally built graph where
attachable (DoG 2410.18415); unconstrained draft retained as cross-check signal (BoostCD
2506.14901).
4. **Training.** Frontier-teacher distillation on broad unlabeled text with
mission-focused instructions for entities (UniversalNER 2308.03279) and reverse-direction
synthesis from gold op-sets for relations (SynthIE 2303.04132), mixed with real Score
sections (synthetic-only degrades out-of-distribution — BoostCD 2506.14901); auxiliary
span-finding and typing subtasks (InstructUIE 2304.08085); anti-memorization noise
(GoLLIE 2310.03668). Size ablation prior from Papaluca et al. tables (2312.01954 —
re-read before finalizing).
5. **Metrics.** Extraction, schema conformance, and hallucination scored separately
(Text2KGBench 2308.02357); soft-matching, never exact-match triple scoring (Han et al.
2305.14450); unannotated-span dominance sets recall-oriented validator thresholds
(2305.14450); date normalisation and verbatim-quote adherence have no literature answer —
Spike 008 is primary evidence.

### 5C. Serving configuration on one 16 GB GPU (Spike 009 setup)

1. Engine on PagedAttention (vLLM 2309.06180) or RadixAttention (SGLang 2312.07104) over
FlashInfer kernels (2501.01005); llama-server with GGUF quantisation as the consumer-card
fallback (ggml-org/llama.cpp, MIT).
2. Skill plus schema plus section-type instruction byte-first in every prompt; per-section
content after; salt the prefix namespace per tenant with SHA256 block hashing in
multi-tenant setups (vLLM APC docs, docs.vllm.ai).
3. Group section jobs by shared prefix; decode-ratio-first reordering; memory-centric
token batching (BatchLLM 2412.03594); chunked prefills so long sections never stall
decodes (SARATHI 2308.16369; Sarathi-Serve 2403.02310); reuse non-prefix chunks with
selective recompute when order varies (CacheBlend 2405.16444).
4. Speculative drafting (Medusa-1 frozen heads 2401.10774; EAGLE-2 no-retraining policy
2406.16858) only after measuring acceptance under the grammar constraint — unstudied
intersection, default to off.
5. Report the missing numbers: concurrency-vs-latency for 0.3–2B workers, prefix-cache hit
rates by ordering, and acceptance rates under constrained decoding. All published
multiples are datacenter-GPU figures and must not be quoted as targets (lane 8).

## 6. Reusable artefacts

Checkpoints, datasets, code, and engines runnable on one 16 GB GPU, with license as
verified in the inventory (HF API or GitHub API; null/unverified flagged).

- **Qwen/Qwen3-Embedding-0.6B** (2506.05176) — Apache-2.0, 8.3M downloads. Distillation
teacher and Spike 006 baseline; in-band size.
- **BAAI/bge-m3** (2402.03216) — MIT, 37.8M downloads. Long-section (8k) reference and
self-distillation template; base far above 0.6B, transfer the mechanism.
- **nomic-embed-text-v1** (2402.01613) — Apache-2.0, 136.7M params, 8k context, fully
reproducible (weights, code nomic-ai/contrastors, data). Replicate first on the rig.
- **Arctic-Embed family 22M–334M** (2405.05374) — Apache-2.0. Small-model data playbook.
- **ibm-granite/granite-embedding-125m-english** (2502.20204) — Apache-2.0. The ~125M
competitiveness floor.
- **EmbeddingGemma-300M** (2509.20354) — Gemma license (restrictive; check before product
use). Closest one-small-model analogue; vendor-reported SOTA under 500M.
- **jina-embeddings-v3 570M** (2409.10173) — CC-BY-NC-4.0 (non-commercial; do not ship).
Task-LoRA asymmetry pattern only.
- **nvidia/NV-Embed-v2** (2405.17428) — CC-BY-NC-4.0 (non-commercial; do not ship or train
into commercial artefacts without approval).
- **huggingface/sentence-transformers** (from SBERT 1908.10084) — Apache-2.0, active. The
experiment stack for small-embedder contrastive runs.
- **FlagOpen/FlagEmbedding** (BGE-M3 2402.03216) — MIT, 12153 stars. Most complete open
training codebase (multi-head, 8k batching).
- **McGill-NLP/llm2vec** (2404.05961) — MIT. LoRA conversion path for the hybrid.
- **arcee-ai/mergekit** — LGPL-3.0 (tooling dependency OK; check policy before vendoring).
All Spike 006 merges as YAML recipes.
- **mlc-ai/xgrammar** (2411.15100) — Apache-2.0. Op-grammar enforcement engine.
- **vLLM / SGLang / FlashInfer** (2309.06180; 2312.07104; 2501.01005) — Apache-2.0.
Serving substrate; LMCache (Apache-2.0, 11771 stars) for CPU-tier KV overflow.
- **ggml-org/llama.cpp** — MIT. Consumer-card fallback with slots and GGUF quantisation.
- **facebookresearch/faiss** — MIT. ANN backend (pin commit; native code).
- **nmslib/hnswlib** — Apache-2.0. Smallest-footprint CPU ANN for small-to-mid corpora.
- **microsoft/DiskANN** — MIT. SSD-resident fallback if vectors outgrow RAM.
- **erikbern/ann-benchmarks** — MIT. Spike 010 index-comparison harness.
- **gusye1234/nano-graphrag** — MIT. Most MelodyScribe-shaped orchestrator (async, hash-key
idempotency, KV+vector+graph split, Ollama/sentence-transformer examples).
- **getzep/graphiti** (2501.13956) — Apache-2.0 core (managed backend proprietary).
Streaming write-path discipline; runs on Ollama plus nomic-embed locally.
- **topoteretes/cognee** (2505.24478) — Apache-2.0. Tunable orchestration surface with
local-Ollama support.
- **stanford-futuredata/ARES** (2311.09476) — Apache-2.0. Synthetic-judgment validation
protocol for the private eval.
- **UKPLab/gpl** (2112.07577) — Apache-2.0. Label-free domain-adaptation starting point.
- **princeton-nlp/SimCSE** (2104.08821) — MIT. Dropout-positive cheapest first run.
- **microsoft/ANCE** (2007.00808) — MIT. ANN-mined-negative training loop.
- **artidoro/qlora** (2305.14314) — MIT. 4-bit-plus-adapter fitting.
- **jakespringer/echo-embeddings** (2402.15449) — Apache-2.0. Echo-template baseline code.
- **xlang-ai/instructor-embedding** (2212.09741) — Apache-2.0. Task-prefix training reference.
- **hitz-zentroa/GoLLIE; universal-ner/universal-ner; universal-ie/UIE; epfl-dlab/SynthIE;
clear-nus/edc; stair-lab/kg-gen; HKUDS/MiniRAG; OSU-NLP-Group/HippoRAG** — all MIT or
Apache-2.0 per inventory (verify kg-gen licence badge before vendoring). Extraction
training and pipeline code.
- **Do not reuse without clarification:** facebookresearch/contriever and
facebookresearch/DPR report license NOASSERTION via the API — treat as unlicensed; prefer
MIT/Apache-2.0 codebases. TensorRT-LLM is proprietary NVIDIA-licensed (numbers baseline
only). TGI is archived (historical reference only).

## 7. Gaps

What nobody has built or measured, stated precisely (each is a Spike or follow-up round).

1. **Small-hybrid generation loss.** No primary source measures generation degradation for
a ≤2B model that also embeds (GRIT evidence is 7B; Hydra's byte-identical claim is
single-author 2026). Spike 006 fills this.
2. **`[EMB]`-marker design.** No paper trains or evaluates a dedicated marker token for
decoder embeddings; query-vs-document prefix ablations with MRR numbers do not exist;
chat-template effects are unisolated. Spike 007 is primary evidence.
3. **Consumer-GPU serving numbers.** No primary source reports 0.3–2B concurrency,
prefix-cache hit rates, or speculative-decoding acceptance (especially under
grammar constraints) on a 16 GB card. Spike 009 is primary evidence.
4. **Pipeline throughput.** No primary source reports documents-per-hour with hardware for
any extraction pipeline, nor incremental index-update/write-amplification costs. Spike 010
owns both.
5. **Small-reranker latency.** No admitted paper reports 0.3–1B reranker QPS with batching
on consumer hardware; MiniLM speedups are GLUE/SQuAD, PLAID latency is datacenter. Spike
010 item.
6. **Fusion weights.** No primary source for RRF/score-fusion weights across dense, sparse,
and graph arms at query time (BGE-M3 fuses at train time). Measure on-corpus.
7. **Date normalisation and quote adherence.** No dedicated primary source for extraction
date canonicalization; verbatim-quote adherence of small extractors is unmeasured directly.
Spike 008 items.
8. **Per-size extraction tables.** Papaluca et al. (2312.01954) span model sizes but tables
were not extracted; re-read before the Spike 008 size ablation.
9. **Current leaderboards.** No MTEB/MMTEB/BEIR/Papers-with-Code leaderboard page was
opened in any lane; top-table numbers and the 2025 frontier past Qwen3-Embedding/MMTEB are
uncovered (S2 throttling blocked citation chaining; aluminum-bench, FreshDiskANN, LVQ,
RaBitQ noted uncovered in lane 10).
10. **Security-adjacent holes.** BadMerging (backdoor attacks on merging) unscreened —
required before any merge-home ships; model2vec static-distillation paper id unverified;
RepLLaMA/LLaRA ids unestablished; DiskANN paper numbers single-sourced via SPANN.

## 8. Reading order

For a maintainer with one day. Order is dependency order; all PDFs are in `merged/papers/`.

1. **Qwen3-Embedding (2506.05176)** — the in-band recipe and teacher; read stages, loss,
negatives, merge steps.
2. **GritLM (2402.09906)** — the unification proof and instruction-switching design.
3. **LLM2Vec (2404.05961)** — the cheap LoRA conversion; read with QLoRA (2305.14314).
4. **Gecko (2403.20327)** — the generate-then-relabel data engine for the GPU plan.
5. **NV-Embed (2405.17428)** — pooling and instruction-masking rules for `[EMB]`.
6. **E5 (2212.03533)** — the two-stage template everything else inherits.
7. **Promptriever (2409.11136)** — instruction negatives; read with the sensitivity study
(2605.22544) to calibrate how much prompts can lie.
8. **GoLLIE (2310.03668) + EDC (2404.03868)** — schema-as-code prompts and
open-then-canonicalize ordering.
9. **KGGen (2502.09956) + BoostCD (2506.14901)** — two-stage extraction with clustering
resolution, plus the corruption model that justifies Proof's two layers.
10. **SGLang/RadixAttention (2312.07104) + BatchLLM (2412.03594)** — the serving design;
skim PagedAttention (2309.06180) for the substrate and ANCE (2007.00808) for the negative
loop on the way out.

## 9. Full inventory

Every screened candidate, admitted or not, sorted by disposition then relevance. Fields are
BRIEF.md section 4 fields (title, authors, year, venue, arXiv id/DOI, repository, stars,
last push, license, artefact released, one line, relevance 0–3) plus serving lanes. Detail
and PDFs: lane `findings.md`/`papers/`; method: part 10.

| title | authors | year | venue | arxiv/doi | repo | stars | last push | license | artefact | one line | rel | disp | lanes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Accelerating Large-Scale Inference with Anisotropic Vector Quantization | Guo, Ruiqi; Sun, Philip; Lindgren, Erik; Geng, Quan; Simcha, David; Chern, Felix; Kumar, Sanjiv | 2019 | arXiv preprint | 1908.10396 | - |  |  | n/a (paper) | yes | Loss penalizing parallel residual component for MIPS; SOTA on ann-benchmarks | 3 | admit | 10 |
| All-but-the-Top: Simple and Effective Postprocessing for Word Representations | Mu, Bhat, Viswanath | 2017 | arXiv preprint (ICLR 2018 — verify before citing) | 1702.01417 |  |  |  |  | unknown | Removes dominant common directions to repair degenerate word-embedding geometry (per title). | 3 | admit | 6 |
| An Empirical Study on Information Extraction using Large Language Models (v1: Is Information Extraction Solved by ChatGPT?) | Ridong Han, Chaohao Yang, Tao Peng, Prayag Tiwari, Xiang Wan, Lu Liu, Benyou Wang | 2023 | arXiv preprint | 2305.14450 | repo URL not captured (code+data stated released in paper) | unknown | unknown | unknown | code+data stated released in paper | GPT-4 vs SOTA gap plus soft-matching, robustness and dominant-error-type analysis over 14 IE subtasks | 3 | admit | 7 |
| ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms | Aumuller, Martin; Bernhardsson, Erik; Faithfull, Alexander | 2018 | arXiv preprint | 1807.05614 | https://github.com/erikbern/ann-benchmarks | 5732 | 2026-07-10 | MIT | yes | Standard recall-vs-QPS harness; graph methods win high recall but fail some datasets | 3 | admit | 10 |
| Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | Lee Xiong, Chenyan Xiong, Ye Li et al. | 2020 | arXiv preprint | 2007.00808 | https://github.com/microsoft/ANCE | 389 | 2026-01-06 | MIT | unverified | Async-refreshed ANN index mines corpus-representative hard negatives during training. | 3 | admit | 1,2,10 |
| Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models | Luke Merrick, Danmei Xu, Gaurav Nuti et al. | 2024 | arXiv preprint | 2405.05374 | https://github.com/Snowflake-Labs/arctic-embed | 91 | 2025-11-03 | Apache-2.0 | yes (Apache-2.0 weights per abs) | Efficiency-first recipe: data filtering and long-context handling; 22M to 334M models, SOTA-for-size on MTEB Retrieval. | 3 | admit | 2,3 |
| BatchLLM: Optimizing Large Batched LLM Inference with Global Prefix Sharing and Throughput-oriented Token Batching | Z. Zheng, X. Ji, T. Fang, F. Zhou, C. Liu, G. Peng | 2024 | MLSys 2026 | 2412.03594 | https://github.com/microsoft/MixLLM/tree/batchllm_vllm_064 | - | - | - | yes (branch stated in paper) | Global prefix tree + prefix-group scheduling + decode-ratio-first reorder; 1.3-10.8x vs vLLM/SGLang | 3 | admit | 8 |
| BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | Thakur, Reimers, Rücklé, Srivastava, Gurevych | 2021 | NeurIPS 2021 Datasets and Benchmarks (per arXiv abs page) | 2104.08663 | https://github.com/beir-cellar/beir | 2288 | 2025-10-16 | Apache-2.0 | yes — code, 18 datasets, HF BeIR org | 18-dataset zero-shot retrieval benchmark; BM25 robust, late-interaction/rerank best, dense often lags. | 3 | admit | 6 |
| Billion-scale similarity search with GPUs | Johnson, Jeff; Douze, Matthijs; Jegou, Herve | 2017 | arXiv preprint | 1702.08734 | https://github.com/facebookresearch/faiss | 40893 | 2026-09-12 | MIT | yes | GPU k-selection at 55% of peak, 8.5x faster than prior GPU SOTA; IVF-PQ on GPU | 3 | admit | 10 |
| CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | J. Yao, H. Li, Y. Liu, S. Ray, Y. Cheng, Q. Zhang, K. Du, S. Lu, J. Jiang | 2024 | arXiv preprint | 2405.16444 | - | - | - | - | yes (paper states code available) | Selective recompute fuses non-prefix cached chunks; TTFT 2.2-3.3x lower, 2.8-5x throughput vs full recompute | 3 | admit | 8 |
| ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | Omar Khattab; Matei Zaharia | 2020 | arXiv preprint | 2004.12832 | https://github.com/stanford-futuredata/ColBERT | 3932 | 2025-10-14 | MIT | yes (weights+code) | Token-level late-interaction (MaxSim) over BERT encodings; per-pair NN cost avoided. | 3 | admit | 1,6,10 |
| ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction | Keshav Santhanam; Omar Khattab; Jon Saad-Falcon; Christopher Potts; Matei Zaharia | 2021 | arXiv preprint | 2112.01488 | https://github.com/stanford-futuredata/ColBERT | 3932 | 2025-10-14 | MIT | yes (weights+code) | Residual compression plus denoised supervision shrinking late-interaction footprint. | 3 | admit | 1,10 |
| Combining Constrained and Unconstrained Decoding via Boosting: BoostCD and Its Application to Information Extraction | Marija Sakota, Robert West | 2025 | arXiv preprint | 2506.14901 | repo URL not captured | unknown | unknown | unknown | artefact status unverified | Boosted model fuses constrained and unconstrained drafts; constrained-only output shown to corrupt entities | 3 | admit | 7 |
| Dense Passage Retrieval for Open-Domain Question Answering | Vladimir Karpukhin; Barlas Oğuz; Sewon Min; Patrick Lewis; Ledell Wu; Sergey Edunov; Danqi Chen; Wen-tau Yih | 2020 | EMNLP 2020 (per abs-page comments) | 2004.04906 |  |  |  |  | yes (weights+code) | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. | 3 | admit | 1,2,6,10 |
| DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving | Y. Zhong, S. Liu, J. Chen, J. Hu, Y. Zhu, X. Liu, X. Jin, H. Zhang | 2024 | OSDI 2024 | 2401.09670 | https://github.com/LLMServe/DistServe | 834 | 2025-04-06 | Apache-2.0 | yes (repo verified) | Co-optimised prefill/decode placement; 4.48x more requests / 10.2x tighter SLO vs SOTA | 3 | admit | 8 |
| Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs | Malkov, Yu. A.; Yashunin, D. A. | 2016 | arXiv preprint | 1603.09320 | https://github.com/nmslib/hnswlib |  |  | unknown | unknown | Log-layered proximity-graph ANN index with neighbor-selection heuristic | 3 | admit | 10 |
| Efficient Memory Management for Large Language Model Serving with PagedAttention | W. Kwon, Z. Li, S. Zhuang, Y. Sheng, L. Zheng, C. H. Yu, J. Gonzalez, H. Zhang, I. Stoica | 2023 | SOSP 2023 | 2309.06180 | https://github.com/vllm-project/vllm | 91577 | 2026-09-12 | Apache-2.0 | yes (engine + paper code) | OS-style paging of KV cache blocks; near-zero fragmentation; 2-4x throughput vs FasterTransformer/Orca | 3 | admit | 8 |
| Efficiently Teaching an Effective Dense Retriever with Balanced Topic Aware Sampling | Sebastian Hofstatter, Sheng-Chieh Lin, Jheng-Hong Yang et al. | 2021 | SIGIR 2021 | 2104.06967 | https://github.com/sebastian-hofstaetter/tas-balanced-dense-retrieval | 60 | 2021-07-11 | Apache-2.0 | unverified | Topic-aware balanced sampling plus MarginMSE distillation from cross-encoder into 6-layer DistilBERT. | 3 | admit | 2 |
| EmbeddingGemma: Powerful and Lightweight Text Representations | Henrique Schechter Vera et al. | 2025 | arXiv preprint | 2509.20354 | weights via sentence-transformers-compatible release (google/embeddinggemma-300m, 2.1M downloads) | not-fetched | not-fetched | Gemma license (weights) | yes (300M params) | 300M decoder-derived embedder; closest public analogue to MelodyScribe one-model goal | 3 | admit | 3 |
| Exploiting Asymmetry for Synthetic Training Data Generation: SynthIE and the Case of Information Extraction | Martin Josifoski, Marija Sakota, Maxime Peyrard, Robert West | 2023 | EMNLP 2023 | 2303.04132 | https://github.com/epfl-dlab/SynthIE | 63 | 2023-05-27 | MIT | code+data+models released | Reverse-direction synthesis (triples to text) yields 1.8M pairs training 220M/770M extractors | 3 | admit | 7 |
| Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | Bowen Zhang, Harold Soh | 2024 | EMNLP 2024 | 2404.03868 | https://github.com/clear-nus/edc | 193 | 2024-08-13 | MIT | code released | Open few-shot extraction first, then schema definition and post-hoc canonicalization | 3 | admit | 7,9 |
| FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving | Z. Ye, L. Chen, R. Lai, W. Lin, Y. Zhang, S. Wang, T. Chen, B. Kasikci, V. Grover, A. Krishnamurthy, L. Ceze | 2025 | MLSys 2025 | 2501.01005 | https://github.com/flashinfer-ai/flashinfer | 6385 | 2026-09-12 | Apache-2.0 | yes (repo verified) | JIT attention templates + block-sparse KV formats + StreamK scheduling; 29-69% inter-token-latency cut; cascade attention for shared prefixes | 3 | admit | 8 |
| FollowIR: Evaluating and Teaching Information Retrieval Models to Follow Instructions | Weller et al. | 2024 | NAACL 2025 | 2403.15246 | unverified | unverified | unverified | unverified | yes (FollowIR-7B model and training data per paper) | TREC-narrative instruction benchmark with p-MRR metric plus training data that teaches instruction following. | 3 | admit | 5 |
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization | Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha Metropolitansky, Robert Osazuwa Ness, Jonathan Larson | 2024 | arXiv preprint | 2404.16130 | https://github.com/microsoft/graphrag | 36000 | 2026-08-24 | MIT | code+prompts+docs released | LLM extracts entity/relation graph with one-shot gleaning prompt, then community summaries | 3 | admit | 7,9 |
| From RAG to Memory: Non-Parametric Continual Learning for Large Language Models | Bernal Jimenez Gutierrez, Yiheng Shu, Weijian Qi, Sizhe Zhou, Yu Su | 2025 | ICML 2025 | 2502.14802 | https://github.com/OSU-NLP-Group/HippoRAG | 3999 | 2026-09-03 | MIT | code+data released | OpenIE NER plus query-to-triple generation and LLM triple filtering before PageRank | 3 | admit | 7,9 |
| Gecko: Versatile Text Embeddings Distilled from Large Language Models | Jinhyuk Lee, Zhuyun Dai, Xiaoqi Ren et al. | 2024 | arXiv preprint | 2403.20327 | none located (Google-internal pipeline) | n/a | n/a | n/a | unverified | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. | 3 | admit | 2,3,5,6 |
| Generative Representational Instruction Tuning | Niklas Muennighoff; Hongjin Su; Liang Wang; Nan Yang; Furu Wei; Tao Yu; Amanpreet Singh; Douwe Kiela | 2024 | arXiv preprint | 2402.09906 | https://github.com/ContextualAI/gritlm | 700 | 2025-06-25 | MIT | yes (weights+code) | Instruction-switched joint generative+embedding training at no loss to either. | 3 | admit | 1,4,5 |
| GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction | Oscar Sainz, Iker Garcia-Ferrero, Rodrigo Agerri, Oier Lopez de Lacalle, German Rigau, Eneko Agirre | 2024 | ICLR 2024 | 2310.03668 | https://github.com/hitz-zentroa/GoLLIE | 443 | 2024-10-27 | Apache-2.0 | code+data+models (HiTZ/GoLLIE-7B/13B/34B) released | Models fine-tuned to follow code-formatted annotation guidelines (Python classes) on unseen schemas | 3 | admit | 7 |
| GPL: Generative Pseudo Labeling for Unsupervised Domain Adaptation of Dense Retrieval | Kexin Wang, Nandan Thakur, Nils Reimers et al. | 2021 | arXiv preprint | 2112.07577 | https://github.com/UKPLab/gpl | 342 | 2023-07-06 | Apache-2.0 | unverified | Query generation plus cross-encoder pseudo-labels plus hard negatives for label-free domain adaptation. | 3 | admit | 2,6 |
| GPT-NER: Named Entity Recognition via Large Language Models | Shuhe Wang, Xiaofei Sun, Xiaoya Li, Rongbin Ouyang, Fei Wu, Tianwei Zhang, Jiwei Li, Guoyin Wang | 2023 | Findings of NAACL 2025 | 2304.10428 | repo URL not captured | unknown | unknown | unknown | code+data stated released in paper | @@## marker-token copy formulation plus self-verification QA to suppress NULL-input hallucinations | 3 | admit | 7 |
| GRC: Unifying Reasoning-Driven Generation, Retrieval and Compression | Zhongtao Miao, Qiyu Wu, Yoshimasa Tsuruoka | 2026 | arXiv preprint | 2605.09100 |  |  |  | UNK | code unverified | Meta latent tokens plus unified generative/representational/compressive tuning unify generation, text representation and context compression in one forward pass. | 3 | admit | 4 |
| HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | Gutierrez et al. | 2024 | NeurIPS 2024 | 2405.14831 | https://github.com/OSU-NLP-Group/HippoRAG | 3999 | 2026-09-03 | MIT | yes (code + data) | Two-step OpenIE plus embedding synonym edges, single-step PPR retrieval; 10-30x cheaper / 6-13x faster than IRCoT | 3 | admit | 9 |
| How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings | Ethayarajh | 2019 | EMNLP-IJCNLP 2019 (per OpenAlex ACL record, secondary) | 1909.00512 |  |  |  |  | unknown | Compares the geometry of BERT, ELMo and GPT-2 embeddings (per title), the only admitted study covering a causal decoder. | 3 | admit | 6 |
| Hydra: Unifying Document Retrieval and Generation in a Single Vision-Language Model | Athos Georgiou | 2026 | arXiv preprint | 2603.28554 |  |  |  | UNK | code unverified | Single LoRA trained only for retrieval is toggled at inference: on gives ColBERT-style multi-vector embeddings, off recovers base generation with 426/426 LM tensors byte-identical; the cleanest adapter-switch measurement found. | 3 | admit | 4 |
| Hydragen: High-Throughput LLM Inference with Shared Prefixes | J. Juravsky, B. Brown, R. Ehrlich, D. Y. Fu, C. Re, A. Mirhoseini | 2024 | ICML 2024 ES-FoMo-II workshop | 2402.05099 | https://github.com/ScalingIntelligence/hydragen | 58 | 2024-05-10 | Apache-2.0 | yes (repo verified, stale) | Prefix/suffix attention decomposition; inter-sequence batching; up to 32x CodeLlama-13B throughput vs vLLM | 3 | admit | 8 |
| Improving Text Embeddings with Large Language Models | Liang Wang; Nan Yang; Xiaolong Huang; Linjun Yang; Rangan Majumder; Furu Wei | 2024 | arXiv preprint | 2401.00368 |  |  |  |  | yes (weights) | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. | 3 | admit | 1,2,3,4,5 |
| InPars: Data Augmentation for Information Retrieval using Large Language Models | Luiz Bonifacio, Hugo Abonizio, Marzieh Fadaee et al. | 2022 | arXiv preprint | 2202.05144 | https://github.com/zetaalphavector/InPars (community mirror; official code not located) | 201 | 2025-06-05 | Apache-2.0 | unverified | GPT-3 generated synthetic queries per document with consistency filtering, then standard finetune. | 3 | admit | 2,6 |
| INSTRUCTIR: A Benchmark for Instruction Following of Information Retrieval Models | Oh et al. | 2024 | arXiv preprint | 2402.14334 | https://github.com/kaistAI/InstructIR | 32 | 2024-06-13 | MIT | yes (HF dataset plus code) | Instance-wise user-aligned instructions with Robustness@10 metric; instruction-tuned retrievers can underperform. | 3 | admit | 5 |
| InstructUIE: Multi-task Instruction Tuning for Unified Information Extraction | Xiao Wang, Weikang Zhou, Can Zu, Han Xia, Tianze Chen, Yuansen Zhang, Rui Zheng, Junjie Ye, Qi Zhang, Tao Gui, Jihua Kang, Jingsheng Yang, Siyuan Li, Chunsai Du | 2023 | arXiv preprint | 2304.08085 | https://github.com/BeyonderXX/InstructUIE | 396 | 2025-02-28 | MIT | code+IE-INSTRUCTIONS (32 datasets) released | Instruction+options+text in, structured sentence out, with auxiliary span/typing subtasks | 3 | admit | 7 |
| IsoScore: Measuring the Uniformity of Embedding Space Utilization | Rudman, Gillman, Rayne, Eickhoff | 2021 | Findings of ACL 2022 (per OpenAlex, secondary) | 2108.07344 |  |  |  |  | unknown — repo not resolved | A score for how uniformly an embedding space is utilised (per title). | 3 | admit | 6 |
| iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models | Yassir Lairgi, Ludovic Moncla, Remy Cazabet, Khalid Benabdeslem, Pierre Cleau | 2024 | WISE 2024 | 2409.03284 | https://github.com/AuvaLab/itext2kg | 965 | 2026-09-04 | Apache-2.0 | code+data released | Four-module zero-shot pipeline separating entity and relation extraction with matcher-based resolution | 3 | admit | 7 |
| jina-embeddings-v3: Multilingual Embeddings With Task LoRA | Saba Sturua et al. | 2024 | arXiv preprint | 2409.10173 | no official training repo found (weights: jinaai/jina-embeddings-v3, 2.0M downloads) | n/a | n/a | CC-BY-NC-4.0 (weights) | yes (570M params, 8192 tokens) | 570M multilingual model with task-specific LoRA adapters; long-context retrieval | 3 | admit | 3,10 |
| KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | Belinda Mo, Kyssen Yu, Joshua Kazdan, Proud Mpala, Lisa Yu, Chris Cundy, Charilaos Kanatsoulis, Sanmi Koyejo | 2025 | NeurIPS 2025 | 2502.09956 | https://github.com/stair-lab/kg-gen | 1269 | 2026-03-24 | unverified | code+package+MINE benchmark released | Two-stage DSPy extraction (entities then relations) plus iterative LM clustering for resolution | 3 | admit | 7,9 |
| LightRAG: Simple and Fast Retrieval-Augmented Generation | Zirui Guo, Lianghao Xia, Yanhua Yu, Tu Ao, Chao Huang | 2024 | EMNLP 2025 Findings | 2410.05779 | https://github.com/HKUDS/LightRAG | 39594 | 2026-09-12 | MIT | code+prompts released | Single-pass LLM extraction of entities/relations plus keyword profiling and dedup | 3 | admit | 7,9 |
| LLM2Vec-Gen: Generative Embeddings from Large Language Models | Parishad BehnamGhader, Vaibhav Adlakha, Fabian David Schmidt, Nicolas Chapados, Marius Mosbach, Siva Reddy | 2026 | arXiv preprint | 2603.10913 | https://github.com/McGill-NLP/llm2vec-gen | 77 | 2026-04-05 | MIT | code yes / weights unverified | Trainable special tokens compress the frozen LLM's own potential response into a fixed-length embedding in output space, trained on unlabeled queries only; backbone stays frozen. | 3 | admit | 4 |
| LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | Parishad BehnamGhader; Vaibhav Adlakha; Marius Mosbach; Dzmitry Bahdanau; Nicolas Chapados; Siva Reddy | 2024 | arXiv preprint | 2404.05961 | https://github.com/McGill-NLP/llm2vec | 1714 | 2026-04-04 | MIT | yes (code+converted weights) | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. | 3 | admit | 1,2,4,5 |
| LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | Y. Liu, Y. Cheng, J. Yao, Y. An, X. Chen, S. Feng, Y. Huang, S. Shen, R. Zhang, K. Du, J. Jiang | 2025 | arXiv preprint | 2510.09665 | https://github.com/LMCache/LMCache | 11771 | 2026-09-12 | Apache-2.0 | yes (repo verified) | Engine-independent KV layer: chunked offload, PD disaggregation, CacheBlend non-prefix reuse; up to 15x vLLM throughput | 3 | admit | 8 |
| M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation | Jianlv Chen; Shitao Xiao; Peitian Zhang; Kun Luo; Defu Lian; Zheng Liu | 2024 | arXiv preprint | 2402.03216 | https://github.com/FlagOpen/FlagEmbedding | 12153 | 2026-08-24 | MIT | yes (weights+code) | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. | 3 | admit | 1,2,3,10 |
| MAGNET: Augmenting Generative Decoders with Representation Learning and Infilling Capabilities | Savya Khosla, Aditi Tiwari, Kushal Kafle, Simon Jenni, Handong Zhao, John Collomosse, Jing Shi | 2025 | arXiv preprint | 2501.08648 |  |  |  | UNK | code unverified | Three self-supervised objectives plus a new attention mechanism adapt a decoder-only LLM to emit robust representations and infill spans while staying generative. | 3 | admit | 4 |
| Making Text Embedders Few-Shot Learners | Li et al. | 2024 | arXiv preprint | 2409.15700 | https://github.com/FlagOpen/FlagEmbedding | 12153 | 2026-08-24 | MIT | yes (model weights per paper; BAAI org on HF, URL unopened) | Train with 0-5 sampled in-context examples prepended to queries so the embedder gains few-shot ability without losing zero-shot. | 3 | admit | 5 |
| Matryoshka Representation Learning | Aditya Kusupati; Gantavya Bhatt; Aniket Rege; Matthew Wallingford; Aditya Sinha; Vivek Ramanujan; William Howard-Snyder; Kaifeng Chen; Sham Kakade; Prateek Jain; Ali Farhadi | 2022 | arXiv preprint | 2205.13147 |  |  |  |  | method only | Nested coarse-to-fine representation; truncate dims at query time, no retraining. | 3 | admit | 1,3,10 |
| MemServe: Context Caching for Disaggregated LLM Serving with Elastic Memory Pool | C. Hu, H. Huang, J. Hu, J. Xu, X. Chen, T. Xie, C. Wang, S. Wang, Y. Bao, N. Sun, Y. Shan | 2024 | arXiv preprint | 2406.17565 | - | - | - | - | unknown | MemPool unifying context caching + disaggregated inference; global prompt-tree routing; JCT/TTFT cuts up to 53%/85% | 3 | admit | 8 |
| mergekit: tools for merging pretrained large language models | arcee-ai contributors | 2024 | n/a (tool) | n/a | https://github.com/arcee-ai/mergekit | 7347 | 2026-09-12 | LGPL-3.0 | tool released (conda/pip) | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with its generative base. | 3 | admit | 3,4,7,9 |
| Meta-Task Prompting Elicits Embeddings from Large Language Models | Lei et al. | 2024 | ACL 2024 | 2402.18458 | https://github.com/Yibin-Lei/MetaEOL | 12 | 2024-07-25 | unverified | no (code only) | Average embeddings over eight meta-task prompts with explicit one-word limitation, no training. | 3 | admit | 5 |
| MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers | Wang, Wenhui; Wei, Furu; Dong, Li; Bao, Hangbo; Yang, Nan; Zhou, Ming | 2020 | arXiv preprint | 2002.10957 | - |  |  | n/a (paper) | yes | Distill last-layer attention + value relations; 6-layer student 2.0x faster at >99% accuracy | 3 | admit | 10 |
| MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | Tianyu Fan, Jingyuan Wang, Xubin Ren, Chao Huang | 2025 | ACL 2026 | 2501.06713 | https://github.com/HKUDS/MiniRAG | 2013 | 2025-10-16 | MIT | code+LiHua-World benchmark released | SLM-friendly design: entity extraction (not abstract summarization) as the small-model task | 3 | admit | 7,9 |
| MMTEB: Massive Multilingual Text Embedding Benchmark | Kenneth Enevoldsen; Isaac Chung; Imene Kerboua; Márton Kardos; Ashwin Mathur; David Stap; Jay Gala; Wissam Siblini; Dominik Krzemiński; Genta Indra Winata; Saba Sturua; Saiteja Utpala; Mathieu Ciancone; Marion Schaeffer; Gabriel Sequeira; Diganta Misra; Shreeya Dhakal; Jonathan Rystrøm; Roman Solomatin; Ömer Çağatan; Akash Kundu; Martin Bernstorff; Shitao Xiao; Akshita Sukhlecha; Bhavish Pahwa; Rafał Poświata; Kranthi Kiran GV; Shawon Ashraf; Daniel Auras; Björn Plüster; Jan Philipp Harries; Loïc Magne; Isabelle Mohr; Mariya Hendriksen; Dawei Zhu; Hippolyte Gisserot-Boukhlef; Tom Aarsen; Jan Kostkan; Konrad Wojtasik; Taemin Lee; Marek Šuppa; Crystina Zhang; Roberta Rocca; Mohammed Hamdy; Andrianos Michail; John Yang; Manuel Faysse; Aleksei Vatolin; Nandan Thakur; Manan Dey; Dipam Vasani; Pranjal Chitale; Simone Tedeschi; Nguyen Tai; Artem Snegirev; Michael Günther; Mengzhou Xia; Weijia Shi; Xing Han Lù; Jordan Clive; Gayatri Krishnakumar; Anna Maksimova; Silvan Wehrli; Maria Tikhonova; Henil Panchal; Aleksandr Abramov; Malte Ostendorff; Zheng Liu; Simon Clematide; Lester James Miranda; Alena Fenogenova; Guangyu Song; Ruqiya Bin Safi; Wen-Ding Li; Alessia Borghini; Federico Cassano; Hongjin Su; Jimmy Lin; Howard Yen; Lasse Hansen; Sara Hooker; Chenghao Xiao; Vaibhav Adlakha; Orion Weller; Siva Reddy; Niklas Muennighoff | 2025 | arXiv preprint | 2502.13595 |  |  |  |  | yes (benchmark code+data) | 500+ tasks, 250+ languages; LLM-embedders lead some languages, not uniformly. | 3 | admit | 1,6 |
| Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | R. Qin, Z. Li, W. He, M. Zhang, Y. Wu, W. Zheng, X. Xu | 2024 | FAST 2025 | 2407.00079 | https://github.com/kvcache-ai/Mooncake | 6562 | 2026-09-12 | Apache-2.0 | yes (repo + transfer engine) | KVCache-centric disaggregation + Conductor scheduler + early rejection; Kimi +75% requests; TE 87-190 GB/s | 3 | admit | 8 |
| MTEB: Massive Text Embedding Benchmark | Niklas Muennighoff; Nouamane Tazi; Loïc Magne; Nils Reimers | 2022 | arXiv preprint | 2210.07316 |  |  |  |  | yes (benchmark code+data) | 58 datasets x 8 tasks; no single method dominates all tasks. | 3 | admit | 1,6 |
| Nomic Embed: Training a Reproducible Long Context Text Embedder | Zach Nussbaum et al. | 2024 | TMLR (accepted) | 2402.01613 | https://github.com/nomic-ai/contrastors | 802 | 2025-03-26 | Apache-2.0 | yes (nomic-ai/nomic-embed-text-v1, 3.5M downloads; data + code released) | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 | 3 | admit | 1,2,3,10 |
| NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | Chankyu Lee; Rajarshi Roy; Mengyao Xu; Jonathan Raiman; Mohammad Shoeybi; Bryan Catanzaro; Wei Ping | 2024 | arXiv preprint | 2405.17428 |  |  |  |  | yes (weights) | Latent-attention pooling beats mean/last-token; causal mask removed for contrastive train; 2-stage instruction tuning. | 3 | admit | 1,2,5 |
| On the Sentence Embeddings from Pre-trained Language Models | Li, Zhou, He, Wang, Yang, Li | 2020 | EMNLP 2020 (per arXiv abs page) | 2011.05864 |  |  |  |  | code linked from paper | Diagnoses anisotropic BERT sentence space, fixes it with unsupervised normalising flows. | 3 | admit | 6 |
| One Embedder Any Task: Instruction-Finetuned Text Embeddings | Su et al. | 2022 | ACL 2023 Findings | 2212.09741 | https://github.com/xlang-ai/instructor-embedding | 2022 | 2025-01-15 | Apache-2.0 | yes (hkunlp/instructor-base-large-xl on HF) | Concatenate a natural-language task instruction to every input and contrastive-train one encoder on 330 tasks. | 3 | admit | 5 |
| One prompt is not enough: Instruction Sensitivity Undermines Embedding Model Evaluation | Kostiuk and Enevoldsen | 2026 | arXiv preprint | 2605.22544 | unverified | unverified | unverified | unverified | no (code per paper, URL unopened) | Fifteen prompts per task over 6 models and 11 datasets show single-prompt scores misrepresent the distribution and rankings are gameable. | 3 | admit | 5 |
| OneGen: Efficient One-Pass Unified Generation and Retrieval for LLMs | Jintian Zhang, Cheng Peng, Mengshu Sun, Xiang Chen, Lei Liang, Zhiqiang Zhang, Jun Zhou, Huajun Chen, Ningyu Zhang | 2024 | EMNLP 2024 | 2409.05152 | https://github.com/zjunlp/OneGen | 148 | 2024-11-13 | MIT | code yes / weights on HF (zjunlp org, unverified count) | One forward pass emits retrieval tokens and generation tokens together via retrieval-token markers; single-pass RAG/EL without a separate retriever call. | 3 | admit | 4 |
| Orca: A Distributed Serving System for Transformer-Based Generative Models | G.-I. Yu, J. S. Jeong, G.-W. Kim, S. Kim, B.-G. Chun | 2022 | OSDI 2022 | doi:10.5555/3542929.3542970 (no arXiv) | https://www.usenix.org/conference/osdi22/presentation/yu | - | - | - | no public code | Iteration-level (continuous) batching + selective batching; 36.9x throughput vs FasterTransformer on GPT-3 175B | 3 | admit | 8 |
| PLAID: An Efficient Engine for Late Interaction Retrieval | Santhanam, Keshav; Khattab, Omar; Potts, Christopher; Zaharia, Matei | 2022 | arXiv preprint | 2205.09707 | - |  |  | n/a (paper) | unknown | Centroid interaction + pruning engine: 2.5-6.8x GPU / 9.2-45x CPU speedups at 140M passages | 3 | admit | 10 |
| Preble: Efficient Distributed Prompt Scheduling for LLM Serving | V. Srivatsa, Z. He, R. Abhyankar, D. Li, Y. Zhang | 2024 | ICLR 2025 | 2407.00023 | - | - | - | - | unknown (promised on acceptance) | E2 exploit/explore scheduler co-optimising KV reuse + load balance; 1.5-14.5x avg latency, 2-10x p99 | 3 | admit | 8 |
| Prompt Cache: Modular Attention Reuse for Low-Latency Inference | I. Gim, G. Chen, S. Lee, N. Sarda, A. Khandelwal, L. Zhong | 2023 | MLSys 2024 | 2311.04934 | - | - | - | - | unknown | Schema-declared prompt modules with position-correct KV reuse; 8x GPU / 60x CPU TTFT cuts | 3 | admit | 8 |
| Promptagator: Few-shot Dense Retrieval From 8 Examples | Zhuyun Dai, Vincent Y. Zhao, Ji Ma et al. | 2022 | arXiv preprint | 2209.11755 | none located (Google-internal FLAN pipeline) | n/a | n/a | n/a | unverified | Few-shot prompted LLM writes per-task synthetic queries, then task-specific dual-encoder training. | 3 | admit | 2,6 |
| Promptriever: Instruction-Trained Retrievers Can Be Prompted Like Language Models | Weller et al. | 2024 | ICLR 2025 | 2409.11136 | https://github.com/orionw/promptriever | 93 | 2025-05-08 | unverified | yes (samaya-ai/promptriever-* on HF plus msmarco-w-instructions dataset) | Per-instance instruction training with instruction negatives makes a bi-encoder promptable like an LM. | 3 | admit | 5 |
| QLoRA: Efficient Finetuning of Quantized LLMs | Tim Dettmers, Artidoro Pagnoni, Ari Holtzman et al. | 2023 | arXiv preprint | 2305.14314 | https://github.com/artidoro/qlora | 11013 | 2024-06-10 | MIT | n/a (method, not a model) | Frozen 4-bit base with LoRA adapters; 65B fine-tunable on one 48GB GPU at full 16-bit quality. | 3 | admit | 2 |
| Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | Yanzhao Zhang; Mingxin Li; Dingkun Long; Xin Zhang; Huan Lin; Baosong Yang; Pengjun Xie; An Yang; Dayiheng Liu; Junyang Lin; Fei Huang; Jingren Zhou | 2025 | arXiv preprint | 2506.05176 | https://github.com/QwenLM/Qwen3-Embedding | 2030 | 2025-09-30 | not stated (API null) | yes (weights 0.6B/4B/8B) | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. | 3 | admit | 1,2,3,5 |
| Repetition Improves Language Model Embeddings | Jacob Mitchell Springer; Suhas Kotha; Daniel Fried; Graham Neubig; Aditi Raghunathan | 2024 | arXiv preprint | 2402.15449 |  |  |  |  | method only | Repeat-input prompting gives causal LMs bidirectional-like embeddings, +5% zero-shot, no training. | 3 | admit | 1,5 |
| Representation Degeneration Problem in Training Natural Language Generation Models | Gao, He, Tan, Qin, Wang, Liu | 2019 | arXiv preprint | 1907.12009 |  |  |  |  | unknown | Diagnoses why likelihood training degenerates token-embedding geometry (per title). | 3 | admit | 6 |
| Resources for Brewing BEIR: Reproducible Reference Models and an Official Leaderboard | Kamalloo, Thakur, Lassance, Ma, Yang, Lin | 2023 | arXiv preprint (project README cites SIGIR 2024) | 2306.07471 | https://github.com/beir-cellar/beir | 2288 | 2025-10-16 | Apache-2.0 | yes — reference models + official leaderboard (per paper title) | Reproducible BEIR baselines plus effect-size meta-analysis replacing naive cross-dataset averaging. | 3 | admit | 6 |
| Rethinking the Role of Token Retrieval in Multi-Vector Retrieval (XTR) | Lee, Jinhyuk; Dai, Zhuyun; Duddu, Sai Meher Karthik; Lei, Tao; Naim, Iftekhar; Chang, Ming-Wei; Zhao, Vincent Y. | 2023 | arXiv preprint | 2304.01982 | - |  |  | n/a (paper) | unknown | Retrieve-top-tokens objective; +2.8 nDCG@10 on BEIR; scoring stage 4000x fewer FLOPs | 3 | admit | 4,10 |
| RetroLLM: Empowering Large Language Models to Retrieve Fine-grained Evidence within Generation | Xiaoxi Li, Jiajie Jin, Yujia Zhou, Yongkang Wu, Zhonghua Li, Qi Ye, Zhicheng Dou | 2024 | ACL 2025 | 2412.11919 | https://github.com/sunnynexus/RetroLLM | 116 | 2025-01-23 | MIT | code yes / weights unverified | One LLM integrates retrieval and generation in a single process, generating fine-grained evidence from the corpus via constrained decoding; removes the separate retriever. | 3 | admit | 4 |
| RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering | Yingqi Qu, Yuchen Ding, Jing Liu et al. | 2020 | arXiv preprint | 2010.08191 | https://github.com/PaddlePaddle/RocketQA | 784 | 2023-12-19 | Apache-2.0 | unverified | Cross-batch negatives, denoised hard negatives, and data augmentation for dual-encoders. | 3 | admit | 2 |
| SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills | A. Agrawal, A. Panwar, J. Mohan, N. Kwatra, B. Gulavani, R. Ramjee | 2023 | arXiv preprint | 2308.16369 | - | - | - | - | unknown | Chunked prefills + decode-maximal batching; decode piggybacking; up to 10x decode throughput (LLaMA-13B/A6000) | 3 | admit | 8 |
| Scaling Sentence Embeddings with Large Language Models | Jiang et al. | 2023 | EMNLP 2024 Findings | 2307.16645 | unverified | unverified | unverified | unverified | unverified | The This-sentence-means-in-one-word template plus in-context demonstrations for training-free decoder embeddings. | 3 | admit | 5 |
| Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | Nils Reimers; Iryna Gurevych | 2019 | arXiv preprint | 1908.10084 | https://github.com/huggingface/sentence-transformers | 19092 | 2026-09-11 | Apache-2.0 | yes (weights+code) | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. | 3 | admit | 1,2,3,6,10 |
| SGLang: Efficient Execution of Structured Language Model Programs | L. Zheng, L. Yin, Z. Xie, C. Sun, J. Huang, C. H. Yu, S. Cao, C. Kozyrakis, I. Stoica, J. Gonzalez, C. Barrett, Y. Sheng | 2023 | arXiv preprint | 2312.07104 | https://github.com/sgl-project/sglang | 35852 | 2026-09-12 | Apache-2.0 | yes (engine) | RadixAttention tree-structured KV reuse across forked programs; compressed FSM for structured decode; up to 6.4x throughput | 3 | admit | 8 |
| SimCSE: Simple Contrastive Learning of Sentence Embeddings | Tianyu Gao, Xingcheng Yao, Danqi Chen | 2021 | EMNLP 2021 | 2104.08821 | https://github.com/princeton-nlp/SimCSE | 3652 | 2024-10-16 | MIT | unverified | Dropout-as-augmentation unsupervised positives; supervised NLI entailment/contradiction variant. | 3 | admit | 2,6 |
| SPANN: Highly-efficient Billion-scale Approximate Nearest Neighbor Search | Chen, Qi; Zhao, Bing; Wang, Haidong; Li, Mingqin; Liu, Chuanjie; Li, Zengzhong; Yang, Mao; Wang, Jingdong | 2021 | Accepted to NeurIPS 2021 (abs page) | 2111.08566 | https://github.com/microsoft/SPTAG |  |  | MIT (via SPTAG repo) | yes | Memory-disk hybrid inverted index; 2x faster than DiskANN at 90% recall, ~1ms, 32GB | 3 | admit | 10 |
| SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval | Thibault Formal; Carlos Lassance; Benjamin Piwowarski; Stéphane Clinchant | 2021 | arXiv preprint | 2109.10086 | https://github.com/naver/splade | 1011 | 2024-05-03 | NOASSERTION | yes (weights+code) | MLM-head sparse expansion with FLOPS regularization; inverted-index retrieval. | 3 | admit | 1,10 |
| Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | A. Agrawal, N. Kedia, A. Panwar, J. Mohan, N. Kwatra, B. Gulavani, A. Tumanov, R. Ramjee | 2024 | arXiv preprint | 2403.02310 | - | - | - | - | yes (paper states source available) | Stall-free chunked-prefill scheduler; 2.6x capacity vs vLLM (Mistral-7B/1xA100), up to 5.6x with pipeline parallelism | 3 | admit | 8 |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training | Liang Wang; Nan Yang; Xiaolong Huang; Binxing Jiao; Linjun Yang; Daxin Jiang; Rangan Majumder; Furu Wei | 2022 | arXiv preprint | 2212.03533 |  |  |  |  | yes (weights) | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. | 3 | admit | 1,2,3,6,10 |
| Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | Nandana Mihindukulasooriya, Sanju Tiwari, Carlos F. Enguix, Kusum Lata | 2023 | ISWC 2023 | 2308.02357 | https://github.com/cenguix/Text2KGBench | 92 | 2024-05-06 | Apache-2.0 (data CC BY 4.0) | benchmark+code+prompts released | Ontology-guided fact extraction task with 7 metrics for extraction, conformance, hallucination | 3 | admit | 7 |
| Understanding Contrastive Representation Learning through Alignment and Uniformity on the Hypersphere | Wang, Isola | 2020 | ICML 2020 (per arXiv abs page) | 2005.10242 |  |  |  |  | code linked from paper page | Contrastive loss asymptotically optimises alignment of positives plus uniformity on the hypersphere. | 3 | admit | 6 |
| Unified Structure Generation for Universal Information Extraction | Yaojie Lu, Qing Liu, Dai Dai, Xinyan Xiao, Hongyu Lin, Xianpei Han, Le Sun, Hua Wu | 2022 | ACL 2022 | 2203.12277 | https://github.com/universal-ie/UIE | 955 | 2022-07-30 | unverified | code+model stated released | SEL linearization plus structural schema instructor (spot/associate/generate control) | 3 | admit | 7 |
| UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recognition | Wenxuan Zhou, Sheng Zhang, Yu Gu, Muhao Chen, Hoifung Poon | 2023 | ICLR 2024 | 2308.03279 | https://github.com/universal-ner/universal-ner | 375 | 2023-12-04 | MIT | recipe+data+models (UniNER-7B/13B) released | ChatGPT-distilled open NER via mission-focused instruction tuning on diverse web text | 3 | admit | 7 |
| Unsupervised Dense Information Retrieval with Contrastive Learning | Gautier Izacard, Mathilde Caron, Lucas Hosseini et al. | 2021 | arXiv preprint | 2112.09118 | https://github.com/facebookresearch/contriever | 779 | 2023-04-07 | NOASSERTION | unverified | Unsupervised contrastive pretraining with ICT and cropping augmentations. | 3 | admit | 2,6 |
| vLLM serving engine (repo + docs) | vLLM project | 2023 | software | - | https://github.com/vllm-project/vllm | 91577 | 2026-09-12 | Apache-2.0 | yes (runnable engine) | APC via enable_prefix_caching with hash-chained KV blocks + cache_salt tenant isolation; chunked prefill + continuous batching built in | 3 | admit | 8,10 |
| Whitening Sentence Representations for Better Semantics and Faster Retrieval | Su, Cao, Liu, Ou | 2021 | arXiv preprint | 2103.15316 | https://github.com/bojone/BERT-whitening | 486 | 2021-06-17 | none declared | yes — reference code | Closed-form whitening (mean-subtract + PCA-whiten + truncate) fixes anisotropy and speeds retrieval. | 3 | admit | 6 |
| Zep: A Temporal Knowledge Graph Architecture for Agent Memory | Preston Rasmussen, Pavlo Paliychuk, Travis Beauvais, Jack Ryan, Daniel Chalef | 2025 | arXiv preprint | 2501.13956 | https://github.com/getzep/graphiti | 30832 | 2026-09-11 | Apache-2.0 | code (Graphiti) released | Episodic ingest with entity/fact/temporal extraction, edge dedup and bi-temporal invalidation | 3 | admit | 7,9 |
| Zero- and Few-Shots Knowledge Graph Triplet Extraction with Large Language Models | Andrea Papaluca, Daniel Krefl, Sergio Rodriguez Mendez, Artem Lensky, Hanna Suominen | 2023 | KaLLM 2024 workshop | 2312.01954 | repo URL not captured | unknown | unknown | unknown | artefact status unverified | Head-to-head triplet-extraction prompts across LLM sizes in zero- and few-shot settings | 3 | admit | 7 |
| Zero-Shot Information Extraction via Chatting with ChatGPT | Xiang Wei, Xingyu Cui, Ning Cheng, Xiaobin Wang, Xin Zhang, Shen Huang, Pengjun Xie, Jinan Xu, Yufeng Chen, Meishan Zhang | 2023 | arXiv preprint | 2302.10205 | https://github.com/cocacola-lab/chatie | 826 | 2024-05-28 | NOASSERTION-listed | code/demo released | Two-stage multi-turn QA: find candidate types first, then chain-extract per type | 3 | admit | 7 |
| A Unified Model and Document Representation for On-Device Retrieval-Augmented Generation | Julian Killingback, Ofer Meshi, Henry Li, Hamed Zamani, Maryam Karimzadehgan | 2026 | arXiv preprint | 2604.14403 |  |  |  | UNK | code unverified | Unified model+document representation so the whole RAG pipeline runs on-device for private local querying; small-model unified relevance. | 2 | admit | 4 |
| Activation-Informed Merging of Large Language Models | Amin Heyrani Nobari, Kaveh Alim, Ali ArjomandBigdeli, Akash Srivastava, Faez Ahmed, Navid Azizan | 2025 | arXiv preprint | 2502.02421 |  |  |  | UNK | code unverified | AIM folds activation-space information into any merging method to preserve critical base weights; a guard against generation degradation when merging an embed-tuned model home. | 2 | admit | 4 |
| AIR-Bench: Automated Heterogeneous Information Retrieval Benchmark | Chen, Wang, Li, Wang, Xiao, Xiao, Liao, Lian, Liu | 2024 | arXiv preprint (ACL 2025 per OpenAlex, secondary) | 2412.13102 |  |  |  |  | unknown — see paper | Automated heterogeneous IR benchmark (per title); the closest public recipe for private-corpus eval sets. | 2 | admit | 6 |
| Answer is All You Need: Instruction-following Text Embedding via Answering the Question | Peng et al. | 2024 | ACL 2024 | 2402.09642 | https://github.com/zhang-yu-wei/InBedder | 31 | 2024-10-11 | MIT | yes (code, dataset, pretrained models per repo) | Embed the expected answer to the instruction-as-question instead of the instruction-text concatenation, trained on abstractive QA only. | 2 | admit | 5 |
| ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | Saad-Falcon, Khattab, Potts, Zaharia | 2023 | NAACL 2024 (per OpenAlex, secondary) | 2311.09476 | https://github.com/stanford-futuredata/ARES | 732 | 2025-03-28 | Apache-2.0 | yes — code | Automated RAG-system eval over synthetic queries and judgments (per title). | 2 | admit | 6 |
| Bagging-Based Model Merging for Robust General Text Embeddings | Hengran Zhang, Keping Bi, Jiafeng Guo, Jiaming Zhang, Wenbo Yang, Daiting Shi, Xueqi Cheng | 2026 | arXiv preprint | 2602.05787 |  |  |  | UNK | code unverified | Systematic study of multi-task embedding training (scheduling) vs model merging for general embeddings and domain adaptation; merging as an alternative to joint training. | 2 | admit | 4 |
| BIRCO: A Benchmark of Information Retrieval Tasks with Complex Objectives | Wang, Wang, Cao, Wang, Paturi, Bergen | 2024 | arXiv preprint | 2402.14151 |  |  |  |  | unknown — see paper | Retrieval tasks with complex objectives (per title). | 2 | admit | 6 |
| C-Pack: Packed Resources For General Chinese Embeddings | Shitao Xiao et al. | 2023 | arXiv preprint | 2309.07597 | https://github.com/FlagOpen/FlagEmbedding | 12153 | 2026-08-24 | MIT (code) | yes (BGE small/base/large; bge-small-en-v1.5, 64M downloads, MIT) | BGE-family training resources: data, small-model baselines, C-MTEB evaluation | 2 | admit | 1,3,10 |
| Decoding on Graphs: Faithful and Sound Reasoning on Knowledge Graphs through Generation of Well-Formed Chains | Kun Li, Tianhua Zhang, Xixin Wu, Hongyin Luo, James Glass, Helen Meng | 2024 | ACL 2025 | 2410.18415 | repo URL not captured | unknown | unknown | unknown | artefact status unverified | KG-topology token mask forces well-formed triplet chains during generation | 2 | admit | 7 |
| DeepSpeed-FastGen: High-throughput Text Generation for LLMs via MII and DeepSpeed-Inference | C. Holmes, M. Tanaka, M. Wyatt, A. A. Awan, J. Rasley, S. Rajbhandari, R. Y. Aminabadi, H. Qin, A. Bakhtiari, L. Kurilenko, Y. He | 2024 | arXiv preprint | 2401.08671 | https://github.com/deepspeedai/DeepSpeed | - | - | Apache-2.0 | yes (in DeepSpeed repo) | Dynamic SplitFuse token-budget batching; 2.3x effective throughput, 2x avg latency vs vLLM | 2 | admit | 8 |
| Document Ranking with a Pretrained Sequence-to-Sequence Model | Nogueira, Rodrigo; Jiang, Zhiying; Lin, Jimmy | 2020 | arXiv preprint | 2003.06713 | - |  |  | n/a (paper) | unknown | Relevance labels as target words; T5-base MRR@10 0.363, T5-large 0.383 on MS MARCO | 2 | admit | 10 |
| EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees | Y. Li, F. Wei, C. Zhang, H. Zhang | 2024 | EMNLP 2024 | 2406.16858 | - | - | - | - | unknown | Confidence-driven dynamic draft trees, no extra training over EAGLE; 3.05-4.26x, 20-40% over EAGLE | 2 | admit | 8 |
| EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty | Y. Li, F. Wei, C. Zhang, H. Zhang | 2024 | ICML 2024 | 2401.15077 | - | - | - | - | unknown | Feature-level autoregression + shifted tokens; 2.7-3.5x latency cut on LLaMA2-Chat 70B, 2x throughput | 2 | admit | 8 |
| Editing Models with Task Arithmetic | Gabriel Ilharco, Marco Tulio Ribeiro, Mitchell Wortsman, Suchin Gururangan, Ludwig Schmidt, Hannaneh Hajishirzi, Ali Farhadi | 2022 | arXiv preprint | 2212.04089 |  |  |  | UNK | code unverified | Add/subtract task vectors (fine-tune minus base) to steer one set of weights toward combined behaviours without joint retraining. | 2 | admit | 4 |
| Embedding And Clustering Your Data Can Improve Contrastive Pretraining | Luke Merrick | 2024 | arXiv preprint | 2407.18887 | https://github.com/Snowflake-Labs/arctic-embed | 91 | 2025-11-03 | Apache-2.0 | yes (method used in arctic-embed-v2) | Cluster-aware sampling for contrastive pretraining data; quality over quantity | 2 | admit | 3 |
| FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | T. Dao, D. Y. Fu, S. Ermon, A. Rudra, C. Re | 2022 | arXiv preprint | 2205.14135 | - | - | - | - | unknown | IO-aware tiled exact attention; 15% BERT-large e2e, 3x GPT-2 train speedups; basis of all serving kernels | 2 | admit | 8 |
| From Louvain to Leiden: guaranteeing well-connected communities | Traag et al. | 2019 | Scientific Reports 9:5233 | 1810.08473 |  |  |  |  | yes (paper; implementation separate) | Leiden community detection with connectivity guarantees; faster and better partitions than Louvain | 2 | admit | 9 |
| GEM: A Generative Embedding Model Bridging Reasoning and Retrieval | Zhili Shen, Craig Macdonald | 2026 | arXiv preprint | 2608.13200 |  |  |  | UNK | code unverified | One model reasons over the query in generation mode, then appends an embedding token encoding the enriched context for retrieval; evaluated on reasoning-intensive retrieval. | 2 | admit | 4 |
| Generating Structured Outputs from Language Models: Benchmark and Studies | Saibo Geng, Hudson Cooper, Michal Moskal, Samuel Jenkins, Julian Berman, Nathan Ranchin, Robert West, Eric Horvitz, Harsha Nori | 2025 | arXiv preprint | 2501.10868 | repo URL not captured | unknown | unknown | unknown | benchmark stated released in paper | 10K real-world JSON schemas comparing 6 constrained-decoding frameworks on efficiency/coverage/quality | 2 | admit | 7 |
| GenIE: Generative Information Extraction | Martin Josifoski, Nicola De Cao, Maxime Peyrard, Fabio Petroni, Robert West | 2022 | NAACL 2022 | 2112.08340 | repo URL not captured | unknown | unknown | unknown | code+data+models stated released in paper | Autoregressive closed IE with bi-level trie-constrained beam search over KB schema | 2 | admit | 7 |
| Giga-Embeddings: Mixture-of-Experts Encoders for High-Throughput Text Embeddings | Egor Kolodin, Egor Krasnoperov, Evgeniy Kosarev, Fyodor Minkin | 2026 | arXiv preprint | 2608.23806 |  |  |  | UNK | code unverified | Sparse 10B MoE encoder (1.8B active/token) tops its family on four MTEB suites and reports 114.5k tok/s in vLLM at 1024-token inputs; MoE embedder evidence with throughput numbers. | 2 | admit | 4 |
| Granite Embedding Models | Parul Awasthy et al. | 2025 | arXiv preprint | 2502.20204 | not-verified | not-fetched | not-fetched | not-fetched | yes (ibm-granite/granite-embedding-125m-english, 117k downloads; Apache-2.0) | 125M RoBERTa-style embedder family with enterprise retrieval focus | 2 | admit | 3 |
| Improving General Text Embedding Model: Tackling Task Conflict and Data Imbalance through Model Merging | Mingxin Li, Zhijie Nie, Yanzhao Zhang, Daiting Long, Richong Zhang, Pengjun Xie | 2024 | arXiv preprint | 2410.15035 |  |  |  | UNK | code unverified | Joint multi-task embedding training shows task-conflict gradient interference; merging per-task models beats joint training for general embedders. | 2 | admit | 4 |
| InPars-v2: Large Language Models as Efficient Dataset Generators for Information Retrieval | Jeronymo, Bonifacio, Abonizio, Fadaee, Lotufo, Zavrel, Nogueira | 2023 | arXiv preprint | 2301.01820 |  |  |  |  | unknown — toolkit repo not resolved | Efficient LLM synthetic query-generation recipe for retrieval datasets. | 2 | admit | 6 |
| Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions | Trivedi et al. | 2023 | ACL 2023 | 2212.10509 | https://github.com/stonybrooknlp/ircot (from paper, not separately verified) | unverified | unverified | unverified | yes (code + data + prompts per paper) | Alternate CoT-reason and retrieve steps; the expensive iterative baseline HippoRAG beats 10-30x on cost | 2 | admit | 9 |
| Iterative Zero-Shot LLM Prompting for Knowledge Graph Construction | Salvatore Carta, Alessandro Giuliani, Leonardo Piano, Alessandro Sebastian Podda, Livio Pompianu, Sandro Gabriele Tiddia | 2023 | arXiv preprint | 2307.01128 | repo URL not captured | unknown | unknown | unknown | artefact status unverified | Iterative zero-shot prompts per graph component without examples or external resources | 2 | admit | 7 |
| Language Models are Super Mario: Absorbing Abilities from Homologous Models as a Free Lunch | Le Yu, Bowen Yu, Haiyang Yu, Fei Huang, Yongbin Li | 2023 | arXiv preprint | 2311.03099 |  |  |  | UNK | code unverified | DARE drops most delta parameters then rescales, so merged homologous models keep abilities with no retraining or GPU; sparsified merges preserve more of each parent. | 2 | admit | 4 |
| LazyGraphRAG: Setting a new standard for quality and cost | Microsoft Research | 2024 | n/a (vendor blog) | n/a (https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) | n/a | n/a | n/a | n/a | n/a (method integrated into GraphRAG/Discovery) | Deferred-LLM indexing (NLP noun phrases + co-occurrence); indexing cost 0.1% of GraphRAG, query budget scales quality | 2 | admit | 9 |
| Linq-Embed-Mistral Technical Report | Choi et al. | 2024 | arXiv preprint | 2412.03223 | unverified | unverified | unverified | unverified | yes (model release claimed in paper; HF URL unopened) | E5-Mistral fine-tune with task-tailored data crafting and one-sided instruction prefixes; documents encoded once and cached. | 2 | admit | 5 |
| LLM-based Embeddings: Attention Values Encode Sentence Semantics Better Than Hidden States | Yeqin Zhang, Yunfei Wang, Jiaxuan Chen, Ke Qin, Yizheng Zhao, Cam-Tu Nguyen | 2026 | arXiv preprint | 2602.01572 |  |  |  | UNK | code unverified | Value Aggregation pools attention value vectors across layers/tokens and reportedly beats hidden-state pooling training-free; a cheap-version candidate reusing generative states. | 2 | admit | 4 |
| Llumnix: Dynamic Scheduling for Large Language Model Serving | B. Sun, Z. Huang, H. Zhao, W. Xiao, X. Zhang, Y. Li, W. Lin | 2024 | OSDI 2024 | 2406.03243 | https://github.com/llumnix-project/llumnix-ray | 562 | 2026-03-12 | Apache-2.0 | yes (repo verified) | Live migration of requests + KV state across instances; 10x tail-latency cut, 36% cost saving | 2 | admit | 8 |
| LM-Cocktail: Resilient Tuning of Language Models via Model Merging | Shitao Xiao, Zheng Liu, Peitian Zhang, Xingrun Xing | 2023 | arXiv preprint | 2311.13534 |  |  |  | UNK | code unverified | Merge a fine-tuned model back toward its base to recover general ability while keeping target-task gains; directly measures the generation side of the trade-off. | 2 | admit | 4 |
| Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads | T. Cai, Y. Li, Z. Geng, H. Peng, J. D. Lee, D. Chen, T. Dao | 2024 | arXiv preprint | 2401.10774 | - | - | - | - | yes (paper states code available) | Extra decoding heads + tree attention; Medusa-1 2.2x lossless frozen, Medusa-2 2.3-3.6x with joint tuning | 2 | admit | 8 |
| Merging: Resolving Interference When Merging Models | Prateek Yadav, Derek Tam, Leshem Choshen, Colin Raffel, Mohit Bansal | 2023 | arXiv preprint | 2306.01708 |  |  |  | UNK | code unverified | Trim low-magnitude deltas, elect per-parameter sign, merge disjoint means; reduces interference when fusing models tuned from one base. | 2 | admit | 4 |
| MS MARCO: A Human Generated MAchine Reading COmprehension Dataset | Bajaj, Campos, Craswell, Deng, Gao, Liu, Majumder, McNamara, Mitra, Nguyen, Rosenberg, Song | 2016 | arXiv preprint | 1611.09268 |  |  |  |  | yes — passage dataset (microsoft.github.io/msmarco) | Large-scale human-generated queries for passage ranking and comprehension (per title). | 2 | admit | 6 |
| Multilingual E5 Text Embeddings: A Technical Report | Wang et al. | 2024 | MSR tech report / arXiv | 2402.05672 | https://github.com/microsoft/unilm/tree/master/e5 | 22213 | 2026-08-26 | MIT | yes (intfloat/multilingual-e5-large-instruct on HF) | Instruction tuning with 150k unique synthetic instructions over 93 languages on an encoder backbone. | 2 | admit | 5 |
| NanoFlow: Towards Optimal Large Language Model Serving Throughput | K. Zhu, Y. Gao, Y. Zhao, et al. | 2024 | OSDI 2025 | 2408.12757 | - | - | - | - | unknown | Intra-device parallelism via nano-batches; serving is compute-bound at scale; 1.91x vs vLLM/FastGen/TRT-LLM | 2 | admit | 8 |
| Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning | Markovic et al. | 2025 | arXiv (preliminary) | 2505.24478 | https://github.com/topoteretes/cognee | 30700 (repo page, approx) | unverified (API rate-limited) | Apache-2.0 | yes (code) | Hyperparameter sweep over Cognee chunking/graph/retrieval/prompting on HotPotQA/2Wiki/MuSiQue; tuning gains real but uneven | 2 | admit | 9 |
| PathRAG: Pruning Graph-Based Retrieval Augmented Generation with Relational Paths | Chen et al. | 2025 | AAAI (doi:10.1609/aaai.v40i36.40268) | 2502.14902 | https://github.com/BUPT-GAMMA/PathRAG | unverified (API rate-limited) | unverified (API rate-limited) | unverified | yes (code linked in paper) | Flow-based pruning of relational paths with reliability-ascending prompt ordering to cut retrieval tokens | 2 | admit | 9 |
| PROD: Progressive Distillation for Dense Retrieval | Zhenghao Lin, Yeyun Gong, Xiao Liu et al. | 2022 | arXiv preprint | 2209.13335 | none located | n/a | n/a | n/a | unverified | Teacher-progressive distillation bridging the teacher-student capacity gap. | 2 | admit | 2 |
| PromptBERT: Improving BERT Sentence Embeddings with Prompts | Jiang et al. | 2022 | EMNLP 2022 | 2201.04337 | https://github.com/kongds/Prompt-BERT | 341 | 2023-11-22 | unverified | code only | Manual and continuous prompt templates with template-denoised contrastive learning for encoder embeddings. | 2 | admit | 5 |
| RankT5: Fine-Tuning T5 for Text Ranking with Ranking Losses | Zhuang, Honglei; Qin, Zhen; Jagerman, Rolf; Hui, Kai; Ma, Ji; Lu, Jing; Ni, Jianmo; Wang, Xuanhui; Bendersky, Michael | 2022 | arXiv preprint | 2210.10634 | - |  |  | n/a (paper) | unknown | Listwise losses beat monoT5 by +1.8% MRR@10 (MARCO) / +2.8% (NQ), better zero-shot | 2 | admit | 10 |
| RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | Sarthi et al. | 2024 | ICLR 2024 | 2401.18059 |  |  |  |  | yes (paper reports method; code linked in paper, not separately verified) | Recursive SBERT-embed, UMAP+GMM-cluster (BIC), LLM-summarize tree; collapsed-tree retrieval | 2 | admit | 9,10 |
| SGPT: GPT Sentence Embeddings for Semantic Search | Niklas Muennighoff | 2022 | arXiv preprint | 2202.08904 | https://github.com/Muennighoff/sgpt | 872 | 2024-02-17 | MIT | code yes / weights unverified | Contrastive fine-tune of GPT decoders (biased + weighted-mean pooling) for symmetric/asymmetric search; earliest proof decoders embed without architecture change. | 2 | admit | 4 |
| SpecInfer: Accelerating Generative LLM Serving with Tree-based Speculative Inference and Verification | X. Miao, G. Oliaro, Z. Zhang, et al. | 2023 | ASPLOS 2024 | 2305.09781 | - | - | - | - | yes (paper states code available) | Small-model draft trees verified in parallel by target LLM; 1.5-2.8x distributed, 2.6-3.5x offloading | 2 | admit | 8 |
| Splitwise: Efficient Generative LLM Inference Using Phase Splitting | P. Patel, E. Choukse, C. Zhang, A. Shah, I. Goiri, S. Maleki, R. Bianchini | 2023 | arXiv preprint | 2311.18677 | - | - | - | - | unknown | Split prefill/decode onto different machines; 1.4x throughput at 20% lower cost, 2.35x same budget | 2 | admit | 8 |
| Task-aware Retrieval with Instructions | Asai et al. | 2022 | ACL 2023 Findings | 2211.09260 | https://github.com/facebookresearch/tart | 168 | 2023-10-04 | NOASSERTION | yes (facebook/tart-dual-contriever-msmarco plus BEIR embeddings) | BERRI multi-task instruction tuning with query-side-only instructions and instruction-unfollowing negatives. | 2 | admit | 5 |
| The Embedder's Dilemma: LLMs Are Better, but at What Cost? | Adnan El Assadi, Niklas Muennighoff, Jinhyuk Lee | 2026 | arXiv preprint | 2608.12875 |  |  |  | UNK | code unverified | Controlled cost-aware comparison of 10 LLMs vs 26 embedding models on 37 tasks: tied in aggregate (0.4 pts), LLMs lead reasoning-heavy retrieval, embedders lead classification, parity costs more. | 2 | admit | 4 |
| The Truth Lies Somewhere in the Middle (of the Generated Tokens) | Sophie L. Wang, Phillip Isola, Brian Cheung | 2026 | arXiv preprint | 2605.09969 |  |  |  | UNK | code unverified | Mean pooling across autoregressively generated tokens beats any single token as a representation (kernel-alignment evidence); generated-state pooling carries distributed semantics. | 2 | admit | 4 |
| Training Sparse Mixture Of Experts Text Embedding Models | Zach Nussbaum et al. | 2025 | arXiv preprint | 2502.07972 | https://github.com/nomic-ai/contrastors | 802 | 2025-03-26 | Apache-2.0 | yes (nomic-embed-text-v2-moe) | Sparse-MoE embedder: capacity without proportional inference cost | 2 | admit | 3 |
| XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models | Yixin Dong, Charlie F. Ruan, Yaxing Cai, Ruihang Lai, Ziyi Xu, Yilong Zhao, Tianqi Chen | 2024 | MLSys 2025 | 2411.15100 | https://github.com/mlc-ai/xgrammar | 1882 | 2026-09-10 | Apache-2.0 | engine released | Byte-level PDA with token-mask cache and GPU-overlapped grammar execution, ~100x faster | 2 | admit | 7 |
| Embedding-based In-Context Prompt Training for Enhancing LLMs as Text Encoders | Ailiang Lin, Zhuoyun Li, Keyu Mao, Kotaro Funakoshi, Manabu Okumura | 2026 | arXiv preprint | 2605.01372 |  |  |  | UNK | code unverified | EPIC replaces discrete demonstration tokens with trained embedding-based in-context prompts to keep ICL gains for embeddings while cutting token overhead. | 1 | admit | 4,5 |
| Evaluating Embedding Generalization: How LLMs, LoRA, and SLERP Shape Representational Geometry | Siyaxolisa Kabane | 2025 | arXiv preprint | 2511.21703 |  |  |  | UNK | code unverified | Tests whether SLERP merging mitigates LoRA over-specialisation in embedding space; single-author study on synthetic numerical-sequence clustering/classification only. | 1 | admit | 4 |
| Layer-wise Representation Dynamics: An Empirical Investigation Across Embedders and Base LLMs | Jingzhou Jiang, Yi Yang, Kar Yan Tam | 2026 | arXiv preprint | 2605.12714 |  |  |  | UNK | code unverified | LRD framework (subspace motion, neighbourhood retention, final-layer alignment) applied to 31 models on 30 MTEB tasks; measurement toolkit for how far an embedder drifts from its base. | 1 | admit | 4 |
| Model soups: averaging weights of multiple fine-tuned models improves accuracy without increasing inference time | Mitchell Wortsman, Gabriel Ilharco, Samir Yitzhak Gadre, Rebecca Roelofs, Raphael Gontijo-Lopes, Ari S. Morcos, Hongseok Namkoong, Ali Farhadi, Yair Carmon, Simon Kornblith | 2022 | arXiv preprint | 2203.05482 |  |  |  | UNK | code unverified | Plain weight averaging of same-base fine-tunes improves accuracy at zero inference cost; baseline every fancier merge must beat. | 1 | admit | 4 |
| Document Expansion by Query Prediction | Rodrigo Nogueira, Wei Yang, Jimmy Lin et al. | 2019 | arXiv preprint | 1904.08375 | https://github.com/castorini/docTTTTTquery | 376 | 2023-03-25 | Apache-2.0 | unverified | Predict queries per document and append them to the document text before indexing. | 2 | abstain | 2,6,10 |
| Jina Embeddings 2: 8192-Token General-Purpose Text Embeddings for Long Documents | Michael Günther; Jackmin Ong; Isabelle Mohr; Alaeddine Abdessalem; Tanguy Abel; Mohammad Kalim Akram; Susana Guzman; Georgios Mastrapas; Saba Sturua; Bo Wang; Maximilian Werk; Nan Wang; Han Xiao | 2023 | arXiv preprint | 2310.19923 |  |  |  |  | yes (weights) | 8192-token general-purpose embeddings via long-context tuning. | 2 | abstain | 1 |
| LoRA: Low-Rank Adaptation of Large Language Models | Edward J. Hu, Yelong Shen, Phillip Wallis et al. | 2021 | arXiv preprint | 2106.09685 | https://github.com/microsoft/LoRA | 13789 | 2024-12-17 | MIT | n/a (method, not a model) | Low-rank adapter fine-tuning freezing base weights. | 2 | abstain | 2 |
| MiniCPM-Embedding (no paper; HF model card only) | n/a (OpenBMB) | n/a | n/a | none | https://github.com/openbmb/MiniCPM | 10879 | 2026-09-12 | Apache-2.0 | yes (openbmb/MiniCPM-Embedding + Light) | 0.5B BERT-style embedder paired with MiniCPM; card links no paper | 2 | abstain | 3 |
| MiniCPM4: efficient end-side LLM | MiniCPM Team et al. | 2025 | arXiv preprint | 2506.07900 | https://github.com/openbmb/MiniCPM | 10879 | 2026-09-12 | Apache-2.0 | yes (generative model, not embedder) | Generative base of MelodyScribe rig; context for MiniCPM-Embedding | 2 | abstain | 3 |
| RAGAs: Automated Evaluation of Retrieval Augmented Generation | unverified — venue record only (OpenAlex, secondary) | 2024 | EACL 2024 demo (per OpenAlex, secondary) | no-arXiv-id |  |  |  |  | reference-only eval metrics | Automated evaluation of retrieval-augmented generation (per title). | 2 | abstain | 6 |
| Representation Learning with Contrastive Predictive Coding | Aaron van den Oord, Yazhe Li, Oriol Vinyals | 2018 | arXiv preprint | 1807.03748 | none (no official code released) | n/a | n/a | n/a | n/a | InfoNCE objective foundation for all contrastive recipes. | 2 | abstain | 2 |
| Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference | Benjamin Warner; Antoine Chaffin; Benjamin Clavié; Orion Weller; Oskar Hallström; Said Taghadouini; Alexis Gallagher; Raja Biswas; Faisal Ladhak; Tom Aarsen; Nathan Cooper; Griffin Adams; Jeremy Howard; Iacopo Poli | 2024 | arXiv preprint | 2412.13663 | https://github.com/AnswerDotAI/ModernBERT | 1720 | 2026-03-01 | Apache-2.0 | yes (weights+code) | Modernized bidirectional encoder (8k context, fast) as efficient alternative to decoder-embedders. | 2 | abstain | 1 |
| Towards General Text Embeddings with Multi-stage Contrastive Learning | Zehan Li, Xin Zhang, Yanzhao Zhang et al. | 2023 | arXiv preprint | 2308.03281 | not checked under lane budget | n/a | n/a | n/a | unverified | Multi-stage contrastive learning recipe for general text embeddings. | 2 | abstain | 2 |
| AnglE-optimized Text Embeddings | Xianming Li, Jing Li | 2023 | arXiv preprint | 2309.12871 | not checked under lane budget | n/a | n/a | n/a | unverified | Angle-based contrastive objective in complex space to fix cosine saturation. | 1 | abstain | 2 |
| Augmented SBERT: Data Augmentation Method for Improving Bi-Encoders for Pairwise Sentence Scoring Tasks | Thakur, Reimers, Daxenberger, Gurevych | 2020 | NAACL 2021 (per OpenAlex, secondary) | 2010.08240 |  |  |  |  | unknown | Data augmentation for improving bi-encoders on pairwise sentence scoring (per title). | 1 | abstain | 6 |
| BiXSE: Improving Dense Retrieval via Probabilistic Graded Relevance Distillation | Christos Tsirigotis, Vaibhav Adlakha, Joao Monteiro | 2025 | arXiv preprint | 2508.06781 | not checked under lane budget | n/a | n/a | n/a | unverified | Probabilistic graded-relevance distillation. | 1 | abstain | 2 |
| Curriculum Learning for Dense Retrieval Distillation | Hansi Zeng, Hamed Zamani, Vishwa Vinay | 2022 | arXiv preprint | 2204.13679 | not checked under lane budget | n/a | n/a | n/a | unverified | Curriculum-ordered distillation for dense retrieval. | 1 | abstain | 2 |
| DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node | Jayaram Subramanya, S. et al. | 2019 | NeurIPS 2019 (unverified) | no-arXiv-found | - |  |  | n/a (paper) | unknown | SSD graph index SOTA that SPANN compares against | 1 | abstain | 10 |
| Evaluating the Zero-Shot Robustness of Instruction-Tuned Models | Gu et al. (unverified) | 2024 | ICLR 2024 | https://proceedings.iclr.cc/paper_files/paper/2024/file/d3221cdb27e49d9c1cd35ad254feccfe-Paper-Conference.pdf | unverified | unverified | unverified | unverified | unverified | Instruction-tuned LMs are sensitive to instruction paraphrase; soft-prompt KL alignment proposed as fix. | 1 | abstain | 5 |
| InPars-Light: Cost-Effective Unsupervised Training of Efficient Rankers | Boytsov, Patel, Sourabh, Nisar, Kundu, Ramanathan, Nyberg | 2023 | arXiv preprint (venue unverified) | 2301.02998 |  |  |  |  | unknown | Cheap reranker training on synthetic queries. | 1 | abstain | 6 |
| KV-Embedding: Training-free Text Embedding via Internal KV Re-routing in Decoder-only LLMs | unverified | 2026 | arXiv preprint | 2601.01046 | unverified | unverified | unverified | unverified | unverified | Compression-oriented prompting plus internal KV re-routing as a PromptEOL successor claim. | 1 | abstain | 5 |
| Llama2Vec: Unsupervised Adaptation of Large Language Models for Dense Retrieval | Liu, Zheng; Li, Chaofan; Xiao, Shitao; Shao, Yingxia | 2023 | arXiv preprint | 2312.15503 | - |  |  | n/a (paper) | unknown | Unsupervised decoder-to-embedder adaptation | 1 | abstain | 10 |
| Pairwise Relevance Distillation for Dense Retrieval | Chao-Wei Huang, Yun-Nung Chen | 2024 | arXiv preprint | 2410.01383 | not checked under lane budget | n/a | n/a | n/a | unverified | Pairwise relevance distillation for dense retrieval. | 1 | abstain | 2 |
| Product quantization for nearest neighbor search | Jegou, H.; Douze, M.; Schmid, C. | 2011 | IEEE TPAMI (unverified) | no-arXiv | - |  |  | n/a (paper) | unknown | Foundational PQ/IVFADC compression | 1 | abstain | 10 |
| Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods | Cormack, C.; Clarke, C.; Buettcher, S. | 2009 | SIGIR 2009 (unverified) | no-arXiv-DOI-only | - |  |  | n/a (paper) | unknown | Parameter-free rank fusion for hybrid retrieval | 1 | abstain | 10 |
| SFR-Embedding-Mistral: Enhance Text Retrieval with Transfer Learning | Meng et al. | 2024 | vendor blog, no paper found | unverified | https://huggingface.co/Salesforce/SFR-Embedding-Mistral | unverified | unverified | unverified | yes (Salesforce/SFR-Embedding-Mistral on HF) | Transfer-learned Mistral embedder family frequently cited as instruction-tuning evidence. | 1 | abstain | 5 |
| SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking | Formal, Thibault et al. | 2021 | arXiv preprint | 2107.05720 | - |  |  | n/a (paper) | unknown | First SPLADE; superseded by admitted v2 | 1 | abstain | 10 |
| TSDAE: Using Transformer-based Sequential Denoising Auto-Encoder for Unsupervised Sentence Embedding Learning | Wang, Reimers, Gurevych | 2021 | arXiv preprint (venue unverified) | 2104.06979 |  |  |  |  | unknown | Unsupervised domain-adapted sentence embeddings via denoising auto-encoding. | 1 | abstain | 6 |
| A Dual-Task Paradigm to Investigate Sentence Comprehension Strategies in Language Models | Rei Emura, Saku Sugawara | 2026 | n/a | 2604.26351 |  |  |  | n/a | n/a | arXiv search hit while hunting LM-Cocktail; cognitive-science study, no embedding/generation unification. | 0 | abstain | 4 |
| Analysis of Local Anisotropy Fluctuations in Compact Objects | Manuel Malaver; Maria Esculpi | 2023 | arXiv preprint | 2310.01730 |  |  |  |  | no | Guessed id for GTE; fetched page is Malaver/Esculpi on compact-object anisotropy. | 0 | abstain | 1 |
| IMAGINE: An Integrated Model of Artificial Intelligence-Mediated Communication Effects | Guerrero-Sole | 2022 | arXiv (manuscript) | 2212.08658 | n/a | n/a | n/a | n/a | n/a | Media-effects theory; irrelevant to lane 9 | 0 | abstain | 9 |
| Multi-view Intent Learning and Alignment with Large Language Models for Session-based Recommendation | Shutong Qiao; Wei Zhou; Junhao Wen; Chen Gao; Qun Luo; Peixuan Chen; Yong Li | 2024 | arXiv preprint | 2402.13840 |  |  |  |  | no | Guessed id for echo embeddings; fetched page is Qiao et al. session recommendation. | 0 | abstain | 1 |
| n/a (recalled id actually a Collatz paper) | Wei Ren (actual paper author) | 2023 | n/a | 2304.10491 |  |  |  | n/a | n/a | Recalled as RepLLaMA dense retrieval; the abs page shows Collatz dynamics, unrelated. | 0 | abstain | 4 |
| n/a (recalled id actually a phylogeny paper) | William Howard-Snyder et al. (actual paper authors) | 2023 | n/a | 2311.10913 |  |  |  | n/a | n/a | Recalled as LM-Cocktail; the abs page shows maximum-parsimony/clade-support work, unrelated. | 0 | abstain | 4 |
| n/a (recalled id actually a QCD paper) | Swagato Mukherjee et al. (actual paper authors) | 2023 | n/a | 2311.16402 |  |  |  | n/a | n/a | Recalled as the DARE merging paper; the abs page shows TMD factorisation/QCD, unrelated. | 0 | abstain | 4 |
| On Pruning State-Space LLMs | Ghattas et al. | 2025 | arXiv (manuscript) | 2502.18886 | n/a | n/a | n/a | n/a | n/a | SSM pruning study; irrelevant to lane 9 | 0 | abstain | 9 |
| uniCOIL: Unified and Effective Weighting for Contextualized Inverted Lists | Lin, J.; Ma, X. (?) | - | - | unresolved | - |  |  | unknown | unknown | Learned sparse weighting in the COIL family | 0 | abstain | 10 |
| When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset | Lucia Zheng; Neel Guha; Brandon R. Anderson; Peter Henderson; Daniel E. Ho | 2021 | arXiv preprint | 2104.08671 |  |  |  |  | no | Guessed id for BEIR; fetched page is Zheng et al. on pretraining for law (CaseHOLD). | 0 | abstain | 1 |
| WRONG ID probe: A Communication Theory Perspective on Prompting Engineering Methods | Y. Song et al. | 2023 | arXiv | 2310.18358 | - | - | - | - | no | Recalled FastGen ID was wrong; actual paper is about prompt engineering, no serving content | 0 | abstain | 8 |
| WRONG ID probe: Blow-up of solutions for semilinear parabolic equation | A. Gladkov | 2024 | arXiv | 2402.05040 | - | - | - | - | no | Recalled HydraGen ID was wrong; actual paper is PDE analysis | 0 | abstain | 8 |
| WRONG ID probe: Drag-guided diffusion models for vehicle image generation | N. Arechiga et al. | 2023 | arXiv | 2306.09935 | - | - | - | - | no | Recalled Orca ID was wrong; actual paper is unrelated image-generation work | 0 | abstain | 8 |
| WRONG ID probe: Statistical Guarantees for Link Prediction using GNNs | A. Chung et al. | 2024 | arXiv | 2402.02692 | - | - | - | - | no | Recalled DistServe ID was wrong; actual paper is GNN theory | 0 | abstain | 8 |

## 10. Method

Per-lane queries, sources, screened/admitted counts, and failures, assembled from the ten
`lanes/<n>/method.md` files. Screened counts per lane (inventory rows filed):
1:24, 2:29, 3:21, 4:33, 5:25, 6:32, 7:25, 8:39, 9:22, 10:37 (287 lane rows total). Admitted unique-inventory rows listing each lane:
1:19, 2:21, 3:16, 4:29, 5:21, 6:26, 7:25, 8:25, 9:15, 10:24 (cross-listed items counted under every lane they serve; 153 unique
admits of 191 unique candidates; 38 abstains; no `refute` dispositions filed — refutations
are claim-level, part 3). Every lane met the minimums (≥20 screened, ≥8 admitted).

- **Lane 1 (architectures).** arXiv export API (`ti:` title queries) plus 24 direct
abs-page fetches; GitHub REST for 14 repos (recovering org renames: sentence-transformers
→ huggingface, FlagEmbedding → FlagOpen). What failed: arXiv API rate limiting after ~8
calls (BEIR/GTE title searches never completed); Semantic Scholar 429 without key; only
abstracts read (inference costs, ablations, MTEB tables still in the staged PDFs); no
citation chaining completed — 2025 successors beyond Qwen3-Embedding/MMTEB likely missed.
- **Lane 2 (training recipes).** arXiv export API (`id_list` batches verifying
memory-guessed ids, then `ti:`/`abs:` searches, 3–15s backoff) — 6 of 11 recalled ids were
wrong and recovered via title search; ~15 GitHub calls; 4 Hugging Face model lookups; 20+
abs pages. What failed: S2 throttled after 1–2 calls (chaining incomplete); NV-Embed repo
404s; sentence-transformers org moved; no PDF text toolchain in-sandbox (stage compute not
extracted).
- **Lane 3 (small embedders).** arXiv export API with ≥60s gaps under throttling; arXiv
HTML search used only to locate ids (never cited); abs pages as primary verification;
arXiv full-text HTML greps for training facts (Qwen3 loss/masking, Gecko 66.31, E5 batch
32,768/20k steps/270M pairs); HF API for 8 checkpoints plus safetensors param counts;
HF-card paper-link mining replacing citation chaining; GitHub API for 7 repos. What failed:
export.arxiv.org throttling; S2 persistent 429; Papers-with-Code empty; no PDF text
tooling; jina/FlagEmbedding org renames corrected via search.
- **Lane 4 (hybrids).** All 27 admitted papers opened at abs pages; export API for
merging/embedding searches until throttled, then slow abs fetches; S2 forward-chaining of
GritLM (~100 citing papers: GEM, LLM2Vec-Gen, GRC, Embedder's Dilemma, Giga-MoE,
MidTokens, LayerDynamics, AttentionValues, EPIC) and OneGen (16 citing: RetroLLM, MAGNET,
Hydra, UnifiedOnDevice); GitHub verification for 7 repos; HF search confirming OneGen
checkpoints. What failed: 4 recalled ids resolved to unrelated papers (2 corrected:
DARE 2311.03099, LM-Cocktail 2311.13534; RepLLaMA/LLaRA unresolved); one S2 call 429'd;
venues claimed only where sourced.
- **Lane 5 (prompts for embeddings).** 15 web searches plus direct primary-source opens
(arXiv abs/HTML/PDF, ACL Anthology, Hugging Face, GitHub, vendor project pages);
forward-chaining via references inside opened papers; GitHub REST for stars/push/license
(INSTRUCTOR recovered via project page after API 404). What failed: export.arxiv.org 503;
S2 429; 3 GitHub 404s (2 recovered, SFR/NV-Embed via HF model pages); no chat-template or
marker-token study found (gaps, not admits); 2025+ items rest on fetched pages only.
- **Lane 6 (evaluation/anisotropy).** No web search available: direct arXiv abs pages
(WebFetch then curl+grep on citation meta tags) for every admitted id; OpenAlex API
(title-exact resolution recovering 13 correct ids); GitHub API for 9 repos (BEIR repo
README supplying the correct BEIR id 2104.08663); Papers-with-Code and DBLP abandoned
(unrelated page; bot challenge). What failed: 10 recalled ids failed abs verification
(recorded so no lane re-tries them); arXiv/S2/GitHub 429s; 14 admits title-record-only
(shallow verification flagged in findings); venues stated only where the abs page shows them.
- **Lane 7 (KG extraction prompts).** 21 web searches; arXiv abs via webfetch (5) plus
search-excerpt evidence for the rest; ACL Anthology, NeurIPS proceedings, OpenReview/ICLR,
WISE/Springer, MLSys pages; GitHub facts via repo-page HTML payload parsing plus atom
commit feeds after REST quota exhaustion (6 repo URLs uncaptured, marked unverified).
What failed: export.arxiv.org "Rate exceeded" throughout; S2 429; GitHub REST quota;
no shell PDF-text tooling (identity via abs verification plus correct PDF retrieval).
- **Lane 8 (serving/KV).** Web search per target plus direct abs fetches for recalled ids
(4 recalled ids wrong, corrected via search); USENIX/ACL/ICLR/MLSys proceedings for
non-arXiv venues (Orca, DistServe, EAGLE-2, Preble, BatchLLM); GitHub REST (shell curl,
then fetcher after 403s); docs.vllm.ai for APC behaviour (first URL guess 404'd,
corrected). What failed: export.arxiv.org and S2 unusable; Papers-with-Code returned HTML;
llama.cpp org moved (recorded); TGI archived; Orca filed under OSDI22 naming exception
(no arXiv id); no consumer-GPU numbers found in primary sources.
- **Lane 9 (pipeline orchestration).** arXiv API rate-limited on all 3 attempts —
verification via 14 abs-page webfetches plus 13 PDF downloads; S2 429 (chaining replaced
by related-work sections plus repo dependency lists); GitHub REST for first 4 repos, then
60/hr quota (remainder via rendered pages or unverified); web search for ID recovery (every
recovered ID abs-verified); pypdf text mining of 10 pipeline PDFs for quoted numbers. What
failed: 2 recalled ids wrong (2502.18886 ≠ PathRAG, 2212.08658 ≠ IRCoT, recorded as
abstains); LangChain docs URL redirected (abstained); no pip/pdf tooling on PATH (used uv);
no documents-per-hour source exists anywhere screened.
- **Lane 10 (retrieval/storage).** arXiv HTML title search verified one-by-one at abs pages
(1–2s spacing) after export API "Rate exceeded" plus timeouts; 18 PDFs text-extracted with
pypdf (uv-run, fonttools added for CFF fonts); GitHub REST for 6 repos; one HF card lookup
(abstained as secondary). What failed: 5 recalled ids wrong, all corrected against fetched
pages (nothing recalled admitted without abs confirmation); S2 429 (chaining approximated
via in-PDF citation trails plus co-cited screening); Papers with Code not attempted;
post-2024 ANN systems (aluminum-bench, FreshDiskANN, LVQ, RaBitQ) uncovered — follow-up
with an S2 key.

Cross-lane dedup: 287 lane rows merged to 191 unique items (merge key: arXiv id/DOI/URL);
one item may serve several lanes and appears once with all lanes listed. Staged PDFs: 150
in `merged/papers/` (admitted papers; tool/doc artefacts carry no PDF by rule; lane 8's
Orca filed under an OSDI22-name exception).

