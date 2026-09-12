# MelodyScribe sources

Code and papers behind the MelodyScribe research. Layout rule: a project that has code gets its own subfolder holding the code **and** the paper(s) about that code. A paper with no code sits directly in this folder.

- `<name>/code/` — a shallow git clone. **On disk, not committed** (root `.gitignore`), following this repo's precedent of keeping the HippoRAG reference clone out of git. `manifest.tsv` pins the commit each clone was at; `./sync.sh` re-creates every clone and re-downloads every paper.
- `<name>/<arxiv-id>_<title>.pdf` — the paper(s) for that code, committed.
- `<name>/<date>_*.md` — dated verbatim snapshots of model cards and READMEs, committed.
- `<arxiv-id>_<title>.pdf` at this level — papers with no code.
- `manifest.tsv` — one row per clone and per paper: name, kind, url or arXiv id, commit or title as fetched from arXiv, date.

To add a source: append a line to the list inside `sync.sh` (`name|repo-url-or--|arxiv-ids-or--`), run `./sync.sh`, commit the PDFs and `manifest.tsv`.

## Why each source is here

| Folder | Code | Paper(s) | What MelodyScribe takes from it |
|---|---|---|---|
| `minicpm/` | OpenBMB/MiniCPM | MiniCPM4 tech report; UltraData tiered data; InfLLM-V2 | The candidate base model and its fine-tune cookbooks and Agent Skills. Snapshots of the 5-2B model card, README, TRL cookbook |
| `gritlm/` | ContextualAI/gritlm | GRIT | One set of weights for embedding and generation; document and query KV caching for RAG |
| `llm2vec/` | McGill-NLP/llm2vec | LLM2Vec | Turning a decoder into an encoder with adapters; the recipe if a joint head is not enough |
| `qwen3-embedding/` | QwenLM/Qwen3-Embedding | Qwen3 Embedding report | The causal last-token embedding recipe; the dedicated-embedder baseline for the rig |
| `llama-cpp/` | ggml-org/llama.cpp | none | The runtime: one decode yields logits and embeddings; per-sequence KV copy, shift, save; grammar sampling; server prompt cache |
| `prompt-cache/` | yale-sys/prompt-cache | Prompt Cache | Reusable KV "modules" placed anywhere in a prompt; the isolation form of middle-of-context caching |
| `cacheblend/` | LMCache/LMCache | CacheBlend | Partial recompute to repair cross-attention when composing cached chunks |
| `mem-alpha/` | wangyu-ustc/Mem-alpha | Mem-α | A small model trained by RL to construct multi-store memory; the routing fine-tune precedent |
| `a-mem/` | agiresearch/A-mem | A-MEM | Note linking and memory evolution; the revise pass precedent |
| `memorag/` | qhjqhj00/MemoRAG | MemoRAG | A small memory model that reads the corpus and emits retrieval clues |
| `self-rag/` | AkariAsai/self-rag | Self-RAG | One model deciding when to retrieve and critiquing itself via reflection tokens |
| `dense-x-retrieval/` | chentong0/factoid-wiki | Dense X Retrieval | A small model in front of the embedder (propositionizer); the `embed="rewrite:propositions"` directive |
| `knn-lm/` | urvashik/knnlm | kNN-LM | A model retrieving from its own representation space, no training |
| `mirix/` | Mirix-AI/MIRIX | MIRIX | Six typed memory stores with a manager per store; the structured Knowledge Vault |
| `hindsight/` | vectorize-io/hindsight | Hindsight | Retain / recall / reflect; mental models as learnings for the frontier model |
| `letta/` | letta-ai/letta | MemGPT | The agent tool-calling into its own memory tiers |
| `sleep-time-compute/` | letta-ai/sleep-time-compute | Sleep-time Compute | A background agent working on memory while the main agent idles |
| `voyager/` | MineDojo/Voyager | Voyager | An LLM-written skill library retrieved by embedding; the Folios precedent |
| `evaporate/` | HazyResearch/evaporate | Evaporate | Documents to structured tables with synthesised extraction code; the SQL target |
| `graphiti/` | getzep/graphiti | Zep | Conversation episodes to a temporal knowledge graph; the small-model structured-output warning |
| `cognee/` | topoteretes/cognee | none | Graph, vector, and relational memory in one layer on one Postgres |
| `mem0/` | mem0ai/mem0 | Mem0 | Fact extraction from conversation into vector plus graph memory |
| `memori/` | GibsonAI/memori | none | Capturing agent execution (tool calls, outcomes) after each turn |
| `memos/` | MemTensor/MemOS | MemOS | Memory as an OS resource: plaintext, activation (KV), parametric |
| `search-r1/` | PeterGriffinJin/Search-R1 | Search-R1 | RL-training a small model to decide when to search |
| (this folder) | none | Memory-R1 | RL-trained memory manager with learned store/update/retrieve; no verified code release |

Already elsewhere in this repo, not duplicated here: HippoRAG 2 paper at `reference/hipporag2-2502.14802.pdf`; LightRAG code under `v1/`; the system model under `docs/system-model/`.

## Not fetched, by choice

Anthropic Contextual Retrieval (blog post, no code, no paper): cited by URL in `../prior-art-survey.md`. Correlated Errors in LLMs and CAPA (the ensembling-quality papers from the dissertation memo): outside MelodyScribe's scope; pointers live in `../README.md`.
