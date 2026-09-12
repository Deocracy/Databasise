# Lane 9 findings: On-device small models and small embedders, 0.3B to 3B

Screened 33 candidates; admitted 27 (23 arXiv papers with PDFs in `papers/`,
1 proceedings-only benchmark, 2 repo/model-card-only releases).
Lane verdict: the substrate MelodyScribe wants — a 0.6–3B tool-calling model
plus a 0.1–0.6B embedder with long-document behaviour — exists off the shelf
under permissive licenses, but no single <3B artefact jointly trains
embedding and generation, and independent long-context evidence cuts against
broad small-model claims (see refutations).

## (a) Admitted items

**Qwen3, incl. 0.6B/1.7B/4B (arXiv 2505.09388).** What it is: Alibaba's dense
0.6B/1.7B/4B/8B/14B/32B plus MoE family with unified thinking/non-thinking
modes; the 0.6B and 1.7B run 32K context, 4B+ runs 128K, and the smalls are
distilled from the 32B/235B flagships with reported agent/tool-task evals.
Take: this is MelodyScribe's default model shortlist — Qwen3-1.7B for op
emission, Qwen3-0.6B as the embedder backbone — Apache-2.0, hybrid-reasoning
modes matching the Score's per-section directives. Careful: all small-model
numbers are vendor-reported; confirm tool-calling on BFCL before trusting the
agent-task tables.

**SmolLM2 1.7B/360M/135M (arXiv 2502.02737).** What it is: HuggingFaceTB's
fully-open data-centric small models overtrained on ~11T tokens, with released
FineMath/Stack-Edu/SmolTalk datasets; the 1.7B-Instruct card documents
function calling, and a 16k variant reports HELMET 8k/16k numbers. Take: the
only fully-open recipe at 1.7B with datasets included — the template to copy
if MelodyScribe trains its own op-emitter. Careful: 8k native context (16k
only via the finetuned variant) is short for paragraph-plus-Skills composition.

**SmolLM3-3B (repo + HF + blog, no paper).** What it is: HuggingFaceTB's 3B
follow-on on 11.2T tokens with GQA + NoPE (3:1 hybrid), 128K via YaRN, dual
`/think`–`/no_think` modes, and native XML/Python tool calling, Apache-2.0.
Take: the strongest near-band instruct model with long context and tool
calling in one checkpoint, plus a published training blueprint. Careful: no
peer-reviewed paper — vendor-primary only — and 3B in fp16 wants quantization
to sit next to an embedder in 16 GB.

**Gemma 3 1B/4B (arXiv 2503.19786).** What it is: Google's open 1B (32K,
text-only) and 4B/12B/27B (128K, multimodal) models with function calling and
structured output, using a 5:1 local/global attention mix that sharply cuts KV
cache. Take: Gemma-3-1B/4B are the KV-frugal alternative for cached-chunk
composition, and the sliding-window trick is directly reusable. Careful:
weights are under Gemma Terms of Use, not Apache-2.0; vendor benchmarks only.

**Phi-4-Mini 3.8B (arXiv 2503.01743).** What it is: Microsoft's 3.8B model
(200K vocab, GQA, 128K via LongRoPE) matching 2x-size models on math/code,
with a mixture-of-LoRAs trick that adds vision/speech while the language
backbone stays frozen. Take: evidence that synthetic-data density beats
parameter count at this scale, and the frozen-backbone-plus-adapters pattern
for adding modalities without regressions. Careful: 3.8B is just above the
band and tool-calling is not its evaluated strength.

**LFM2 350M–2.6B + MoE + Nanos (arXiv 2511.23404).** What it is: Liquid AI's
edge-first family (hybrid gated-conv/attention, ~2x CPU prefill/decode vs
same-size transformers, 32K) with task-specialized Nanos for tool-calling,
RAG, extraction and math, plus an LFM2-ColBERT retriever. Take: the single
best existence proof for the lane — small models explicitly post-trained for
tool dispatch and paired with their own retriever. Careful: newest vendor in
the set (Nov 2025), thinnest independent evaluation; verify BFCL and MTEB
yourself before depending on the Nanos.

