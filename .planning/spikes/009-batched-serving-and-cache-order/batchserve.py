"""Spike 009 shared scheduler: K-slot wave serving over llama-cpp-python.

Two schedulers on one model instance (embedding=True, so n_seq_max > 1):
  (a) SERIAL-GRAMMAR: batched prefill of a wave + serial grammar decode per
      slot. The true op path: every output decodes under the v0.2 GBNF.
  (b) PARALLEL-GREEDY: batched prefill + lockstep batched greedy decode
      (one decode call advances all live slots; argmax per output). The
      batching ceiling: no grammar, validity measured offline.

Design constraints learned on this build (see README Investigation Trail):
  - eval()/generate() wipe ALL sequences (kv_cache_seq_rm(-1,...)), so a
    K-slot scheduler must hand-roll raw batches and sample via a persistent
    sampler; a fresh sampler per token would restart grammar state.
  - Never decode a token at an already-filled position (llama_decode -1 on
    this build). The bulk prefill therefore covers bodies only; each
    prompt's last token goes out in its own single-row call at its natural
    (first-time) position.
  - Never use get_logits_ith/sampler-sample on a multi-output decode
    (NULL logits / GGML_ASSERT on this build). Multi-row decodes are read
    with get_logits() as one (M x vocab) buffer, argmax per row; samplers
    only ever see single-output calls. The instance is flipped with
    llama_set_embeddings(ctx, False) after load (keeps n_seq_max>1 from
    embedding=True, restores generative outputs); embed() is never called
    on it.

Stdlib + numpy + llama_cpp only. All GPU work happens under flock via run.sh.
"""
from __future__ import annotations

import datetime
import json
import subprocess
import time

import numpy as np


def set_generative(llm) -> None:
    """Flip the C-side embeddings flag off after load.

    The instance is loaded with embedding=True (required for n_seq_max>1,
    the multi-sequence serving this spike measures). In embeddings mode
    only the last decode output carries real logits
    (GGML_ASSERT(logits != nullptr) otherwise), which makes per-slot first
    tokens unsampleable. Flipping to generative outputs restores logits
    for every output while keeping n_seq_max; causal attention is
    untouched. Never call embed()/create_embedding on a flipped instance
    (009 never does on the 2B; retrieval uses the separate 0.6B load)."""
    import llama_cpp
    llama_cpp.llama_set_embeddings(llm._ctx.ctx, False)


def ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(log, event: str, ok: bool = True, **detail) -> None:
    log.write(json.dumps({"ts": ts(), "event": event, "ok": ok,
                          **detail}) + "\n")
    log.flush()


