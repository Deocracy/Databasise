# Prior art: self-embedding LLMs and memory harnesses that route to graph, vector, and SQL

Snapshot date: 2026-09-11. Answers three owner questions. Every repo below was checked to exist via the GitHub or Hugging Face API on this date (stars and last push recorded). Every capability claim carries its source. Claims that could not be verified against a primary source are in the ledger at the end, not in the body.

Search term that finds this category: **"agent memory layer"** / **"memory OS for agents"**. "Micro harness" finds nothing.

## Q1. One network that is both LLM and embedding model; an LLM that embeds for itself

Yes. Three distinct mechanisms exist, one trained, one adapter-based, one free.

| Project | What it is | Evidence | Repo / model |
|---|---|---|---|
| **GritLM** (Muennighoff et al., Feb 2024, arXiv 2402.09906) | One model trained to do both, selected by instruction: bidirectional attention for embedding, causal for generation. Unification at no performance loss. RAG sped up >60% on long documents because the document's KV cache computed while embedding is reused for generation, so no separate retriever model. This is literally "the model embeds, then switches back and generates" | README quotes the abstract; README code shows `model.generate(..., past_key_values=cache)` reusing the embedding pass. Released checkpoints: GritLM-7B (MTEB 66.8, gen 55.5) and GritLM-8x7B | github.com/ContextualAI/gritlm ★700, last push 2025-06-25; HF GritLM/GritLM-7B |
| **LLM2Vec** (McGill, Apr 2024, arXiv 2404.05961) | Turns any decoder LLM into an encoder in three steps (bidirectional attention, masked next-token prediction, SimCSE). Delivered as LoRA adapters over the base model: adapter on = embed, adapter off = the original generator. Same base weights | README: `LLM2Vec.from_pretrained(base, peft_model_name_or_path=adapter)` | github.com/McGill-NLP/llm2vec ★1,714, push 2026-04-04 |
| **llama.cpp embedding** | Any GGUF model yields an embedding with `llama-embedding -m model --pooling mean`. Zero training. Quality of an untrained generator's pooled states is not measured in the source | examples/embedding/README | github.com/ggml-org/llama.cpp ★127,879 |
| **kNN-LM** (Khandelwal et al., 2019, arXiv 1911.00172) | The LM's own embedding space is the datastore key; retrieval by nearest neighbour in that space, interpolated into next-token prediction, no extra training. The oldest form of "a model retrieves from its own representations" | abstract | github.com/urvashik/knnlm ★332 (archived 2021) |
| **Self-RAG** (Asai et al., 2023, ICLR 2024) | One 7B/13B model trained with reflection tokens to decide when to retrieve and to critique its own output. Embeddings still come from a separate Contriever model, so not fully self-contained | README training + `generate_passage_embeddings.py --model_name_or_path facebook/contriever-msmarco` | github.com/AkariAsai/self-rag ★2,423 |

Same-lineage pairs (separate weights, shared base): **MiniCPM-Embedding** (2.4B, from MiniCPM-2B), **MiniCPM-Embedding-Light**, **MiniCPM-Reranker-Light** on HF under `openbmb/`; **Qwen3-Embedding-0.6B/4B/8B** (LLM-initialised; ★2,028 repo). These are the "one family, two heads" pattern, not one set of weights.

**Harness in front of an embedding model.** In the agentic sense, no. In the pipeline sense, yes, and two are exactly a small model doing prep work before embedding:

- **Dense X Retrieval propositionizer** (Chen et al., Dec 2023, arXiv 2312.06648): a fine-tuned Flan-T5-large splits passages into atomic propositions before they are embedded. HF `chentong00/propositionizer-wiki-flan-t5-large` exists. Repo github.com/chentong0/factoid-wiki ★171.
- **Anthropic Contextual Retrieval** (Sep 2024): a cheap model writes a short context prefix per chunk before embedding and BM25 indexing; contextual embeddings cut top-20 retrieval failure by 35%, with contextual BM25 by 49%; one-time cost $1.02 per million document tokens with prompt caching. Source: anthropic.com/news/contextual-retrieval.

## Q2. A model plus harness that watches a frontier model, extracts to embeddings, graph, and SQL, links them, and routes retrieval

Nobody ships that as one small model. Every piece exists in the "agent memory" category, split across projects. Ranked by closeness to the description.

