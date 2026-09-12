You are building ONE spike for the MelodyScribe project. Read, in this order: `.planning/spikes/MANIFEST.md` (the idea and its requirements), `.planning/spikes/001-score-io-model/SCORE-IO-SPEC.md` and `ops.schema.json` (the shared input/output contract every spike builds against), `reference/micro-harnesses/README.md` for orientation, and your spike's README.md. Then build it. Do not spawn sub-agents. Work only inside your spike folder plus the shared, git-ignored `.planning/spikes/.venv` and `.planning/spikes/.models`.

Environment, already prepared: `.planning/spikes/.venv/bin/python` (3.12) has `llama_cpp` with CUDA, `numpy`, `faiss`, `httpx`, `jsonschema`. Before any Python that imports llama_cpp, run `source .planning/spikes/env.sh` (sets LD_LIBRARY_PATH for the driver, libstdc++, and the pip CUDA runtime, plus `$MELODYSCRIBE_PY` and `$MELODYSCRIBE_MODELS`). Your `run.sh` must source it too. GGUF models are in `.planning/spikes/.models/`. The rig corpus is `databasise/tests/fixtures/corpus/` (MANIFEST.json plus one .txt per document, HotpotQA queries with gold passages); load it with `databasise/parity/corpus.py` or read the files directly. API credentials for a frontier teacher are in `v1/.env.parity` (OpenRouter): `set -a; source v1/.env.parity; set +a` in a shell, never print the values, never write them into any file.

GPU discipline, mandatory: any process that loads a model on the GPU runs under `flock /tmp/melodyscribe-gpu.lock <command>`. Code, labelling through the API, parsing, and analysis run without the lock. Never hold the lock while waiting on the network.

Method, mandatory:
- Depth over speed. Never declare VALIDATED from one happy path. Test edge cases, follow surprises, record each iteration in the README's Investigation Trail.
- Every number in Results comes from a run whose command and raw log are in the folder. Write logs as JSON lines with ISO timestamps.
- Comparison spikes run every arm on identical inputs and report a head-to-head table.
- If a core assumption fails, say so in Results as INVALIDATED or PARTIAL with the evidence; do not soften it.
- Keep code small and plain: one `run.sh` that reproduces everything, standard library where possible, no frameworks, no Docker, no config systems.
- Finish the README: frontmatter verdict set to VALIDATED, INVALIDATED, or PARTIAL; Research, How to Run, What to Expect, Investigation Trail, Results all filled with what actually happened.

When finished, reply with one line: SPIKE DONE <number> verdict=<VALIDATED|INVALIDATED|PARTIAL>.

Round 2 additions: what earlier spikes settled is in `.claude/skills/spike-findings-melodyscribe/` (read `SKILL.md` and the reference your README names before building; do not re-measure settled results). A second venv `.planning/spikes/.venv-train/bin/python` has PyTorch with CUDA, transformers, peft, accelerate, sentence-transformers, safetensors, datasets, and mergekit if `.planning/spikes/.logs/setup-train.out` says so; safetensors weights are under `.planning/spikes/.models/hf/<org>__<name>/`. Teacher-generated queries with a fixed train/test split are in `.planning/spikes/shared/queries-v1.json`; never train on `test` documents. The v0.2 quote-evidence schema and grammar live in `.planning/spikes/003-op-emission-size-sweep/` (`ops.v0.2.schema.json`, `v02_grammar.py`, `resolve.py`); import them read-only.

YOUR SPIKE:
