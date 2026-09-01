# API Coverage — OpenAI-compatible model endpoint (OpenRouter, Ollama)

Full coverage is the default; this table is the subtraction record. Every `OPT-OUT` carries a
one-line reason so a later reader can weigh it — an opt-out without a reason is the un-decided
hole this matrix exists to close.

| capability | decision | reason |
|---|---|---|
| `chat.completions` (non-streaming) | INTEGRATE | the `keywords` and `generate` nodes call it (D-06/D-07) |
| `embeddings` | INTEGRATE | `embedder-query` and `embedder-index` call it (D-06/D-07) |
| response `usage` / token accounting | INTEGRATE | MACH-05 meters spend at each node's declared boundary; a node reporting zero spend for a real call is a refusal, not a free node |
| provider routing / provider pinning | INTEGRATE | Phase 2 D-07 pins the provider because a re-routed provider changes identity mid-run |
| deterministic sampling parameters (temperature, seed) | INTEGRATE | both arms are handed the same sampling parameters from one pinned record (D-07) |
| `chat.completions` streaming | OPT-OUT | the parity comparison reads completed outputs; the streaming transport is Phase 4's §18 seam concern |
| rerank | OPT-OUT | D-09 keeps the `rerank` node and its `calls_rerank` declaration but configures it as a pass-through — standing up a rerank provider adds a cost source and a variance source to the one comparison meant to isolate decomposition |
| model catalogue listing | OPT-OUT | model identity is derived from the provider and model the response actually returns, never from a catalogue lookup (Phase 1 D-12, Phase 2 D-08) |
| tool / function calling | OPT-OUT | no §L.1 query-side position calls a tool |
| structured-output / JSON mode | OPT-OUT | the ported keyword extractor parses v1's own output shape, and matching v1 is what parity requires |
| logprobs | OPT-OUT | nothing in the retrieval-level comparison reads them |
| images (vision input/output) | OPT-OUT | no §L.1 query-side position accepts or produces image content; the corpus and query surface are text-only |
| audio (speech-to-text / text-to-speech) | OPT-OUT | no §L.1 query-side position handles audio; the query and answer surfaces are text-only |
| files (upload / retrieval-file API) | OPT-OUT | corpus ingestion is Phase 5's opaque-admission concern (MODAL-02), not a Phase 3 query-side capability |
| fine-tuning | OPT-OUT | D-08 pins fixed model identities (`qwen/qwen3.7-flash`, local Ollama embedder); no fine-tuned variant is part of this phase's scope |
| batch API | OPT-OUT | the parity harness runs interactive per-query calls to keep the retrieval-level comparison keyed to one query at a time; batched submission is an operational optimization outside this phase's scope |
| moderations | OPT-OUT | the corpus is a fixed, owner-controlled HotpotQA snapshot (D-14); no untrusted user content passes through the query path this phase ports |
| responses API (stateful multi-turn) | OPT-OUT | D-07's one client shape is chat-completions plus embeddings; the responses API is a separate, stateful surface neither arm's pinned configuration uses |