def vram_used_mb() -> float | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return float(out.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def raw_decode_rows(llm, rows: list[tuple[int, int, int, bool]]) -> float:
    """Decode rows (seq, pos, tok, want_logit) chunked to n_batch. One row
    chunk per llama_decode call; positions explicit so chunking is exact."""
    cap = int(llm.n_batch)
    t = 0.0
    b = llm._batch.batch
    for c in range(0, len(rows), cap):
        chunk = rows[c:c + cap]
        llm._batch.reset()
        b.n_tokens = len(chunk)
        for i, (s, p, tok, lg) in enumerate(chunk):
            b.token[i] = tok
            b.pos[i] = p
            b.seq_id[i][0] = s
            b.n_seq_id[i] = 1
            b.logits[i] = lg
        t0 = time.perf_counter()
        llm._ctx.decode(llm._batch)  # raises on nonzero return
        t += time.perf_counter() - t0
        llm._batch.reset()
    return t


def wave_prefill(llm, prompts: list[list[int]],
                 first_seq: int = 1) -> tuple[float, list[int]]:
    """Batched prefill of prompt BODIES (all but each prompt's last token),
    chunked arbitrarily. Timing only: no output reads follow from this call
    (multi-output readback is NULL on this build). Each prompt's last token
    goes out in its own single-row call via slot_first(), at its natural
    first-time position. Returns (wall seconds, prompt lengths)."""
    t = 0.0
    body: list[tuple[int, int, int, bool]] = []
    for j, toks in enumerate(prompts):
        s = first_seq + j
        for i, tok in enumerate(toks[:-1]):
            body.append((s, i, tok, False))
    t += raw_decode_rows(llm, body)
    return t, [len(p) for p in prompts]


def wave_prefill_naive(llm, prompts: list[list[int]],
                       first_seq: int = 1) -> float:
    """Single-phase batched prefill (all tokens incl. last, one row stream).
    Only valid when NO output reads follow (chunking may split slot ends).
    Returns wall seconds. Prefer wave_prefill when sampling follows."""
    rows: list[tuple[int, int, int, bool]] = []
    for j, toks in enumerate(prompts):
        s = first_seq + j
        for i, tok in enumerate(toks):
            rows.append((s, i, tok, i == len(toks) - 1))
    return raw_decode_rows(llm, rows)


def wave_prefill_prefix_once(llm, prefix: list[int],
                             tails: list[list[int]],
                             first_seq: int = 1) -> tuple[float, float]:
    """Prefill shared prefix once on seq 0, copy to slots, then batched
    tail BODIES (no output reads; last tokens via slot_first).
    Returns (setup_s, tails_s)."""
    t0 = time.perf_counter()
    llm._ctx.kv_cache_seq_rm(0, -1, -1)
    raw_decode_rows(llm, [(0, i, tok, False)
                          for i, tok in enumerate(prefix)])
    for j in range(len(tails)):
        llm._ctx.kv_cache_seq_cp(0, first_seq + j, -1, -1)
    llm._ctx.kv_cache_seq_rm(0, -1, -1)
    t_setup = time.perf_counter() - t0
    t = 0.0
    body: list[tuple[int, int, int, bool]] = []
    for j, tail in enumerate(tails):
        s = first_seq + j
        for i, tok in enumerate(tail[:-1]):
            body.append((s, len(prefix) + i, tok, False))
    t += raw_decode_rows(llm, body)
    return (t_setup, t)


def fresh_grammar_sampler(llm, grammar_text: str):
    from llama_cpp import LlamaGrammar
    llm._sampler = llm._init_sampler(
        top_k=1, top_p=1.0, min_p=0.0, temp=0.0,
        grammar=LlamaGrammar.from_string(grammar_text, verbose=False))
    return llm._sampler


def fresh_greedy_sampler(llm):
    llm._sampler = llm._init_sampler(top_k=1, top_p=1.0, min_p=0.0,
                                     temp=0.0)
    return llm._sampler


def slot_first(llm, slot: int, L: int, tok_last: int, sampler) -> tuple[int,
                                                                        float]:
    """First token for one slot: its last prompt token goes out in a
    single-row call at its natural position (first time there -- never a
    same-position re-decode), then one sample from that single output.
    Returns (token id, seconds)."""
    t0 = time.perf_counter()
    raw_decode_rows(llm, [(slot, L - 1, tok_last, True)])
    llm.n_tokens = L
    tok = int(sampler.sample(llm._ctx, -1))
    return tok, time.perf_counter() - t0


def slot_decode_grammar(llm, slot: int, L: int, tok_last: int,
                        grammar_text: str, cap: int, eos: int = 1
                        ) -> tuple[str, list[int], float, float]:
    """Serial grammar decode of one slot, continuing on its OWN sequence
    (no seq copy). First token via slot_first() with a fresh per-slot
    grammar sampler; follow-ups at new positions L, L+1, ...
    Returns (text, out_ids, ttft_s, dec_s)."""
    sampler = fresh_grammar_sampler(llm, grammar_text)
    first, ttft = slot_first(llm, slot, L, tok_last, sampler)
    out = [first]
    llm.n_tokens = L + 1
    pos = L
    t1 = time.perf_counter()
    while len(out) < cap and out[-1] != eos:
        raw_decode_rows(llm, [(slot, pos, out[-1], True)])
        pos += 1
        llm.n_tokens = pos
        out.append(int(sampler.sample(llm._ctx, -1)))
    dec_s = time.perf_counter() - t1
    llm._sampler = None
    text = llm.detokenize(out).decode("utf-8", errors="replace")
    return text, out, ttft, dec_s


def read_all_argmax(llm, m: int) -> list[int]:
    """Argmax per row of the last decode's full logits buffer (m outputs).
    The ONLY safe multi-output readback on this build (dbg6: byte-exact vs
    generate() refs). Must be called before the next decode call."""
    buf = np.ctypeslib.as_array(llm._ctx.get_logits(),
                                shape=(m * llm.n_vocab(),))
    return [int(np.argmax(buf[r * llm.n_vocab():(r + 1) * llm.n_vocab()]))
            for r in range(m)]


def wave_decode_parallel_greedy(llm, slots: list[int],
                                lens: list[int], toks_last: list[int],
                                cap: int, eos: int = 1
                                ) -> tuple[list[list[int]], float,
                                           list[float]]:
    """Lockstep batched greedy decode. First tokens come from per-slot
    single-row calls (one shared greedy sampler); then one decode call per
    step advances every live slot, tokens read with read_all_argmax().
    Returns (per-slot id lists, decode seconds, first-token seconds)."""
    sampler = fresh_greedy_sampler(llm)
    first_ids: list[int] = []
    first_ss: list[float] = []
    for slot, L, tl in zip(slots, lens, toks_last):
        f, s = slot_first(llm, slot, L, tl, sampler)
        first_ids.append(f)
        first_ss.append(s)
    llm._sampler = None
    live = [f != eos for f in first_ids]
    outs: list[list[int]] = [[f] for f in first_ids]
    cur = list(first_ids)
    pos = list(lens)  # next position to fill per slot
    t = 0.0
    while any(live) and max(len(o) for o in outs) < cap:
        order = [j for j, l in enumerate(live) if l]
        rows = [(slots[j], pos[j], cur[j], True) for j in order]
        t += raw_decode_rows(llm, rows)
        toks = read_all_argmax(llm, len(order))
        for r, j in enumerate(order):
            tok = toks[r]
            outs[j].append(tok)
            cur[j] = tok
            pos[j] += 1
            if tok == eos:
                live[j] = False
    return outs, t, first_ss
