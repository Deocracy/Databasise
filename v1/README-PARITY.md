# v1 Parity Arm — README

This directory (`v1/`) is stock, pre-decomposition LightRAG. In Phase 3's parity comparison it is
**the original arm**: the pre-decomposition baseline that `databasise/`'s decomposed query side is
compared against. This environment exists solely for that comparison and is never imported into
`databasise/` (Phase 1 D-14, D-04) — `databasise/tools/check_import_boundary.py` enforces that at
the AST level.

## Recreating the environment

```bash
cd v1
uv venv --python 3.12       # writes .venv/, matches the pinned .python-version
uv sync                      # base deps: pycozo[embedded]==0.7.6, faiss-cpu (D-05's store family)
uv sync --extra api          # adds the openai client + FastAPI stack (not required to run ingest,
                              # kept in sync with the base image's api extra for parity with prod)
```

Resolved interpreter: **Python 3.12.13** (pinned via `v1/.python-version`, matching
`databasise/.python-version` so both arms build on the same interpreter family).

Confirm the venv actually holds the packages (do not assume `uv sync` succeeded silently):

```bash
cd v1 && uv run python -c "import lightrag, pycozo, faiss; print('v1 arm runnable')"
```

## Pinned run configuration (`.env.parity`)

`v1/.env.parity` (gitignored — holds a live OpenRouter API key) carries the exact run
configuration; `v1/.env.parity.example` is its tracked, secret-free twin with every variable name
and every non-secret value filled in.

| Decision | Setting |
|---|---|
| D-06 | Corpus: HotpotQA distractor setting (`databasise/tests/fixtures/corpus/`) |
| D-07 | Generator: `qwen/qwen3.7-flash` via OpenRouter (`https://openrouter.ai/api/v1`), provider pinned to `Alibaba` (`allow_fallbacks: false`) — verified live 2026-08-31: this model has exactly one upstream provider on OpenRouter today, so the pin is a no-op in effect but still asserted, per D-07's own stated rationale ("a re-routed provider changes identity mid-run") |
| D-08 | Keyword-extraction model: same `qwen/qwen3.7-flash`, same provider pin |
| D-09 (**AMENDED** — see `.planning/phases/03-lightrag-query-side/03-D09-AMENDMENT.md`) | Embedder: `qwen/qwen3-embedding-8b` via OpenRouter's embeddings endpoint (`https://openrouter.ai/api/v1/embeddings`), **not** a local Ollama endpoint as the original D-09 said. Verified live 2026-08-31: a real embeddings call against this model and endpoint returns a 4096-dimension vector. Provider pinned to `DeepInfra` (cheapest of three live providers at pin time) for reproducibility, though the amendment text does not itself require pinning the embedder |
| D-09 (unchanged half) | Rerank: disabled (`RERANK_BINDING=null`) |
| D-05 | Storage: `CozoGraphStorage` (graph) + `FaissVectorDBStorage` (vector) — Phase 1's frozen store family, never v1's `NetworkXStorage`/`NanoVectorDBStorage` quick-start defaults |

Load it into a run with:

```bash
cd v1 && set -a && . .env.parity && set +a
```

## Ingest run record (Task 2)

The one-time v1 ingest run over the fixed corpus snapshot (`databasise/tests/fixtures/corpus/`)
writes its native Cozo graph, Faiss index + `.index.meta.json` sidecar, and JSON KV state into:

```
v1/.parity_working_dir/
```

(gitignored — a build artifact; its identity is carried by the corpus manifest hashes and the
Task 3 import verification, not by committing binaries). See
`databasise/parity/corpus.py` for the loader and `databasise/parity/import_index.py` for the
verified import into the v2 namespace layout.

**This ingest is run exactly once.** Every parity number recorded in plans 03-07 and 03-09 is keyed
to this one build; re-running it means re-running the whole comparison, not editing a config value
(D-01, rated costly).

Ingest command (see `databasise/parity/run_v1_ingest.py`, written for Task 2):

```bash
cd v1 && set -a && . .env.parity && set +a && uv run python ../databasise/parity/run_v1_ingest.py
```
