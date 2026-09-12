# MelodyScribe runtime: one pass over a paragraph, two outputs

Date: 2026-09-11. Answers "how does the runtime pull in embeddings and characters at the same time?" Verified facts carry a source; the rest is owner analysis.

## What one run of a decoder model actually produces

A forward pass over a prompt ("prefill") computes, for every prompt token, a hidden state at every layer, and fills the KV cache. Two things fall out of the same pass:

- the **last-layer hidden states** of the paragraph's tokens, which pooled give the paragraph's embedding;
- the **logits at the last position**, from which generation starts, continuing token by token ("decode") against the cache the prefill just built.

So the embedding is a by-product of the prefill that generation needs anyway. There is no second pass. The only extra work is reading a vector out of memory.

```
 prompt:  [doc_prefix][ paragraph ][ instruction + tool schema ]  →  generated ops
                        │ pooled last-layer state ──────────────────►  embedding → Faiss
                        └────────── KV cache ─────────────────────────►  decode → tool calls → graph / SQL / folio / agent
```

## Prompt layout is a rule, not a style

With causal attention a token's state depends only on tokens before it. Therefore:

- Everything **before** the paragraph becomes part of the embedding's identity. Keep it a fixed `doc_prefix`; the `EmbeddingSpace` hash already records `doc_prefix`, `query_prefix`, and `pooling` (CONTRACT §4), so this is the contract's own requirement.
- Everything **after** the paragraph (the instruction, the tool schema, few-shot examples) does not touch the paragraph's states. The embedding is a pure function of `(doc_prefix, paragraph)`, reproducible regardless of what the transcriber asks the model to do with it.
- Pooling: last token of the paragraph span, or mean over the span. Last-token is the causal-model convention (Qwen3-Embedding, e5-mistral).
- Query time: `[query_prefix][query]` with the same pooling, then the same KV can serve the answer, which is GritLM's query-caching trick.

## Three verified ways to get both outputs from one pass

| Route | Mechanism | Verified | Cost |
|---|---|---|---|
| **A. llama.cpp C API** (via `llama-cpp-python`, in nixpkgs) | Context created with `embeddings=true`. One `llama_decode` over the batch yields **both** logits and embeddings: `has_logits = true; has_embd = cparams.embeddings;` (`src/llama-context.cpp` lines 2056-2057, 2026-09-11). Read `llama_get_embeddings_ith(ctx, i)` at the paragraph's last token (or `llama_get_embeddings_seq` per sequence), read `llama_get_logits_ith` at the last position, sample the tool call with a grammar sampler, keep decoding on the same cache. Many paragraphs batch as separate sequences (`n_seq_max`) | llama.h, llama-context.cpp | About a hundred lines of Python. No PyTorch. This is the custom Scriptorium endpoint |
| **B. llama-server, two requests** | Embedding request on `[doc_prefix][paragraph]`, then a completion request on `[doc_prefix][paragraph][instruction]`. With `cache_prompt` (default on) "only the unseen suffix is evaluated" | tools/server/README.md line 491 | Zero custom code, two HTTP calls, same compute as one pass. Ledger item: whether an embedding request populates the same slot cache as a completion when the server is not in `--embeddings` mode |
| **C. SGLang `return_hidden_states`** | One generate request returns the prompt tokens' hidden states and the generated text | `examples/runtime/hidden_states/hidden_states_server.py`, 84 code hits in sgl-project/sglang | PyTorch inside the server process, HTTP for Databasise. Also gives the native MiniCPM5 tool-call parser and DSpark speculative decoding |

Recommended order: B for the first spike (no code), A when the harness is real (one process, one cache, full control), C if tool-call parsing or decode speed becomes the bottleneck.

## The output side: a list of operations, grammar-constrained

The generation is constrained to a schema so it cannot be anything but a well-formed operation list. llama-server accepts `json_schema`, `grammar`, and OpenAI-style `response_format: {type: json_schema}` (README lines 151-154, 569-571, 1316); SGLang uses xgrammar. A paragraph can yield several operations, so the schema is a list:

```json
{"ops": [
  {"target": "graph", "triples": [["Ada Lovelace", "born", "1815-12-10"]]},
  {"target": "sql",   "table": "people", "row": {"name": "Ada Lovelace", "birthday": "1815-12-10"}},
  {"target": "folio", "slug": "how-to-search-people-by-date", "markdown": "..."},
  {"target": "agent", "ask": "..."}
]}
```

The `filer` node dispatches each op: `graph` → Cozo (`writes_graph`); `sql` → the SQLite blob artifact (`writes_artifact`, CONTRACT §15.3); `folio` → KV plus vector at scope `self_storage` (`writes_kv`, `writes_vector`); `agent` → a machine-mediated client call (`calls_llm`), never raw network, per §8 condition 3. The embedding goes to Faiss (`writes_vector`) under the declared `space_id`. Grammar removes syntax errors; semantic errors (wrong target, wrong entity) are what the routing-accuracy spike measures.

## Where a trained embedding adapter fits, and one correction

A LoRA applied during the pass changes the weights for generation too, because it is one pass. Three options:

1. **Unified training** (GritLM's recipe): the same weights are trained for both embedding and generation; the paper reports no loss at 7B. The intended end state for `MelodyScribe-2B-v1`.
2. **A small trained head** (linear or MLP) over the pooled state of the frozen base: zero interference with generation, cheapest to train, embedding quality unknown until measured. **First choice for the spike.**
3. **Per-request LoRA scale** on llama-server: forces two passes (adapter on for embedding, off for generation), which defeats the one-pass goal. Not used.

Correction to `runtime-and-training-stack.md`, which said "train an LLM2Vec-style adapter": for one-pass co-generation the adapter must be either jointly trained (option 1) or a head (option 2). An embedding-only LoRA is only compatible with two passes.

## The efficiency claim, stated precisely

- The embedding costs nothing **given** the model reads the paragraph for extraction anyway. The paragraph prefill is the shared cost; decoding the tool call is the dominant cost and is unchanged.
- Against a dedicated 0.6B embedder, the saving per paragraph is roughly that embedder's pass, about a quarter of the 2B prefill. The saving is real but modest; index-time cost is still dominated by generation (feasibility note, reason 2).
- The larger win is structural: one model, one prompt template, one KV cache, one `space_id`, and at query time the query's own embedding pass becomes the prefill of the answer.
- Batching is where throughput comes from: paragraphs are independent, so a decode call carries many sequences. Measure tokens per second on legion; do not estimate.

## Contract question this raises (adds to system-model-fit.md §9)

5. One client call that returns both an embedding and a generation has no declared capability yet. ANATOMY §E already lets the LLM client declare `prefix_continuation` and `prompt_cache`; a flag for "returns pooled hidden states" would be a §14 capability-table addition of the same kind as the embedding client's own flags (PARTS-06 G2). Until then the node declares both `calls_llm` and `calls_embedding`, and the two machine clients are two views of one served endpoint.

## Ledger

- Route B: whether an embedding request and a completion request share a slot's prompt cache in llama-server's default mode. **unverifiable here**; the spike checks it.
- Ollama prefix-cache behaviour across `/api/embed` and `/api/chat`. **no source**
- SGLang `return_hidden_states` returning states for prompt tokens as well as generated tokens: the example file exists; which positions it returns was not read. **unverifiable here**
- Quality of a head-over-frozen-base embedding at 2B. **no source**; the first rig experiment.
