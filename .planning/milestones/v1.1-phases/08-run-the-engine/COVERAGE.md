# Phase 8 API coverage record

This is the phase API coverage record for the external HTTP surfaces Phase 8 integrates: the rerank endpoint (`databasise/clients/rerank.py`) and the OpenAI-compatible chat and embeddings endpoints (`databasise/clients/openai_compat.py`). It is distinct from `databasise/evidence/COVERAGE.md`, which is the CONTRACT section 18.5 tool record. Each row states one capability, whether this phase integrates it, and why.

Owner decisions that shape this table (2026-10-16): the rerank client mirrors LightRAG v1's bindings ("Use a reranker the same way lightrag uses it or any other."), and the owner does not use TEI ("I dont know what TEI is").

| capability | decision | reason |
|---|---|---|
| rerank request `model`, `query`, `documents` (cohere, jina, vLLM binding) | INTEGRATE | The standard body v1's `generic_rerank_api` sends. |
| rerank request `top_n` | INTEGRATE | Sent only when the caller passes it; the completeness check then expects `min(top_n, len(documents))` results. |
| rerank response `results[].index` and `results[].relevance_score` | INTEGRATE | The only fields read; ranking is score descending, ties by ascending index. |
| rerank response `model` (identity) | INTEGRATE | Used as `resolved_model_identity` when present. |
| rerank response `usage.total_tokens` | INTEGRATE | Recorded as `prompt_tokens`; absent usage is `unbudgetable` (D-05). |
| full-URL endpoint (`RERANK_BINDING_HOST` as written) | INTEGRATE | v1's convention; covers Cohere v1/v2, Jina, and vLLM `/rerank`, `/v1/rerank`, `/v2/rerank` paths. |
| `RERANK_BINDING` values `cohere`, `jina` | INTEGRATE | Same request and response shape; v1 routes vLLM through the cohere binding. |
| `RERANK_BINDING=aliyun` request `input.query`, `input.documents`, `parameters.top_n` | INTEGRATE | The Dashscope shape v1 supports; owner chose "the same way lightrag uses it". |
| aliyun response `output.results[]` | INTEGRATE | Same index and score fields, nested under `output`. |
| rerank response without `model` falls back to the configured `RERANK_MODEL` | INTEGRATE | Owner-approved, rerank-scoped exception to the identity rule in `clients/base.py`; LLM and embedding keep the strict rule. |
| OpenAI-compatible `chat.completions.create` `model`, `messages` | INTEGRATE | The one LLM call shape (D-07). |
| `extra_body` provider-routing pin from `OPENAI_LLM_EXTRA_BODY` | INTEGRATE | D-07 pin, chat only, never embeddings. |
| OpenAI-compatible `embeddings.create` `model`, `input` | INTEGRATE | The one embedding call shape. |
| response `usage` on chat and embeddings (absent = unbudgetable) | INTEGRATE | D-05: no usage is an unknown spend, not zero. |
| response `model` on chat and embeddings | INTEGRATE | Strict identity: an absent model raises `ModelIdentityMissingError`. |
| `choices[0].message.content` (None = named error) | INTEGRATE | D-06: refusals and tool-call answers are not blank answers. |
| embedding `data[].index` (reorder and validate) | INTEGRATE | D-06: vectors bind to the right text. |
| rerank `return_documents` | OPT-OUT | The part maps indices back to its own items; any extra keyword raises `TypeError`. |
| v1 chunking options `RERANK_ENABLE_CHUNKING`, `RERANK_MAX_TOKENS_PER_DOC` | OPT-OUT | Not needed yet; v1 default is off, and no wiring enables live rerank in this phase (D-09). |
| rerank `rank_fields` | OPT-OUT | Documents are plain strings in the `RerankClient` protocol. |
| Cohere `meta.billed_units.search_units` | OPT-OUT | A search-unit count, not a token count; the call is counted `unbudgetable`. |
| Cohere `priority` | OPT-OUT | A queueing hint with no effect on ranking. |
| TEI native bare-list `score` response | OPT-OUT | Not a LightRAG v1 rerank binding; the owner does not use TEI; refused as `RerankResponseError`. |
| v1 `extra_body` pass-through on rerank | OPT-OUT | No caller needs provider-specific rerank parameters yet. |
| OpenAI streaming | OPT-OUT | The seam streams envelope events; no part needs token streaming. |
| tools and function calling | OPT-OUT | No part issues tool calls; a tool-call answer is a named refusal. |
| `n` greater than 1 choices | OPT-OUT | Only `choices[0]` is read. |
| `logprobs`, `response_format`, `seed`, embedding `dimensions` and `encoding_format` | OPT-OUT | Not wrapped; callers may pass them as keyword arguments, which reach `create` unchanged. |
| audio, images, moderation, files, batch, assistants | OPT-OUT | No modality uses them. |
