# MelodyScribe Score I/O specification, v0.1

Status: draft for spike 001. Owner review required before v0.2. This document is the shared contract for spikes 002 to 005: what enters the model at every step, what leaves it, and how each output becomes a store operation. Anything not stated here is not agreed.

## 1. Vocabulary

| Term | Meaning |
|---|---|
| Score | A sectioned input document with per-section directives (section 3). Produced by the harness chunker for bulk ingest, or by the frontier model through the MelodyScribe skill |
| Section | One unit of text with an id and directives. The unit of embedding and of filing |
| Token plan | The compiled form of a Score: an ordered list of decode steps over named sequences (section 4) |
| Main sequence `S0` | The one sequence that holds the whole Score in order plus everything generated. Its final state is the cache for the next prompt |
| Embedding sequence `E_i` | A sequence holding `doc_prefix` plus one section plus `[EMB]`, isolated from every other section. Freed after its vector is read |
| `doc_prefix` | Every token that precedes a section's content in an embedding sequence, including any chat-template preamble. Fixed per version, recorded in the `EmbeddingSpace` hash (CONTRACT §4) |
| `query_prefix` | The same for a query at recall time |
| `[EMB]`, `[RQ]` | Single positions whose last-layer state is read as a vector. Resolved per model by the token policy (section 2) |
| Op | One typed store operation emitted by the model (section 5) |
| Proof | The deterministic validator every op passes before dispatch (section 6) |

## 2. Token policy

The vector is read at exactly one position. Which token sits there is a per-model decision recorded with the model revision:

1. Preferred: an unused reserved or special token in the base tokenizer, so `[EMB]` is one token id and never appears in natural text.
2. Fallback: a literal marker string `⟦EMB⟧`; the harness reads the state at its last token. The marker is escaped if it appears in content.
3. Trained (spike 004c and later): the same token id, with the head or adapter trained so its state is the embedding. Untrained, the state is the base model's last-token representation; spike 004 measures the difference.

`[RQ]` follows the same policy with a distinct id. The policy string, for example `emb=reserved:128002;rq=reserved:128003`, is part of the `EmbeddingSpace` hash as `namespace_text_convention`.

Pooling is `last` at the `[EMB]` position. No mean pooling in v0.1.

## 3. The Score document

```xml
<score v="1" corpus="…" doc="…">
  <section id="s1" embed="isolated">text…</section>
  <section id="s2" embed="off" respond="text">a command…</section>
  <section id="s3" embed="isolated" respond="ops" file="graph,sql">text…</section>
  <section id="s4" embed="rewrite:propositions" link="raw,graph">text…</section>
</score>
```

| Attribute | Values | Default | Who acts |
|---|---|---|---|
| `id` | unique within the Score, `[a-z0-9_-]+` | required | harness |
| `embed` | `isolated`, `context`, `off`, `rewrite:<style>` | `isolated` | harness (rewrite: model then harness) |
| `respond` | `none`, `ops`, `text` | `none` | model |
| `file` | comma list from `graph`, `sql`, `folio`, `agent`, or `any` | `any` when `respond=ops`, else none | model + harness |
| `link` | comma list from `raw`, `graph`, `sql`, `folio` | `raw` | harness |

Rules: sections are processed in document order; content is plain text, entities escaped; an unknown attribute or value is a compile error, never ignored; `rewrite` requires a style from the registered set (`propositions`, `canonical`, `summary`); `file` without `respond=ops` is an error; a Score with zero sections is an error. The model never authors directives: directives come from the chunker or the frontier skill, and the compiler refuses a Score whose provenance is the model itself.

## 4. Compilation: Score → token plan

The compiler emits steps in order. Each step names a sequence, the tokens to append, the positions at which to read outputs, and, for decode steps, the grammar and the token cap.

