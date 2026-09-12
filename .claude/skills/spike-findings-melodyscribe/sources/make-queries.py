"""Teacher-generated query set for the round-2 spikes (006 hybrid embedder, 007 prompt sensitivity, 010 pipeline).
Six questions per corpus document, each answerable from that document alone, with the answer and a verbatim quote
that the harness verifies as a substring. Split train/test by document (every fourth document, sorted by id, is test).
Credentials: `set -a; source v1/.env.parity; set +a` first; nothing from the environment is written to the output.
Output: shared/queries-v1.json. Reasoning disabled on the teacher, temperature 0, one call per document, one retry."""
import datetime, hashlib, json, os, re, sys, time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "databasise/tests/fixtures/corpus"
OUT = Path(__file__).resolve().parent / "queries-v1.json"
HOST = os.environ.get("LLM_BINDING_HOST", "https://openrouter.ai/api/v1").rstrip("/")
MODEL = os.environ["LLM_MODEL"]; KEY = os.environ["LLM_BINDING_API_KEY"]
N_PER_DOC = 6

def norm(s): return re.sub(r"\s+", " ", s).strip().lower()

def extra_body():
    try:
        e = json.loads(os.environ.get("OPENAI_LLM_EXTRA_BODY", "null")); return dict(e) if isinstance(e, dict) else {}
    except Exception: return {}

def ask(client, doc_id, text):
    prompt = (f"Read the passage and write exactly {N_PER_DOC} questions that can be answered from this passage alone, "
              "with varied forms: one asking who or what an entity is, one asking for a date or number, one asking about a "
              "relation between two entities, one paraphrased so it shares few words with the passage, one short keyword-style "
              "query (3 to 6 words, no question mark), and one asking for a detail from the second half of the passage. "
              "For each give the answer in at most 12 words and a verbatim quote (a contiguous substring of the passage, "
              "20 to 200 characters) that contains the answer. Reply with JSON only: "
              '{"questions":[{"q":"...","answer":"...","quote":"..."}]}\n\nPASSAGE:\n' + text)
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 2048,
            "reasoning": {"effort": "none", "exclude": True}}
    e = extra_body()
    if e: e.setdefault("reasoning", {"effort": "none", "exclude": True}); body["extra_body"] = e
    r = client.post(f"{HOST}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json=body, timeout=180)
    r.raise_for_status(); msg = r.json()["choices"][0]["message"]; t = msg.get("content") or ""
    if not t.strip(): raise RuntimeError("reasoning-only response")
    s, e2 = t.index("{"), t.rindex("}") + 1
    return json.loads(t[s:e2])["questions"]

def main():
    man = json.load(open(CORPUS / "MANIFEST.json"))
    docs = man["documents"]; docs = docs if isinstance(docs, dict) else {d["id"]: d for d in docs}
    ids = sorted(docs); test_ids = set(ids[3::4])
    out = {"version": "queries-v1", "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "corpus_hash": man.get("corpus_hash"), "teacher": "v1/.env.parity LLM_MODEL (id not recorded), temperature 0, reasoning disabled",
           "split_rule": "documents sorted by id; every fourth starting at index 3 is test", "test_document_ids": sorted(test_ids),
           "queries": [], "dropped": []}
    with httpx.Client() as client:
        for did in ids:
            d = docs[did]; fn = d.get("file") or d.get("path") or f"{did}.txt"
            p = CORPUS / fn if (CORPUS / fn).exists() else CORPUS / "documents" / Path(fn).name
            if not p.exists(): p = next((CORPUS / "documents").glob(f"{did}*"))
            text = p.read_text(encoding="utf-8")
            qs = None
            for attempt in (1, 2):
                try: qs = ask(client, did, text); break
                except Exception as ex: print("retry", did, attempt, ex, flush=True); time.sleep(3)
            if not qs: out["dropped"].append({"doc": did, "reason": "teacher failed twice"}); continue
            for i, q in enumerate(qs[:N_PER_DOC]):
                quote = str(q.get("quote", "")); ok = norm(quote) in norm(text) and 20 <= len(quote) <= 220
                rec = {"id": f"{did}#{i+1}", "doc": did, "split": "test" if did in test_ids else "train",
                       "q": str(q.get("q", "")).strip(), "answer": str(q.get("answer", "")).strip(), "quote": quote}
                (out["queries"] if ok and rec["q"] else out["dropped"]).append(rec if ok and rec["q"] else {**rec, "reason": "quote not a substring or malformed"})
            print("ok", did, len(qs), flush=True); time.sleep(1)
    out["counts"] = {"queries": len(out["queries"]), "train": sum(q["split"] == "train" for q in out["queries"]),
                     "test": sum(q["split"] == "test" for q in out["queries"]), "dropped": len(out["dropped"])}
    out["queries_hash"] = hashlib.sha256(json.dumps(out["queries"], sort_keys=True).encode()).hexdigest()
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)); print("QUERIES-DONE", out["counts"], flush=True)

if __name__ == "__main__": main()
