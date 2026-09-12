# Lane 5 method

## Queries run (websearch, 8 results each)

1. `PromptEOL one word embeddings arXiv large language models 2023`
2. `echo embeddings failure modes quote repetition arXiv 2024 decoder embeddings`
3. `NV-Embed universal embeddings instructions latent attention arXiv`
4. `E5-Mistral instruction text embeddings arXiv 2024`
5. `Qwen3 Embedding instruction design model card 2506.05176`
6. `InstructIR instruction following retriever benchmark arXiv`
7. `Meta-task prompting elicits embeddings large language models MetaEOL arXiv`
8. `PromptBERT contrastive learning template denoising sentence embeddings arXiv`
9. `Promptriever instruction trained retrievers Llama promptable retrieval arXiv 2024`
10. `"Answer is All You Need" instruction following text embedding answering question arXiv`
11. `bge-en-icl few-shot in-context learning embedding instruction arXiv`
12. `TART instruction aware retrieval MEDI multitask embedding arXiv`
13. `instruction wording sensitivity embedding retrieval prompt paraphrase robustness BEIR`
14. `SFR-Embedding-Mistral transfer learning instruction E5 Mistral technical report`
15. `Gecko text embedding distillation synthetic instructions arXiv 2024`

Plus direct primary-source opens (webfetch) of arXiv abs pages 2212.09741, 2307.16645,
2605.22544, 2401.00368, 2412.03223; arXiv HTML/PDF and ACL Anthology excerpts taken via
search-result fetches for 2405.17428, 2402.15449, 2402.18458, 2506.05176, 2409.11136,
2402.14334, 2403.15246, 2402.09642, 2409.15700, 2211.09260, 2201.04337, 2403.20327,
2402.05672; Hugging Face model/repo pages for e5-mistral-7b-instruct, Qwen3-Embedding-4B,
NV-Embed-v1, SFR-Embedding-Mistral; GitHub web pages for InstructIR, InBedder, TART,
Promptriever, echo-embeddings, MetaEOL; project pages instructor-embedding.github.io and
Qwen3-Embedding README; GitHub REST API (`api.github.com/repos/...`) for star counts,
push dates, and licenses.

Forward-chaining: followed citations/references named inside opened pages (e.g. SFR and
E5-Mistral inside the NV-Embed and Linq reports; GritLM/LLM2Vec/E5 inside echo and
bge-en-icl comparisons; InstructIR/FollowIR inside Promptriever) rather than a separate
citation API.

## Counts

- Screened: 25 candidates (18 admitted, 7 abstained).
- Admitted with PDF filed in `papers/`: 18, every file verified to start with `%PDF`.
- Lane minimums (20 screened / 8 admitted) met.

## What failed

- `export.arxiv.org` API returned HTTP 503 for the search query attempted; arXiv
  discovery was done through abs-page fetches and web search instead, with 3 s+
  spacing between PDF downloads.
- Semantic Scholar API returned HTTP 429 (rate limit) on both calls attempted; citation
  chaining was done manually from references inside opened papers instead.
- GitHub API returned 404 for `HKUST-KnowComp/Instructor-Embedding`,
  `Salesforce/SFR-Embedding-Mistral`, and `nvidia/NV-Embed`; correct paths were
  recovered for INSTRUCTOR (`xlang-ai/instructor-embedding`: 2022 stars,
  2025-01-15 push, Apache-2.0) via the official project page, and HF model pages were
  used as artefact sources for SFR and NV-Embed.
- No dedicated study found for chat-template effects or [EMB]-style marker tokens;
  recorded as gaps, not admits.
- Anything 2025+ rests on fetched pages only (no recall): 2506.05176, 2605.22544,
  2605.01372 (abstained), 2601.01046 (abstained).
