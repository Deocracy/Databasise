# Lane 4 method: thinking modes for small models

## Queries run
Web-search queries (via session search tool), each returning up to 8 results whose pages were
opened as data:
- `ToRL tool-integrated reasoning LLM reinforcement learning arXiv 2025` -> fixed ToRL
  identity as arXiv:2503.23383 (two earlier abs-page guesses, 2505.14115 and 2507.02046,
  were opened and rejected: shell finite elements and dark-matter lensing, respectively).
- `overthinking small language models chain-of-thought hurts 1B 3B arXiv 2025` -> Do NOT Think,
  Under/Overthinking-1.5B, short-m@k, Mirage, When-More-is-Less, ThinkBrake seed set.
- `MiniCPM4 ultra-efficient LLM on-device arxiv technical report 2025` -> arXiv:2506.07900.
- `"Do NOT Think That Much" overthinking long reasoning models arxiv Chen` -> arXiv:2412.21187
  plus ICML 2025 PMLR page and the galaxyChen/overthinking repo.
- `NoThinking large reasoning models suffit BFCL function calling arxiv Ma 2025` -> arXiv:2504.09858.
- `ThinkBrake efficient reasoning log-probability margin tool use small reasoning models arxiv`
  -> arXiv:2510.00546 plus holi-lab/ThinkBrake repo and ACL 2026 Findings DOI page.
- `continuous chain-of-thought latent reasoning small model open weights LightThinker CCoT
  SoftCoT arxiv` -> CCoT (2412.13171), SoftCoT (2502.12134), LightThinker (2502.15589).
- `Huginn recurrent depth looped transformer reasoning open weights arxiv` -> arXiv:2502.05171,
  huginn-0125 HF page, seal-rg/recurrent-pretraining, and the probing paper arXiv:2507.02199.
- `reasoning models structured output JSON validity thinking tokens constrained decoding
  accuracy arxiv` -> arXiv:2408.02442 and arXiv:2601.07525.

Primary-source abs-page opens (webfetch of https://arxiv.org/abs/<id>, full text kept):
2501.19393, 2412.06769, 2505.09388, 2203.11171, 2503.09516, 2504.11536, 2503.23383,
2502.07266, 2506.04210, 2505.17813, 2505.00127, 2503.04697, 2504.09858, 2412.21187,
2410.21333, 2506.07900, 2510.00546, 2501.12948, 2502.15589, 2501.18585, 2502.05171,
2408.02442, 2601.07525, 2507.02199, 2502.12134, 2412.13171 (title/date only).
Two wrong-ID opens (2505.14115, 2507.02046) are documented above and excluded everywhere.

## Other primary sources fetched
- GitHub REST API (stars, pushed_at, license) for 12 repos: QwenLM/Qwen3, OpenBMB/MiniCPM,
  simplescaling/s1, facebookresearch/coconut, GAIR-NLP/ToRL, PeterGriffinJin/Search-R1,
  holi-lab/ThinkBrake, zjunlp/LightThinker, xuyige/SoftCoT, galaxyChen/overthinking,
  seal-rg/recurrent-pretraining, wenquanlu/huginn-latent-cot, Nokia-Bell-Labs/InWriting.
  License `None` means the API returned null, recorded as not-verified rather than invented.
- Raw Qwen3 README (raw.githubusercontent.com) grepped for `enable_thinking|/think|/no_think|
  thinking budget`: hits at lines 133, 173, 188, 200-201.
- ArXiv HTML pages for 2503.04697, 2503.09516, 2504.11536, 2503.23383 grepped for
  `github.com/<owner>/<repo>` to confirm code URLs (Search-R1, ToRL confirmed; ReTool and L1
  expose no repo link in HTML, recorded as unverified).
- Hugging Face model page snippet for tomg-group-umd/huginn-0125 (3.5B, 800B tokens).
- PMLR pages for chen25bx (PMLR 267:9487-9499) and patil25a (BFCL); ACL Anthology page for
  SoftCoT (2025.acl-long.1137); DOI page for ThinkBrake (2026.findings-acl.1095).

## Forward/backward chaining
Per-brief chaining via Semantic Scholar (paper search + citations/references endpoints) and the
arXiv search API was attempted first: both returned HTTP 429 (arXiv API also 503) from this
environment. Chaining was therefore done through (a) reference lists visible on opened abs/HTML
pages, (b) citing-paper trails on fetched aggregator pages (arxiv.gg, AlphaXiv, HF paper pages),
and (c) targeted follow-up searches (Huginn probe, structured-output studies). The S2S/API
failure is the reason citation-count and reference-list figures do not appear in this lane.

## Screening counts
- Candidates screened: 37 rows in inventory.tsv (25 admitted papers + 2 admitted vendor-doc
  items + 10 abstains).
- Admitted: 27 items (25 papers with PDFs in papers/, 2 vendor-doc items without PDFs).
- Refutes: 4 (filed as disposition admit with capability refutes where the paper overturns a
  background assumption; the refutation targets are listed in findings.md section b).
- Abstains: 10, each with a reason (not opened, lane-1 scope, or no source found).
- What failed: arXiv API + Semantic Scholar API rate limits (see above); ToRL arXiv id needed
  three attempts; ReTool and L1 code URLs could not be verified and are left blank rather than
  guessed; no primary numbers exist for MiniCPM5-2B think-on/off tool-call accuracy (unresolved).

## Download verification
All 25 PDFs fetched from https://arxiv.org/pdf/<id>, each checked to start with `%PDF`.
Filenames are `<arxiv-id>_<Title_Slug>.pdf`, slugs <= 70 chars, no spaces. One size note:
2506.04210 PDF is ~20 MB (14.7 MB source + figures); total papers/ is ~110 MB.
