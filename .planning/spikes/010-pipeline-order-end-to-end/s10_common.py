"""Spike 010 shared helpers (stdlib only, no GPU, no network).

Corpus loading (hash-verified, same rule as spike 003/004), chunker
variants, Score XML build validated by spike 001's compiler (read-only
import), v0.2 Proof via spike 001 + spike 003 resolve (read-only imports),
JSONL logging, normalisation helpers.

Reuse rule: 001's compiler/proof and 003's prompt/resolver/grammar are
imported read-only through sys.path; nothing is re-implemented here.
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # 010 folder -> spikes -> .planning -> repo root
SPIKE001 = REPO / ".planning" / "spikes" / "001-score-io-model"
SPIKE003 = REPO / ".planning" / "spikes" / "003-op-emission-size-sweep"
FIXTURE = REPO / "databasise" / "tests" / "fixtures" / "corpus"
SHARED = REPO / ".planning" / "spikes" / "shared"

sys.path.insert(0, str(SPIKE001))
sys.path.insert(0, str(SPIKE003))
sys.path.insert(0, str(HERE))

import ops_validate  # noqa: E402  (spike 001, VALIDATED)
import score as score001  # noqa: E402  (spike 001, VALIDATED)
import resolve as v02  # noqa: E402  (spike 003, VALIDATED)
from common import INSTRUCTION as D0_INSTRUCTION  # noqa: E402  (spike 003 D0)

FILE_SET = ("graph", "sql")

# doc_prefix for this spike: the D0 instruction bytes (stated in README).
# The embedding input is "<INSTRUCTION>\\n\\nSection:\\n<content>" at the
# token level per spike 002's gotcha (single-string tokenisation); the
# marker form is the literal fallback per SPEC section 2 (spike 004 arm B).
MARKER = "\u27e6EMB\u27e7"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(log_fh, event: str, **fields):
    rec = {"ts": now(), "event": event, **fields}
    log_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log_fh.flush()
    return rec


def norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def load_corpus():
    """20 (doc_id, text) with hash verification; text is raw .txt bytes."""
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    docs = []
    for doc_id in sorted(manifest["documents"]):
        text = (FIXTURE / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert actual == manifest["documents"][doc_id]["sha256"], f"drift: {doc_id}"
        docs.append((doc_id, text))
    assert len(docs) == 20, f"expected 20 docs, got {len(docs)}"
    return docs, manifest["corpus_hash"]


def chunk_whole(doc_id: str, text: str):
    """Variant `whole`: one unit per document (spike 003's unit)."""
    return [(f"{doc_id}#s1", text)]


def chunk_split(doc_id: str, text: str):
    """Variant `split`: title section + body section (every corpus doc has
    exactly 2 newline-separated paragraphs: title, blank, body)."""
    paras = [p for p in text.split("\n\n") if p.strip()]
    assert len(paras) == 2, f"{doc_id}: expected 2 paras, got {len(paras)}"
    return [(f"{doc_id}#title", paras[0]), (f"{doc_id}#body", paras[1])]


def build_score_xml(doc_id: str, sections):
    """Score with v0.1 defaults: embed=isolated, respond=ops, file=graph,sql.
    sections: list of (sec_id, content). Returns XML string."""
    import xml.sax.saxutils as sax

    parts = [f'<score v="1" corpus="parity" doc="{doc_id}" provenance="chunker">']
    for sec_id, content in sections:
        short = sec_id.split("#", 1)[1] if "#" in sec_id else sec_id
        parts.append(
            f'<section id="{short}" embed="isolated" respond="ops"'
            f' file="graph,sql">{sax.escape(content)}</section>'
        )
    parts.append("</score>")
    return "".join(parts)


def compile_and_check(doc_id: str, sections):
    """Validate the Score through 001's compiler; return (spec, plan)."""
    xml_text = build_score_xml(doc_id, sections)
    spec = score001.parse_score(xml_text)
    plan = score001.compile_plan(spec)
    return spec, plan


def student_prompt(content: str) -> str:
    """Byte-identical to spike 003's student prompt (D0 instruction)."""
    return D0_INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"


def parse_ops_text(text: str):
    """Strict parse, then brace-extraction fallback. Returns (obj, how)."""
    try:
        return json.loads(text), "strict"
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1]), "brace-extract"
        except Exception as e:
            return None, f"unparseable: {e}"
    return None, "unparseable: no braces"


def prove_section(text: str, content: str):
    """Parse + v0.2 Proof for one decoded op list. Returns dict with
    passed (carrying _span) and failed (carrying _reasons)."""
    obj, how = parse_ops_text(text)
    if obj is None:
        return {"ok": False, "how": how, "passed": [], "failed": [],
                "error": how, "verdicts": []}
    res = v02.validate_v02(obj, FILE_SET, content, ops_validate)
    res["how"] = how
    return res


def load_queries_v1():
    d = json.loads((SHARED / "queries-v1.json").read_text(encoding="utf-8"))
    return d["queries"]


def load_hotpot_queries():
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    return manifest["queries"]
