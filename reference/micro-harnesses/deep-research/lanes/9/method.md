# Lane 9 method

## Queries run (web search; 14 rounds, 2 queries each unless noted)

1. `Qwen3 technical report arXiv 2025 small models 0.6B 1.7B 4B`
2. `SmolLM2 SmolLM3 arXiv HuggingFace small language models 1.7B`
3. `EmbeddingGemma Google arXiv 300M embedding model MTEB`
4. `Phi-4-mini technical report arXiv Microsoft small language model`
5. `Gemma 3 1B 4B technical report arXiv Google 2025`
6. `LFM2 Liquid AI arXiv small language model on-device tool calling`
7. `MiniCPM MiniCPM4 MiniCPM5 technical report arXiv 2025 small model on-device`
8. `Arctic Embed 2.0 Snowflake arXiv MTEB small embedding model`
9. `Nomic Embed 2 MoE text embedding arXiv 2501 MTEB multilingual`
10. `MTEB massive text embedding benchmark arXiv 2210 Muennighoff BEIR`
11. `jina-embeddings-v3 multilingual embedding arXiv 2024 Jina AI` +
    `LongEmbed benchmark long context retrieval embedding arXiv 2024`
12. `BFCL Berkeley function calling leaderboard arXiv small language models tool use evaluation` +
    `Nemotron Nano NVIDIA small language model arXiv 2025 hybrid Mamba`
13. `SmolLM3 3B arXiv paper 2025 HuggingFaceTB 11T tokens` +
    `ModernBERT arXiv 2024 long context encoder 8k retrieval`
14. `OLMo 2 small 1B 7B technical report arXiv fully open language model` +
    `E5-Mistral text embedding large language models arXiv 2402 Wang`
15. `BGE-M3 multi-functionality multilingual hybrid retrieval arXiv 2402 Chen 8k long context` +
    `HELMET long context evaluation benchmark arXiv 2024 synthetic recall RAG`
16. `MiniCPM-Embedding lightweight text embedding model OpenBMB 2024` (single)
17. `IBM Granite small language model 1B 3B instruct arXiv technical report 2025` (single)
18. `princeton-nlp HELMET github long context evaluation benchmark repository` +
    `ModernBERT github repository answerdotai encoder model release`

## Sources used

- arXiv abs pages and full paper HTML/PDFs, opened via webfetch (seeds
  2506.05176, 2506.07900 confirmed here; everything 2025+ taken from fetched
  pages, never recall).
- GitHub repository pages (Snowflake-Labs/arctic-embed via webfetch) and the
  GitHub REST API for stars/pushed_at/license (allenai/OLMo,
  embeddings-benchmark/mteb, ShishirPatil/gorilla, FlagOpen/FlagEmbedding,
  dwzhu-pku/LongEmbed succeeded; see failures).
- Hugging Face model cards and blog posts (SmolLM2/3, EmbeddingGemma, jina-v3,
  MiniCPM-Embedding-Light, ModernBERT, MiniCPM4.1) — treated as
  vendor-primary: authoritative for "what the vendor ships", nothing more.
- PMLR proceedings (BFCL) and the live BFCL leaderboard; IBM docs and Ollama
  model pages for Granite (secondary — hence abstain).
- ACL Anthology pages (MTEB, E5-Mistral, BGE-M3, ModernBERT) for venue
  confirmation.

## Counts

- Screened: 33 rows in `inventory.tsv`.
- Admitted: 27 (23 arXiv papers with PDFs in `papers/`, each verified to start
  with `%PDF`; BFCL proceedings-only; SmolLM3 and MiniCPM-Embedding-Light
  repo/card-only, no PDFs per the do-not-file-unadmitted rule).
- Refuted/abstained: 7 with per-row reasons (2 out-of-band model families, 1
  out-of-band paper, 2 superseded reports, 1 secondary-only vendor family,
  plus metadata gaps recorded as `not-fetched` rather than asserted).

## What failed

- `export.arxiv.org` API over shell curl returned empty bodies, so no
  Atom-API screening was possible; replaced with abs-page fetches plus search.
- GitHub REST API rate-limited the shared egress IP after ~6 calls; remaining
  star/push/license cells are honestly marked `not-fetched`, and HELMET /
  ModernBERT / arctic-embed stars were recovered from fetched repo pages
  instead.
- Semantic Scholar citation-chaining endpoints were not used (same egress
  limits); forward/backward chaining was done through paper reference sections
  visible in fetched content, which is thinner than planned — a second pass
  with S2 access would most likely surface missed 2025 decoder-embedder
  follow-ons.
- Full author lists were not captured for six papers (noted per row); venues
  for proceedings versions confirmed via ACL Anthology / PMLR excerpts.
- No sub-agents were spawned (single-lane worker); the ten-lane parallelism
  belongs to the orchestrator.