| Directive | Steps |
|---|---|
| any section | `S0 += tokens(section content)` |
| `embed=isolated` | `E_i = copy(P)`; `E_i += tokens(section content) + [EMB]`; read vector at `[EMB]`; free `E_i`. `P` is the prefilled `doc_prefix` sequence, copied not recomputed |
| `embed=context` | `S0 += [EMB]`; read vector at that position (depends on everything before it in `S0`; recorded as `form=context`) |
| `embed=off` | nothing |
| `embed=rewrite:<style>` | `S0 += tokens(rewrite instruction for style)`; decode text with cap `rewrite_max_tokens`; `S0 += [EMB]`; read vector there; store both the rewrite text and the vector with `form=rewrite:<style>` |
| `respond=ops` | `S0 += tokens(ops instruction for the `file` set)`; decode under grammar `G(file set)` with cap `ops_max_tokens`; parse; the decoded tokens stay in `S0` |
| `respond=text` | `S0 += tokens(answer instruction)`; decode free text with cap `text_max_tokens` and the stop set |
| `link=…` | no tokens; metadata assembled at dispatch (section 6) |

Position accounting: `S0` positions continue across sections and across generated tokens. `E_i` positions start at `len(P)`. With the C API this is `llama_memory_seq_cp` for `P → E_i`, one `llama_decode` per step with `embeddings=true`, `llama_get_embeddings_ith` at the marked position, `llama_get_logits_ith` at the last position for decode, `llama_memory_seq_rm` to free `E_i`.

Invariants the compiler and runtime must hold, and spike 001 tests:

- I1 Isolation: the vector for `embed=isolated` depends only on `(doc_prefix version, section content, token policy)`. Moving the section elsewhere in the Score, or changing other sections, changes nothing.
- I2 Order: the final `S0` equals the in-order concatenation of section tokens, instruction tokens, and generated tokens. Nothing is dropped or reordered.
- I3 No directive leakage: no directive text or tag enters an embedding sequence.
- I4 Bounded decode: every decode step has a token cap, and either a grammar or a stop set.
- I5 One read per vector: each `[EMB]`/`[RQ]` position is read exactly once and recorded with its sequence and position.

## 5. Output: the op list

Every `respond=ops` decode produces one JSON object matching `ops.schema.json` (beside this file). Shape:

```json
{"ops": [
  {"target": "graph", "s": "Ada Lovelace", "p": "born_on", "o": "1815-12-10", "s_type": "person", "o_type": "date", "evidence": [12, 48]},
  {"target": "sql",   "subject": "Ada Lovelace", "attribute": "birthday", "value": "1815-12-10", "value_type": "date", "evidence": [12, 48]},
  {"target": "folio", "slug": "find-people-by-birth-year", "kind": "procedure", "title": "…", "markdown": "…"},
  {"target": "agent", "ask": "…", "why": "…"}
]}
```

Rules: `{"ops": []}` is the cheapest legal output and means "nothing to file"; at most 32 ops per section; strings at most 512 characters; `evidence` is a `[start, end]` character span into the section content, required for `graph` and `sql`, and the quoted span must contain the subject or the value, which Proof checks; `graph` and `sql` may both be emitted for the same fact; `agent` is legal only when `agent` is in the `file` set; the grammar for a section is the schema restricted to the targets in its `file` set. SQL in v0.1 is one generic table, `facts(subject, attribute, value, value_type, unit, valid_from, valid_to, evidence_ref)`, so no schema catalog is needed until a query type demands one.

## 6. Dispatch: ops → stores, through Proof

Proof rejects an op, logs it, and continues; a rejected op never blocks the section's embedding.

| Check | Applies to | Rule |
|---|---|---|
| Schema | all | validates against `ops.schema.json` restricted to the `file` set |
| Evidence | graph, sql | span inside the section; the span text contains the subject or value after whitespace and case normalisation |
| Non-empty | graph, sql | subject, predicate, object, attribute, value non-empty after trimming |
| Value type | sql | `date` parses as ISO 8601 or a year; `number` parses as a decimal; `text` otherwise |
| Slug | folio | kebab-case, at most 64 characters, unique in the Folios store or explicitly `supersedes` |
| Permission | agent | present only if allowed by the `file` set |

