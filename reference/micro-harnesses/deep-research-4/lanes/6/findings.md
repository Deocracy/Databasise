# Lane 6 findings: Caching and parallel workload

Scope: prefix/radix KV caching, KV composition, semantic and result caches,
continuous batching and chunked prefill, priority scheduling of realtime
requests over bulk ingest on one GPU, one model process serving two jobs,
concurrent store writes with locks and idempotency, cache invalidation.
Screened 39 candidates; admitted 27 (22 papers with PDFs filed in
`papers/`, 5 repo/docs systems); 12 abstains with reasons in
`inventory.tsv` and the ledger below.

## (a) Admitted items

**SGLang and RadixAttention (arXiv 2312.07104).** A serving runtime whose
request scheduler holds decoded tokens in a radix tree and reuses the KV
of any shared prefix across requests, plus a compressed finite-state
machine for constrained decoding; vendor-reports up to 6.4x throughput
over contemporary inference systems. Take: this is the reference design
for the rig's "runtime prefix reuse stays" plus instruction-first
ordering doubling the shared prefix — put the invariant instruction text
first so every section decode shares one radix path. Be careful: reuse is
hit-or-miss at block granularity in descendants (see vLLM APC limits),
and reuse is not behavior-transparent (see Cache-divergence below);
treat hit-rate as a metric the harness logs, not an assumption.

**PagedAttention / vLLM (arXiv 2309.06180, SOSP 2023).** Block-paged KV
management giving near-zero fragmentation and safe sharing of blocks
within and across requests; vendor-reports 2-4x throughput at equal
latency. Take: block granularity is the unit of sharing, eviction, and
accounting the harness should reason in — MelodyScribe's per-section
decodes are naturally block-aligned sharers of the instruction prefix.
Be careful: paging alone does not decide *what* to share; the radix
policy above it does, and sharing changes numerics (see
Cache-divergence).

**Orca (OSDI 2022, https://www.usenix.org/conference/osdi22/presentation/yu).**
Iteration-level (continuous) batching with selective batching of
attention vs non-attention ops; vendor-reports large throughput gains
over static batching on GPT-3 175B. Take: the harness's asyncio-workers-
over-one-model-lock design is a single-process Orca: schedule at decode-
iteration granularity, never hold a batch open waiting for a straggler
section. Be careful: Orca assumes a distributed engine; on one 16 GB
card the analog of its scheduler is the lock ordering between ingest
sections, recall queries, and embed jobs — which Orca does not solve.

**SARATHI (arXiv 2308.16369).** Chunked prefills piggybacked onto decode
batches so long prompts do not stall running decodes. Take: section
prefills (~3.7k tokens at ~3.7k tok/s is ~1 s of prefill) should be
chunked so a bulk-ingest section never head-of-line-blocks a realtime
recall or frontier-assist decode. Be careful: chunking adds launch
overhead per chunk; chunk size is a tuned constant, not free (see
SLOWeave).

**Sarathi-Serve (arXiv 2403.02310).** Stall-free scheduling built on
chunked prefills; vendor-reports 2.6x capacity on Mistral-7B/A100 and up
to 5.6x with pipeline parallelism under tail-latency constraints. Take:
optimize for tail latency (p99 time-to-first-op for realtime requests),
not mean throughput, when bulk ingest and realtime share the card. Be
careful: numbers are A100-cluster serving figures; the transferable part
is the scheduling discipline, not the multipliers.

**CacheBlend (arXiv 2405.16444).** Reused KV from non-prefix RAG chunks
ignores cross-attention with preceding text, so naive reuse degrades
quality; selective recompute of a small fraction of tokens recovers it.
Take: KV is composable only with a recompute budget — when the harness
reorders or concatenates Score sections, or reuses a Folio prefix in a
new context, it must either keep byte-identical prefixes (free reuse) or
pay recompute; there is no middle option. Be careful: the recompute
fraction is workload-dependent; log a quality gate (Proof pass rate)
against reuse rate rather than assuming zero loss.

**Prompt Cache (arXiv 2311.04934).** Prompt modules with precomputed
attention states reused in new positions, with CPU/GPU tiering. Take:
precompute-and-pin the harness's invariant pieces (extraction
instruction, held-out example, grammar preamble) once and treat them as
read-only modules — the static analog of instruction-first prefixing.
Be careful: positional independence tricks do not survive relative
position encodings without care; keep pinned modules strictly prefixal.