| Project | Which part of the description it covers | Evidence | Repo |
|---|---|---|---|
| **Cognee** | Graph + vector + relational metadata as one memory layer; ingests documents and conversations; 1.0 runs the whole stack on a single Postgres. Closest to "one system deciding what goes to graph, vector, SQL" | README: "graph database for relationships, a vector database for embeddings, Redis for sessions, and a relational database for metadata … run the entire memory layer on a single Postgres instance"; "can now ingest from relational databases at scale" | github.com/topoteretes/cognee ★30,641, push 2026-09-11 |
| **MIRIX** (arXiv 2507.07957) | Six typed stores (Core, Episodic, Semantic, Procedural, Resource, Knowledge Vault) each managed by its own agent; a structured vault for facts like the "birthday" case; Postgres BM25 + vector; watches the screen, not just the chat. Closest to "meta-manager routes each piece to the right store" | README feature list; abstract | github.com/Mirix-AI/MIRIX ★3,441, push 2026-08-20 |
| **Letta** (MemGPT lineage) | The agent tool-calls into its own memory tiers; **sleep-time compute** (arXiv 2504.13171, Apr 2025) is a background agent that works on memory while the main agent is idle. Closest to "a sub-agent watching another agent". Current docs call the feature "Memory & dreaming" over a git-backed memory filesystem (MemFS) | docs.letta.com Memory & dreaming page; paper repo letta-ai/sleep-time-compute | github.com/letta-ai/letta ★24,699; code now in letta-ai/letta-code |
| **Graphiti** (Zep) | Conversation and document episodes → temporal knowledge graph with embeddings on nodes and edges; hybrid retrieval. Closest to "watch the conversation, build the graph". **Warns that small models fail**: "works best with LLM services that support Structured Output … particularly problematic when using smaller models" | README | github.com/getzep/graphiti ★30,814, push 2026-09-11 |
| **Memori** | Captures structured memory from conversation **and agent execution** after each turn (tool calls, decisions, outcomes); LLM, datastore, and framework agnostic. Closest to "listens to the frontier model and records the necessary information" | README (OpenClaw plugin section; tagline) | github.com/GibsonAI/memori ★16,617, push 2026-09-03 |
| **Hindsight** (arXiv 2512.12818) | Retain / recall / reflect; four memory kinds: world facts, experiences, observations (consolidated beliefs), mental models (synthesised understanding). Postgres + pgvector. Closest to "generates learnings for the frontier model to follow" | README memory-types list and storage table | github.com/vectorize-io/hindsight ★23,464, push 2026-09-11 |
| **A-MEM** (Zettelkasten memory) | Each new memory becomes a note with attributes and tags; the system links it to prior notes and **evolves** earlier notes when new ones arrive. Closest to "stop and do a cycle to update the graph" | README 5-step add flow | github.com/agiresearch/A-mem ★1,174 |
| **Mem0** | LLM extracts facts from messages into vector memory; graph memory links entities across memories (built in on the platform; OSS graph backends not verified here) | docs.mem0.ai graph-memory page | github.com/mem0ai/mem0 ★65,138 |
| **MemOS** | "Memory OS": MemCube abstraction, Neo4j + Qdrant in the docker stack, scheduler | README docker compose line | github.com/MemTensor/MemOS ★11,287 |
| Same category, not individually verified for the specific features | MemoryOS (BAI-LAB, EMNLP 2025), SimpleMem, Honcho, Supermemory, Memobase, LangMem, Nemori | GitHub API existence only | see ledger |

**Document → SQL slot** ("when it sees a birthday or a chart it goes to SQL"):

- **Evaporate** (HazyResearch, VLDB 2024): an LLM generates structured tables from heterogeneous document lakes, synthesising extraction code to cut cost. github.com/HazyResearch/evaporate ★498.
- **DocETL** (★4,086), **LOTUS** (★1,671), **Palimpzest** (★238): LLM semantic operators over documents into tables. Existence verified; feature detail not re-read.
- **LlamaIndex SQLAutoVectorQueryEngine**: "first decides whether to query your structured tables … then" the vector store. The "knows when to pull SQL vs embeddings" router exists as a library component. Source: developers.llamaindex.ai docs page.

**The small-model-specific line** (a small model *trained* to do the memory-routing job, which is the micro-harness idea proper):

- **Memory-R1** (Aug 2025, arXiv 2508.19828): RL trains a memory manager and an answer agent so the model learns "what to store, update, or retrieve" instead of heuristics. No verified repo; cite the paper.
- **Mem-α** (Sep 2025, arXiv 2509.25911): RL trains an agent to manage a complex multi-store memory through interaction and feedback, with a purpose-built dataset. github.com/wangyu-ustc/Mem-alpha ★227.
- **MemoRAG** (arXiv 2409.05591): a "memory model" reads the corpus and produces clues that guide retrieval; a Qwen2-7B memory model checkpoint exists (HF TommyChien/memorag-qwen2-7b-inst). github.com/qhjqhj00/MemoRAG ★2,266.
- **Search-R1** (★5,407): RL trains a small model to decide when to call a search engine. Existence verified; details not re-read.

## Q3. Verdict on "one model that embeds for itself, routes to graph/vector/SQL, refines cyclically, then answers from all of them"

No single repository does all of it. The closest composite is:

- self-embedding: GritLM or LLM2Vec-adapter over one base;
- store ownership and routing: Cognee (stores) or MIRIX (typed routing incl. a structured vault);
- self tool-calling into memory plus a background worker: Letta;
- learned routing in a small model: Mem-α / Memory-R1.

The intersection is unbuilt as far as this survey found. For Databasise the intersection maps onto the machine's own primitives (graph, vector, KV) directly: the harness would be a wiring, the small model a component behind the LLM-client seam, and the "does it beat the frontier model on this slot" question is a rig comparison, which the project already knows how to run.

## Unresolved ledger

- Mem-α base model size and the "generalises to 400k tokens" figure. Abstract read; those specifics were not in the fetched text. **unverifiable here**
- Memory-R1 operation names (ADD/UPDATE/DELETE/NOOP) and training-set size. Same. **unverifiable here**
- Hindsight benchmark scores. Not in fetched text. **unverifiable here**
- Ollama `/api/embed` returning embeddings from a generative model. Not fetched. **no source**
- Mem0 open-source graph backends (Neo4j, Memgraph, Kuzu). Only the platform page was fetched. **non-authoritative for OSS**
- MemoRAG memory-model mechanism (global memory, clue generation). README fetched but the relevant section was not surfaced. **unverifiable here**
- Letta "sleep-time agents" as a current product feature. The docs page now describes "dreaming" over MemFS; whether that is the same mechanism is not stated. **source-vs-prior conflict**
- Quality of untrained pooled embeddings from llama.cpp on a 2B generator. **no source**
- MemoryOS, SimpleMem, Honcho, Supermemory, Memobase, LangMem, Nemori, DocETL, LOTUS, Palimpzest, Search-R1: existence and star counts only. **feature claims not made**
