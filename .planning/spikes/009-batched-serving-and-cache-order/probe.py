"""Probe 009-0: single-request timings to size the sweep (GPU, under flock)."""
from __future__ import annotations
import datetime, importlib.util, json, os, sys, time
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
sys.path.insert(0, os.path.join(D))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from llama_cpp import Llama, LlamaGrammar  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
def ts(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def emit(**ev):
    print(json.dumps({"ts": ts(), **ev}), flush=True)

units, chash = load_units()
emit(event="corpus", docs=len(units), corpus_hash=chash,
     lens=sorted([(u[0], len(u[1])) for u in units], key=lambda x: x[1])[:3])
prompt0 = student_prompt(units[0][1][:600])
emit(event="prompt_chars", n=len(prompt0))

t0 = time.perf_counter()
m = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
          n_gpu_layers=-1, n_ctx=4096, n_batch=512, verbose=False)
emit(event="load_2b", seconds=round(time.perf_counter() - t0, 3))
toks = m.tokenize(prompt0.encode(), add_bos=False, special=False)
emit(event="prompt_tokens", n=len(toks))

grammar = LlamaGrammar.from_string(grammar_v02(), verbose=False)
for i in range(3):
    t0 = time.perf_counter()
    r = m.create_completion(prompt0, grammar=grammar, max_tokens=48,
                            temperature=0.0, seed=11)
    dt = time.perf_counter() - t0
    u = r.get("usage", {})
    emit(event="grammar_decode", rep=i, seconds=round(dt, 3),
         prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
         text_len=len(r["choices"][0]["text"]))
for i in range(3):
    t0 = time.perf_counter()
    gen = m.generate(toks, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, reset=True)
    out = []
    for t in gen:
        out.append(int(t))
        if len(out) >= 48:
            break
    gen.close()
    dt = time.perf_counter() - t0
    emit(event="greedy_decode", rep=i, seconds=round(dt, 3), out_tokens=len(out))

t0 = time.perf_counter()
m2 = Llama(model_path=os.path.join(MODELS, "Qwen3-Embedding-0.6B-Q8_0.gguf"),
           n_gpu_layers=-1, n_ctx=2048, embedding=True, verbose=False)
emit(event="load_06b", seconds=round(time.perf_counter() - t0, 3))
qs = ["Who directed the movie?", "Where was the actor born?"]
for i in range(3):
    t0 = time.perf_counter()
    v = m2.embed("query: " + qs[i % 2])
    dt = time.perf_counter() - t0
    emit(event="embed_q", rep=i, seconds=round(dt, 4), dim=len(v))
