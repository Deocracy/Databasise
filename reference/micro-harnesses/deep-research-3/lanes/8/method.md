# Lane 8 method

## Queries run

No search-engine MCP was available in this lane; all discovery used
direct HTTP endpoints plus the session web-search tool for id verification:

- arXiv abs pages via `curl https://arxiv.org/abs/<id>` (with 4 s sleep
  between calls) for all 19 arXiv candidates, grepping `<title>` to confirm
  id-to-title mapping before downloading.
- arXiv PDFs via `curl https://arxiv.org/pdf/<id>`; every file checked to
  start with `%PDF` and size-recorded; content spot-checked by
  zlib-decompression of document streams (BEIR, MTEB) or metadata/title
  search (WebIE, Smucker-SIGIR09).
- ACL Anthology pages (`aclanthology.org/...pdf`) for WebIE (2023.acl-long.428).
- Author-hosted PDFs: `ciir-publications.cs.umass.edu/getpdf.php?id=744`
  (Smucker CIKM07) and `maroo.cs.umass.edu/getpdf.php?id=885` (Smucker
  SIGIR09); cross-checked against the ACM DL records, the Semantic Scholar
  record, and the UMass CIIR author publication list (which pins the SIGIR09
  venue/year/pages 630-631).
- GitHub REST API (`api.github.com/repos/<owner>/<repo>`, unauthenticated,
  2 s sleep) for stars / pushed_at / license of 11 repos; followed the
  `explodinggradients/ragas -> vibrantlabsai/ragas` redirect via the
  repository-id endpoint.
- export.arxiv.org API and Semantic Scholar API were both tried first and
  were rate-limited (HTTP 429 / "Rate exceeded"); no data from recalled
  memory was used for any admitted claim. One recalled id (BEIR as
  2104.08671) proved wrong on fetch and is recorded as screened/abstain
  (CaseHOLD) — the verification loop works.
- Web-search queries (session tool) used only to find candidate ids and
  confirm abs-page contents: BEIR, MTEB/MMTEB, LLM-judge, ARES, BDC survey,
  RAGAS, KILT, Text2KGBench, HELM, PPI, G-Eval, Re-DocRED, WebIE, Smucker
  significance tests, Prometheus 1/2, AlpacaEval-LC, FLASK, Sainz
  contamination, Smucker-2009 venue.

## Counts

- Screened: 31 rows in inventory.tsv.
- Admitted with PDFs: 16 (13 arXiv + WebIE via ACL + 1 Smucker via ACM/author
  PDF; PPI and generative-IE-survey PDFs from arXiv, repo URLs unrecorded).
- Refute disposition: 6 (all verified at primary source with PDFs filed;
  counted toward the 8+ verified minimum alongside admits: 22 total).
- Abstain: 9, each with its reason (unopened primary, out of scope, or
  superseded).
- PDFs in papers/: 22 (19 `<arxiv-id>_<slug>.pdf` with slugs truncated to 70
  chars, plus `ACL2023_...`, `DOI10_1145_...`, `AuthorPDF_...` for the three
  non-arXiv primaries, documented here so the integrator's merge is not
  confused by the prefix).

## Capability-column convention

The brief asks for the section-1 question each item bears on (1-6, or
refutes). Lane 8 is the evaluation lane, so the mapping is approximate and
means "which training question this eval evidence serves": 1 = extraction-emission
eval, 2 = dataset-hygiene eval, 3 = joint retrieval/generation metric and
small-n statistics, 6 = payload/consumer-output quality eval. `refutes` marks
items contradicting a claim in our vocabulary (detailed in findings.md §b).
No item maps to Q4 (distillation/RL) or Q5 (LoRA science); that is a scope
outcome, not an oversight — evaluator-side evidence for those questions was
not found in this lane's sweep.

## What failed

- arXiv export API: "Rate exceeded" on first query; Semantic Scholar API:
  HTTP 429. Both abandoned in favor of abs-page curl + web search.
- No PDF text-extraction tooling on the machine (no pdftotext/pdfinfo,
  no pymupdf); verification done via raw-stream decompression and landing
  pages instead.
- Smucker CIKM07 author PDF is scanned (no extractable text, no font
  objects); verification rests on ACM/Semantic-Scholar/UMass records plus
  matching page count (10 pp = 623-632). Recorded transparently in inventory.
- Urbano SIGIR13 (paywalled), Deng NAACL24, DCR, 2409.09927, 2502.14425,
  GenIE, ADELIE, BiGGen-Bench primaries never opened — all abstain, none
  cited for claims.
- Repo metadata not recorded where the paper gave a URL but the API was not
  queried (PPI code, G-Eval, LLM4IE survey repo): stars/push left blank
  rather than invented. FLASK repo records no license; left blank.
