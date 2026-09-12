# MelodyScribe: where PyTorch lives, and where it does not

Date: 2026-09-11. Answers the owner's question "we will have to use PyTorch; how is it intertwined with the micro-harness?" Verified facts carry a source; the rest is owner analysis.

## The one-line answer

PyTorch is a **build-time** dependency of the model artifact and never a **run-time** dependency of MelodyScribe. The runtime talks to a served model over HTTP. The two worlds meet at a file (a GGUF plus adapter) and a registry entry (`model_id`, `revision` inside the `EmbeddingSpace` hash, CONTRACT §4).

This is not a preference; the contract forces it. CONTRACT §8 condition 3 admits a node only with its network namespace denied and the machine acting as the injected LLM provider. A model running inside the node would make MelodyScribe `unbudgetable`. So the model is a `core` client the machine serves, and the node code is plain Python with no tensor library (see `system-model-fit.md` §3). The Databasise venv has no torch today (checked 2026-09-11) and should stay that way.

## The three environments

| Environment | Contains PyTorch | What runs there | Talks to the others via |
|---|---|---|---|
| **Databasise process** (MelodyScribe nodes, stores, seam) | No | `melodyscribe/transcriber`, `/filer`, `/reviser`, `/recaller`; Cozo, Faiss, SQLite | HTTP to the model server |
| **Model server** (the Scriptorium in deployment terms) | No with Ollama or llama.cpp; yes inside the process with SGLang or vLLM, still outside Databasise | `MelodyScribe-2B-v{n}` serving generation and embedding roles | OpenAI-compatible endpoints; the machine injects the URL |
| **Training rig** (offline, separate venv or devshell) | Yes | LLM2Vec-style embed adapter; LoRA SFT per the MiniCPM TRL cookbook; later distillation | Emits adapter weights, converted to GGUF, registered as a new model revision |

## Serving on legion (checked 2026-09-11)

Hardware: NVIDIA RTX 3080 Laptop, 16 GB VRAM, driver 595.71; 62 GB RAM. Neither Ollama nor llama.cpp is installed yet; `services.ollama` is not enabled.

| Fact | Source |
|---|---|
| nixpkgs unstable: `ollama` 0.20.3, attribute `ollama-cuda` for NVIDIA; module options `services.ollama.enable`, `.package`, `.loadModels`, `.models`, `.host`, `.port`, `.environmentVariables` | nixos MCP |
| nixpkgs unstable: `llama-cpp` build 8667; `python313Packages.llama-cpp-python` 0.3.16 | nixos MCP |
| Ollama serves `/api/embed` and `/api/chat` from one loaded model | ollama docs/api.md |
| llama-server: multiple GGUF LoRA adapters loaded at start, per-request `lora: [{id, scale}]` field, `GET/POST /lora-adapters`; `--lora-init-without-apply` | llama.cpp tools/server/README.md |
| llama-server `--embeddings` "restricts to only support embedding use case; use only with dedicated embedding models" | same |
| llama.cpp C API has `llama_set_embeddings()` and `llama_set_causal_attn()` (llama.h lines 1007 and 1011): one loaded model can switch between causal generation and non-causal embedding at runtime, in C, no PyTorch | llama.h |
| VRAM budget: 2.5B parameters is about 5 GB at bf16, about 2.7 GB at Q8, plus KV cache; 16 GB leaves room for the adapter and long contexts | arithmetic |

Recommended serving path: **Ollama with `ollama-cuda`** (`services.ollama.package = pkgs.ollama-cuda;` avoids the global `nixpkgs.config.cudaSupport` flag that `configuration.nix` line 549 already warns triggers from-source rebuilds). Ollama is already the local provider in the v1 stack, so the machine's LLM client needs no new code. Move to llama-server only when per-request adapter switching is needed, and to SGLang only for native tool-call parsing or DSpark speculative decoding.

## The one point where training and serving constrain each other

The embedding adapter's attention mode decides which server can serve it:

- **Causal attention + last-token pooling** (the Qwen3-Embedding and e5-mistral recipe): any llama.cpp-based server serves it as-is, including Ollama. Simplest path.
- **Bidirectional attention** (the LLM2Vec and GritLM recipe): llama-server's HTTP path has no per-request causal toggle. The C API does (`llama_set_causal_attn`), reachable from `llama-cpp-python`, so a small custom embed endpoint is needed. Still no PyTorch.

Decision for the first spike: train the **causal + last-token** variant first, because it is servable with zero custom code; move to bidirectional only if retrieval parity fails.

## Training on legion, sized honestly

- **LoRA SFT** (r=16 on all projection layers, bf16, gradient checkpointing, batch 4 × 2048 tokens, per the MiniCPM TRL cookbook): fits a 16 GB card. The cookbook's own log shows a 200-sample single-GPU run converging.
- **Embed adapter** (masked next-token prediction then contrastive): same footprint class as LoRA SFT.
- **Full fine-tune of 2.5B**: optimizer state alone exceeds 16 GB. Not on this box.
- **On-policy distillation as MiniCPM did it** needs full-vocabulary teacher logits at every position, which a frontier API does not expose and a local open teacher would need VRAM this box lacks alongside the student. On legion the distillation path is **sequence-level (hard) distillation**: the frontier teacher writes labelled outputs for our schema, and the student is trained on them with LoRA SFT. That produces `MelodyScribe-2B-v0.1`. This corrects `feasibility.md`, which said "OPD-style"; the OPD idea survives as "teacher on our schema, distilled into the 2B", the mechanism is SFT on teacher outputs.

nixpkgs unstable has `python313Packages.torch` 2.11.0, `peft` 0.18.1, `trl` 0.24.0 (nixos MCP). CUDA-enabled builds of those depend on the global `cudaSupport` flag, which is the from-source rebuild `configuration.nix` line 549 warns about. Two ways to avoid it, to be decided when the spike is scheduled: a `uv` venv with PyPI CUDA wheels in the training directory (needs the NVIDIA driver library visible, the usual `nix-ld` arrangement on NixOS), or a cachix-backed CUDA build. Neither touches the Databasise venv.

## What crosses the boundary

1. Training rig emits `adapter.safetensors` (and optionally a merged checkpoint).
2. `convert_lora_to_gguf.py` (llama.cpp) produces `melodyscribe-2b-v0.1-embed.gguf`; the base stays `MiniCPM5-2B` GGUF from the vendor.
3. Ollama Modelfile (or llama-server `--lora`) loads base plus adapter under the model name `melodyscribe-2b-v0.1`.
4. Databasise registers `core/embedder-melodyscribe-2b@0.1.0` with `model_id`/`revision` in its `EmbeddingSpace` (CONTRACT §4) and `core/llm-minicpm5-2b@…` for generation. From here on, the machine sees two clients and a URL. PyTorch is gone.

## Ledger

- llama-server serving `/v1/embeddings` for a generative model **without** `--embeddings`: the README fetched says the flag restricts to embedding-only; whether the embedding endpoint also works in the default mode was not verified. **unverifiable here**. Ollama does both, which is why it is the recommendation.
- llama.cpp's `examples/gritlm` (the worked GritLM demo) returned 404 at that path on 2026-09-11; the C API entry points exist regardless. **moved or removed, not checked further**
- Ollama Modelfile `ADAPTER` directive for GGUF LoRA: from memory, not fetched. **unverifiable here**
- Binary-cache status of `ollama-cuda` for the channel's 0.20.3 build: the cache probe answered for a different version. **unverifiable here**
- `torchWithCuda` as a nixpkgs attribute that avoids the global flag: not checked. **unverifiable here**