**MiniCPM4 0.5B/8B (arXiv 2506.07900).** What it is: OpenBMB's end-side models
with sparse attention, quantization-aware training, speculative sampling
(CPM.cu) and a dedicated MiniCPM4-MCP tool-use track; vendor-reports 7x
faster 128K prefilling than Qwen3-8B. Take: the inference-stack co-design
(sparse attention + quant + speculative decoding) MelodyScribe needs for
single-pass paragraph filing on weak hardware. Careful: 7x figure is
vendor-measured on their chips; the 0.5B is the only in-band size.

**MiniCPM 1.2B/2.4B (arXiv 2404.06395).** What it is: the original MiniCPM
paper — SLMs matching 7–13B models via WSD scheduling and ModelTunnel, a
procedure that searches training strategy on tiny proxy models and transfers
it up. Take: the cheap-training methodology lane: use ModelTunnel-style proxy
search before burning 16 GB GPU time. Careful: 2024 vintage; contexts are
short by current standards.

**MiniCPM5-1B (repo release, no paper).** What it is: OpenBMB's May-2026 1B
dense checkpoint (Think/No-Think, native long context, vanilla Llama arch,
GGUF/MLX, Apache-2.0) that ships deployment/fine-tuning Agent Skills. Take:
the brief's named candidate corrected — there is no verified MiniCPM5-2B; the
shipped small checkpoint is 1B, and its Agent-Skills packaging is exactly the
Folio-adjacent pattern to study. Careful: release notes only, no paper.

**OLMo 1B/7B (arXiv 2402.00838, ACL 2024).** What it is: Ai2's truly-open
programme — weights, Dolma data, code, logs, hundreds of checkpoints, explicit
decontamination. Take: the openness baseline; any MelodyScribe claim about
training data or contamination must meet this bar to be credible. Careful: the
1B is old and weak vs. current 1B models; use it as process reference, not
substrate.

**Qwen3-Embedding 0.6B/4B/8B (arXiv 2506.05176).** What it is: decoder-derived
embedders built on the Qwen3 backbones with two-stage contrastive training on
LLM-synthesized data plus model merging, Apache-2.0, SOTA on multilingual
MTEB (vendor-reported). Take: the prime capability-1 candidate — an embedder
that shares lineage (and potentially hidden states) with the generator
MelodyScribe would use. Careful: SOTA claim is vendor-measured; test the 0.6B
on MelodyScribe's own paragraphs and long sections before adopting.

**EmbeddingGemma 300M (arXiv 2509.20354).** What it is: Google's 308M
encoder distilled from Gemma-3 via T5Gemma encoder-init plus geometric
distillation, SOTA under 500M across MTEB multilingual/English/code, with the
lead surviving 128-dim truncation and int4 quantization (<200 MB RAM).
Take: the default sub-500M embedder — multilingual, tiny, quantization-proof.
Careful: Gemma license (not Apache-2.0); encoder-only, so no hidden-state
sharing with a generator.

**Arctic-Embed 2.0 (arXiv 2412.04506).** What it is: Snowflake's multilingual
retrievers (~113M m, ~335M l) that fix the prior generation's English-quality
regression, with two-stage MRL so 256-dim truncation barely hurts. Take: the
storage-sizing evidence — truncated + scalar-quantized vectors down to 128
bytes — for MelodyScribe's vector store budget. Careful: retrieval-only
benchmarking; verify clustering/STS behaviour for Folio-like use.

**Nomic Embed v2 MoE (arXiv 2502.07972).** What it is: the first general MoE
text embedder (475M total / 305M active), best in its class mono- and
multilingually and competitive at 2x size, with code+models+eval data
released. Take: architectural precedent for routing different stores through
different experts — the closest published analogue to per-store embedding
heads. Careful: 512-token context; not a long-document model.

**Nomic Embed v1 137M (arXiv 2402.01613, TMLR 2025).** What it is: a fully
reproducible 137M, 8K-context embedder beating ada-002 and
text-embedding-3-small on MTEB and LoCo with open weights, code and data.
Take: proof that 8K long context fits in 137M, and the reproducibility
gold standard. Careful: English-centric; multilingual needs come from v2.

**jina-embeddings-v3 570M (arXiv 2409.10173, ECIR 2025).** What it is:
XLM-R-based multilingual embedder with RoPE to 8K and five task-specific LoRA
adapters, beating OpenAI/Cohere on English MTEB (vendor-reported). Take: the
task-LoRA pattern — one backbone, per-task heads — maps onto per-store filing
heads. Careful: CC-BY-NC-4.0 bars commercial deployment; exclude from any
commercial MelodyScribe distribution.

