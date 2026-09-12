# Lane 2 method

## Queries and sources

No web search engine was available; all discovery used direct endpoint calls (curl) plus page
fetches (webfetch), exactly as the lane brief prescribes:

- **arXiv abs pages** (`https://arxiv.org/abs/<id>`) to verify title/authors/date/abstract for
  every admitted item and to expose recalled-id misses (5 recalled ids proved wrong on opening:
  2406.20003, 2311.00135, 2402.11205, 2310.16256, 2412.14771, 2307.08013, 2311.05232, 2306.00712,
  2308.09688, 2408.03624, 2406.17539, 2307.06215, 2412.15215, 2310.12964 — each checked, none
  admitted under the wrong id).
- **arXiv search HTML** for title lookups (worked 2 of 4 attempts; endpoint throttled after).
- **OpenAlex API** (`api.openalex.org/works`) for title/DOI resolution and one forward-chain
  pass (works citing WizardLM 2304.12244; top hits were appliers, so the chain contributed
  WizardCoder 2306.08568 via targeted search, not via citations). Also used to resolve
  FineWeb (2406.17557), Nemotron-CC (2412.02595), Tulu 3 (2411.15124), RegMix (2407.01492),
  Instruction Mining (2307.06290), and venues for ACL/EMNLP rows via DOI records.
- **GitHub API**: direct `/repos/` checks (hit the 60/hr unauthenticated quota partway) then
  `/search/repositories` (separate quota) for stars, pushed_at, license. Every star/license/
  date figure in inventory.tsv came from a live API response; fields that could not be fetched
  say `unverified`, never a recalled number.
- **Hugging Face API** (`huggingface.co/api/datasets`) to confirm released datasets
  (PersonaHub, Magpie-Align org, UltraChat, Nemotron-CC, Bonito-experiment, FineWeb,
  HelpSteer2, self_instruct, WizardLM evol sets).
- **Semantic Scholar API**: attempted, 429 rate-limited; replaced by OpenAlex. No data from it.
- **arXiv export API**: attempted, 503/timeout; replaced by abs-page + search-HTML + OpenAlex.

PDFs downloaded from `https://arxiv.org/pdf/<id>` (23 files, each verified to start with
`%PDF`). Key figures re-checked by extracting PDF text with a small pure-Python parser
(FlateDecode + Tj/TJ operators; no PDF tooling on the machine) and grepping for counts.

## Counts

- Screened: 34 rows in inventory.tsv (23 admit, 11 abstain). Per-lane minimums met
  (≥20 screened, ≥8 admitted).
- Forward-chaining: 1 seed (WizardLM) via OpenAlex cited-by (110 citers scanned, top-30
  inspected); remaining seeds covered by targeted title search, which proved higher-yield.
- Backward-chaining (references of seeds): not run systematically; PDFs were text-mined for
  figures instead, given the per-lane budget. Flagged as a residual gap: reference lists of
  Humpback, Bonito and DEITA likely contain further document-grounded generators.

## What failed

1. arXiv export API (503/timeouts) and Semantic Scholar (429) were unusable; OpenAlex + abs
   pages substituted.
2. GitHub core API quota exhausted after ~8 calls; search API substituted; a few repo fields
   remain `unverified` (stated, not filled).
3. No PDF text-extraction tooling (no pdftotext, no pip); hand-rolled parser used, which drops
   some ligatures/hex-encoded strings — figures cited are those that survived extraction and
   were cross-checked against abs-page abstracts.
4. Lane brief says capability "(1-5 or refutes)" but the brief's section 1 has 6 questions;
   inventory uses the brief's Q1-Q6 numbering (all lane-2 admits bear on Q2) and notes this.
5. GLAN, Genie, Auto Evol-Instruct could not be resolved to any record after arXiv + OpenAlex
   title searches; recorded as abstains with reasons, nothing invented.