Effects per op, in the contract's vocabulary: graph → `writes_graph`; sql → `writes_artifact` (the SQLite blob, CONTRACT §15.3); folio → `writes_kv` and `writes_vector` at scope `self_storage`; agent → `calls_llm` through a machine client, never `net`; the section vector → `writes_vector` in the declared `space_id`.

Link record written per vector: `{vector_id, space_id, chunk_ref, section_id, form, graph_ids[], sql_row_ids[], folio_slug?, doc_prefix_version, model_revision}`. Graph nodes and SQL rows carry `chunk_ref` and `section_id` back. This is the `metadata` bag of `ScoredItem` (CONTRACT §4).

## 7. Recall-time I/O

One stream: `[query_prefix][query][RQ]` then one grammar-constrained decode of a recall op list, then the harness appends results, then the model answers or hands off.

```json
{"recall": [
  {"source": "vector", "k": 8},
  {"source": "graph", "seeds": ["Ada Lovelace"], "hops": 1},
  {"source": "sql", "attribute": "birthday", "subject": "Ada Lovelace"},
  {"source": "folio", "slug": "find-people-by-birth-year"}
]}
```

The `[RQ]` vector is read at its position before the decode. Results are appended as a fenced block the model treats as data. A second recall list is allowed after results, up to `max_hops` (budget-owned, not model-owned). The final answer is either free text or `{"target": "agent", …}` to hand a distilled context across the seam.

## 8. Worked example

Score: three sections. s1 `embed=isolated`; s2 `embed=isolated respond=ops file="graph,sql"`; s3 `embed=off respond=text`.

Token plan: `P` prefilled once. Step 1: `S0 += s1`; `E_1 = copy(P) + s1 + [EMB]` → vector v1; free. Step 2: `S0 += s2`; `E_2 = copy(P) + s2 + [EMB]` → v2; free; `S0 += ops-instruction(graph,sql)`; decode under `G({graph,sql})`, cap 256 → `{"ops":[…]}`; parse; Proof; dispatch; link records for v2 carry the graph ids and sql row ids produced. Step 3: `S0 += s3 + answer-instruction`; decode text, cap 512. End: `S0` holds s1, s2, instruction, ops tokens, s3, instruction, answer. Two vectors written, one op list dispatched, one answer returned.

## 9. Acceptance tests for spike 001

1. Unique ids enforced; unknown attribute rejected; `file` without `respond=ops` rejected; `rewrite` without a registered style rejected.
2. I1: the same section compiled at position 1 and at position 7 of two different Scores yields byte-identical `E_i` token lists.
3. I2: `S0` reconstruction equals the in-order concatenation.
4. I3: no tag bytes appear in any `E_i` token list.
5. Grammar round trip: schema → grammar → sampled outputs parse and validate for every `file` subset.
6. Proof catches a fabricated evidence span and a mistyped date; passes a correct op; passes `{"ops": []}`.
7. The demo page renders any pasted Score as its token plan with coloured spans and shows the op list and Proof verdicts for a supplied model output.

## 10. Open decisions for the owner

1. Entity resolution: v0.1 files graph nodes by normalised name; alias merging is a revise-op concern. Confirm.
2. One generic `facts` table versus a typed catalog. v0.1 is generic.
3. Whether `folio` ops are allowed during bulk ingest or only from `respond=ops` sections the frontier authored. v0.1 allows both; the sandbox rule (D-MS-01) holds either way.
4. Whether `doc_prefix` includes the chat-template system turn. v0.1 says yes, because the ops instruction must be in the template and the prefix must be everything before the section.
5. `[EMB]` token choice per model, recorded when spike 002 inspects each tokenizer.