**BGE-M3 569M (arXiv 2402.03216, ACL Findings 2024).** What it is:
single-checkpoint dense + sparse + ColBERT multi-vector retrieval over 100+
languages and 8K tokens, trained by self-knowledge-distillation. Take: the
closest single artefact to typed-store fusion — three retrieval
functionalities, one model — study its distillation recipe for MelodyScribe's
graph/vector/table routing. Careful: 569M is the top of the band and
multi-vector retrieval is index-heavy.

**ModernBERT 149M/395M (arXiv 2412.13663, ACL 2025).** What it is: a
modernized encoder (RoPE, alternating local/global attention, FlashAttention)
on 2T tokens with native 8K context; SOTA short- and long-context retrieval
per size and the fastest measured encoder, dominant in the ColBERT setting.
Take: the best separate-embedder backbone if MelodyScribe does not share
hidden states with the generator. Careful: masked-LM backbone, so no
generative reuse; English + code heavy.

**E5-Mistral recipe (arXiv 2401.00368, ACL 2024).** What it is: the canonical
synthetic-data-only decoder-embedder method (<1k steps, no labels; SOTA once
labels are mixed in). Take: the training template behind Qwen3-Embedding-0.6B
and MiniCPM-Embedding-Light — read this before attempting capability 1.
Careful: demonstrated at 7B; the sub-1B transfer is asserted by follow-ons,
not by this paper.

**Multilingual-E5 small/base/large (arXiv 2402.05672).** What it is:
Microsoft's 1B-pair contrastive pretraining recipe for small multilingual
encoders plus an instruction-tuned variant. Take: the small-encoder
multilingual training template, including hard-negative mining and
cross-encoder distillation. Careful: 2023-era sizes and scores; superseded as
artefacts, retained as recipe.

**MiniCPM-Embedding-Light 440M (HF model card, no paper).** What it is:
OpenBMB/THUNLP/NEUIR's bilingual decoder-derived embedder (from MiniCPM-2B,
converted to bidirectional attention + weighted mean pooling, 8K, dense +
sparse heads, MRL, 260M training pairs). Take: direct proof a small
instruction-tuned decoder converts into a strong embedder — the cheapest
capability-1 prototype path (take Qwen3-0.6B-Instruct, repeat). Careful: model
card only, bilingual (ZH/EN), no paper.

**MTEB (arXiv 2210.07316, EACL 2023).** What it is: the 8-task/58-dataset/112-
language embedding benchmark plus harness; headline finding: no method
dominates all tasks. Take: mandatory harness — every embedder candidate gets
an MTEB number before admission to MelodyScribe. Careful: short-context and
aging; pair with LongEmbed and MMTEB.

**MMTEB (arXiv 2502.13595, ICLR 2025).** What it is: the 500-task/250-language
community expansion with instruction-following, long-doc and code tasks;
notable result: the best public model is a 560M instruct embedder, not an
LLM. Take: the multilingual/long-doc/code evaluation frame, and a datapoint
for small-model sufficiency. Careful: full runs are heavy; use the
downsampled splits.

**LongEmbed (arXiv 2404.12096, EMNLP 2024).** What it is: six-task long-doc
retrieval to 32K (two synthetic, four dispersed-answer real tasks) showing
512-context models collapse, training-free PI/NTK/SelfExtend recovers length,
and RoPE beats APE for extension. Take: the acceptance test for filing and
retrieving long Score sections; NTK-extension of a 0.6B decoder-embedder is
the first experiment to run. Careful: repo declares no license; treat code as
reference-only.

**HELMET (arXiv 2410.02694, ICLR 2025).** What it is: Princeton/Intel's
seven-category controllable-length (to 128K) long-context eval over 59 models:
NIAH does not predict downstream; open models trail closed on reasoning and
citations with gaps widening by length; RAG tasks are the best cheap proxy.
Take: the independent check on any small-model long-context claim, and the
prescription to use RAG-style tasks during development. Careful: full 128K
runs are GPU-expensive (the SmolLM2-16k card shows HELMET can be run at
8k/16k instead).

