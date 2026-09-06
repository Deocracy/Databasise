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
| D-08 | Keyword-extraction model: same `qwen/qwen3.7-flash` — no separate binding is configured; D-07/D-08 pin the same model for both roles, so LightRAG's single `llm_model_func` already satisfies this |
| D-09 (**AMENDED** — see `.planning/phases/03-lightrag-query-side/03-D09-AMENDMENT.md`) | Embedder: `qwen/qwen3-embedding-8b` via OpenRouter's embeddings endpoint (`https://openrouter.ai/api/v1/embeddings`), **not** a local Ollama endpoint as the original D-09 said. Verified live 2026-08-31: a real embeddings call against this model and endpoint returns a 4096-dimension vector. No provider pin: the amendment does not require one, v1's `openai_embed()` wrapper has no `extra_body` plumbing to carry one, and D-01 makes it moot — vectors are computed exactly once and never recomputed |
| D-09 (unchanged half) | Rerank: disabled (`RERANK_BINDING=null`) |
| D-05 | Storage: `CozoGraphStorage` (graph) + `FaissVectorDBStorage` (vector) — Phase 1's frozen store family, never v1's `NetworkXStorage`/`NanoVectorDBStorage` quick-start defaults |

Load it into a run with:

```bash
cd v1 && set -a && . .env.parity && set +a
```

**JSON-valued variables must be single-quoted.** `OPENAI_LLM_EXTRA_BODY` carries a JSON object
(`'{"provider":{"order":["Alibaba"],"allow_fallbacks":false}}'`). `set -a && . .env.parity`
sources this file through bash, and bash's quote-removal on an *unquoted* assignment strips the
value's inner double quotes before the process ever sees it — the resulting string
(`{provider:{order:[Alibaba],allow_fallbacks:false}}`) is not valid JSON, and every extraction
call that reads it raises `JSONDecodeError` (03-11-PLAN.md's root-cause finding). Wrapping the
value in single quotes, as shown above, makes the inner double quotes survive sourcing intact.
Any other JSON-valued line added to this file later needs the same single-quoting.

**This pinned v1 also carries the same coercion fix at two sites in `lightrag/operate.py`:**
every `BaseGraphStorage` backend's `get_edge()` returns attribute values as strings, so an
existing edge's `weight` arrived as `"1.0"` and crashed on `float + str` the first time an
entity was mentioned in 2+ documents; both `_merge_edges_then_upsert` and the cache-rebuild path
`_rebuild_single_relationship` read the identical shape from the identical `get_edge()` source,
so both wrap the read in `float(...)`. Recorded here so the original-arm identity stays honest —
this is a bug fix to the pinned baseline, not a behavior change to what it measures (03-11-PLAN.md
finding; second site closed in the phase-03 review-fix cycle).

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

Ingest command (see `v1/scripts/run_parity_ingest.py`, written for Task 2). This script lives
under `v1/`, not `databasise/`, because it necessarily imports v1's own `lightrag` package to
drive the ingest — `databasise/tools/check_import_boundary.py` forbids that import anywhere
under `databasise/` (D-14), so the importer/verifier that later reads the resulting index lives
in `databasise/parity/import_index.py` (Task 3) instead, reading v1's on-disk files directly and
never importing v1's Python:

```bash
cd v1 && set -a && . .env.parity && set +a && uv run python scripts/run_parity_ingest.py
```
