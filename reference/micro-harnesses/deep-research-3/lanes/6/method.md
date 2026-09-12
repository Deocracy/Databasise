# Lane 6 method

Lane: Extraction fine-tunes and their datasets (models fine-tuned for triple
and entity extraction, datasets, evaluation protocols, small-model results).

## Queries run

No general web-search engine was available at first, so work began with direct
endpoint calls, then switched to the `websearch` tool once its value was
clear, plus `curl` against arXiv abs pages, the GitHub REST API, and the
Hugging Face Hub API:

- arXiv export API (`export.arxiv.org/api/query`) — abandoned after immediate
rate-limiting ("Rate exceeded") on the first two queries.
- Semantic Scholar API (`api.semanticscholar.org`) — abandoned after HTTP 429
on the first query.
- `curl https://arxiv.org/abs/<id>` + a local HTML extractor
(`/tmp/opencode/abs.py`, title/authors/date/comments/subjects) — the primary
verification path for every arXiv id; ~20 ids checked with 3–4 s spacing, no
further rate limits.
- `websearch` (fast, 3–4 results): one query per candidate family —
REBEL arXiv/DOI, DocRED arXiv id, GenIE, InstructUIE, ReLiK, GLiNER, PIVOINE,
Text2KGBench, ChatIE, KnowCoder, RexUIE, WebIE, Re-DocRED, GENRE, Triplex,
NuExtract, USM, DREEAM, GLiREL, BoostCD, SynthIE repo, UniversalNER
repo/data. Each returned an arXiv abs or ACL anthology page confirming the id.
- GitHub REST API (`api.github.com/repos/<owner>/<repo>`, unauthenticated):
verified stars/pushed_at/license for hitz-zentroa/GoLLIE (443, 2024-10-27,
Apache-2.0), epfl-dlab/GenIE (104, 2023-03-28, MIT), epfl-dlab/BoostCD (2,
2025-10-28, MIT), SapienzaNLP/relik (518, 2025-07-29), urchade/GLiNER (3641,
2026-09-08, Apache-2.0), jackboyla/GLiREL (290, 2026-03-30),
Babelscape/rebel (576, 2023-11-09), amazon-science/webie (8, 2023-07-26),
tonytan48/re-docred (68, 2023-08-21, MIT), ICT-GoKnow/KnowCoder (108,
2025-05-28). Hit the 60/hr unauthenticated rate limit twice; recovered with
45–60 s waits. SynthIE (63 stars, MIT) and universal-ner (375 stars, MIT)
facts come from fetched GitHub pages via websearch, not the API.
- Hugging Face Hub API: `Babelscape/rebel-large` (CC-BY-NC-SA-4.0),
`Universal-NER/UniNER-7B-*` (llama-based, CC-BY-NC-4.0),
`Universal-NER/Pile-NER-type` (gpt-3.5-turbo-0301, CC-BY-NC 4.0).

Forward/backward chaining was done through citations found in fetched full
texts (BoostCD cites GenIE/SynthIE/REBEL; GLiREL cites Pile-NER/GLiNER;
KnowCoder compares GoLLIE/InstructUIE/UniNER; ReLiK cites GENRE-line work),
plus the GLiNER repo page for GLiNER2/GLiGuard successors.

## Counts

- Screened: 36 candidates (33 papers/datasets + Triplex, NuExtract, WikiNRE).
- Admitted: 33. Abstained: 3 (all with reasons in findings §c).
- PDFs downloaded: 33 (30 from `https://arxiv.org/pdf/<id>`, 3 from ACL
Anthology PDFs for the admits with no arXiv version: REBEL
2021.findings-emnlp.204, UIE 2022.acl-long.395, PIVOINE
2023.findings-emnlp.1009). Every file was checked to start with `%PDF`.
Filenames use the arXiv id, or the ACL anthology id where no arXiv id
exists (documented deviation from the `<arxiv-id>` pattern).

## What failed

- Four hand-guessed arXiv ids were wrong and caught by title verification:
2104.07736 and 2104.08744 are not REBEL; 1906.03207 and 1906.06163 (first
attempt) are not DocRED (correct: 1906.06127); 2301.00786 is not GenIE
(correct: 2112.08340); 2304.08007 is not InstructUIE (correct: 2304.08085).
Lesson applied: no id was recorded without opening its abs page, and the
wrong guesses are not in the inventory.
- No primary source was found for SciPhi Triplex (vendor artefact only), for
NuExtract internals (vendor blog/HF cards only), or for WikiNRE (known only
as a citation inside WebIE). All three are abstains, not admits.
- R1-RE, MR-UIE, GLiDRE, GLiNER2, KGGen were verified at their abs pages but
their full texts were not read; their findings entries rest on
abstract-page claims only.
- Code/checkpoint release status was individually verified for 12 repos; for
the remaining paper admits the inventory marks artefact status unknown and
findings §c forbids citing them as reusable without a follow-up check.
