# Positioning: MelodyScribe against LightRAG, HippoRAG 2, and GraphRAG

Date: 2026-09-11. The owner's framing, confirmed: MelodyScribe builds the same kind of knowledge structure those systems build (chunks, entities, relations, embeddings over each, a graph to walk, structured facts to look up), but does the work inside one small model, mostly in one pass, on both the index side and the query side. The goals are cost, speed, and, as the model is trained on the rig, accuracy above those systems.

Stage descriptions of the three systems are from their papers and, for LightRAG, from the v1 code in this repo (`v1/lightrag/operate.py`, the 4-stage query pipeline). Call counts are qualitative on purpose.

## 1. Index side: what collapses into one pass

| Stage | LightRAG | HippoRAG 2 | GraphRAG | MelodyScribe |
|---|---|---|---|---|
| Entity and relation extraction | one LLM call per chunk, plus gleaning calls | OpenIE: NER call then triple call per passage | one LLM call per chunk | the op list decoded after the paragraph prefill, in the same pass |
| Description merging and summarising | LLM calls when merged descriptions grow | none | LLM summarisation per entity | a rare, gated revise op (lane 8 rules), not per-ingest |
| Chunk embeddings | separate embedder | separate embedder | separate embedder | `[EMB]` token after the section, same pass (OneGen mechanism) |
| Entity and relation embeddings | separate embedder, two more vector sets | separate embedder for phrases, synonym edges by similarity | entity embeddings for local search | `[EMB]`-style tokens after filed entity and relation mentions, same pass: one representation for filing and for retrieving |
| Graph construction | upsert nodes and edges | passage nodes plus phrase nodes plus synonym edges | Leiden communities | graph ops applied by the filer; community-level summaries only if a revise op earns them |
| Community reports | none | none | one LLM call per community per level, the dominant cost | none by default |
| Structured facts (dates, tables) | none | none | none | SQL ops into the SQLite artifact |
| Procedural knowledge | none | none | none | Folio ops into the sandboxed skills store |

Per paragraph, the competition pays several API calls and several embedder passes. MelodyScribe pays one prefill and a short constrained decode on a local 2B model, and the prefill is batched across paragraphs. That is where cost and speed come from.

## 2. Query side: where it gets interesting

| Stage | LightRAG | HippoRAG 2 | GraphRAG | MelodyScribe |
|---|---|---|---|---|
| Understanding the query | LLM keyword-extraction call (high- and low-level keywords) | NER call on the query | none for local, map-reduce for global | the model reads the query and emits `[RQ]` tokens and seed ops as it thinks |
| Query embedding | separate embedder | separate embedder | separate embedder | the `[RQ]` token's state, same stream |
| Graph walk | neighbours of matched entities and relations | Personalised PageRank from seeds, after an LLM "recognition memory" filter call | community reports | seeds named in the ops; PPR or neighbourhood run by the harness; results appended to the same context |
| Structured lookup | none | none | none | a SQL op when the query is a fact lookup |
| Multi-hop | one pass | one PPR | map-reduce | the model emits another `[RQ]` after reading results, as many times as the budget allows (Search-R1, OneGen pattern) |
| Answer | separate LLM call | separate reader call | separate LLM calls | the same stream continues, or a distilled context is handed to the frontier model through the seam |

Three properties fall out. First, retrieval decisions are made mid-generation with the retrieved text already in the cache, so there is no re-prefill between "decide", "retrieve", and "answer". Second, the query embedding and the document embeddings come from the same weights and the same training objective, so filing and retrieving share one representation, which none of the three systems can say. Third, the harness can still run the classical machinery, PPR, vector search, SQL, exactly as the machine already does; the model only chooses and seeds it.

## 3. Where accuracy above the competition can come from

The competition's extraction and keyword stages are frozen prompts around an API model; nothing in their pipeline learns from retrieval outcomes. MelodyScribe's are trainable, and the rewards are verifiable on the rig:

1. **Distillation from the frontier teacher on this exact task** (rationale-augmented SFT) gets the 2B to the teacher's filing behaviour cheaply.
2. **Reinforcement learning with verifiable rewards** (DeepRetrieval, 2503.00223: a 3B beat GPT-4o on retrieval and SQL) optimises the ops for retrieval usefulness, not for extraction F1. An extraction that helps recall is rewarded even when it is not the extraction a human would write.
3. **Joint embedding-and-filing training** makes the representation consistent across index and query sides.
4. **Per-corpus adaptation** is a LoRA run, affordable on one 16 GB card; the competition cannot adapt an API model to a corpus.

Honest starting point: a 2B model begins below the frontier extractor the rig currently uses (Phase 2 D-07, `qwen/qwen3.7-flash`). The claim is that it climbs past it under training, and the rig is built to show exactly that, same corpus, same seam, modalities side by side. No number is claimed until the rig produces it.

## 4. Two things the competition does that MelodyScribe deliberately does not

- GraphRAG's community reports: the most expensive step in the field, and lane 8's rules on gated revision say do not schedule it; earn it from a revise op when retrieval misses show a need.
- LightRAG's per-ingest description summarisation: same rule.

What MelodyScribe adds that none of them has: structured facts in SQL, procedural knowledge in sandboxed Folios, and a model that can be trained on the outcome.
