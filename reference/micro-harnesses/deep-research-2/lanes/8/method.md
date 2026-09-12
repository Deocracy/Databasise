# Lane 8 method

## Queries run

Web search (session provider, fast mode), one query per target, e.g.
"DistServe disaggregating prefill decoding LLM serving arXiv id",
"Hydragen high-throughput LLM inference shared prefixes arXiv",
"Mooncake KVCache-centric disaggregated architecture LLM serving arXiv",
"Orca distributed serving system transformer generative models OSDI 2022 Yu",
"Llumnix dynamic rescheduling LLM serving arXiv",
"NanoFlow large language model serving throughput nanoscale arXiv",
"Preble efficient distributed prompt scheduling LLM serving arXiv",
"MemServe context caching disaggregated LLM serving elastic memory pool arXiv",
"FlashInfer kernels LLM serving attention arXiv 2412",
"DeepSpeed-FastGen high-throughput text generation MII SplitFuse arXiv",
"BatchLLM optimizing batched LLM inference prefix sharing arXiv",
"LMCache elastic KV cache reuse engine arXiv",
"EAGLE-2 dynamic draft tree speculative sampling arXiv 2406",
"vLLM documentation automatic prefix caching enable-prefix-caching KV cache reuse".
Direct arXiv abs fetches for IDs recalled up front (vLLM, SGLang, SpecInfer,
Sarathi-Serve, SARATHI, EAGLE, Medusa, Splitwise, FlashAttention, Prompt
Cache, CacheBlend). GitHub REST API for repo facts (stars, pushed_at,
license), via shell curl first, then via fetcher after 403 rate limits.

## Sources used

arXiv abs pages + PDFs (primary for papers); USENIX proceedings pages + PDFs
for Orca, DistServe (corroboration), Llumnix, NanoFlow; ACL Anthology page for
EAGLE-2 venue; ICLR/MLSys proceedings pages for Preble/BatchLLM venues; GitHub
API + repo pages (primary for engine facts); docs.vllm.ai (primary for APC
behaviour). Semantic Scholar and export.arxiv.org APIs were unusable (429 /
"Rate exceeded" from this egress); Papers with Code API returned HTML, not
JSON. No Hugging Face Hub or OpenReview data was needed.

## Screening counts

39 candidates screened: 24 papers admitted, 11 engine/repo/doc artefacts admitted,
4 wrong-ID probes abstained (irrelevant on opening). 24 PDFs downloaded to `papers/`, each verified to start with `%PDF`.
Per-lane minimums met (20+ screened, 8+ admitted).

## Failures and corrections

- Four recalled arXiv IDs were wrong and caught on opening: 2306.09935,
  2310.18358, 2402.02692, 2402.05040 (all unrelated work). Correct IDs found
  via search and recorded. Lesson: never cite recalled IDs.
- export.arxiv.org and api.semanticscholar.org rate-limited this egress;
  worked around with direct abs fetches + web search excerpts of abs pages.
- api.github.com 403'd from shell after ~4 calls; same endpoints fetched fine
  through the fetcher.
- First vLLM docs URL guess 404'd; corrected to
  /en/latest/features/automatic_prefix_caching via search.
- llama.cpp moved orgs (ggerganov -> ggml-org); recorded as fetched.
- TGI repo is archived; admitted as historical reference with disposition note.
- Orca has no arXiv id: PDF filed as
  OSDI22_Orca_A_Distributed_Serving_System_for_Transformer_Based_Gener.pdf
  (documented exception to the <arxiv-id> naming rule).
- No consumer-GPU (16 GB) concurrency numbers found in primary sources; all
  throughput multiples are datacenter-GPU figures and are labelled as such.