**ChunkAttention (ACL 2024, doi:10.18653/v1/2024.acl-long.623).** Chunks
monolithic KV tensors into a runtime prefix tree shared across requests
and pairs it with a two-phase partitioned attention kernel;
vendor-reports 3.2-4.8x kernel speedups for 1-4k shared prompts. Take:
sharing the tree is only half the win; the kernel must be locality-aware
over shared chunks, otherwise shared-prefix batching saves memory but
not time. Be careful: gains are kernel-level on long shared prompts;
with short sections the harness wins on memory pressure, not speed.

**Splitwise (arXiv 2311.18677).** Splits prefill and decode phases onto
different machines with phase-aware provisioning. Take: prefill and
decode contend differently (compute-bound vs memory-bound); even on one
GPU the harness should account and schedule them as different job
classes, not one FIFO. Be careful: the paper's answer (more machines)
is unavailable on the rig; import the diagnosis, not the prescription.

**DistServe (arXiv 2401.09670).** Goodput-aware placement of prefill and
decode across GPUs, searching placement and parallelism jointly. Take:
define harness goodput explicitly (realtime requests meeting deadline +
bulk sections per hour) and schedule to it, rather than to raw tok/s.
Be careful: its search assumes a cluster; on one card goodput reduces to
priority and chunk-size policy (see SLOWeave).

**Mooncake (arXiv 2407.00079).** Disaggregated serving with paged KV
pooled in CPU DRAM/SSD and transferred over RDMA, with overload-oriented
scheduling. Take: the strongest published counterpoint to "no persisted
per-chunk KV at 2B scale" — persistence pays when transfer is cheaper
than recompute; the rig's spike 005 verdict (20-110 ms saved) should be
re-tested against an LMCache-style tier before being cast in concrete.
Be careful: Mooncake's economics assume datacenter networking and long-
reuse horizons; a 2B model's cheap prefill weakens the case for keeping
bytes around.

**Hydragen (arXiv 2402.05099).** Batches sequences with long shared
prefixes into one shared-prefix attention pass plus per-sequence
suffixes. Take: the closest published analog of the rig's
instruction-first batching —28 section decodes sharing one instruction
prefix is exactly a Hydragen batch; cite it as prior art for the
technique. Be careful: Hydragen shares within a batch, not across time;
cross-request persistence still needs the radix layer (SGLang).

**XGrammar (arXiv 2411.15100).** Byte-level pushdown-automaton grammar
engine with token-mask cache and persistent execution stack, co-designed
with the inference engine; vendor-positions it as near-zero-overhead
structured generation. Take: this is the direct attack on the rig's
measured ingest bottleneck (grammar filtering 9x on CPU): move the mask
computation into a cached automaton overlapping GPU execution instead of
filtering logits on the CPU per step. Be careful: near-zero is a vendor
claim on large-model serving; verify mask-cache hit rates on the small
op grammar before assuming the 9x disappears.

**Punica (arXiv 2310.18547).** Serves many LoRA adapters on one base
model in one batch via segmented gather-GEMM. Take: the nearest
existence proof for the rig's colocation questions — one resident model
serving heterogeneous jobs (here: embedding reads vs op-emitting
decodes; by analogy, the contrastive-LoRA vs op-emission conflict of
spikes 004/006/011 is a multi-tenant batching problem, and Punica-style
segregated execution is the pattern that keeps tenants from destroying
each other). Be careful: Punica segregates adapters, not embedding-vs-generate
modes of one weight set; the KL-anchored adapter still needs
its own validation.

**Llumnix (arXiv 2406.03243).** Live-migrates requests across serving
instances to rebalance load with preemption-safe rescheduling. Take: the
migration primitive is what a priority scheme needs to preempt bulk
ingest for realtime work without losing it — checkpoint section state,
yield the lock, resume. Be careful: migration across instances has no
meaning on one GPU; shrink it to yield/resume points inside the asyncio
scheduler.

