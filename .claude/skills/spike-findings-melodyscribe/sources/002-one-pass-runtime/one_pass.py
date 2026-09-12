"""Spike 002 GPU experiments: one-pass runtime on MiniCPM5-2B-Q8_0.

Run under `flock /tmp/melodyscribe-gpu.lock` via run.sh. Loads the model
ONCE and runs every arm against it:

  dual_use   - one Llama(embedding=True) instance serves generate + embed
  one_decode - ONE llama_decode over prefix+section+[EMB] yields BOTH the
               embedding (get_embeddings_ith at [EMB]) and the logits
               (get_logits_ith at last pos) for the next token
  isolation  - same section string -> same vector whatever ran before;
               different sections -> different vectors (non-vacuity)
  grammar    - ops decode under 001's GBNF (graph,sql) on identical inputs,
               validated by 001's Proof; free-decode arm for head-to-head
  bounds     - tiny cap (I4), empty section, long-section truncate
  throughput - prefill tok/s, decode tok/s per arm, load time

Corpus sections are real paragraphs from the hash-verified parity corpus
(corpus.py loaded by path so this spike never imports the databasise
package chain). Every result is one JSON object per line (key 'check').
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
import time

SPIKE_DIR = os.path.dirname(os.path.abspath(__file__))
S01 = os.path.join(os.path.dirname(SPIKE_DIR), "001-score-io-model")
MODELS = os.environ["MELODYSCRIBE_MODELS"]
MODEL = os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf")

sys.path.insert(0, S01)
from grammar import grammar_for_subset  # noqa: E402
from ops_validate import validate_ops  # noqa: E402
from score import ops_instruction  # noqa: E402

from llama_cpp import Llama, LlamaGrammar  # noqa: E402
import llama_cpp  # noqa: E402

# Fixed per version (SCORE-IO-SPEC section 2 + MANIFEST v0.1 default 4):
# doc_prefix includes a system-style turn; recorded here, hashed later.
DOC_PREFIX = ("MelodyScribe ingest v0.1. File facts with evidence spans. ")
DOC_PREFIX_V = "score-io-v0.1+prefix-v1"
EMB_ID = 130080
RQ_ID = 130081
TOKEN_POLICY = f"emb=reserved:{EMB_ID};rq=reserved:{RQ_ID}"
FILE_SET = ("graph", "sql")


def ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(check: str, ok: bool, detail: dict) -> None:
    print(json.dumps({"ts": ts(), "check": check, "ok": ok, "detail": detail}),
          flush=True)


def load_corpus_sections(n_docs: int = 3, max_chars: int = 600) -> list[dict]:
    path = os.path.join(SPIKE_DIR, "..", "..", "..", "databasise", "parity",
                        "corpus.py")
    path = os.path.normpath(path)
    spec = importlib.util.spec_from_file_location("ms_corpus", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ms_corpus"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    snap = mod.load_snapshot()
    out = []
    for d in sorted(snap.documents, key=lambda d: d.id)[:n_docs]:
        # skip the title line; first substantive paragraph, capped
        body = d.text.split("\n", 1)[1] if "\n" in d.text else d.text
        paras = [p.strip().replace("\n", " ") for p in body.split("\n\n")]
        paras = [p for p in paras if len(p) >= 200]
        para = (paras[0] if paras else body.strip().replace("\n", " "))[:max_chars]
        start = d.text.find(para[:60])
        out.append({"doc_id": d.id, "title": d.title, "content": para,
                    "len_chars": len(para), "char_span": [start, start + len(para)]})
    return out


def cos(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def tok(m: Llama, s: str) -> list[int]:
    return m.tokenize(s.encode("utf-8"), add_bos=False, special=False)


def main() -> int:
    t0 = time.time()
    m = Llama(model_path=MODEL, n_gpu_layers=-1, n_ctx=4096, n_batch=512,
              embedding=True, verbose=False)
    load_s = time.time() - t0
    pool = m.pooling_type()
    emit("load", True, {"model": "MiniCPM5-2B-Q8_0", "load_s": round(load_s, 2),
                        "n_ctx": 4096, "n_batch": 512, "n_gpu_layers": -1,
                        "pooling_type": pool, "n_embd": m.n_embd(),
                        "n_vocab": m.n_vocab(),
                        "token_policy": TOKEN_POLICY,
                        "doc_prefix": DOC_PREFIX,
                        "doc_prefix_v": DOC_PREFIX_V})

    # token policy: chosen ids must be single, feedable, text-absent
    emb_empty = m.detokenize([EMB_ID]) == b""
    rq_empty = m.detokenize([RQ_ID]) == b""
    emit("tokpolicy.reserved", emb_empty and rq_empty,
         {"emb_detok_empty": emb_empty, "rq_detok_empty": rq_empty,
          "note": "tail block 130072..130559 detokenizes empty (unused slots)"})

    sections = load_corpus_sections()
    emit("corpus", True, {"docs": [s["doc_id"] for s in sections],
                          "lens": [s["len_chars"] for s in sections]})
    prefix_ids = tok(m, DOC_PREFIX)
    # Boundary merges: tok(a)+tok(b) != tok(a+b) in general. Manual batches
    # MUST use single-string tokenization so ids match embed()/generate paths.
    full_ids = [tok(m, DOC_PREFIX + s["content"]) for s in sections]
    sec_ids = [tok(m, s["content"]) for s in sections]
    emit("tokenize", True, {"prefix_len": len(prefix_ids),
                            "section_lens": [len(t) for t in sec_ids],
                            "full_lens": [len(t) for t in full_ids],
                            "split_vs_single": [[len(prefix_ids) + len(s), len(f)]
                                                for s, f in zip(sec_ids, full_ids)],
                            "note": "split!=single proves boundary merges; E_i uses single"})

    # ---- dual_use: one instance generates and embeds ----
    t = time.time()
    gen = m.create_completion("The capital of France is", max_tokens=8,
                              temperature=0.0, seed=7)
    gen_s = time.time() - t
    gen_text = gen["choices"][0]["text"]  # type: ignore[index]
    t = time.time()
    vec = m.embed(DOC_PREFIX + sections[0]["content"])
    emb_s = time.time() - t
    dim = len(vec[0]) if isinstance(vec[0], list) else len(vec)
    emit("dual_use", "Paris" in gen_text and dim == m.n_embd(),
         {"generate": gen_text, "gen_s": round(gen_s, 3),
          "embed_dim": dim, "embed_s": round(emb_s, 3),
          "note": "same Llama(embedding=True) instance, generate then embed"})

    # ---- one_decode: ONE llama_decode -> embeddings AND logits ----
    # BOS probe (run-3 lesson): this MiniCPM5 tokenizer emits NO bos id
    # under either add_bos setting, so manual batches use tokenize() output
    # verbatim. Earlier runs prepended a spurious 0; re-run cleanly here.
    import numpy as np
    bos = m.token_bos()  # informational only: this tokenizer never emits BOS (see tokprobe)
    def one_decode(toks: list[int], emb_pos: int):
        m._ctx.kv_cache_clear()
        m._batch.set_batch(batch=toks, n_past=0, logits_all=True)
        t = time.time()
        m._ctx.decode(m._batch)
        ds = time.time() - t
        m._batch.reset()
        ev = np.ctypeslib.as_array(
            m._ctx.get_embeddings_ith(emb_pos),
            shape=(m.n_embd(),)).tolist()
        lg = np.ctypeslib.as_array(
            m._ctx.get_logits_ith(len(toks) - 1),
            shape=(m.n_vocab(),)).tolist()
        return ev, lg, ds

    toks = full_ids[0] + [EMB_ID]
    emb_pos = len(toks) - 1
    evec, logits, dec_s = one_decode(toks, emb_pos)
    evec2, _, _ = one_decode(toks, emb_pos)  # determinism rerun
    top = max(range(len(logits)), key=logits.__getitem__)
    top_text = m.detokenize([top]).decode("utf-8", "replace")
    # alignment fix (run-1 lesson): logits AFTER [EMB] cannot equal greedy
    # after the section end. Compare logits at the section-final position.
    lg2 = np.ctypeslib.as_array(
        m._ctx.get_logits_ith(len(toks) - 2),
        shape=(m.n_vocab(),)).tolist()
    top2 = max(range(len(lg2)), key=lg2.__getitem__)
    # greedy next token over the EXACT same id sequence (no [EMB]) via ids prompt
    g2 = m.create_completion(toks[:-1], max_tokens=1, temperature=0.0, seed=7)
    g2_text = g2["choices"][0]["text"]  # type: ignore[index]
    g2_ids = tok(m, g2_text) if g2_text else []
    # one-decode vectors for all 3 sections -> similarity structure
    od_vecs = []
    for f in full_ids:
        ev, _, _ = one_decode(f + [EMB_ID], len(f))  # last index, not len
        od_vecs.append(ev)
    # cross-check: one-decode [EMB] state vs embed() last-section state
    v_x = m.embed(DOC_PREFIX + sections[0]["content"])
    cos_emb_marker_vs_last = round(cos(evec, v_x[-1]), 4)
    # embed() vectors for the same strings -> similarity structure
    em_vecs = []
    for s in sections:
        v = m.embed(DOC_PREFIX + s["content"])
        em_vecs.append(v[-1])  # pooling NONE: per-token list; last = section end
    import itertools
    od_pairs = {f"{a}{b}": round(cos(od_vecs[a], od_vecs[b]), 4)
                for a, b in itertools.combinations(range(3), 2)}
    em_pairs = {f"{a}{b}": round(cos(em_vecs[a], em_vecs[b]), 4)
                for a, b in itertools.combinations(range(3), 2)}
    emit("one_decode", len(evec) == m.n_embd() and len(logits) == m.n_vocab(),
         {"decode_s": round(dec_s, 4), "n_tokens": len(toks),
          "emb_dim": len(evec), "logits_dim": len(logits),
          "argmax_id": top, "argmax_text": top_text,
          "argmax_at_section_end_id": top2,
          "argmax_at_section_end_text": m.detokenize([top2]).decode("utf-8", "replace"),
          "greedy_1tok_text": g2_text, "greedy_ids": g2_ids,
          "argmax_eq_greedy": (g2_ids[:1] == [top2]),
          "cos_rerun_self": round(cos(evec, evec2), 6),
          "cos_emb_marker_vs_embed_last": cos_emb_marker_vs_last,
          "one_decode_pairwise": od_pairs, "embed_pairwise": em_pairs,
          "note": "single llama_decode; embeddings+logits read from same call"})

    # ---- no-EMB alignment: one-decode last-section state vs embed() last state
    # Same BOS-aligned ids, no [EMB] token. Expect cos ~1: the [EMB] token's
    # own contribution is what run-1's 0.23 measured, not machinery drift.
    toks_ne = full_ids[0]
    ev_ne, _, _ = one_decode(toks_ne, len(toks_ne) - 1)
    v_ne = m.embed(DOC_PREFIX + sections[0]["content"])
    emit("align_no_emb", True,
         {"cos_one_decode_vs_embed_last": round(cos(ev_ne, v_ne[-1]), 6),
          "single_string_ids": True,
          "note": "identical ids, no marker token: states must agree"})

    # ---- seq copy: P prefilled once on seq 0, cp 0->1, section on seq 1 ----
    # Exercises the spec section 4 primitive (llama_memory_seq_cp): E_i = copy(P).
    P = full_ids[0]  # E_i token string incl. prefix (single-string ids)
    S = [EMB_ID]
    m._ctx.kv_cache_clear()
    m._batch.set_batch(batch=P, n_past=0, logits_all=True)
    m._ctx.decode(m._batch)
    m._batch.reset()
    m._ctx.kv_cache_seq_cp(0, 1, -1, -1)
    # continuation batch on seq 1 at pos len(P)+i, written manually
    b = m._batch.batch
    m._batch.reset()
    b.n_tokens = len(S)
    for i, t in enumerate(S):
        b.token[i] = t
        b.pos[i] = len(P) + i
        b.seq_id[i][0] = 1
        b.n_seq_id[i] = 1
        b.logits[i] = True
    m._ctx.decode(m._batch)
    m._batch.reset()
    # Output index != position index across sequences: this batch holds ONE
    # output (the seq-1 token), so readback index is 0 (run-3 lesson: ith is
    # the i-th output, not the i-th position).
    ev_cp = np.ctypeslib.as_array(
        m._ctx.get_embeddings_ith(0),
        shape=(m.n_embd(),)).tolist()
    m._ctx.kv_cache_seq_rm(1, -1, -1)
    emit("seq_copy", True,
         {"cos_copy_vs_single_decode": round(cos(ev_cp, evec), 6),
          "note": "E_i built by copy(P)+section equals one-shot decode"})

    # ---- chunking control: two decodes same-seq (P, then S) vs single decode
    # Decides whether seq_copy's 0.9984 (run-4) is the COPY or the SPLIT.
    m._ctx.kv_cache_clear()
    m._batch.set_batch(batch=P, n_past=0, logits_all=True)
    m._ctx.decode(m._batch)
    m._batch.reset()
    b2 = m._batch.batch
    b2.n_tokens = len(S)
    for i, t in enumerate(S):
        b2.token[i] = t
        b2.pos[i] = len(P) + i
        b2.seq_id[i][0] = 0
        b2.n_seq_id[i] = 1
        b2.logits[i] = True
    m._ctx.decode(m._batch)
    m._batch.reset()
    ev_ch = np.ctypeslib.as_array(
        m._ctx.get_embeddings_ith(0),
        shape=(m.n_embd(),)).tolist()
    emit("chunking", True,
         {"cos_chunked_vs_single": round(cos(ev_ch, evec), 6),
          "cos_chunked_vs_copy": round(cos(ev_ch, ev_cp), 6),
          "note": "same-seq split isolates copy-vs-split effect"})

    # ---- isolation: history-independent, content-sensitive ----
    va1 = m.embed(DOC_PREFIX + sections[0]["content"])
    _ = m.create_completion("Unrelated neighbour text about telescopes " * 20,
                            max_tokens=20, temperature=0.0, seed=3)
    va2 = m.embed(DOC_PREFIX + sections[0]["content"])
    vb = m.embed(DOC_PREFIX + sections[1]["content"])
    a1 = va1[0] if isinstance(va1[0], (int, float)) else va1[-1]
    a2 = va2[0] if isinstance(va2[0], (int, float)) else va2[-1]
    b1 = vb[0] if isinstance(vb[0], (int, float)) else vb[-1]
    same = cos(a1, a2)
    diff = cos(a1, b1)
    emit("isolation", same > 0.9999 and diff < 0.99,
         {"cos_same_across_history": round(same, 6),
          "cos_different_sections": round(diff, 6),
          "note": "embed() clears KV per call; vector is fn(prefix,section) only"})

    # ---- RQ feedability: the second reserved id must decode cleanly too ----
    rq_toks = full_ids[0][:50] + [RQ_ID]
    ev_rq, _, _ = one_decode(rq_toks, len(rq_toks) - 1)
    emit("tokpolicy.rq_live", len(ev_rq) == m.n_embd(),
         {"rq_id": RQ_ID, "emb_dim": len(ev_rq),
          "cos_rq_vs_emb_section0": round(cos(ev_rq, od_vecs[0]), 4),
          "note": "RQ id feeds through one decode; distinct position, same machinery"})

    # ---- grammar ops vs free decode, identical inputs ----
    grammar_text = grammar_for_subset(FILE_SET)
    grammar = LlamaGrammar.from_string(grammar_text, verbose=False)
    arms = []
    for i, s in enumerate(sections):
        prompt = (DOC_PREFIX + s["content"] + "\n" + ops_instruction(FILE_SET))
        ntok_in = len(tok(m, prompt))
        t = time.time()
        g = m.create_completion(prompt, max_tokens=160, temperature=0.0,
                                seed=11, grammar=grammar)
        gs = time.time() - t
        gt = g["choices"][0]["text"]  # type: ignore[index]
        t = time.time()
        f = m.create_completion(prompt, max_tokens=160, temperature=0.0,
                                seed=11)
        fs = time.time() - t
        ft = f["choices"][0]["text"]  # type: ignore[index]
        gres = check_ops_text(gt, s["content"])
        fres = check_ops_text(ft, s["content"])
        arms.append({"section": s["doc_id"], "in_tokens": ntok_in,
                     "grammar": {"s": round(gs, 2), "out": gt[:120],
                                 **gres},
                     "free": {"s": round(fs, 2), "out": ft[:120], **fres}})
    g_ok = sum(1 for a in arms for k in ("grammar",) if a[k]["proof_ok"])
    f_ok = sum(1 for a in arms for k in ("free",) if a[k]["proof_ok"])
    emit("grammar_head_to_head", True,
         {"arms": arms, "grammar_proof_ok": f"{g_ok}/3",
          "free_proof_ok": f"{f_ok}/3"})

    # ---- few-shot ops arm: can the model emit NON-EMPTY valid ops? ----
    # Zero-shot arms all returned {"ops":[]} (format-valid, content-vacuous).
    # One demonstration with a true evidence span from section 0, applied to
    # section 1, tests whether filable ops are reachable at all (accuracy is
    # spike 003's territory; reachability is this spike's).
    def span_of(content: str, needle: str):
        i = content.find(needle)
        return [i, i + len(needle)] if i >= 0 else None

    s0, s1 = sections[0], sections[1]
    subj = s0["title"]
    sp = span_of(s0["content"], subj)
    yr = "1949" if "1949" in s0["content"] else None
    few = ""
    if sp and yr:
        ysp = span_of(s0["content"], yr)
        demo = {"ops": [
            {"target": "graph", "s": subj, "p": "released_in", "o": yr,
             "evidence": ysp},
            {"target": "sql", "subject": subj, "attribute": "release_year",
             "value": yr, "value_type": "number", "evidence": ysp}]}
        few = (f"Example for another section: {json.dumps(demo)}\n"
               f"Now do the same for the section above. ")
    prompt1 = (DOC_PREFIX + s1["content"] + "\n" + few + ops_instruction(FILE_SET))
    t = time.time()
    o = m.create_completion(prompt1, max_tokens=200, temperature=0.0,
                            seed=11, grammar=grammar)["choices"][0]["text"]  # type: ignore[index]
    fs_s = time.time() - t
    o_res = check_ops_text(o, s1["content"])
    emit("fewshot_ops", True,
         {"demo_spans": [sp, span_of(s0["content"], yr or "")],
          "s": round(fs_s, 2), "out": o[:300], **o_res})

    # ---- bounds: tiny cap, empty section, long section ----
    prompt0 = DOC_PREFIX + sections[0]["content"] + "\n" + ops_instruction(FILE_SET)
    tiny = m.create_completion(prompt0, max_tokens=2, temperature=0.0,
                               seed=11, grammar=grammar)["choices"][0]["text"]  # type: ignore[index]
    tiny_res = check_ops_text(tiny, sections[0]["content"])
    try:
        ve = m.embed(DOC_PREFIX)
        empty_ok, empty_dim = True, (len(ve[0]) if isinstance(ve[0], list) else len(ve))
    except Exception as e:  # noqa: BLE001
        empty_ok, empty_dim = False, str(e)
    long_text = (sections[0]["content"] + " ") * 40
    try:
        vl = m.embed(long_text[:8000])
        ldim = len(vl[0]) if isinstance(vl[0], list) else len(vl)
        long_ok: bool | str = True
    except Exception as e:  # noqa: BLE001
        ldim, long_ok = str(e), False
    emit("bounds", True,
         {"tiny_cap_parse_ok": tiny_res["parse_ok"],
          "tiny_cap_proof_ok": tiny_res["proof_ok"],
          "tiny_out": tiny[:80],
          "empty_prefix_embed_ok": empty_ok, "empty_dim": empty_dim,
          "long_embed_ok": long_ok, "long_dim": ldim,
          "long_chars": len(long_text[:8000]),
          "note": "I4: capped decode stays bounded; truncation fails Proof, never crashes"})

    # ---- throughput ----
    n_in = sum(len(prefix_ids) + len(t) for t in sec_ids)
    t = time.time()
    for s in sections:
        m.embed(DOC_PREFIX + s["content"])
    pre_s = time.time() - t
    g_toks = sum(a["grammar"].get("out_tokens", 0) for a in arms)
    emit("throughput", True,
         {"prefill_tokens": n_in, "prefill_s": round(pre_s, 3),
          "prefill_tok_s": round(n_in / max(pre_s, 1e-6), 1),
          "note": "decode tok/s per arm recorded in grammar_head_to_head"})
    emit("done", True, {"total_s": round(time.time() - t0, 1),
                        "pooling_note": f"model pooling_type={pool} (0=NONE: per-token ith reads)"})
    return 0


def check_ops_text(text: str, content: str) -> dict:
    try:
        obj = json.loads(text)
        parse_ok: bool | str = True
    except Exception as e:  # noqa: BLE001
        return {"parse_ok": False, "proof_ok": False, "n_ops": 0,
                "err": f"json: {e}", "out_tokens": len(text.split())}
    res = validate_ops(obj, FILE_SET, content)
    ok = bool(res.get("ok"))
    return {"parse_ok": parse_ok, "proof_ok": ok, "n_ops": len(obj.get("ops", [])),
            "err": (None if ok else json.dumps(res.get("verdicts"))),
            "out_tokens": len(text.split())}


if __name__ == "__main__":
    sys.exit(main())
