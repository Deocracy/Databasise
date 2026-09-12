# Spike Conventions

Patterns and stack choices established across spike sessions. New spikes follow these unless the question requires otherwise.

## Stack
- Python 3.12 in one shared venv at `.planning/spikes/.venv` (git-ignored), built by `setup-env.sh`: `llama-cpp-python` from the prebuilt CUDA wheel index plus NVIDIA's pip `cuda-runtime` and `cublas` packages, `numpy`, `faiss-cpu`, `httpx`, `jsonschema`. No PyTorch in the spike venv; training-side experiments use numpy on cached states or a separate training venv.
- `source .planning/spikes/env.sh` before any Python that imports `llama_cpp`. It sets the library path (driver `libcuda`, nix-ld `libstdc++`, pip CUDA runtime) and exports `$MELODYSCRIBE_PY` and `$MELODYSCRIBE_MODELS`. No NixOS change is needed for GPU work.
- Models are GGUF under `.planning/spikes/.models` (git-ignored), fetched by `fetch-models.py`; Q8 everywhere it fits so quantisation stays out of size comparisons.
- Demos are a single static HTML file with inline JavaScript, checked with `node --check` and a stdlib DOM stub; no bundlers, no frameworks.

## Structure
- One folder per spike, `NNN-name/`, holding `README.md` (frontmatter verdict), `run.sh` that reproduces everything from scratch, the code, `logs/` (JSON lines with ISO timestamps, one file per run), and `results/` (tables and reports). Vector dumps over about 3 MB stay on disk under a per-spike `.gitignore`.
- The shared input/output contract lives in `001-score-io-model/SCORE-IO-SPEC.md` and `ops.schema.json`; every later spike imports the compiler and the Proof validator from 001 rather than re-implementing them.
- The rig corpus is `databasise/tests/fixtures/corpus/` (hash-verified, 20 documents, HotpotQA queries with gold passages). Sections for experiments are real paragraphs from it, never synthetic text.

## Patterns
- Every model load runs under `flock /tmp/melodyscribe-gpu.lock`; one model per process; code, API labelling, and analysis run without the lock. Throughput numbers are only reported from lock-held runs.
- Greedy decoding and identical token inputs across arms of a comparison; medians of three repetitions for timings; text equality against a full-prefill reference for quality.
- Every number in a README traces to a log line produced by `run.sh`. Verdicts are VALIDATED, INVALIDATED, or PARTIAL, with sub-claims marked individually; against-interest results are stated as such.
- Token policy per model is recorded as a string (`emb=reserved:130080;rq=reserved:130081` for MiniCPM5-2B) and enters the embedding-space identity. Never prepend BOS for MiniCPM5 tokenisers; tokenise prefix and section as one string; `llama_get_embeddings_ith` indexes the i-th output, not the position.
- Reject empty sections before embedding and enforce context limits chunker-side; both llama.cpp paths truncate silently past `n_ctx`.
- Muse Spark agents build spikes from `SPIKE-AGENT-PROMPT.md` through `run-spike.sh`, with the session id captured for nudged retries; the owner-side re-run of `run.sh` is the acceptance step before a verdict enters the manifest.
- Evidence in an op is a verbatim quote (3 to 256 characters) that the harness resolves to character offsets by first occurrence after Proof's own normalisation; neither frontier nor small models can count character offsets (spike 003, spec v0.2 candidate). Proof's span check then runs unchanged on the resolved offsets.
- Frontier teacher labelling: disable reasoning explicitly (`"reasoning": {"effort": "none", "exclude": true}` merged with, not replacing, `OPENAI_LLM_EXTRA_BODY`), `max_tokens` at least 4096, temperature 0. Repair loops keep passing ops byte-identical in the prompt and accept the best round's passing set; a repair reply otherwise rewrites ops that already passed.
- Size comparisons decode by raw completion with identical prompt bytes across arms (no per-model chat template), which also disables Qwen3 thinking by construction; every output is scanned for think tags and the count is reported.
- The grammar guarantees shape, only the token cap guarantees termination (a 2B arm looped one op about 66 times until the cap): every decode step carries an I4 cap and truncation is reported as its own Proof category.
- Head-to-head accuracy across sizes uses `routing_exact` (the set of target stores per section) as the alias-free comparator; string-match recall and F1 against teacher ops are strict lower bounds until a normaliser exists.

## Tools & Libraries
- `llama-cpp-python` 0.3.35 (CUDA wheel index cu125), `nvidia-cuda-runtime-cu12` 12.5.82, `nvidia-cublas-cu12` 12.5.3.2: worked on legion (RTX 3080 Laptop, driver 595).
- `faiss-cpu` for recall evaluation; `jsonschema` for op validation; GBNF grammars generated from the JSON schema for constrained decoding.
- Avoid: `--embeddings` mode on llama-server for a generative model (it is embedding-only); `arxiv.org/search` HTML pages for agents (rate limits and 400s; use the export API or abs pages).
- Teacher labelling goes through the OpenAI-compatible endpoint configured in `v1/.env.parity`, sourced at runtime (`set -a; source v1/.env.parity; set +a`); credentials are never printed, logged, or written.