**BFCL (ICML 2025, PMLR v267; live leaderboard).** What it is: Berkeley's
AST-plus-execution function-calling benchmark (serial/parallel/multi-turn/
multi-step agentic) with a continuously updated public leaderboard — the
de-facto tool-use standard. Take: the acceptance test for the op-emitting
small model; every 0.6–3B candidate gets a BFCL number. Careful: no arXiv
version exists (proceedings + leaderboard only); leaderboard snapshots drift,
so pin the eval commit. Note: an Aug-2026 audit paper flags score instability
across reruns — treat small leaderboard gaps as noise.

**LoCoV1 + M2-BERT 80M (arXiv 2402.07440, ICML 2024).** What it is: a 12-task
benchmark for retrieval over unchunkable long documents plus an 80M
Monarch-Mixer state-space retriever (to 32K) beating transformer baselines by
23+ points, with a single-sample-batch finetuning recipe. Take: the cheapest
long-doc retriever design point and a non-transformer hedge if attention KV
budgets bite. Careful: state-space encoders are off the mainstream path;
serving and fine-tuning support is thinner.

## (b) Refutations

**R1 — the brief's candidate name is wrong.** The brief names "MiniCPM5-2B,
Apache-2.0" as the current candidate. The fetched OpenBMB/MiniCPM README
(primary source) announces **MiniCPM5-1B** (May 2026) as the first MiniCPM5
checkpoint, and the MiniCPM4 series ships 0.5B/8B. No 2B MiniCPM5 artefact was
found. Correct the candidate to MiniCPM5-1B or cite where a 2B build lives.

**R2 — scoped counter-evidence on "small matches frontier".**
HELMET (2410.02694) finds open-source models significantly lag closed models
on tasks requiring full-context reasoning or complex instruction following,
and the gap widens with length. This does not refute the brief's narrow
hypothesis (extraction, routing, schema-constrained emission), but it rules
out any broad reading: small-model parity must be claimed per narrow task
with a benchmark attached, and long-context reasoning is the wrong task to
claim it on.

**R3 — license constraint, not a refute but binding.** jina-embeddings-v3's
fetched HF card is CC-BY-NC-4.0: the task-LoRA idea is reusable, the weights
are not shippable commercially. Gemma-3 and EmbeddingGemma weights sit under
the Gemma Terms of Use, not Apache-2.0 — fine for research, a procurement flag
for products.

## (c) Unresolved ledger

- **OLMo 2 (2501.00656): abstain (out of band).** Verified paper and repo
  (6675 stars, Apache-2.0), but 7B/13B/32B exceeds the 0.3–3B band. Recipe
  (Dolmino Mix late curriculum, RLVR instruct) is relevant if MelodyScribe
  ever trains above 3B.
- **Nemotron-H (2504.03624) / Nemotron Nano 2 (2508.14444): abstain (out of
  band).** Both verified; 8B–56B and 9B respectively. Hybrid Mamba-Transformer
  KV savings noted for capability 3, but sizes disqualify them as substrates.
  (A 4B Nemotron 3 Nano exists per vendor blog — secondary source only, not
  verified, not admitted.)
- **Arctic-Embed v1 (2405.05374): abstain (superseded).** Verified; kept only
  for the 22M/33M tiny sizes and the m-long 8K variant, which the 2.0 report
  does not reproduce.
- **IBM Granite small models (2B dense, 1B/3B MoE, 4.x 3B, 30M–278M
  embeddings): abstain (secondary only).** Function-calling/RAG positioning,
  128K (3.1) and 512K-phase (4.1) contexts verified only from IBM docs and
  Ollama pages; no arXiv id or paper verified. Revisit if IBM publishes the
  report.
- **Gemma 1 2B/7B (2403.08295): abstain (superseded).** Verified; dominated by
  Gemma 3 on every lane dimension.
- **Nomic v1/v2 training-code URLs, Qwen3/Gemma/LFM2/Phi-4-mini repo
  star/push metadata: not captured.** Papers and weights verified; repo-side
  fields are `not-fetched` in the inventory, not asserted. GitHub API
  rate-limiting during the lane window is the cause (see method.md).

## (d) Security findings

None in this lane's scope (memory/skill injection is lane 6). Two procurement
constraints with security-adjacent handling: (1) CC-BY-NC-4.0 weights
(jina-v3) must be blocked from commercial build paths by license check, not by
trust; (2) LongEmbed code has no declared license — vendor it as
reference-only, do not copy it into the tree.
