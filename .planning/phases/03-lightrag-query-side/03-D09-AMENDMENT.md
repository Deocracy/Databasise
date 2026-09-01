# Amendment: D-09 embedder — OpenRouter-hosted qwen3-embedding-8b replaces local Ollama

**Date:** 2026-08-31
**Decided by:** Owner (Christopher), explicit instruction during Phase 3 execution
**Amends:** Phase 2 banked decision D-09 (`.planning/phases/02-falsifier-gate/02-CONTEXT.md`, "Embedder: local (bge / nomic via Ollama) — keeps T1 genuinely free; OpenRouter is chat-completions oriented.")

## What changed

The parity-arm embedder is now **`qwen/qwen3-embedding-8b` served via OpenRouter's embeddings endpoint** (`https://openrouter.ai/api/v1`), not a local model via Ollama.

Unchanged parts of D-09: rerank remains **off** in the parity arm; the rerank node stays authored and wired but configured out.

## Why

- D-09's premise is outdated: OpenRouter now operates a dedicated embeddings endpoint (`/api/v1/embeddings`, 33 models, verified live 2026-08-31). "OpenRouter is chat-completions oriented" no longer holds.
- Ollama is not installed on the execution host and the owner declined installing it.
- `qwen/qwen3-embedding-8b` is the best-rated open-weights embedder available there (top open model on MTEB multilingual), 32k context, 4096 dims, $0.01/M tokens — corpus embedding cost is well under one cent, so T1 remains effectively free.
- One endpoint and one key now cover both the generator (`qwen/qwen3.7-flash`, D-07/D-08) and the embedder.

## Effect on parity claims

None on the comparison mechanism: both arms share ONE index (D-01), vectors are copied verbatim between stores and never recomputed, so the embedder choice cancels out of the parity diff. The pinned model id recorded in `v1/.env.parity` and `v1/README-PARITY.md` must name `qwen/qwen3-embedding-8b` @ OpenRouter so the run record stays honest.
