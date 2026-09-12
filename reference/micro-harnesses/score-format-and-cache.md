# The MelodyScribe Score: a sectioned input format with embed / respond / file directives, and what the KV cache can and cannot reuse

Date: 2026-09-11. Answers two owner questions: (1) can one input stream switch embedding and responding on and off per section, mark sections back to raw text and graph, and still leave a usable cache for the next prompt; (2) can a segment in the middle of the context be cached, not only a prefix. Verified facts carry a source; the rest is owner analysis. "Score" is the proposed name for the format (naming rule 1: purpose-built for MelodyScribe).

## 1. The Score format, draft

```xml
<score v="1">
  <section id="1" embed="isolated">                    …raw paragraph…                </section>
  <section id="2" embed="off" respond="text">          …a command to answer here…     </section>
  <section id="3" embed="isolated">                    …raw paragraph…                </section>
  <section id="4" embed="off" respond="ops" file="graph">  …content to file as triples… </section>
  <section id="5" embed="rewrite:propositions" link="raw,graph">  …paragraph…        </section>
</score>
```

| Directive | Who acts | Meaning |
|---|---|---|
| `embed="isolated"` | harness | The section is embedded as its own sequence: `[doc_prefix][section]`. The vector is a pure function of the section, so it is searchable and reproducible |
| `embed="context"` | harness | Pooled from the main stream's span, so it includes everything before it. Cheaper (no extra sequence), prefix-dependent. For "meaning in context" only |
| `embed="off"` | harness | Not pooled |
| `embed="rewrite:<style>"` | model, then harness | The model first rewrites the section in the named style (propositions, canonical form); the rewritten tokens' own hidden states are pooled as they are generated, so no re-prefill. Raw and rewritten vectors can both be stored, marked by form |
| `respond="text\|ops"` | model | Generation is triggered at the end of this section, before the next section is read. The response is appended to the main stream and becomes context for what follows |
| `file="graph\|sql\|folio\|agent"` | model + harness | The response is grammar-constrained to that target's op schema; the harness executes it |
| `link="raw,graph"` | harness | The vector entry's metadata carries the machine-minted `ChunkRef` of the raw text and the graph node ids created by this section's ops (CONTRACT §4: `ChunkRef`, `ScoredItem.metadata`) |

The model sees the `respond` and `file` directives (they are instructions to it). The `embed` and `link` directives are for the harness; an isolated embedding sequence contains only `doc_prefix` plus the section content, never the tags.

Who writes a Score: the harness's deterministic pre-pass (chunker plus rules) for bulk ingest, or the frontier model following the MelodyScribe skill when it hands work over. Either way the model never authors its own directives; that keeps the format a trust boundary, not a suggestion.

## 2. How one pass executes a Score (llama.cpp C API, verified primitives)

The `llama_batch` carries per token: `token`, `pos`, `seq_id`, and an output flag (`llama.h` lines 262-271). Tokens with different `seq_id` do not attend to each other; tokens in the same sequence attend causally. That is the whole mechanism.

1. Prefill `doc_prefix` once as sequence P. Prefill the main stream as sequence S0, section by section, positions continuing.
2. For a section with `embed="isolated"`: copy P's KV into a fresh sequence Si (`llama_memory_seq_cp`, `llama.h` line 757), append the section's tokens under Si, decode in the same batch as S0's tokens. Pool Si's last-layer states → vector. Free Si (`llama_memory_seq_rm`, line 748). The vector is a function of `(doc_prefix, section)` only.
3. For `embed="context"`: pool the span of S0 instead; no extra sequence.
4. For `respond`: sample from S0's last logits, under the op grammar if `file` is set, until stop. Execute the ops. The generated tokens are already in S0's KV; continue prefilling the next section after them. This is read-respond-read-respond inside one context.
5. For `embed="rewrite"`: as step 4 with a rewrite instruction; pool the generated tokens' states (embeddings are produced for output tokens in the same decode, `llama-context.cpp` lines 2056-2057).
6. At the end, S0 holds the entire stream plus every response. The next prompt appends to S0: this is the ordinary prefix cache. To keep it across processes, `llama_state_seq_save_file` / `_load_file` (`llama.h` lines 890, 898) persist one sequence's state to disk.

Cost: every section is prefilled exactly once in S0. An isolated embedding costs one extra prefill of that section (not of the whole stream), because P is copied, not recomputed. Nothing is prefilled twice.

## 3. Marks back to raw and graph

Every vector entry stores `{vector, space_id, ref: ChunkRef, section_id, form: raw|rewritten:<style>, graph_ids, sql_row_ids, folio_slug}`. Every graph node and edge stores its source `ChunkRef`. Search then moves in any direction: vector hit → raw text and its graph nodes; graph node → its chunks and their vectors. This is the `metadata` bag CONTRACT §4 already gives `ScoredItem`, and the pattern LightRAG already uses (`source_id` on entities and relations).

## 4. What the KV cache can reuse: the 1A / 1X2 question

A token's KV entry is a function of three things: its content, its absolute position, and every token before it in its sequence. Exact reuse needs all three to match. That is why a shared **prefix** (1, then 1A, 1B, 1C) is the only case that is exact for free.

For a segment in the **middle** (1X2 versus 1S2, reuse "2"):

| Form | Mechanism | Exact? | Source |
|---|---|---|---|
| **Shift reuse** | llama-server `--cache-reuse N` / request field `n_cache_reuse`: chunks of at least N tokens found in the previous prompt are reused "via KV shifting" (their positions are moved, `llama_memory_seq_add` is the primitive, `llama.h` line 772). "2"'s KV was computed after X and is reused after S, still carrying X's influence | No, approximate | tools/server/README.md lines 221, 532 |
| **Isolation** | Prefill "2" as its own sequence so its KV depends only on "2" (or on "1" plus "2"). At use time `seq_cp` it into the target and `seq_add` it to the right position. Later tokens attend to it normally; "2" itself never saw X or S | Yes, by construction; "2" is context-blind | Prompt Cache, arXiv 2311.04934: schema-defined reusable "prompt modules" with positional accuracy |
| **Isolation plus repair** | As above, then recompute a small fraction of the module's tokens to restore cross-attention with what now precedes it | Approximate, tunable | CacheBlend, arXiv 2405.16444 |
| **Reorder** | Put the invariant part first so it becomes a prefix | Yes | trivial |

A generated **output** is cached exactly like input: its tokens' KV obey the same three-part rule. An output in the middle of a later context is reusable under the same three forms, and `llama_state_seq_save_file` persists it.

## 5. Why the two questions are one design

An `embed="isolated"` section is prefilled as its own sequence anyway (section 2, step 2). That sequence's KV is exactly a Prompt Cache module. Keep it instead of freeing it, and the same pass yields the section's embedding **and** its reusable KV module. At query time, retrieved chunks are composed by isolation (form 2): `[system + query_prefix]` is the prefix, each retrieved chunk's module is copied in, the question follows, and only the question is prefilled. That is GritLM's document caching generalised to many chunks, and it is what makes "read that along with using cache for your next prompt" hold.

The order of concessions if quality suffers: isolation first (free, exact for the module, blind to neighbours), then CacheBlend-style partial recompute, then full prefill of the chunks that matter.

## Ledger

- Quality of shift reuse and of isolated modules at 2B on our corpus: **no source**; a rig experiment, added to the spike todo.
- Prompt Cache and CacheBlend accuracy figures: abstracts read, results tables not read. **unverifiable here**
- Whether llama-server applies `--cache-reuse` to embedding requests. **no source**
- SGLang and vLLM equivalents of isolation (both have prefix caching; module composition would need their APIs checked). **not checked**
