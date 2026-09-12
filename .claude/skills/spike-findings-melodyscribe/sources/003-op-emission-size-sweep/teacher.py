"""Frontier teacher labelling for spike 003 v0.2 (no GPU, network only).

Reads OpenRouter credentials from the environment (v1/.env.parity sourced
by the caller; values never printed, never written to any file). The pinned
model is a reasoning model, so the labeller disables thinking
(OpenRouter "reasoning": {"effort": "none", "exclude": true}, merged with
-- not replacing -- the project's OPENAI_LLM_EXTRA_BODY) and budgets
max_tokens >= 4096. A reasoning-only response is retried once with a higher
budget, then the doc is marked failed.

For each of the 20 corpus units: ask for the v0.2 op list (quote evidence),
parse the JSON (brace-extraction fallback, logged), resolve quotes and run
Proof. Up to 3 rounds with Proof reasons fed back. A document is ACCEPTED
when at least one op passes Proof; failing ops are dropped from the label
(kept in the log with reasons). Writes teacher.json; every attempt is one
JSON line (ISO timestamp) in logs/teacher-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FILE_SET, HERE, load_units, teacher_messages  # noqa: E402
import resolve as v02  # noqa: E402
from common import ops_validate  # noqa: E402

HOST = os.environ.get("LLM_BINDING_HOST", "https://openrouter.ai/api/v1").rstrip("/")
MODEL = os.environ["LLM_MODEL"]
KEY = os.environ["LLM_BINDING_API_KEY"]
assert KEY and MODEL and HOST, "source v1/.env.parity first (set -a; source v1/.env.parity; set +a)"

MAX_ROUNDS = 3
TIMEOUT_S = 180.0
MAX_TOKENS = 4096
MAX_TOKENS_RETRY = 8192


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _extra_body() -> dict:
    try:
        extra = json.loads(os.environ.get("OPENAI_LLM_EXTRA_BODY", "null"))
        return dict(extra) if isinstance(extra, dict) else {}
    except Exception:
        return {}


def parse_json(text: str):
    try:
        return json.loads(text), "strict"
    except Exception:
        pass
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end]), "brace-extract"
    except Exception as e:
        return None, f"unparseable: {e}"


def label_once(client: httpx.Client, messages: list[dict],
               max_tokens: int) -> tuple[str, float, int]:
    """Returns (text, seconds, reasoning_tokens). Raises on HTTP errors and
    on reasoning-only responses (caller retries with a higher budget)."""
    extra = _extra_body()
    body = {"model": MODEL, "messages": messages, "temperature": 0,
            "max_tokens": max_tokens,
            "reasoning": {"effort": "none", "exclude": True}}
    if extra:
        merged = dict(extra)
        merged.setdefault("reasoning", {"effort": "none", "exclude": True})
        body["extra_body"] = merged
    t0 = time.perf_counter()
    r = client.post(f"{HOST}/chat/completions",
                    headers={"Authorization": f"Bearer {KEY}"},
                    json=body, timeout=TIMEOUT_S)
    dt = time.perf_counter() - t0
    r.raise_for_status()
    data = r.json()
    msg = data["choices"][0]["message"]
    text = msg.get("content") or ""
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    rt = details.get("reasoning_tokens", 0)
    if not text.strip():
        raise RuntimeError(f"reasoning-only response (reasoning_tokens={rt})")
    return text, dt, rt


def main() -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = HERE / "logs" / f"teacher-{stamp}.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    units, corpus_hash = load_units()
    only = os.environ.get("SPIKE003_DOCS", "")
    if only:
        keep = set(only.split(","))
        units = [(d, c) for d, c in units if d in keep]
    out: dict = {"corpus_hash": corpus_hash, "file_set": list(FILE_SET),
                 "schema": "ops.v0.2", "labels": {}}
    with httpx.Client() as client, open(log_path, "w") as log:
        def emit(ev: dict):
            ev = {"ts": now(), **ev}
            log.write(json.dumps(ev) + "\n")
            log.flush()

        for doc_id, content in units:
            messages = teacher_messages(content)
            verdict, last_obj, rounds = None, None, 0
            best = None  # best round's validation (most ops passing)
            budget = MAX_TOKENS
            best = None  # best round's validation result (most ops passing)
            for rnd in range(1, MAX_ROUNDS + 1):
                rounds = rnd
                try:
                    text, dt, rt = label_once(client, messages, budget)
                except RuntimeError as e:
                    emit({"event": "teacher-error", "doc": doc_id,
                          "round": rnd, "error": f"{type(e).__name__}: {e}",
                          "budget": budget})
                    budget = MAX_TOKENS_RETRY  # one higher-budget retry
                    time.sleep(2)
                    continue
                except Exception as e:
                    emit({"event": "teacher-error", "doc": doc_id,
                          "round": rnd,
                          "error": f"{type(e).__name__}: {str(e)[:200]}"})
                    time.sleep(5)
                    continue
                budget = MAX_TOKENS
                obj, method = parse_json(text)
                if obj is None:
                    emit({"event": "teacher-round", "doc": doc_id, "round": rnd,
                          "seconds": round(dt, 2), "reasoning_tokens": rt,
                          "parse": method, "chars": len(text),
                          "proof": {"passed": 0, "failed": 0},
                          "raw": text[:4000]})
                    messages = messages + [
                        {"role": "assistant", "content": text},
                        {"role": "user", "content": "That was not valid JSON. "
                         "Return the JSON object only, no prose."}]
                    continue
                res = v02.validate_v02(obj, FILE_SET, content, ops_validate)
                last_obj = obj
                if best is None or len(res["passed"]) > len(best["passed"]):
                    best = res
                emit({"event": "teacher-round", "doc": doc_id, "round": rnd,
                      "seconds": round(dt, 2), "reasoning_tokens": rt,
                      "parse": method, "chars": len(text),
                      "proof": {"passed": len(res["passed"]),
                                "failed": len(res["failed"]),
                                "reasons": [f"op{v['index']}[{v['target']}]: "
                                            + "; ".join(v["reasons"])
                                            for v in res["verdicts"] if not v["pass"]]},
                      "raw": text[:4000]})
                if res["failed"] and rnd < MAX_ROUNDS:
                    messages = messages + [
                        {"role": "assistant", "content": text},
                        {"role": "user", "content":
                         "Proof rejected some ops. Keep every PASSING op "
                         "byte-identical; change only the rejected ones. "
                         "Each quote must be ONE contiguous substring copied "
                         "character-for-character from the section -- never "
                         "join spans with '...' and never paraphrase. If the "
                         "value is normalised (ISO date, decimal), quote a "
                         "span containing the subject instead:\n- "
                         + "\n- ".join(
                             f"op{v['index']}[{v['target']}]: " + "; ".join(v["reasons"])
                             for v in res["verdicts"] if not v["pass"])
                         + "\nReturn the corrected full JSON only, no prose."}]
                    verdict = res
                    continue
                verdict = res
                break
            final = best if best is not None else verdict
            if final is None or not final["passed"]:
                emit({"event": "teacher-failed", "doc": doc_id, "rounds": rounds})
                out["labels"][doc_id] = {"ops": [], "_teacher_failed": True,
                                         "_rounds": rounds}
            else:
                if best is not None and verdict is not None and best is not verdict:
                    emit({"event": "teacher-best-round", "doc": doc_id,
                          "best_passed": len(best["passed"]),
                          "last_passed": len(verdict["passed"])})
                emit({"event": "teacher-accepted", "doc": doc_id, "rounds": rounds,
                      "passed": len(final["passed"]),
                      "dropped": len(final["failed"])})
                out["labels"][doc_id] = {
                    "ops": [{k: v for k, v in o.items() if not k.startswith("_")}
                            for o in final["passed"]],
                    "spans": [o["_span"] for o in final["passed"]],
                    "_rounds": rounds,
                    "_dropped": len(final["failed"])}
    (HERE / "teacher.json").write_text(json.dumps(out, indent=1) + "\n")
    n_ok = sum(1 for o in out["labels"].values() if not o.get("_teacher_failed"))
    print(f"docs={len(out['labels'])} accepted={n_ok} log={log_path}")
    failed = [d for d, o in out["labels"].items() if o.get("_teacher_failed")]
    if failed:
        print(f"TEACHER-FAILED docs: {failed}")


if __name__ == "__main__":
    sys.exit(main())
