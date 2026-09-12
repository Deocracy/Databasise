# Lane 2 findings: KV-cache reuse beyond the prefix

Scope: position-independent / modular KV-cache reuse, out-of-order composition quality,
partial-recompute repair, and the serving engines that expose these as APIs.
Bears on MelodyScribe capability 3 (paragraph KV cache kept as a reusable module,
retrieved chunks composed from cached attention states at query time).
Screened 43 candidates; 24 admitted (20 papers with PDFs in `papers/`, 4 code-only
engines with GitHub-verified facts); 19 abstained with reasons in `inventory.tsv`.

## (a) Admitted items

**Prompt Cache (arXiv 2311.04934, MLSys 2024; code: https://github.com/yale-sys/prompt-cache, MIT).**
The original modular-reuse design: a Prompt Markup Language schema marks reusable
segments ("prompt modules") so their attention states are precomputed once and
spliced into any prompt with positional correctness, reporting 8x GPU and 60x CPU
time-to-first-token cuts at unchanged accuracy. MelodyScribe should take the
schema idea directly: Score sections are exactly prompt modules, and the
per-section directives ("embed in isolation", "do not embed") are a PML equivalent.
Be careful: reuse is author-declared and static here, and the prototype repo
(114 stars, last push Nov 2024) is research-grade, not a serving engine.

**CacheBlend (arXiv 2405.16444; research code https://github.com/YaoJiayi/CacheBlend;
production home https://github.com/LMCache/LMCache, Apache-2.0, ~11.8k stars).**
The central repair result for this lane: concatenating independently computed chunk
caches loses cross-chunk attention, and recomputing only the highest-KV-deviation
tokens (~a small subset) restores full-prefill quality while cutting TTFT 2.2-3.3x
and raising throughput 2.8-5x; recompute is pipelined with cache fetch so slower
tiers are free. MelodyScribe should take selective recompute as the default compose
operator for retrieved chunks rather than raw concatenation. Be careful: a 2026
follow-up (DAF, 2607.21599, abstained) claims severe degradation at longer contexts,
so the no-loss claim needs our own length sweep before depending on it.

**EPIC (arXiv 2410.15332; code https://github.com/DerekHJH/epic, Apache-2.0).**
Formalizes position-independent caching and names the failure mode naive splicing
hits: every document start acts as an attention sink, so concatenated blocks carry
spurious sink mass; the LegoLink algorithm neutralizes it for up to 8x TTFT / 7x
throughput at negligible accuracy loss. MelodyScribe should take sink-aware repair
as mandatory, not optional, in any compose path. Be careful: small repo (22 stars),
unreplicated outside the authors, and evaluated on large models, not 1-3B.

**RAGCache (arXiv 2404.12457; no public repo found).**
Caches retrieved knowledge as a multilevel GPU/host-resident knowledge tree with an
LLM/RAG-aware replacement policy and retrieval/inference overlap: 4x TTFT, 2.1x
throughput over vLLM+Faiss. MelodyScribe should take the tree + replacement-policy
framing for its paragraph/chunk pool (reuse has a cache-management half, not just
an attention half). Be careful: no artefact released, prefix/tree-structured, and
numbers are against a 2024 vLLM baseline.

**TurboRAG (arXiv 2410.07590; code https://github.com/MooreThreads/TurboRAG).**
Precomputes document KV fully offline and eliminates online KV computation, using
mask/position redesign plus a fine-tune of the base model to hold accuracy (mean
8.6x, up to 9.4x TTFT cut). MelodyScribe should take the lesson that layout
decisions (masks, positions) and weights can be co-adapted to reuse — relevant if
we fine-tune MiniCPM5-2B for Score-shaped inputs. Be careful: accuracy depends on
that fine-tune, and the repo (102 stars, no declared license, untouched since Nov
2024) is effectively archival.

**CacheGen (arXiv 2310.07240, SIGCOMM 2024; code https://github.com/UChi-JCL/CacheGen).**
Orthogonal axis: a distribution-aware KV tensor codec plus bandwidth-adaptive
compression levels, shrinking caches 3.5-4.3x and fetch+process delay 3.2-3.7x at
negligible quality cost. MelodyScribe should take compression as the answer to
"cached states don't fit on one 16 GB GPU". Be careful: compression interacts with
non-prefix reuse — C2KV (2607.17715, abstained) shows naive combination severely
degrades accuracy, so any compress+compose stack must be validated jointly.

**ChunkAttention (arXiv 2402.15220, ACL 2024; code https://github.com/microsoft/chunk-attention, MIT).**
Prefix-tree chunked KV sharing across requests with a two-phase locality-aware
kernel (3.2-4.8x attention speedup). MelodyScribe should take the chunked-storage
plus sharing-aware kernel co-design point. Be careful: strictly prefix-bound, so it
is the baseline PIC exists to beat, not the target design.

**KVLink (arXiv 2502.16002; code https://github.com/UCSB-NLP-Chang/KVLink).**
Concatenates per-document precomputed caches at inference with link techniques that
mitigate missing cross-document attention. MelodyScribe should take it as a second,
independent implementation of the CacheBlend-family repair pattern (concat + fix-up).
Be careful: small repo (48 stars, no license stated), 2025, single-group evaluation.

**Block-Attention (arXiv 2409.15355; code https://github.com/TemporaryLoRA/Block-Attention).**
Encodes each retrieved passage as an independent KV block (all but the last),
enabling direct passage-cache reuse in RAG; the same group's 2026 follow-up adds
automatic segmentation and block distillation (2605.15913, abstained, cited not
filed). MelodyScribe should take per-passage blocks as the simplest viable compose
unit for Score sections. Be careful: independent encoding is exactly what breaks
cross-chunk attention, so this design inherits the full repair burden.

**MiniPIC (arXiv 2606.13126; implementation in https://github.com/IBM/vllm, Apache-2.0).**
PIC in under 100 lines of vLLM change: store unrotated K, apply RoPE late to tiles,
expose user-controlled reuse primitives, avoiding host-to-device transfer overhead
of sidecar designs. MelodyScribe should take this as the existence proof that
modular reuse fits inside a production engine with a tiny diff — the integration
template for our own serving path. Be careful: IBM fork (27 stars), 2026 preprint,
performance claims not yet independently reproduced.

**HYPIC (arXiv 2607.01299; no dedicated repo).**
First PIC for hybrid linear/full-attention models: per-token KV primitives do not
transfer to per-request recurrent state, and the paper rebuilds them. MelodyScribe
should take the warning seriously — if the final small model is a hybrid
architecture, the whole token-indexed compose design must be reworked. Be careful:
2026 preprint, no artefact, single evaluation family.

**CacheClip (arXiv 2510.10129; no dedicated repo).**
Uses a small auxiliary LLM's last-layer attention distribution to predict which
tokens need recomputation, explicitly positioning against APE and CacheBlend.
MelodyScribe should take the "cheap model decides the repair set" pattern — it
maps cleanly onto using the 2B harness model itself to gate recompute. Be careful:
2026 preprint, no code, and the auxiliary-model similarity assumption is unevaluated
at 1-3B scale.

**vLLM / PagedAttention (arXiv 2309.06180; https://github.com/vllm-project/vllm, Apache-2.0, ~91.5k stars).**
Paged KV memory with automatic prefix caching: the substrate every other item
assumes, extends, or beats. MelodyScribe should take it as the default serving
target and the prefix-caching baseline for ablations. Be careful: automatic prefix
caching only fires on identical prefixes, which RAG/agent assemblies rarely share
— the limitation motivating the entire PIC line.

**SGLang / RadixAttention (arXiv 2312.07104; https://github.com/sgl-project/sglang, Apache-2.0, ~35.8k stars).**
Radix-tree KV reuse across requests and program branches, plus compressed FSMs for
structured decoding — reuse plus grammar-constrained emission in one runtime, both
of which MelodyScribe needs. MelodyScribe should evaluate SGLang as the serving
engine first. Be careful: radix reuse is still prefix-structured; non-prefix chunks
need the PIC techniques above composed with it.

**KV Packet (arXiv 2604.13226; code https://github.com/ChuangtaoChen-TUM/KVPacket, MIT).**
Recomputation-free alternative: treat cached documents as immutable packets wrapped
in lightweight trainable soft prompts instead of repairing by recompute.
MelodyScribe should take it as the counter-design to CacheBlend/EPIC — if soft
wrappers work at 2B, compose cost drops to zero. Be careful: 2026 preprint, tiny
repo (37 stars), soft-prompt training cost unreported at small scale.

**Grounded Cache Routing (arXiv 2605.27494; no artefact).**
Reframes reuse as a safety decision, not a hit-rate optimization: cached answers
go stale under evidence drift and are hijackable by collisions; includes a survey
touching RAGCache, TurboRAG, CacheBlend, EPIC, PCR, and LMCache. MelodyScribe
should take the groundedness gate (evidence present, corpus version unchanged) as a
required pre-condition for any reuse. Be careful: single-author 2026 position-style
preprint; framework, not a measured system.

**HijackKV (arXiv 2607.19957; PoC https://github.com/YichiCS/KV-Cache-Hijack, MIT).**
Demonstrates KV-cache hijacking: token-match-retrieved KV encodes its original
context, so a benign-looking chunk steers victim generation under PIC. MelodyScribe
must take context-binding of cached blocks as a security requirement (see below).
Be careful: attack PoC (6 stars), exact transfer to our harness untested — treat as
threat model, not a measured exploit rate.

**CachePrune (arXiv 2605.23640; no dedicated repo).**
Unrestricted cross-user KV sharing leaks inputs through side channels; defense is
fine-grained sharing of privacy-irrelevant segments only. MelodyScribe should take
segment-level share/don't-share labels as part of the Score directive vocabulary.
Be careful: 2026 preprint, no artefact; the privacy classifier itself is unevaluated.

**ReCache (arXiv 2608.19662; code https://github.com/EIT-NLP/ReCache).**
The closest functional analogue to Folio reuse: tool/skill schemas recurring in
different orders get composition-invariant KV blocks via resource-local positions,
with retention restricted to contribution-selected layer/head routes. MelodyScribe
should take resource-local positioning for skill/Folio blocks and the
layer/head-pruned retention idea for the 16 GB budget. Be careful: August 2026
preprint, 10-star repo, no license stated, unreplicated.

**CoinRAG (arXiv 2608.07458; no dedicated repo).**
Pushes reuse below chunk level to contextualized nuggets, cutting redundancy/noise
of coarse chunks under prefill-latency budgets. MelodyScribe should take nugget
granularity as a candidate indexing unit finer than sections. Be careful: 2026
preprint, no artefact, and nugget extraction quality bounds are unreported.

**LMCache (https://github.com/LMCache/LMCache, Apache-2.0, ~11.8k stars; code-only admit).**
Production disaggregated KV store (GPU/DRAM/remote tiers, disaggregated
prefill/decode) that the CacheBlend research line ships in. MelodyScribe should
treat it as the reusable backing store rather than building tiering from scratch.
Verified via GitHub API; not cloned per lane rules.

**llama.cpp (https://github.com/ggml-org/llama.cpp, MIT, ~127.9k stars; code-only admit).**
Local-first engine with prompt-caching and KV primitives plus GGUF small-model
support — the most plausible local substrate for a 1-3B harness. Verified via
GitHub API.

**TensorRT-LLM (https://github.com/NVIDIA/TensorRT-LLM, ~14.6k stars; code-only admit).**
High-performance serving with KV-cache management/reuse APIs; cited as a PIC
target by MiniPIC-line work. Caution: GitHub reports license NOASSERTION
(NVIDIA proprietary license), limiting reuse of the code itself. Verified via
GitHub API.

**MLX (https://github.com/ml-explore/mlx, MIT, ~28.4k stars; code-only admit).**
Apple-silicon local serving with KV-cache support; relevant to the on-device
overlap of this lane with lane 9. Verified via GitHub API.

## (b) Refutations of claims in the brief

- **R1 — "Cached chunk states can be composed out of order" is false without repair.**
  CacheBlend (2405.16444), EPIC (2410.15332), TurboRAG (2410.07590), and KVLink
  (2502.16002) all show raw concatenation loses cross-chunk attention and/or
  carries sink distortion; each paper's contribution *is* the repair (selective
  recompute, LegoLink, fine-tune, link techniques). Any MelodyScribe text claiming
  free composition must be rewritten as compose-plus-repair.
- **R2 — CacheBlend's "without compromising generation quality" is contested at long contexts.**
  DAF (2607.21599, abstained, abs-verified) reports severe CacheBlend accuracy
  degradation as contexts lengthen and proposes decoupled fusion instead. Status:
  unresolved conflict between two primary sources; requires our own length sweep,
  not a citation.
- **R3 — Prefix caching does not suffice for RAG/agent assembly.**
  RAGCache (2404.12457), EPIC (2410.15332), and CacheClip (2510.10129) document
  that shared prefixes rarely occur when prompts are assembled from retrieved or
  agentic segments. Any plan resting on vLLM's automatic prefix cache for Score
  sections is refuted as a strategy; PIC or explicit modules are required.
- **R4 — Position-independent reuse is not safe by default.**
  HijackKV (2607.19957) demonstrates context-hijack via token-match retrieval;
  CachePrune (2605.23640) demonstrates cross-user input leakage via sharing side
  channels. Naive "reuse whenever text matches" is refuted; context binding and
  principal isolation are required (see security requirements).
- **R5 — Compression and non-prefix reuse do not compose freely.**
  C2KV (2607.17715, abstained, abs/HTML/GitHub-verified) reports severe accuracy
  degradation from naive compression-plus-reuse stacking and builds a unified
  framework instead. A MelodyScribe plan that adds CacheGen-style compression to a
  PIC compose path without joint validation is contradicted.

## (c) Unresolved ledger

Each abstained entry carries its reason in `inventory.tsv`; summary by cause:
- *Scope-bounded despite verification* (abs page opened, not filed): TokenDance,
  SparseX, PCR, MoT, Universal Context-Reuse Layer, LinearKV, AgentKVShift, Block
  Segmentation/Distillation, AdapShot, ObjectCache, Can-I-Buy-Your-KV-Cache —
  each overlaps an admitted neighbour or sits outside the single-harness scope.
- *Security overlap with lane 6* (abs-verified, cited not filed): CacheProbe
  (2605.30613), KeyPooling (2608.17485).
- *Quality-measurement cites* (abs-verified, cited not filed): DAF (contests
  CacheBlend, needs replication), C2KV (compression interaction warning), Probing
  the Prompt KV Cache (2605.30574: redundancy is template form, not content).
- *Not verifiable*: KVBoost and ProphetKV surfaced only as arXiv-search snippets;
  ids were not captured and abs pages were never opened — no id, repo, or number
  is recorded for either. KVShareArena (2609.10266) surfaced with id but its abs
  page was never opened; too fresh to depend on.

## (d) Security findings (requirements for the Folio gate)

- **REQ-L2-1 Context-bind every reusable block (HijackKV, 2607.19957).**
  Retrieval of a cached block must key on (content hash, source-context hash,
  producer identity), never on surface token match alone; re-verify binding at
  compose time.
- **REQ-L2-2 Isolate pools by trust principal (CachePrune, 2605.23640; KeyPooling,
  2608.17485; CacheProbe, 2605.30613).**
  Human-authored skill, model-written Folio, and retrieved-third-party blocks must
  live in separate KV pools; cross-pool sharing defaults off; share only segments
  explicitly labeled privacy-irrelevant, since sharing state is timing-observable.
- **REQ-L2-3 Gate reuse on groundedness (Grounded Cache Routing, 2605.27494).**
  Every reuse decision checks that the backing evidence is still present and the
  corpus version is unchanged; stale or collided entries abstain to full prefill.
- **REQ-L2-4 Repair sinks on every compose (EPIC, 2410.15332).**
  Out-of-order composition must include sink mitigation (recompute of boundary
  tokens or equivalent); raw concatenation is prohibited by R1 above.
