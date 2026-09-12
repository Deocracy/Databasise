# Lane 8 findings: batched serving and KV sharing on one GPU

Scope: continuous batching, prefix caching, prompt/output ordering for shared
prefixes, speculative decoding for small models, single-GPU throughput/VRAM
scaling, multi-agent shared-prefix serving. Screened 39 candidates, admitted 35
(24 papers with PDFs in `papers/`, 11 engine/repo/doc artefacts).

## (a) Admitted items

**Orca — iteration-level (continuous) batching (OSDI 2022, no arXiv).**
Iteration-level scheduling plus selective batching (no batching inside
attention) gave 36.9x throughput over FasterTransformer on GPT-3 175B at equal
latency (https://www.usenix.org/conference/osdi22/presentation/yu).
Take: continuous batching is the non-negotiable substrate for MelodyScribe
workers — every engine below inherits it. Careful: the 36.9x is vs a static
batcher on 175B over 16 GPUs; expect far smaller multiples on a 2B model on
one 16 GB card where prefill saturates compute quickly.

**vLLM / PagedAttention (2309.06180, SOSP 2023).** Block-paged KV cache kills
fragmentation and enables block sharing within and across requests; reported
2-4x throughput over FasterTransformer/Orca at equal latency, growing with
sequence length. Take: run the harness decoder on vLLM (or any PagedAttention
engine) — it is the mechanism that lets hundreds of section-workers coexist in
16 GB. Careful: vLLM shares identical *prefix* blocks; MelodyScribe sections
differ per document, so sharing comes from the skill prompt, not the content.

**vLLM Automatic Prefix Caching docs (docs.vllm.ai).**
`enable_prefix_caching=True`; blocks are hash-chained over prefix tokens;
SHA256 option against collisions; `cache_salt` isolates tenants against cache
timing probes. Take: put the entire human-authored skill + Score schema first
in every prompt so one hash chain covers all workers; salt per tenant if
serving untrusted users. Careful: any per-section token before the shared
region breaks the chain — order is load-bearing.

**SGLang / RadixAttention (2312.07104).** A radix tree over KV pages reuses
shared prefixes across forked programs (agents, few-shot, trees) with a
cache-aware scheduler; structured-output FSM speeds constrained decoding;
reported up to 6.4x throughput on agentic/structured workloads. Take: this is
the closest published analogue of MelodyScribe (one skill, many forked
section calls) — prefer SGLang when the shared unit is a program, not just a
string. Careful: tree management pays off only when fan-out shares deep
prefixes; shallow sharing adds lookup overhead for no win.

**SARATHI (2308.16369) and Sarathi-Serve (2403.02310).** Split prefills into
chunks and piggyback decodes in every batch (decode-maximal batching):
LLaMA-13B on A6000 gained up to 10x decode and 1.33x end-to-end throughput;
Sarathi-Serve's stall-free scheduler reached 2.6x serving capacity vs vLLM on
Mistral-7B/1xA100 and 5.6x with pipeline parallelism. Take: enable
chunked-prefill-style scheduling so one long section never stalls the decode
of all others — this is the output-ordering answer. Careful: chunk size is a
latency knob, not free throughput; tiny chunks inflate prefill round-trips.

**DeepSpeed-FastGen / Dynamic SplitFuse (2401.08671).** Same family as
SARATHI but framed as fixed token-budget forward passes: 2.3x effective
throughput, 2x lower average latency, 3.7x lower tail latency vs vLLM.
Take: a second implementation of the same ordering principle with an explicit
benchmarking methodology worth copying for Spike 009. Careful: vendor
self-benchmark vs vLLM; treat as "what the vendor reports".

**Splitwise (2311.18677) and DistServe (2401.09670, OSDI 2024).** Both split
prefill from decode: Splitwise onto phase-suited machines (1.4x throughput at
20% lower cost); DistServe co-optimises per-phase parallelism and placement
(4.48x more requests / 10.2x tighter SLO vs SOTA). Take: the prefill/decode
asymmetry is real and measured — but on ONE 16 GB GPU there is nowhere to
disaggregate to; use these as the argument for chunked colocation, not for
splitting. Careful: DistServe's repo (LLMServe/DistServe, 834 stars, last push
2025-04) is stale reference code, not a dependency.

**Mooncake (2407.00079, FAST 2025).** KVCache-centric disaggregation with a
Conductor scheduler, early overload rejection, and a Transfer Engine
(87-190 GB/s) now reused by SGLang/vLLM/TRT-LLM/NIXL; Kimi served 75% more
requests. Take: production proof that scheduling *around the KV cache* (not
the requests) wins, plus a reusable transfer layer. Careful: multi-node
RDMA/DRAM/SSD design; on one GPU only the cache-centric scheduling lesson
transfers.

