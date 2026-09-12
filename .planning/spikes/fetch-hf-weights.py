"""Safetensors weights for the round-2 spikes (adapters need trainable weights; GGUF is inference-only).
Stored under .models/hf/<org>__<name>/ (git-ignored). Re-runnable; skips complete downloads."""
import os, sys
from huggingface_hub import snapshot_download
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".models", "hf")
repos = ["openbmb/MiniCPM5-2B", "Qwen/Qwen3-0.6B", "Qwen/Qwen3-Embedding-0.6B", "Qwen/Qwen3-1.7B"]
for r in repos:
    dest = os.path.join(root, r.replace("/", "__"))
    p = snapshot_download(r, local_dir=dest, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.py", "*.jinja", "tokenizer*"])
    print("ok", r, p, flush=True)
print("HF-WEIGHTS-DONE", flush=True)