**FastServe (arXiv 2305.05920).** Skip-join MLFQ scheduling with
proactive KV upload/download overlapped with compute. Take: shortest-
remaining-work-first with aging is the right default when short realtime
queries share the lock with long bulk sections; overlap any KV movement
with compute rather than stopping the world. Be careful: MLFQ needs a
job-size predictor; section token counts are known but op-emission
lengths are not — predict from the token cap, not history.

**MeanCache (arXiv 2403.02694).** Client-side, per-user semantic cache
with precision control, reporting hit-rate/precision tradeoffs. Take:
semantic caching belongs client-side (in the harness, keyed per
session/namespace), not inside the engine; per-user keys are the privacy
unit. Be careful: precision (false-hit) control is load-bearing — a
wrong recall payload poisons the frontier model's context silently.

**Cache Saver (EMNLP 2025 Findings, doi:10.18653/v1/2025.findings-emnlp.1402).**
Namespace-aware list-valued response cache preserving i.i.d. sampling
and reproducibility; vendor-reports ~25% cost and ~35% CO2 cuts (~60% in
ablation-style repeated workloads). Take: memoise harness-level results
(retrieval payloads, Proof verdicts on repeated ops) under namespace
keys (session + store-version + model-hash), and keep a list of values
per key so repeated sampling stays statistically honest. Be careful:
list-valued caching costs memory per key; bound list lengths and expire
by store version, or the cache becomes a stale-memory bug.

**SLOWeave / deadline-aware adaptive prefill chunking (arXiv
2609.07883).** Online scheduler selecting the largest prefill chunk
predicted to finish before the earliest active decode deadline, via
log-time search over a monotone cost model, with no per-workload tuning.
Take: replace the fixed chunk-size constant with a deadline-driven rule
— realtime decodes publish deadlines, bulk prefills fill the slack.
Be careful: needs a calibrated iteration-cost model for the specific
card and model; calibrate once per rig (MiniCPM5-2B Q8 numbers exist in
spike 009) and re-check after fine-tunes.

**KV-cache timing side channel under contention (arXiv 2609.06853).**
Seven experiments on live shared serving show prefix-cache hit/miss
timing distinguishes cached prefixes, with effect size collapsing as
tenant contention rises. Take: shared-prefix reuse is an observable
channel — any future multi-tenant or cloud-backed MelodyScribe must
treat cache-hit timing as information disclosure (see security). Be
careful: single-user local rig is barely exposed; apply proportionally.

**Cache-induced divergence under quantization (arXiv 2609.04748).**
Enabling prefix caching changed an agentic tool-use trajectory on 36.2%
of episodes at 16-bit and 75.0% with quantized weights, holding model,
seed, and order fixed. Take: on a Q8 2B rig, prefix reuse is a
correctness variable, not a transparent optimization — gate reuse
experiments on Proof pass rate and downstream recall quality, and record
cache on/off in every eval. Be careful: one workload, vendor-reported;
treat as a strong caution with a replication obligation, not a veto.

**CacheTracer (arXiv 2608.20732).** API-only discovery of hidden
reseller dependencies via prefix-cache timing. Take: independent
confirmation that the prefix-cache channel is practical at Internet
scale — defense belongs in the harness threat model from the start. Be
careful: ecosystem-audit context; relevance to the rig is via the
mechanism, not the setting.

