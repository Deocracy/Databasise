# MiniCPM5-2B — research notes

Snapshot date: 2026-09-11. Sources are the two primary pages the owner supplied, saved verbatim in `sources/`:

- Model card: https://huggingface.co/openbmb/MiniCPM5-2B (`sources/minicpm/2026-09-11_hf_openbmb_MiniCPM5-2B_model-card.md`)
- Repo README: https://github.com/OpenBMB/MiniCPM (`sources/minicpm/2026-09-11_gh_OpenBMB_MiniCPM_README.md`)
- TRL fine-tune cookbook: https://github.com/OpenBMB/MiniCPM/blob/main/docs/finetune/trl.md (`sources/minicpm/2026-09-11_gh_OpenBMB_MiniCPM_docs_finetune_trl.md`)

Every fact below is tagged with where it came from. Facts labelled **[owner analysis]** are our inference, not a source claim.

## 1. Identity

| Field | Value | Source |
|---|---|---|
| Publisher | OpenBMB (Modelbest Inc., THUNLP, RUC Gaoling School of AI) | repo README §Institutions |
| Released | 2026-09-07 (MiniCPM5-1B: 2026-05-19) | repo README §Changelog |
| License | Apache-2.0, weights and code | model card + repo LICENSE |
| Architecture | Standard `LlamaForCausalLM`, no custom kernels, no model-code fork | model card §Model Information |
| Parameters | 2,516,756,480 total; 1,981,982,720 non-embedding | model card |
| Layers / heads | 42 layers; GQA 16 query heads, 2 KV heads | model card |
| Context | 131,072 tokens | model card |
| Modes | Hybrid: `enable_thinking=True/False` in the chat template | model card §Quickstart |
| Tool calling | Emits XML-style tool calls; SGLang `--tool-call-parser minicpm5` converts to OpenAI `tool_calls` | model card §Tool Calling |
| Languages | en, zh | model card frontmatter |
| Repo health | 10,853 stars, 737 forks, last push 2026-09-10 | GitHub API 2026-09-11 |

Sampling recommended by the card: `temperature=1.0, top_p=0.95`. (The 1B card lists think `T=0.9` / no-think `T=0.7`, both `top_p=0.95`.)

### Checkpoints and formats (model card §Model List)

MiniCPM5-2B, -Base (pre-training only), -Midtrain (before SFT), -SFT (before RL/OPD), -GGUF (llama.cpp / Ollama / LM Studio), -MLX (4-bit Apple Silicon), -GPTQ (4-bit), -DSpark (speculative-decoding draft model), -DSpark-GGUF, -LiteRT (on-device runtime). Same set exists for MiniCPM5-1B.

The Base / Midtrain / SFT checkpoints matter for us: they are the starting points for our own post-training rather than stacking on top of the RL+OPD release.

## 2. Benchmarks (model card, vendor-reported)

Caveats first. These numbers are reported by the vendor. Rows marked † are from Artificial Analysis; all others were reproduced internally by OpenBMB. Comparators are 2B-class and 4B-class open models only. **No frontier model appears in this table**, so the card neither supports nor refutes the "small model matches frontier" hypothesis. Per this project's evidence standard, no benchmark number settles a decision here; the rig does.

