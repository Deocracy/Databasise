# Lane 6 method

Lane: 6 — Caching and parallel workload. Worker: single research
sub-agent, no sub-agents spawned, no files touched outside this lane
folder.

## Queries run

arXiv abs verification (curl + webfetch, one id at a time, 4-6 s
spacing): 2312.07104, 2309.06180, 2403.02310, 2308.16369, 2311.04934,
2311.18677, 2310.18547, 2406.03243, 2405.16444, 2411.15100, 2407.00079,
2401.09670, 2402.05099, 2403.02694, 2305.05920, 2609.07883, 2609.06853,
2609.04748, 2608.20732. Three initial ID guesses were wrong and
corrected rather than admitted: 2402.10028 (guessed DistServe, is
Diffusion Models Meet Contextual Bandits), 2409.21389 (guessed LMCache,
404), 2412.06238 (guessed Mooncake, is an autoethnography post). The
correct IDs came from OpenAlex search results, then each abs page was
opened and title/authors/date confirmed.

arXiv API (export.arxiv.org): attempted once, immediate 429
(rate exceeded) — all ten lanes share the egress, so the API path was
abandoned in favor of abs-page fetches.

Semantic Scholar API: first search call succeeded (SGLang record:
venue NeurIPS, 1372 citations), then 429s under burst load. Retried
with backoff; citations endpoint eventually returned 100 records each
for arXiv:2309.06180 and arXiv:2312.07104 (note: envelope shape is
{"data":[{"citingPaper":{...}}]}, not flat). Keyword-filtered both
sets (cache|prefix|KV|batch|schedul|... ) and title-screened ~200
citing works; 4 were promoted to full abs verification (the Sep-2026
cluster), the rest are abstains with reason "title-screened, primary
source not opened". References (outbound) were not enumerated per
paper — partial compliance, documented here.

OpenAlex API (openalex.org, generous limits, worked throughout):
search queries for DistServe, Block-Attention, Hydragen, MeanCache,
FastServe, LMCache, block-attention-prefix-reuse; work records for
two seed DOIs. This is where DistServe (2401.09670), Hydragen
(2402.05099), MeanCache (2403.02694), FastServe (2305.05920),
ChunkAttention (ACL DOI), and CacheSaver (EMNLP DOI) were discovered.

GitHub REST API (unauthenticated, 60/hr shared quota): repo facts for
zilliztech/GPTCache, LMCache/LMCache, mlc-ai/xgrammar,
kvcache-ai/Mooncake, dottxt-ai/outlines, vllm-project/vllm,
sgl-project/sglang, AlibabaPAI/llumnix, ScalingIntelligence/hydragen,
punica-ai/punica, au-clan/cachesaver; repo searches for Punica
(punchycloud/punica 404d, punica-ai/punica confirmed),
Llumnix, Hydragen, MeanCache (0 hits), DistServe, ChunkAttention.
Quota exhausted (403 rate limit) before verifying stars for the six
paper-linked repos (DistServe, PromptCache, MeanCache, Sarathi-Serve,
Splitwise-sim, jordan-benjamin/hydragen) — their URLs were instead
extracted from admitted PDF bytes via strings-matching
`github.com/<owner>/<repo>` and recorded with stars "n/a (unverified)".

Hugging Face Hub API and Papers with Code API: attempted (models
search, papers search) — PwC returned unparseable/empty responses,
HF not needed; neither contributed candidates. Documented as tried.

Vendor/official docs (webfetch, primary for what APIs allow):
USENIX OSDI22 Orca page (verified authors, abstract, BibTeX, PDF
link); ACL Anthology pages for ChunkAttention and CacheSaver (full
metadata + abstracts); vLLM Automatic Prefix Caching docs (first
guessed URL /en/latest/automatic_prefix_caching/ 404d; corrected to
/features/automatic_prefix_caching/ and verified); sqlite.org/wal.html
(full WAL semantics incl. the 2026 WAL-reset bug section).

README mining (raw.githubusercontent.com): LMCache (main + dev, no
paper ref found), Mooncake (arxiv refs incl. 2407.00079), xgrammar
(refs incl. 2411.15100).

## Counts

- Screened (inventory rows): 39 = 27 admit + 12 abstain.
- Admitted papers with PDFs filed: 22 (19 arXiv + Orca/USENIX + 2 ACL).
- Admitted repo/docs systems without PDFs: 5 (GPTCache, LMCache,
Outlines, vLLM APC docs, SQLite WAL docs). No paper exists for the
first three by the projects' own account (repo is the primary
source); docs items are primary for API behavior only.
- Minimums: >= 20 screened, >= 8 admitted — met (39 / 27).

## What failed

- arXiv export API: 429, abandoned.
- S2 burst queries: 429s; recovered with backoff for the chaining pass.
- Papers with Code API: empty/unparseable responses.
- GitHub API: 403 rate-limit before the last six repo fact-checks;
mitigated via PDF-byte URL extraction, facts marked unverified.
- NDSS 2026 poisoning PDF: downloaded (1.9 MB, %PDF) but title/authors
unverifiable from bytes — abstained, kept out of papers/.
- Block-Attention: no primary source found anywhere — abstained.
- No 2025+ claim rests on memory: every post-2024 item was verified
at its abs/DOI/docs page this session.

## Filing deviations

- Non-arXiv PDFs use venue prefixes instead of arXiv ids:
OSDI22_*, ACL2024_*, EMNLP2025-Findings_*. Slugs capped at 70 chars,
non-alphanumerics to underscores, no spaces. Every file starts with
%PDF (byte-checked).
- inventory.tsv repo stars "n/a" means unverified-or-inapplicable,
never zero; artefact_released "paper" vs "paper+code" vs "code" vs
"docs" records what was actually confirmed.
