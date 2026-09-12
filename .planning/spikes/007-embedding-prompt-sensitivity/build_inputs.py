"""Build rendered input texts for spike 007 (CPU only, stdlib).

Reads the 20-document corpus (hash-verified) and queries-v1.json (hash-verified),
renders every design text for both models, writes inputs/emb_texts.json and
inputs/gen_texts.json plus inputs/meta.json. Refuses on empty renders.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

import designs

SPIKE_DIR = Path(__file__).resolve().parent
IN = SPIKE_DIR / "inputs"
LOGS = SPIKE_DIR / "logs"
FIXTURE = Path("/home/chris/coding/Databasise-2.0-fully-agnostic-system"
               "/databasise/tests/fixtures/corpus")
SHARED = SPIKE_DIR.parent / "shared" / "queries-v1.json"
EXPECT_CORPUS_HASH = "ac55d19ec162cc9abf51ddf8502436109b1439c5cbaea4cf41c448c11575d5bd"
EXPECT_QUERIES_HASH = "ddfb9401a7498894bb60cddc2a98ad46930311438b9055129e42d4c2ba73e548"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def log(run_name, event, **fields):
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "run": run_name, "event": event, **fields}
    with open(LOGS / f"{run_name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_corpus():
    manifest = json.loads((FIXTURE / "MANIFEST.json").read_text(encoding="utf-8"))
    docs = []
    for doc_id in sorted(manifest["documents"]):
        text = (FIXTURE / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert actual == manifest["documents"][doc_id]["sha256"], f"drift: {doc_id}"
        docs.append({"id": doc_id,
                     "title": manifest["documents"][doc_id]["title"],
                     "text": text})
    # corpus-level hash: parity-loader convention (sha256 of newline-joined
    # per-document digests in sorted-id order) checked against the manifest
    # field, which itself must equal the known anchor.
    assert manifest["corpus_hash"] == EXPECT_CORPUS_HASH, "manifest corpus_hash changed"
    ch = hashlib.sha256(
        "\n".join(manifest["documents"][d]["sha256"] for d in sorted(manifest["documents"])).encode("utf-8")
    ).hexdigest()
    assert ch == manifest["corpus_hash"], f"corpus hash drift: {ch}"
    gold = manifest["queries"]
    return docs, gold


def main():
    run_name = sys.argv[1] if len(sys.argv) > 1 else "build"
    IN.mkdir(parents=True, exist_ok=True)
    docs, gold2 = load_corpus()
    shared = json.loads(SHARED.read_text(encoding="utf-8"))
    assert shared["queries_hash"] == EXPECT_QUERIES_HASH, "queries-v1 drift"
    assert shared["corpus_hash"] == EXPECT_CORPUS_HASH, "queries-v1 corpus mismatch"
    queries = shared["queries"]  # 116: id, doc, split, q

    emb_ids, emb_texts = [], []
    gen_ids, gen_texts = [], []

    def add(store_ids, store_texts, key, text):
        assert isinstance(text, str) and len(text) > 0, f"empty render: {key}"
        assert key not in store_ids, f"dup key: {key}"
        store_ids.append(key)
        store_texts.append(text)

    for d in docs:
        i, title, text = d["id"], d["title"], d["text"]
        add(emb_ids, emb_texts, f"d:bare:{i}", text)
        add(emb_ids, emb_texts, f"d:title:{i}", designs.titled_doc(title, text))
        add(emb_ids, emb_texts, f"d:instr:{i}", designs.instr_doc(text))
        add(gen_ids, gen_texts, f"d:bareM:{i}", designs.gen_bare(text))
        add(gen_ids, gen_texts, f"d:titleM:{i}", designs.gen_titled(title, text))
        add(gen_ids, gen_texts, f"d:sysM:{i}", designs.gen_sys(text))
        add(gen_ids, gen_texts, f"d:taskM:{i}", designs.gen_task(text))
        add(gen_ids, gen_texts, f"d:eol:{i}", designs.gen_eol(text))
        add(gen_ids, gen_texts, f"d:about:{i}", designs.gen_about(text))

    for q in queries:
        qid, qt = q["id"], q["q"]
        add(emb_ids, emb_texts, f"q:bare:{qid}", qt)
        add(emb_ids, emb_texts, f"q:vendor:{qid}", designs.vendor_q(qt))
        add(emb_ids, emb_texts, f"q:task:{qid}", designs.task_q(qt))
        add(emb_ids, emb_texts, f"q:wrong:{qid}", designs.wrong_q(qt))
        add(gen_ids, gen_texts, f"q:bareM:{qid}", designs.gen_bare(qt))

    for g in gold2:
        for prefix, fn in (("bare", lambda t: t), ("vendor", designs.vendor_q),
                           ("task", designs.task_q), ("wrong", designs.wrong_q)):
            add(emb_ids, emb_texts, f"g:{prefix}:{g['id']}", fn(g["question"]))
        add(gen_ids, gen_texts, f"g:bareM:{g['id']}",
            designs.gen_bare(g["question"]))

    json.dump({"ids": emb_ids, "texts": emb_texts},
              open(IN / "emb_texts.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"ids": gen_ids, "texts": gen_texts},
              open(IN / "gen_texts.json", "w", encoding="utf-8"), ensure_ascii=False)
    keyword = [q["id"] for q in queries if q["id"].endswith("#5")]
    meta = {"n_docs": len(docs), "n_queries": len(queries),
            "n_keyword": len(keyword),
            "n_emb_texts": len(emb_ids), "n_gen_texts": len(gen_ids),
            "gold2": [{"id": g["id"], "gold": g["gold_document_ids"]} for g in gold2],
            "queries": [{"id": q["id"], "doc": q["doc"]} for q in queries],
            "min_query_chars": min(len(q["q"]) for q in queries),
            "max_doc_chars": max(len(d["text"]) for d in docs)}
    json.dump(meta, open(IN / "meta.json", "w", encoding="utf-8"), indent=1)
    print(f"emb_texts={len(emb_ids)} gen_texts={len(gen_ids)} "
          f"queries={len(queries)} keyword={len(keyword)} "
          f"min_q_chars={meta['min_query_chars']} max_doc_chars={meta['max_doc_chars']}")
    log(run_name, "inputs_built", **{k: v for k, v in meta.items()
                                     if k not in ("queries", "gold2")})


if __name__ == "__main__":
    main()