| Benchmark | MiniCPM5-2B | LFM2.5-2.6B | Qwen3.5-2B | Gemma-4-E2B-it | Qwen3.5-4B | granite-4.2-3B | Nemotron-3-Nano-4B | Gemma-4-E4B-it | LFM2.5-8B-A1B |
|---|---|---|---|---|---|---|---|---|---|
| Average | 53.9 | 33.2 | 28.0 | 24.6 | 51.1 | 42.7 | 32.6 | 31.2 | 28.4 |
| LiveCodeBench v6 | 69.1 | 42.1 | 20.2 | 42.9 | 56.4 | 58.9 | 50.7 | 53.9 | 39.8 |
| SWE-bench Verified | 46.4 | 6.0 | 5.0 | 2.0 | 33.6 | 36.8 | 3.0 | 15.0 | 0.4 |
| AIME 2025 | 86.5 | 41.9 | 29.6 | 31.7 | 78.8 | 79.4 | 56.3 | 37.1 | 46.0 |
| MATH-500 | 94.6 | 89.6 | 85.8 | 85.4 | 99.0 | 97.0 | 91.6 | 88.2 | 93.2 |
| IFEval | 86.7 | 93.4 | 77.5 | 31.4 | 90.2 | 93.7 | 88.0 | 44.4 | 90.8 |
| IFBench | 66.3 | 59.0 | 46.0 | 25.7 | 59.0 | 73.0 | 58.3 | 28.3 | 51.0 |
| Multi-IF | 71.8 | 76.8 | 57.1 | 40.3 | 73.6 | 75.9 | 65.9 | 45.9 | 71.4 |
| MMLU-Pro | 70.8 | 65.2 | 64.3 | 56.0 | 78.0 | 65.8 | 65.7 | 68.3 | 63.1 |
| MMLU-Redux | 84.7 | 80.0 | 80.0 | 71.8 | 88.7 | 78.9 | 79.8 | 83.7 | 80.0 |
| GPQA-Diamond † | 70.2 | 55.8 | 45.6 | 43.3 | 77.1 | 55.9 | 51.3 | 57.6 | 51.3 |
| NoLiMa (long ctx) | 68.1 | 0.7 | 17.1 | 3.9 | 43.5 | 5.1 | 1.1 | 2.3 | 0.5 |
| LongBench v2 | 43.7 | 30.3 | 24.9 | 33.2 | 47.3 | 36.0 | 32.0 | 42.7 | 30.4 |
| AA-LCR † | 59.0 | 5.3 | 28.7 | 17.0 | 61.0 | 24.3 | 17.3 | 33.0 | 0.0 |
| BFCL v4 (tool use) | 66.6 | 61.1 | 43.6 | 36.6 | 56.8 | 52.2 | 43.7 | 47.0 | 49.2 |
| τ²-Bench Telecom | 97.1 | 90.4 | 69.0† | 20.8† | 92.1† | 40.9 | 28.1† | 20.8† | 16.1† |
| τ³-Bench Banking † | 20.8 | 7.2 | 2.1 | 3.9 | 6.8 | 5.6 | 1.2 | 4.1 | 3.4 |
| GAIA Text-103 | 88.7 | 49.5 | 47.9 | 30.1 | 78.6 | 57.3 | 26.5 | 39.5 | 41.1 |
| BrowseComp Top100 | 39.7 | 13.7 | 19.3 | 6.0 | 33.3 | 19.0 | 4.7 | 6.3 | 9.7 |
| Terminal-Bench v2.1 † | 8.6 | 4.5 | 3.0 | 0.4 | 25.8 | 13.9 | 3.8 | 1.9 | 1.9 |

Full table (37 rows incl. HLE, SuperGPQA, OJBench, SciCode, LCB-Pro, LongBenchPro, SWE-bench Pro, BrowseComp-ZH, GDPval, Claw-Gym, WildClaw, QwenClaw) is in the model-card snapshot.

**[owner analysis]** The rows that matter for a micro-harness are the narrow, verifiable ones: instruction following (IFEval 86.7), tool-call formatting (BFCL v4 66.6), long-context needle work (NoLiMa 68.1, where every other 2B model collapses), and structured multi-step agent loops (τ²-Bench Telecom 97.1). Those are the skills a harnessed extraction, routing, or schema-emission node needs. Open-ended knowledge (MMLU-Pro 70.8, HLE 8.9) is where a 2B model will not match a frontier model and where a harness should not put it.

## 3. Training recipe (model card §Training Recipe)

Three stages under **UltraData Tiered Data Management** (arXiv 2602.09003):

