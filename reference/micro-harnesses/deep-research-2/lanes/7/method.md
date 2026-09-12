# Lane 7 method

## Queries run (websearch, 14 queries)

1. `Microsoft GraphRAG knowledge graph extraction paper arXiv 2024`
2. `LightRAG simple and fast retrieval-augmented generation arXiv`
3. `KGGen knowledge graph generation paper arXiv Google`
4. `EDC Extract Define Canonicalize zero-shot triples knowledge graph arXiv`
5. `iText2KG incremental knowledge graph extraction arXiv`
6. `Triplex knowledge graph construction small language model constrained decoding arXiv`
7. `ChatIE zero-shot information extraction multi-turn question answering arXiv`
8. `GoLLIE guideline following large language model information extraction arXiv`
9. `UniversalNER targeted distillation ChatGPT named entity recognition arXiv`
10. `UIE unified structure generation universal information extraction Lu ACL 2022`
11. `GPT-NER named entity recognition large language models hallucination self-verification`
12. `HippoRAG 2 retrieval-augmented generation knowledge graph 2502.14802`
13. `MiniRAG small language model retrieval-augmented generation graph arXiv`
14. `Graphiti temporal knowledge graph episodic semantic memory Zep arXiv`
15. `Text2KGBench benchmark ontology-driven knowledge graph generation text arXiv`
16. `GenIE generative information extraction constrained generation BART arXiv Josifoski`
17. `Outlines structured text generation finite-state indexing constrained decoding arXiv`
18. `SynthIE exploiting asymmetry synthetic training data information extraction arXiv`
19. `InstructUIE multi-task instruction tuning universal information extraction arXiv`
20. `"Triplex" knowledge graph extraction language model paper`
21. `XGrammar flexible efficient structured generation engine constrained decoding`

Queries 6–7 in the first batch returned Decoding-on-Graphs and survey material instead
of a "Triplex" paper; query 20 resolved Triplex as a vendor model (Hugging Face
`SciPhi/Triplex`), not a publication.

## Sources used

- arXiv abs pages via webfetch (primary verification of title, authors, date,
abstract): 2404.16130, 2305.14450, 2307.01128, 2506.14901, 2410.18415.
- arXiv abs/HTML/PDF page excerpts returned by websearch (verbatim page chunks treated
as fetched primary evidence): all other arXiv ids.
- ACL Anthology pages (EDC, iText2KG via WISE/Springer, ChatIE repo, GoLLIE OpenReview
+ ICLR proceedings, UniversalNER repo, UIE, GenIE, SynthIE, InstructUIE repo,
Text2KGBench, DoG, Papaluca-TE).
- NeurIPS proceedings pages (KGGen poster/proceedings).
- GitHub repository pages via curl HTML payload extraction (`ownerLogin`,
`stargazerCount`, `forksCount`, `spdxId`) and `/commits/<branch>.atom` feeds for
last-push dates. MLSys proceedings page (XGrammar).
- Forward chaining: BoostCD and the COLING generative-IE survey surfaced SynthIE/GenIE
relations; iText2KG references surfaced Carta 2307.01128 and the ATOM follow-up (noted,
not separately screened); XGrammar references surfaced Outlines/Guidance (noted, not
separately screened).

## Counts

- Screened: 25 candidates (24 papers with arXiv ids + 1 vendor model).
- Admitted: 24. Minimums met (≥20 screened, ≥8 admitted).
- Abstained: 1 (SciPhi Triplex — no primary source).
- Refutations recorded: 4. Unresolved ledger: 9 entries.
- PDFs downloaded: 24, each verified to start with `%PDF`; title-to-id mapping
additionally confirmed by abs-page verification and, for BoostCD, embedded PDF metadata
(DOI 10.48550/arXiv.2506.14901).

## What failed

- arXiv export API (`export.arxiv.org/api/query`): `Rate exceeded` on every attempt
even with 10s delays and a descriptive User-Agent; abandoned in favour of
websearch + webfetch.
- Semantic Scholar API: HTTP 429 (`Too Many Requests`) without an API key; citation
forward-chaining therefore done via paper reference sections and survey excerpts
instead of the citation graph.
- GitHub REST API: `API rate limit exceeded` for the shared egress IP; replaced with
(public) repo-page HTML payload parsing plus atom commit feeds. Six repo URLs
(GPT-NER, BoostCD, DoG, Papaluca-TE, Han-study, Carta) were not captured and are
marked unverified rather than guessed.
- No shell PDF-text tooling (`pdftotext` absent); PDF identity rests on abs-page
verification plus correct `arxiv.org/pdf/<id>` retrieval, not on extracted PDF text.