**GPTCache (https://github.com/zilliztech/GPTCache, 8190 stars, MIT).**
Production semantic cache with embedding-similarity lookup and
LangChain/llama_index integrations. Take: the baseline semantic-hit
expectations and eviction/similarity-threshold knobs to beat; use it as
the reference when the harness prices a semantic tier. Be careful: no
canonical paper — features, not benchmarks, are the citable facts.

**LMCache (https://github.com/LMCache/LMCache, 11785 stars,
Apache-2.0).** The fastest-moving external KV-cache tier with vLLM
kv-connector integration. Take: the concrete persisted-KV option
against which "no persisted KV at 2B" must be periodically re-tested;
watch its hit-rate-vs-recompute numbers per release. Be careful: no
paper found in the README (main or dev branches) — cite the repo, not a
result.

**Outlines (https://github.com/dottxt-ai/outlines, 15790 stars,
Apache-2.0).** The incumbent structured-generation library (FSM-index
guided generation). Take: the baseline grammar stack XGrammar must beat
on the rig; keep an Outlines backend as the fallback while measuring.
Be careful: no canonical paper — same citation discipline as GPTCache.

**vLLM Automatic Prefix Caching docs
(https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/).**
`enable_prefix_caching` reuses block-granular KV for shared prefixes;
documented limits: prefill-only savings, zero gain for decode-dominated
or prefix-less workloads, sub-block mismatches do not share. Take:
align section and query layouts to block boundaries and put shared text
strictly first; measure prefill-time saved, never tok/s blended. Be
careful: docs are primary only for what the API allows, not for
performance claims.

**SQLite WAL docs (https://www.sqlite.org/wal.html).** WAL gives
readers-don't-block-writer with a single writer, 1000-page
autocheckpoint, checkpoint starvation under continuous readers,
SQLITE_BUSY edge cases, and a 2026 WAL-reset corruption race (fixed in
3.51.3) when two connections write/checkpoint simultaneously. Take: one
write lock per store is not just policy, it is the engine's own model —
plus pin SQLite >= 3.51.3 and checkpoint on idle, never inline on the
realtime path. Be careful: WAL needs same-host shared memory and
`-wal`/`-shm` sidecars — the blob-artifact story must carry them.

## (b) Refutations

1. **"Runtime prefix reuse is transparent" is contradicted.**
Cache-divergence (arXiv 2609.04748) holds model, decoding parameters,
seed, and order fixed and still changes agentic trajectories on 36.2%
of episodes at 16-bit and 75.0% under quantization when the prefix
cache is on. The brief's settled line "runtime prefix reuse stays"
(spike 005/009 basis) survives only as a performance decision; as a
correctness claim it is refuted for quantized small models until the
harness replicates the measurement on MiniCPM5-2B Q8 with Proof pass
rate as the gate.
2. **"KV of reused chunks composes freely" is contradicted.**
CacheBlend (arXiv 2405.16444) shows reused non-prefix KV ignores
cross-attention with preceding text and needs selective recompute.
Any harness plan that concatenates section contexts or reuses Folio
prefixes mid-prompt without a recompute budget contradicts this
primary source; only byte-identical prefix reuse is free.
3. **"SQLite WAL + one writer is bulletproof" is contradicted.**
The sqlite.org WAL page documents the WAL-reset data race (present
3.7.0 through 3.51.2, fixed in 3.51.3, 2026-03-03): two connections
writing/checkpointing at the same instant can corrupt the database.
The one-write-lock-per-store rule must be enforced in the harness
*and* the SQLite floor must be >= 3.51.3; either alone is insufficient.

## (c) Unresolved ledger

- **Block-Attention.** Named in the brief; no arXiv id, DOI, or
repository could be pinned (OpenAlex queries returned only
PagedAttention/survey noise). Reason: unverifiable primary source.
- **NDSS 2026 semantic-cache-poisoning paper
(doi:10.14722/ndss.2026.240200).** DOI resolves to a 1.9 MB NDSS PDF
and OpenAlex carries the title record, but title/authors could not be
verified from readable bytes. Reason: existence corroborated,
authorship unverified — do not cite as admitted.
- **One model process serving two jobs (embedding + generation).**
No paper isolating embed-vs-generate colocation in one process was
found; Punica (multi-LoRA) is the nearest verified analog and vLLM's
pooling/embed endpoints were observed in docs navigation but never
opened. Reason: thin literature, not negative evidence.
- **Single-GPU bulk-ingest vs realtime priority.** FastServe, Llumnix,
and SLOWeave all assume serving clusters or instance pools; none
isolates one-card priority between a bulk backfill and a latency-
sensitive request. Reason: gap, needs a rig-side experiment.
- **Cache invalidation on store change.** No dedicated study found;
practice is scattered across docs (APC limits, WAL checkpointing,
CacheSaver namespaces). Reason: gap, harness must design it.
- **Semantic-cache hit-rate numbers.** MeanCache's tradeoff curves and
GPTCache's reported rates live inside the admitted PDFs/repos and were
not extracted here. Reason: admitted but unextracted — pull numbers
before pricing a semantic tier.
- **Paper-linked repo stars.** DistServe, PromptCache, MeanCache,
Sarathi-Serve, and Splitwise-sim URLs come from admitted PDF bytes,
but star/push/license facts are missing (GitHub API rate-limited at
fetch time). Reason: recorded as unverified, never invented.
- **FlashInfer (arXiv 2501.01005), DroidSpeak (arXiv 2411.02820),
BurstGPT, py-kvcache, KVMem, GraniKV, ReCache, CacheRoute, TOPAS,
To-Keep-or-Not (SYSTOR).** Title-screened in the S2 forward-chain
sweep of vLLM/SGLang citations (200 records) as adjacent but
out-of-scope or unopened. Reason: screened, primary source not opened.

## (d) Security findings (stated as requirements)

- **R1 — namespace-isolate every cache tier.** Semantic and result
caches must key on (session, store-version, model-hash); CacheSaver's
namespace-aware design is the pattern, and the unverified NDSS
poisoning report plus MINJA/PoisonedRAG-class risks mean unkeyed
caches are an ingestion hole for persistent memory.
- **R2 — treat prefix-hit timing as observable.** KV-timing
(2609.06853) and CacheTracer (2608.20732) establish the channel on
live systems; any multi-tenant or cloud-backed deployment must add
no-reuse boundaries for sensitive prefixes (Folios, private facts).
Single-user local rig: document, do not over-engineer.
- **R3 — pin SQLite >= 3.51.3 and checkpoint off the realtime path.**
WAL-reset race (sqlite.org, 2026-03); autocheckpoint stalls and
SQLITE_BUSY cases must never execute inline on a frontier-assist
deadline.
- **R4 — gate every reuse optimization on Proof pass rate.**
Cache-divergence (2609.04748) makes reuse a correctness variable;
prefix reuse, semantic hits, and memoised payloads ship only with a
measured non-regression on Proof and recall quality.

## Harness implications

1. Keep runtime prefix reuse with instruction-first ordering, but log
hit-rate and gate it on Proof pass rate, because reuse is fast yet not
behavior-transparent under quantization (SGLang 2312.07104;
Cache-divergence 2609.04748).
2. Chunk section prefills and schedule them against realtime decode
deadlines (SLOWeave rule), because fixed-size chunks and FIFO locks let
bulk ingest stall frontier-assist responses (SARATHI 2308.16369;
Sarathi-Serve 2403.02310; SLOWeave 2609.07883).
3. Reuse KV only across byte-identical prefixes and budget recompute
for any composition, because cross-attention makes naive chunk reuse
lossy (CacheBlend 2405.16444; vLLM APC docs).
4. Replace CPU-side per-step grammar filtering with a cached-automaton
engine (XGrammar), because the 9x filtering overhead is the measured
ingest bottleneck and mask caching is its direct remedy (XGrammar
2411.15100; Outlines baseline).
5. Memoise harness-level results under namespace keys with bounded
list-valued entries expired by store version, because unkeyed caches
are poisoning and staleness holes (CacheSaver
2025.findings-emnlp.1402; MeanCache 2403.02694; GPTCache repo).
6. Enforce one write lock per store, checkpoint SQLite off the
realtime path, and pin SQLite >= 3.51.3, because WAL gives single-
writer semantics but carried a real corruption race below that floor
(SQLite WAL docs; Llumnix yield/resume pattern 2406.03243).
7. Define and schedule to goodput (realtime deadlines met + bulk
sections/hour) with shortest-remaining-work-first and aging, because
raw tok/s hides the tail latency the co-processor lives or dies by
(DistServe 2401.09670; FastServe 2305.05920).
8. Treat one-process-two-jobs as multi-tenant batching with
segregated execution and per-tenant validation, because embedding and
op-emission already destroy each other in naive colocation (Punica
2310.18547; Hydragen batching 2402.05099).
9. Re-test persisted KV tiers (LMCache/Mooncake-style) against
recompute each release, because "no persisted KV at 2B" is a price
ratio, not a law, and the ratio moves (Mooncake 2407.00079; LMCache
repo).
10. Add no-reuse boundaries and cache-timing discipline to the threat
model now, because prefix-cache side channels are practical on live
systems even though the local single-user rig is barely exposed
(KV-timing 2609.06853; CacheTracer 2608.20732).