1. **Base training** — stable + decay phases. Corpus released: Ultra-FineWeb, Ultra-FineWeb-L3, UltraX, UltraData-Code, UltraData-Math.
2. **Mid-training** — strengthens target capabilities, adapts to the target distribution.
3. **Post-training** — SFT → RL → OPD.
   - SFT: 400B tokens of deep-thinking SFT. Data released as UltraData-SFT-2605 and UltraData-SFT-Agent-2609 (500K agent samples).
   - RL: critic-based algorithm from JustRL II (https://panhaoxuan.notion.site/justrl-ii-scaling-small-llms-to-128k-reasoning-with-a-critic). Specialised RL teachers per domain: math, code, agentic, writing. Data released as UltraData-RL-2609 (80K+ samples).
   - **OPD (On-Policy Distillation)**: merges 16 RL expert models (5 agentic) into one release model. At each response position the full-vocabulary reverse KL between student and teacher logits is the advantage estimate, replacing verification-based advantage. Reuses each RL teacher's prompts as distillation data, so no new corpus is built.
   - Reported gain from RL+OPD: +10.96 points reasoning/general, +6.96 points agentic (vendor-reported).

**[owner analysis]** OPD is the directly reusable idea for "fine-tune a model for a harness": train (or borrow) a task-specific teacher, then distill on-policy into the small model using only the teacher's own prompts. The open SFT/RL datasets mean a Databasise-specific expert (entity extraction, keyword extraction, query routing) can be added to the same pipeline rather than built from zero.

## 4. Deployment (model card §Quickstart, §Cookbooks)

| Backend | Requirement | Note |
|---|---|---|
| Transformers | `transformers>=5.6` | BF16/FP16, GPU + CPU |
| vLLM | `vllm>=0.21`; `vllm serve openbmb/MiniCPM5-2B` | OpenAI-compatible server |
| SGLang | `sglang[srt]>=0.5.16` | Recommended for tool calling; DSpark speculative decoding (`--speculative-algorithm DSPARK --speculative-dspark-block-size 7`) |
| llama.cpp / Ollama / LM Studio | GGUF checkpoint | CPU/GPU local |
| MLX | 4-bit | Apple Silicon |
| LiteRT | `.litertlm` | Android / iOS / IoT |
| ArcLight, FlagOS | — | Multi-chip; FlagOS adapted it to 9 AI chips |

**[owner analysis]** Every backend above exposes an OpenAI-compatible chat endpoint. Databasise's LLM client seam already targets that shape (v1 talks to OpenRouter and Ollama the same way), so a local MiniCPM5-2B is a config change at the client node, not a code change. On legion, Ollama + GGUF is the zero-friction path; SGLang is the path if we need native tool-call parsing or DSpark speed.

## 5. Fine-tuning

The repo ships one-page cookbooks plus Claude Code / Cursor **Agent Skills** (repo `skills/`, 18 skills): `minicpm5-deploy` (+ per-backend: transformers, vllm, vllm-ascend, sglang, llama-cpp, ollama, lmstudio, mlx, litert, arclight) and `minicpm5-finetune` (+ trl, llamafactory, ms-swift, unsloth, xtuner, gguf-lora). These can be installed into `.claude/skills/` when we start a fine-tune.

TRL + PEFT reference recipe (cookbook `docs/finetune/trl.md`, snapshot in `sources/`):

```python
LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
           target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])
SFTConfig(num_train_epochs=2, per_device_train_batch_size=4, gradient_accumulation_steps=4,
          learning_rate=2e-4, bf16=True, max_length=2048)
# gradient checkpointing on; needs trl>=0.21 for max_length
```

Cookbook claim: a 200-sample, 1-epoch tiny LoRA on a single GPU converges cleanly (loss 4.07 → 3.52 over one epoch in their log). Dataset shape is plain `{"messages": [...]}` chat rows.

## 6. Related papers and datasets

- MiniCPM4 tech report — arXiv 2506.07900 (the citation the card asks for)
- InfLLM-V2 trainable sparse attention — arXiv 2509.24663 (used in MiniCPM4.1 and SALA, not in the 5-series dense models)
- UltraData tiered data management — arXiv 2602.09003
- HyPE hybrid positional encoding — arXiv 2601.22156 (MiniCPM-SALA, 1M-token context)
- JustRL II critic-based RL for small LLMs — notion page linked above
- Datasets on HF under `openbmb/`: Ultra-FineWeb, Ultra-FineWeb-L3, UltraX-Preview, UltraData-Code, UltraData-Math, UltraData-SFT-2605, UltraData-SFT-Agent-2609, UltraData-RL-2609

## 7. Open questions this snapshot does not answer

- No frontier comparator in the card. The owner's "small ≈ frontier" finding has to be established per task on our rig.
- No latency or tokens/second figures for the 2B model in the card (SALA and 4.1 have speed charts; 5-series does not).
- No published eval of the GPTQ / GGUF quantised checkpoints versus BF16.
- Thinking-mode token cost per call is not reported; for a high-volume harness node, no-think mode is the likely default and its quality delta is unmeasured.
