# Lane 6 method

## Queries and sources

No web search engine was available. All discovery used direct HTTP endpoints:

1. **arXiv abs pages** (`https://arxiv.org/abs/<id>`) via WebFetch (full page) for the
   first items and via `curl + grep` on `<meta name="citation_*">` tags for the rest
   (title, authors, date per id). Every admitted id was opened at its abs page.
2. **OpenAlex API** (`https://api.openalex.org/works`, `filter=title.search:` and
   `search=`) via WebFetch to resolve uncertain arXiv ids from exact titles. This
   recovered the correct ids for All-but-the-Top (1702.01417), Ethayarajh
   (1909.00512), Representation Degeneration (1907.12009), IsoScore (2108.07344),
   Gecko (2403.20327), Promptagator (2209.11755), InPars (2202.05144), InPars-v2
   (2301.01820), E5 (2212.03533), ARES (2311.09476), AIR-Bench (2412.13102), BIRCO
   (2402.14151) and AugSBERT (2010.08240).
3. **GitHub API** (`https://api.github.com/repos/<owner>/<repo>`) via curl for stars,
   `pushed_at` and license. Resolved: embeddings-benchmark/mteb (3420),
   beir-cellar/beir (2288), bojone/BERT-whitening (486), princeton-nlp/SimCSE
   (3652), facebookresearch/DPR (1871), stanford-futuredata/ColBERT (3932),
   facebookresearch/contriever (779), UKPLab/gpl (342), stanford-futuredata/ARES
   (732). The BEIR repo README supplied the correct BEIR arXiv id (2104.08663).
4. **Papers with Code API** — attempted once; returned an unrelated page, abandoned.
5. **DBLP API** — blocked by an Anubis bot challenge, abandoned.

Forward-chaining (citations/references of seeds) was not possible: Semantic Scholar
and the arXiv API both returned HTTP 429 for this egress IP for the whole session,
so chaining was replaced by title-exact OpenAlex resolution plus abs-page
verification, which catches id errors but not citation-graph neighbours.

## Counts

- Screened: 32 (22 admit, 10 abstain). Per-lane minimums (≥20 screened, ≥8 admitted)
  met.
- PDFs downloaded: 22, each verified to start with `%PDF` and listed in `papers/`.
  InPars-v2's record PDF is a complete 4-page file (ends `%%EOF`); flagged in
  findings.

## What failed

- **Recalled arXiv ids are unreliable; six failed verification against the abs
  page:** 2104.08645 and 2104.08648 (guessed for BEIR; actual 2104.08663),
  1706.03028 (guessed for All-but-the-Top; a Galileo physics paper),
  1909.00551 (guessed for Ethayarajh; a curve-reconstruction paper), 2206.13259
  (guessed for InPars; an HPC user's guide), 2304.07135 (guessed for InPars-v2;
  quantum-well physics), 2102.03334 (guessed for AugSBERT; ViLT), 2309.15266
  (guessed for RAGAS; a tomography paper), 2406.14733 (guessed for AIR-Bench; a
  Rust dataflow paper), 2310.13501 (guessed for BIRCO; nuclear dynamics),
  1607.06520 (guessed for SIF/Arora; a debiasing paper). None of these appear in
  the inventory; all are recorded here so no future lane re-tries them blind.
- **Rate limits:** arXiv API and Semantic Scholar API 429 throughout; GitHub API
  429 on the final calls (RAGAS repo unresolved, sentence-transformers org move
  unresolved — hence no repo URLs recorded for those rows).
- **Shallow verification:** for title-record admits (BIRCO, AIR-Bench, ABTT,
  Ethayarajh, RepDeg, IsoScore, E5, Promptagator, InPars-v2, GPL, ARES, Gecko,
  DPR, MS MARCO) only the abs-page title/authors/date were read, not the full
  abstract or PDF. Their findings paragraphs say so explicitly; the integrator
  should read those PDFs before quoting numbers.
- **Venue column:** venue is stated only where the fetched abs page showed it
  (SimCSE→EMNLP 2021, BERT-flow→EMNLP 2020, BEIR→NeurIPS 2021 D&B, MMTEB→ICLR,
  AlignUniform→ICML 2020); otherwise "arXiv preprint" with secondary-source venue
  hints labelled as such.
