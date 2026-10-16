"""S2 extraction rules (P2): two independent extractions cover the frozen rows."""
import importlib.util
import json
import re
from pathlib import Path


def load_p1():
    """trace-check.py beside this module: its line split, quote window and
    where parser are used as they are, never copied."""
    spec = importlib.util.spec_from_file_location(
        "bak_trace_check", Path(__file__).with_name("trace-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P1 = load_p1()
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
HARNESS = ("claude-code", "dsh", "script")
WORDS = "trace/s1-words.md"
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f  ]")


def clean(cell):
    """One line per violation; the shared copy in trace-check.py owns the rule."""
    return P1.clean(cell)


def log_ops(root_r):
    try:
        text = (root_r / "ledger" / "history" / "log.jsonl").read_text(
            encoding="utf-8")
    except OSError:
        return None
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except Exception:
        return None


def freeze_op(ops):
    for op in ops:
        if isinstance(op, dict) and op.get("op") == "freeze" \
                and isinstance(op.get("v"), int):
            return op
    return None


def added_at(ops):
    at = {}
    for op in ops:
        if isinstance(op, dict) and op.get("op") == "add" \
                and isinstance(op.get("id"), str) \
                and isinstance(op.get("v"), int):
            at.setdefault(op["id"], op["v"])
    return at


def enable_since(ops):
    for op in ops:
        if isinstance(op, dict) and op.get("op") == "enable-trace" \
                and isinstance(op.get("v"), int):
            return op["v"]
    return None


def load_rules(kind):
    """Rule ids of implied-items-<kind>.json: beside this script (a project's
    scripts/), then ../templates, then ../core/templates (the kit)."""
    here = Path(__file__).resolve().parent
    name = f"implied-items-{kind}.json"
    for path in (here / name, here.parent / "templates" / name,
                 here.parent / "core" / "templates" / name):
        if path.is_file():
            try:
                cats = json.loads(path.read_text(encoding="utf-8"))["categories"]
                return {c.get("name") for c in cats if isinstance(c, dict)}, None
            except Exception:
                return None, "checklist file does not parse"
    return None, "checklist file not found"


def invalid(fname, why):
    return {"id": None, "step": "S2", "class": "invalid", "file": fname,
            "detail": f"{fname}: invalid ({why})"}


def info(fname, text):
    return {"id": None, "step": "S2", "class": "info", "file": fname,
            "detail": f"{fname}: info ({text})"}


def load_one(root_r, fname):
    path = root_r / fname
    if not path.is_file():
        return None, {"id": None, "step": "S2", "class": "missing", "file": fname,
                      "detail": f"{fname}: missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception:
        return None, invalid(fname, "file does not parse")


def validate_shape(fname, part, data):
    if not isinstance(data, dict):
        return invalid(fname, "top-level JSON must be an object")
    for key in ("bak_trace", "step", "part", "source", "checker", "candidates"):
        if key not in data:
            return invalid(fname, f"missing key \"{key}\"")
    if data["bak_trace"] != 1 or isinstance(data["bak_trace"], bool):
        return invalid(fname, "bak_trace must be 1")
    if data["step"] != "S2" or data["part"] != part:
        return invalid(fname, "step or part does not match file name")
    if "ledger_version" in data and (
            not isinstance(data["ledger_version"], int)
            or isinstance(data["ledger_version"], bool)):
        return invalid(fname, "ledger_version must be an integer")
    if not isinstance(data["source"], dict) or not data["source"]:
        return invalid(fname, "source must be a non-empty map")
    checker = data["checker"]
    if not isinstance(checker, dict) or checker.get("harness") not in HARNESS \
            or not isinstance(checker.get("model"), str) \
            or not isinstance(checker.get("session"), str):
        return invalid(fname, "checker must name harness, model, session")
    if not isinstance(data["candidates"], list):
        return invalid(fname, "candidates must be a list")
    for cell in data["candidates"]:
        if not isinstance(cell, dict) or not isinstance(cell.get("text"), str) \
                or not isinstance(cell.get("where"), str):
            return invalid(fname, "candidate needs text and where")
    return None


def candidate_key(cell):
    rid = cell.get("id")
    if isinstance(rid, str) and rid:
        return "id", rid
    return "text", P1.normalize(cell["text"]).casefold()


def difference_lines(files):
    """Spec G1: show the owner each candidate that only one extraction found,
    matched by ledger id, or by normalized text when the id is null."""
    keys = {part: {candidate_key(c) for c in data["candidates"]}
            for part, data in files.items()}
    out = []
    for part, other in (("a", "b"), ("b", "a")):
        for num, cell in enumerate(files[part]["candidates"], start=1):
            key = candidate_key(cell)
            if key in keys[other]:
                continue
            label = cell["text"] if key[0] == "text" else f"{key[1]} {cell['text']}"
            out.append(info(f"trace/s2-{part}.json",
                            f"candidate {num} not in trace/s2-{other}.json: {label}"))
    return out


def decision_lines(fname, data):
    return [info(fname, f"candidate {num} not-a-requirement: {cell.get('reason', '')}")
            for num, cell in enumerate(data["candidates"], start=1)
            if cell.get("decision") == "not-a-requirement"]


def check(root, ledger, trace_dir):
    return [clean(cell) for cell in check_raw(Path(root), ledger)]


def check_raw(root_r, ledger):
    ops = log_ops(root_r)
    if ops is None:
        return []
    freeze = freeze_op(ops)
    if freeze is None:
        return []
    frozen_v = freeze["v"]
    since = enable_since(ops)
    if since is not None and since > frozen_v:
        return []
    trace = ledger.get("trace") if isinstance(ledger, dict) else None
    kind = trace.get("kind") if isinstance(trace, dict) else "code"
    if kind not in ("code", "document"):
        return []
    words_path = root_r / WORDS
    words_sha = P1.file_sha(words_path)
    bound = freeze.get("words_sha256")  # R18; absent when no words file existed
    if isinstance(bound, str) and words_sha != bound:
        return [invalid(WORDS, f"{WORDS} changed since the freeze")]
    words_lines = P1.read_lines(words_path)
    vio = []
    rule_ids, why = load_rules(kind)
    if rule_ids is None:
        vio.append({"id": None, "step": "S2", "class": "invalid", "file": None,
                    "detail": f"implied-items-{kind}.json: invalid ({why})"})
    files = {}
    for part in ("a", "b"):
        fname = f"trace/s2-{part}.json"
        data, err = load_one(root_r, fname)
        err = err or validate_shape(fname, part, data)
        if err is not None:
            vio.append(err)
            continue
        if words_lines is None or data["source"].get(WORDS) != words_sha:
            vio.append({"id": None, "step": "S2", "class": "stale", "file": fname,
                        "detail": f"{fname}: stale (source {WORDS} hash mismatch)"})
            continue
        files[part] = data
    if len(files) < 2:
        for part, data in files.items():
            vio.extend(decision_lines(f"trace/s2-{part}.json", data))
        return vio
    if files["a"]["checker"]["session"] == files["b"]["checker"]["session"]:
        vio.append(invalid("trace/s2-b.json", "checker sessions must differ"))
    at = added_at(ops)
    rows = [r for r in ledger.get("items", [])
            if isinstance(r, dict) and isinstance(r.get("id"), str)]
    known = {r["id"] for r in rows}
    # I8: a row the owner dropped or deferred needs no source in the words.
    frozen_ids = {r["id"] for r in rows if at.get(r["id"], 0) <= frozen_v
                  and r.get("status") not in ("dropped", "deferred-approved")}
    referenced = set()
    for part, data in files.items():
        fname = f"trace/s2-{part}.json"
        for num, cell in enumerate(data["candidates"], start=1):
            where = cell["where"]
            rid = cell.get("id")
            reason = cell.get("reason", "")
            if where.startswith(WORDS + ":"):
                head, line = P1.where_split(where)
                if head != WORDS or line is None \
                        or not P1.quote_ok(cell.get("quote") or "", line, words_lines):
                    vio.append({"id": None, "step": "S2", "class": "quote-not-found",
                                "file": fname,
                                "detail": f"{fname}: quote-not-found at {where} "
                                          "(words quote not found)"})
            elif where.startswith("checklist:"):
                rule = where.split(":", 1)[1]
                if rule_ids is not None and rule not in rule_ids:
                    vio.append(invalid(fname, f"unknown checklist rule {rule}"))
            else:
                vio.append(invalid(fname, f"candidate {num} has a bad where"))
            if isinstance(rid, str) and rid:
                if not ID_RE.match(rid):
                    vio.append({"id": rid, "step": "S2", "class": "unknown-item",
                                "file": fname,
                                "detail": f"{rid}: unknown-item in {fname} (id is malformed)"})
                elif rid not in known:
                    vio.append({"id": rid, "step": "S2", "class": "unknown-item",
                                "file": fname,
                                "detail": f"{rid}: unknown-item in {fname} (no such ledger row)"})
                else:
                    referenced.add(rid)
            elif cell.get("decision") == "not-a-requirement" \
                    and isinstance(reason, str) and reason.strip():
                vio.append(info(fname, f"candidate {num} not-a-requirement: {reason}"))
            else:
                vio.append({"id": None, "step": "S2", "class": "not-captured",
                            "file": fname,
                            "detail": f"{fname}: not-captured (candidate {num} "
                                      "has no ledger id)"})
    for rid in sorted(frozen_ids - referenced):
        vio.append({"id": rid, "step": "S2", "class": "no-source",
                    "file": None, "detail": f"{rid}: no-source at S2"})
    vio.extend(difference_lines(files))
    return vio