**MemServe / MemPool (2406.17565).** One API layer (memory, index, transfer)
unifying context caching and disaggregated inference, with prompt-tree
locality-aware routing: ShareGPT JCT -30% from disaggregation plus -17% from
caching; ReAct P99 JCT -53%, TTFT -85%. Take: the MemPool abstraction is the
right shape for MelodyScribe's KV-reuse layer if it ever spans processes.
Careful: single-server 8xH800 evaluation; no consumer-GPU numbers.

**LMCache (2510.09665 + LMCache/LMCache repo, 11771 stars, Apache-2.0).**
Engine-independent KV layer over vLLM/SGLang: large-chunk CPU/disk/Redis
offload, NIXL PD transfer, CacheBlend non-prefix reuse; up to 15x vLLM
throughput on multi-round QA/document workloads. Take: the most runnable
artefact in this lane for one-GPU work — tier overflow KV to CPU RAM while
keeping hot prefixes on GPU. Careful: 2025 paper, enterprise-tuned; verify
the 15x on our workload before believing it.

**HydraGen (2402.05099, ICML 2024 workshop).** Exact prefix/suffix attention
decomposition with inter-sequence batching: up to 32x CodeLlama-13B
throughput over vLLM at large batch/prefix, <15% drop growing prefix 1K-16K
vs >90% for baselines. Take: when thousands of workers share one long skill,
prefix attention should be one batched matmul, not N vector products — check
whether our engine's cascade/cascade-like path already does this (FlashInfer
below does). Careful: repo (58 stars) untouched since May 2024; read, don't
depend.

**Preble / E2 (2407.00023, ICLR 2025).** First distributed scheduler that
co-optimises KV reuse against load balance (exploit + explore): 1.5-14.5x
average latency, 2-10x p99 over SOTA on long shared-prompt workloads, as a
layer over vLLM/SGLang. Take: the prompt-ordering algorithm for worker fleets
— route same-prefix sections to the same replica, spill over on imbalance.
Careful: distributed setting; single-GPU analogue is group-by-prefix
scheduling inside one batch (see BatchLLM).

**BatchLLM (2412.03594, MLSys 2026).** Built for exactly our shape —
throughput-oriented *offline batches* with shared prefixes: global prefix
tree built ahead of time, prefix-group scheduling, decode-ratio-first
reordering, memory-centric token batching; 1.3-10.8x over vLLM/SGLang. Take:
for Spike 009/010, sort section jobs by shared prefix and schedule
high-decode-ratio groups first — this paper is the recipe. Careful: newest
item here (v3 Apr 2026); re-verify numbers against the MLSys version.

**Prompt Cache (2311.04934, MLSys 2024).** Schema-declared reusable prompt
modules with position-correct KV reuse: 8x GPU / 60x CPU TTFT cuts on
long-prompt QA. Take: declare Score sections as modules with explicit
position IDs — the disciplined version of "shared prefix". Careful:
modules must be *verbatim* repeats; paraphrased sections get zero reuse.

**CacheBlend (2405.16444).** Reuses KV of *non-prefix* chunks with selective
recompute of a small token subset: TTFT 2.2-3.3x lower, 2.8-5x throughput vs
full recompute at equal quality. Take: the fallback when sections share
retrieved chunks in different orders — reuse plus surgical recompute beats
full prefill. Careful: recompute fraction is quality-critical; the paper's
sweet spot must be re-measured per model.

**Llumnix (2406.03243, OSDI 2024).** Runtime request rescheduling with live KV
migration across instances: order-of-magnitude tail-latency cut, 36% cost
saving. Take: migration as an escape hatch for stragglers, not the base
design; on one GPU its lesson is "pre-empt and requeue the long tail".
Careful: Ray-based implementation (llumnix-project/llumnix-ray, 562 stars)
is heavy for a single card.

**NanoFlow (2408.12757, OSDI 2025).** Intra-device parallelism over nano-batches
plus the validated claim that large-batch serving is *compute-bound*, not
memory-bound: 1.91x over vLLM/FastGen/TRT-LLM, 68.5% of theoretical optimal.
Take: at high concurrency, overlap compute/memory/network inside the device
instead of assuming memory walls — sizes the batch target for Spike 009.
Careful: 8xA100 DGX numbers; the compute-bound crossover sits at far smaller
batches on a 16 GB card.

