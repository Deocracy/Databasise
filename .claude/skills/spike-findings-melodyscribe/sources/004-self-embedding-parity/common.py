"""Shared helpers for spike 004: corpus loading, chunking, cosine recall, JSONL logging."""
import datetime
import hashlib
import json
import math
import re
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
RESULTS = SPIKE_DIR / "results"
LOGS = SPIKE_DIR / "logs"
FIXTURE = Path("/home/chris/coding/Databasise-2.0-fully-agnostic-system"
               "/databasise/tests/fixtures/corpus")

MARKER = "\u27e6EMB\u27e7"  # literal fallback marker per SCORE-IO-SPEC section 2


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def log(run_name, event, **fields):
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "run": run_name, "event": event, **fields}
    with open(LOGS / f"{run_name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load_corpus():
    """Read MANIFEST.json + .txt files directly (stdlib only)."""
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    docs = []
    for doc_id in sorted(manifest["documents"]):
        text = (FIXTURE / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert actual == manifest["documents"][doc_id]["sha256"], f"drift: {doc_id}"
        docs.append({"id": doc_id,
                     "title": manifest["documents"][doc_id]["title"],
                     "text": text})
    queries = manifest["queries"]
    return docs, queries


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"\'])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def recall_at_k(ranked_ids, gold_ids, k):
    top = set(ranked_ids[:k])
    gold = set(gold_ids)
    return len(top & gold) / len(gold)


def rank_docs(query_vec, doc_vecs):
    q = norm(query_vec)
    scored = [(cos(q, norm(v)), did) for did, v in doc_vecs]
    scored.sort(reverse=True)
    return [did for _, did in scored]
