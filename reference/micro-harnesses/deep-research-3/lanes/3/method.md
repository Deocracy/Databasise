# Lane 3 method

## Queries run

arXiv search pages (via `https://arxiv.org/search/?query=...`, abstracts shown,
newest first), exact-phrase and keyword forms:

- `"arrow routing"` → identified 2405.11157 (Ostapenko et al.) among 2 hits
- `"catastrophic forgetting" LLM fine-tuning` → 221 hits; first page screened,
yielding 2609.10750, 2608.20794, 2605.29495, 2605.28860, 2605.17774, 2606.01967
- `"mixture of LoRA"` → 57 hits; first page screened, yielding 2603.15965,
2605.07111, 2603.10160 (abstain), 2604.19048 (abstain), 2603.00573 (abstain),
2510.17898 (abstain), 2602.12746 (abstain), 2606.02576 (abstain),
2608.09819 (abstain)
- `LoRAMoE mixture experts world knowledge` → 2312.09979
- `"echo embeddings"` → 2402.15449
- `"X-LoRA" mixture experts` → 2402.07148
- `"GritLM"` → 2402.09906 + 2603.28554 (seeds confirmed, not re-found)
- `"NV-Embed"` → 2405.17428
- `"joint" contrastive "language modeling" embedding generation LLM` and
`"unified" embedding generation single model contrastive` → low precision;
2412.04948 (KaLM) and 2604.11095 (abstain, multimodal) kept
- `"Length-Induced Embedding Collapse"` → 2410.24200

Citation chaining: OpenAlex API
(`api.openalex.org/works/https://doi.org/10.48550/arXiv.2402.09906` and the
`filter=cites:` endpoint) for GritLM forward citations — 15 citing works, thin
coverage, mostly applied papers; no additional interference measurement found
that way. Semantic Scholar graph API returned HTTP 429 for the whole session.

Repository verification: GitHub REST API (`search/repositories`,
`repos/{owner}/{repo}`) for LoRAHub (sail-sg/lorahub: 669 stars, MIT),
SimCSE (princeton-nlp/SimCSE: 3652 stars, MIT), X-LoRA (EricLBuehler/xlora:
285 stars, Apache-2.0), OPR (Yancey2024/OnPolicyReplay: 3 stars, no license),
MoLF (11785T23/molf: 3 stars, Apache-2.0), and a Mixture-of-LoRA code search
that surfaced community re-implementations (recorded, not claimed official).

Primary-source verification: every admitted id was opened at
`https://arxiv.org/abs/<id>` and title/authors/date/abstract read from page
metadata; every admitted PDF was downloaded from `https://arxiv.org/pdf/<id>`
and checked to start with `%PDF`, then renamed to
`<arxiv-id>_<Title_Slug>.pdf` (slug ≤ 70 chars, no spaces).

## Counts

Screened 39 (22 admit, 17 abstain). Per-lane minimums met (≥20 screened,
≥8 admitted).

## What failed

- `export.arxiv.org` API: `Rate exceeded` on every attempt this session, so no
Atom-API screening; arXiv HTML search pages used instead (verbose, parsed with
a local script).
- Semantic Scholar API: HTTP 429 throughout; forward/backward chaining moved
to OpenAlex, whose citer coverage for GritLM was thin (15 works).
- Papers with Code API returned empty bodies for lane queries; not used.
- Three recalled arXiv ids (2405.19944, 2312.10369, 2102.13304) resolved to
unrelated papers on verification; all recorded as abstain traps, none admitted.
- No full-text mining: screening from abs pages + abstracts only; PDF contents
not parsed beyond the `%PDF` check.
- Venues recorded as `arXiv preprint` wherever the abs page comments did not
state a venue in text this lane captured; only COLM 2024 (LoRAHub), TMLR
(LoRA Learns Less), PNAS (EWC), and EMNLP 2026 Industry (Synthetic-Hurts) were
verified from primary-source text.
