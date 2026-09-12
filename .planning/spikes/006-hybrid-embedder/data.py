"""Shared data loading for spike 006 (stdlib only, no GPU, no network).

Corpus: 20 docs via databasise/parity/corpus.py (hash-asserted, same as 003).
Queries: .planning/spikes/shared/queries-v1.json (teacher-generated, fixed
train/test split by document). Gold HotpotQA queries from the corpus MANIFEST.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHARED = REPO / ".planning" / "spikes" / "shared" / "queries-v1.json"
SPIKE003 = REPO / ".planning" / "spikes" / "003-op-emission-size-sweep"
FIXTURE = REPO / "databasise" / "tests" / "fixtures" / "corpus"


def load_docs():
    """[(doc_id, text)] in sorted order + corpus hash. Text is raw .txt bytes
    (title + blank line + paragraph), identical to spike 003 units."""
    path = REPO / "databasise" / "parity" / "corpus.py"
    spec = importlib.util.spec_from_file_location("spike006_corpus", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["spike006_corpus"] = mod
    spec.loader.exec_module(mod)
    snap = mod.load_snapshot()
    units = [(d.id, d.text) for d in snap.documents]
    assert len(units) == 20, f"expected 20 docs, got {len(units)}"
    return units, snap.corpus_hash


def load_queries():
    """(queries, test_doc_ids). Each query: id/doc/split/q/answer/quote."""
    q = json.loads(SHARED.read_text(encoding="utf-8"))
    return q["queries"], q["test_document_ids"], q["corpus_hash"]


def load_gold():
    """HotpotQA gold queries from the corpus MANIFEST (hash-verified docs)."""
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    for doc_id, meta in manifest["documents"].items():
        text = (FIXTURE / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert actual == meta["sha256"], f"drift: {doc_id}"
    return manifest["queries"]