**FlashAttention (2205.14135).** IO-aware exact attention; the kernel all
serving stacks descend from. Take: lineage only. Careful: its headline
numbers are *training* speedups — do not cite them for serving.

**FlashInfer (2501.01005, MLSys 2025 + repo, 6385 stars, Apache-2.0).** JIT
attention templates, block-sparse/composable KV formats, StreamK load
balancing, and cascade attention for shared prefixes; 29-69%
inter-token-latency cuts; ships inside SGLang/vLLM/MLC. Take: the kernel
substrate to standardise on — including its shared-prefix path. Careful:
JIT template surface is large; pin versions.

**Speculative decoding trio: SpecInfer (2305.09781, ASPLOS 2024), Medusa
(2401.10774), EAGLE (2401.15077, ICML 2024) + EAGLE-2 (2406.16858, EMNLP
2024).** SpecInfer's tree verification (1.5-3.5x), Medusa's extra heads
(2.2-3.6x, frozen-backbone mode is lossless), EAGLE's feature-level drafting
(2.7-3.5x, 2x throughput), EAGLE-2's confidence-grown dynamic trees
(3.05-4.26x, no extra training). Take: for a 2B-class worker, Medusa-1-style
frozen heads or EAGLE-style single-head drafting are the only variants that
do not demand a second model in 16 GB; EAGLE-2's no-retraining adaptation is
the most practical. Careful: every variant needs per-target draft training
except EAGLE-2's tree policy, all numbers are 7B-70B on datacenter GPUs, and
grammar-constrained op emission eriodes acceptance rates — measure, don't
assume.

**Engines for one 16 GB GPU.** llama.cpp/llama-server (ggml-org, ~128k stars,
MIT): slot-based continuous batching, KV reuse, CPU+GPU hybrid, GGUF
quantisation — the best consumer-card fit. TensorRT-LLM (14606 stars,
proprietary NVIDIA license): inflight batching, closed kernels, NVIDIA-only.
TGI (10886 stars, Apache-2.0): archived — historical reference only, do not
build on it. Take: prototype on llama-server or vLLM/SGLang small-model
configs; keep TRT-LLM as a numbers baseline. Careful: no paper in this set
reports small-model concurrency on 16 GB cards — all scaling numbers are
A100/H100-class.

## (b) Refutations

No brief claim was contradicted by a primary source. Two cautions that read
like refutations but are scope limits: (1) every throughput multiple above
was measured on datacenter GPUs (A100/H100, often multi-GPU) with 7B+ models
— none transfers numerically to a 2B model on one 16 GB card; (2) Orca has no
arXiv id (verified: OSDI 2022 proceedings only), so any citation by arXiv id
is fabrication — cite the USENIX page/DOI.

## (c) Unresolved ledger

- Consumer-GPU concurrency numbers (16 GB, 0.3B-2B, hundreds/thousands of workers): no primary source found; vendor blogs claim them but were excluded as secondary. Reason: literature evaluates 7B+ on A100/H100.
- Output-ordering (decode scheduling across heterogeneous section lengths): SARATHI/Sarathi-Serve cover prefill/decode interleaving, not which *finished* outputs to surface first. Reason: no paper found on output ordering as such.
- llama.cpp slot sizing / cache-reuse measurements: repo verified, but no paper or doc page with numbers was opened. Reason: docs not fetched; engine behaviour confirmed only at README level.
- SGLang cache-aware scheduling policy details beyond the paper: not fetched from docs. Reason: bounded to paper + repo facts.
- TensorRT-LLM KV-cache/prefix-caching specifics: no primary doc opened. Reason: closed-source; docs not fetched this round.
- Preble code: promised on acceptance; no repo verified. Reason: could not confirm release.
- EAGLE/Medusa acceptance rates under grammar-constrained decoding: no source found. Reason: intersection not studied in fetched set; must be measured in Spike 009.

## (d) Security findings (requirements)

- R1 (tenant isolation): any shared prefix cache MUST support per-tenant salt/namespace (vLLM `cache_salt` pattern, docs.vllm.ai) — otherwise response-time differences leak cached content across users.
- R2 (hash strength): block-hash prefix caches in multi-tenant setups MUST use a collision-resistant hash (vLLM SHA256 option), not the fast default.
- R3 (module integrity): schema-declared reusable segments (Prompt Cache pattern) MUST be byte-verified before KV reuse; paraphrase ≠ reuse, silent substitution = wrong attention.
- R4 (untrusted workers): thousands of parallel workers sharing one KV pool MUST be treated as mutually untrusted for cache addressing — partition the radix/prefix namespace per job.
