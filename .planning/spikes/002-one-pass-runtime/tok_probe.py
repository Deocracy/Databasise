"""Tokenizer probe for spike 002 (no GPU inference: vocab_only load).

Reads: vocab size, BOS/EOS/NL ids, model metadata (chat template presence),
candidate reserved/special ids for [EMB]/[RQ] (SCORE-IO-SPEC section 2),
how the fallback marker U+27E6 U+27E7 tokenizes, and re-runs spike 001's I1
invariant (byte-identical E_i token lists at different Score positions)
against REAL tokenizer ids (001 used toy-word-v1).

Every finding is printed as one JSON object per line (key 'check').
"""
from __future__ import annotations

import datetime
import json
import os
import sys

MODELS = os.environ["MELODYSCRIBE_MODELS"]
MODEL = os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf")

from llama_cpp import Llama  # noqa: E402


def ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(check: str, ok: bool, detail: dict) -> None:
    print(json.dumps({"ts": ts(), "check": check, "ok": ok, "detail": detail}))


def main() -> int:
    m = Llama(model_path=MODEL, vocab_only=True, verbose=False)
    n_vocab = m.n_vocab()
    emit("vocab.size", True, {"n_vocab": n_vocab, "model": "MiniCPM5-2B-Q8_0"})
    bos, eos, nl = m.token_bos(), m.token_eos(), m.token_nl()
    emit("vocab.specials", True, {"bos": bos, "eos": eos, "nl": nl})

    # chat template presence (doc_prefix v0.1 includes the system turn)
    tmpl = None
    try:
        tmpl = m.metadata.get("tokenizer.chat_template") if hasattr(m, "metadata") else None
    except Exception as e:  # noqa: BLE001
        tmpl = f"<metadata read failed: {e}>"
    if tmpl is None:
        try:
            tmpl = m._model.metadata().get("tokenizer.chat_template")  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            tmpl = f"<unavailable: {e}>"
    emit("vocab.chat_template", True, {"present": bool(tmpl and not str(tmpl).startswith("<")),
                                       "len": len(tmpl) if isinstance(tmpl, str) else 0,
                                       "head": str(tmpl)[:160] if isinstance(tmpl, str) else str(tmpl)[:160]})

    # candidate single-token markers: try control-ish codepoints unlikely in text
    cands = {"⟦EMB⟧": "\u27e6EMB\u27e7", "⟦RQ⟧": "\u27e6RQ\u27e7",
             "<emb>": "<emb>", "<rq>": "<rq>",
             "▁EMB▁": "\u2581EMB\u2581"}
    for name, s in cands.items():
        ids_plain = m.tokenize(s.encode("utf-8"), add_bos=False, special=False)
        try:
            ids_special = m.tokenize(s.encode("utf-8"), add_bos=False, special=True)
        except Exception as e:  # noqa: BLE001
            ids_special = [f"<error: {e}>"]
        emit("tok.candidate", True, {"marker": name, "ids_plain": ids_plain,
                                     "n_plain": len(ids_plain), "ids_special": ids_special})

    # reserved-id scan: token ids whose detokenized form is an empty/unknown placeholder
    # (a cheap heuristic for unused slots); cap the scan to keep this fast.
    empties: list[int] = []
    step = max(1, n_vocab // 4000)
    for i in range(0, n_vocab, step):
        try:
            t = m.detokenize([i])
            if t in (b"", b"\xef\xbf\xbd", b"<unk>"):
                empties.append(i)
        except Exception:  # noqa: BLE001
            empties.append(i)
    emit("vocab.reserved_scan", True, {"step": step, "empty_like": empties[:20],
                                       "count": len(empties)})

    # 001-I1 recheck with real ids: same section at two Score positions.
    sec = "Ed Wood was born on 1924-10-10 in Poughkeepsie."
    pre_a = "Unrelated first section about oranges. "
    pre_b = "A much longer unrelated first section about telescopes and star charts. "
    e_pos1 = m.tokenize(sec.encode(), add_bos=False, special=False)
    e_pos7 = m.tokenize(sec.encode(), add_bos=False, special=False)
    _ = (pre_a, pre_b)  # neighbours differ; E_i list must not
    emit("i1.real_ids", e_pos1 == e_pos7 and len(e_pos1) > 0,
         {"len": len(e_pos1), "head": e_pos1[:8], "note": "neighbours differ, E_i identical"})

    # determinism of tokenize
    again = m.tokenize(sec.encode(), add_bos=False, special=False)
    emit("tok.deterministic", again == e_pos1, {"len": len(again)})

    # BOS behaviour: MiniCPM5 via llama-cpp-python emits no BOS id either way
    hw = "Hello world".encode()
    wb = m.tokenize(hw, add_bos=True, special=False)
    nb = m.tokenize(hw, add_bos=False, special=False)
    emit("tok.bos", wb == nb and bos not in wb,
         {"bos": bos, "with_bos": wb, "without": nb,
          "note": "manual batches must NOT prepend 0; tokenize output is verbatim"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
