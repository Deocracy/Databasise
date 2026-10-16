#!/usr/bin/env python3
"""Coverage trace gate: S3/S4/S5 quote traces cover every due done/verified row."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path


def _baklog(root, part, event, decision, reason, target=None, session=None):
    try:
        import importlib.util
        here = Path(__file__).resolve()
        for cand in (here.parent / "baklog.py",):  # the kit copy beside this script
            if cand.is_file():
                spec = importlib.util.spec_from_file_location("baklog", str(cand))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.append(str(root), part, event, decision, reason, target=target, session=session)
    except BaseException:
        pass
    return None


ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
DONE = ("done", "verified")
STEPS = ("S3", "S4", "S5")
FILE_RE = re.compile(r"^s([345])(?:-([a-z0-9][a-z0-9-]{0,39}))?\.json$")


def check_key(root, path_part):
    """Canonical key of an artifact path: resolved under root, relative to
    root, in POSIX form. trace-check.py holds the same code as check_key in
    phase-gate.py and ledger-amend.py, plus its own canonical-spelling rule
    (ruling R25): a key that differs from the returned string is refused with
    "must be written as <key>", so ./x or x/../y cannot slip past the
    BAK-record and S3/S4 checks under another spelling. Raises ValueError
    with the stale reason for an absolute path, one that leaves root, or one
    that passes through a symlink (resolved and lexically normalized paths
    differ)."""
    if Path(path_part).anchor:
        raise ValueError("must be relative")
    try:
        root_r = Path(root).resolve()
        target = (root_r / path_part).resolve()
        key = target.relative_to(root_r).as_posix()
    except (OSError, RuntimeError, ValueError):
        raise ValueError("escapes root") from None
    if target != Path(os.path.normpath(root_r / path_part)):
        raise ValueError("must not pass through a symlink")
    if path_part != key:
        raise ValueError(f"must be written as {key}")
    return key


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def clean(cell):
    """One line per violation, and only info or extra lines carry their marker."""
    out = dict(cell)
    out["detail"] = CONTROL_RE.sub(" ", str(cell["detail"]))
    if isinstance(cell.get("id"), str):
        out["id"] = CONTROL_RE.sub(" ", cell["id"])
    if cell["class"] not in ("info", "extra"):
        out["detail"] = out["detail"].replace(": info (", ":info (").replace(
            ": extra ", ":extra ")
    return out


def parse_phase(value):
    if isinstance(value, str) and value.strip().lower() == "backlog":
        return (10 ** 9,)
    try:
        parts = str(value).strip().split(".")
        if not parts or any(p == "" for p in parts):
            return None
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def completed_at_map(ops):
    done_at = {}
    for op in ops:
        if not isinstance(op, dict):
            continue
        changes = op.get("changes")
        moved = changes.get("status") if isinstance(changes, dict) else None
        if isinstance(moved, list) and len(moved) == 2 and moved[0] not in DONE \
                and moved[1] in DONE and isinstance(op.get("v"), int):
            done_at[op.get("id")] = op["v"]
    return done_at


def due_done_rows(data):
    cur_raw = data.get("current_phase")
    cur_p = parse_phase(cur_raw) if isinstance(cur_raw, str) and cur_raw.strip() else None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    rows = []
    for row in items:
        if not isinstance(row, dict):
            continue
        if row.get("status") not in DONE:
            continue
        rp_raw = str(row.get("phase", ""))
        row_p = parse_phase(rp_raw) if rp_raw.strip() else None
        if not rp_raw.strip() or cur_p is None or row_p is None or row_p <= cur_p:
            rows.append(row)
    return rows


def file_sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def split_lines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def read_lines(path):
    try:
        return split_lines(Path(path).read_text(encoding="utf-8",
                                                 errors="replace"))
    except OSError:
        return None


def quote_ok(quote, where_line, lines):
    if not isinstance(quote, str) or not quote.strip():
        return False
    if not isinstance(where_line, int) or where_line < 1 or where_line > len(lines):
        return False
    span = len(quote.split("\n"))
    window = "\n".join(lines[where_line - 1:where_line + span])
    want = normalize(quote)
    return bool(want) and want in normalize(window)


BAK_DIRS = ("ledger/", "trace/", "debug/", "verifier/", ".bak/")


def is_bak_record(path):
    return path in ("ledger", "trace", "debug", "verifier", ".bak") \
        or path.startswith(BAK_DIRS)


def validate_file(root_r, fname, step, part, data, s3s4_paths=None):
    """(violations, entries) where entries holds usable per-id cells. A file
    returning valid False is left out of the coverage union."""
    vio = []
    if not isinstance(data, dict):
        return [{"id": None, "step": None, "class": "invalid", "file": fname,
                 "detail": f"{fname}: invalid (top-level JSON must be an object)"}], None
    for key in ("bak_trace", "step", "part", "ledger_version", "artifacts",
                "checker", "items", "extra"):
        if key not in data:
            return [{"id": None, "step": step, "class": "invalid", "file": fname,
                     "detail": f"{fname}: invalid (missing key \"{key}\")"}], None
    if data["bak_trace"] != 1 or isinstance(data["bak_trace"], bool):
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (bak_trace must be 1)"})
        return vio, None
    if data["step"] != step:
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (step \"{data['step']}\" "
                              "does not match file name)"})
        return vio, None
    if data["part"] != part:
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (part does not match file name)"})
        return vio, None
    if not isinstance(data["ledger_version"], int) or isinstance(data["ledger_version"], bool):
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (ledger_version must be an integer)"})
        return vio, None
    arts = data["artifacts"]
    if not isinstance(arts, dict) or not arts \
            or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v
                   for k, v in arts.items()):
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (artifacts must be a non-empty map)"})
        return vio, None
    checker = data["checker"]
    if not isinstance(checker, dict) or checker.get("harness") not in ("claude-code", "dsh", "script") \
            or not isinstance(checker.get("model"), str) \
            or not isinstance(checker.get("session"), str):
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (checker must name harness, model, session)"})
        return vio, None
    if not isinstance(data["items"], list) or not isinstance(data["extra"], list):
        vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                    "detail": f"{fname}: invalid (items and extra must be lists)"})
        return vio, None
    for entry in data["items"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) \
                or entry.get("status") not in ("present", "missing", "cut"):
            vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                        "detail": f"{fname}: invalid (entry must hold id and status)"})
            return vio, None
        if entry["status"] == "present" and (
                not isinstance(entry.get("where"), str)
                or not isinstance(entry.get("quote"), str)):
            vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                        "detail": f"{fname}: invalid (present entry needs where and quote)"})
            return vio, None
    for cell in data["extra"]:
        if not isinstance(cell, dict) or not isinstance(cell.get("where"), str) \
                or not isinstance(cell.get("quote"), str) \
                or not isinstance(cell.get("note"), str):
            vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                        "detail": f"{fname}: invalid (extra needs where, quote, note)"})
            return vio, None
    seen = set()
    for entry in data["items"]:
        if entry["id"] in seen:
            vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                        "detail": f"{fname}: invalid (duplicate id {entry['id']})"})
            return vio, None
        seen.add(entry["id"])
    stale = None
    for path, want in arts.items():
        try:
            check_key(root_r, path)
        except ValueError as exc:
            stale = (path, str(exc))
            break
        target = root_r / Path(path)
        if not target.is_file():
            stale = (path, "missing")
            break
        if file_sha(target) != want:
            stale = (path, "hash mismatch")
            break
    if stale is not None:
        path, reason = stale
        vio.append({"id": None, "step": step, "class": "stale", "file": fname,
                    "detail": f"{fname}: stale (artifact {path} {reason})"})
        return vio, None
    for path in sorted(arts):
        if is_bak_record(path):
            vio.append({"id": None, "step": step, "class": "invalid",
                        "file": fname,
                        "detail": f"{fname}: invalid (artifact {path} "
                                  "is a BAK record, not work)"})
            return vio, None
    if step == "S5" and s3s4_paths:
        for path in sorted(arts):
            if path in s3s4_paths:
                vio.append({"id": None, "step": step, "class": "invalid",
                            "file": fname,
                            "detail": f"{fname}: invalid (artifact {path} "
                                      "is an S3/S4 document and cannot be "
                                      "S5 evidence)"})
                return vio, None
    texts = {}
    for path in arts:
        lines = read_lines(root_r / Path(path))
        texts[path] = lines if lines is not None else []
    return vio, {"artifacts": arts, "texts": texts, "items": data["items"],
                 "extra": data["extra"]}


def where_split(where):
    head, sep, tail = where.rpartition(":")
    if not sep or not head or not (tail.isascii() and tail.isdigit()):
        return None, None
    return head, int(tail)


def load_extensions(script_path, root_r, ledger, trace_dir, step=None):
    vio = []
    try:
        sib = sorted(p for p in Path(script_path).parent.glob("trace_s*.py"))
    except OSError:
        return vio
    for mod_path in sib:
        name = mod_path.stem
        try:
            spec = importlib.util.spec_from_file_location(name, mod_path)
            if spec is None or spec.loader is None:
                raise ImportError(name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            found = module.check(str(root_r), ledger, trace_dir)
            for cell in found:
                if step is not None and cell.get("step") is not None \
                        and cell.get("step") != step:
                    continue
                vio.append({"id": cell.get("id"), "step": cell.get("step"),
                            "class": cell.get("class"), "file": cell.get("file"),
                            "detail": cell.get("detail")})
        except (Exception, SystemExit):
            vio.append({"id": None, "step": None, "class": "invalid", "file": None,
                        "detail": f"trace-check: cannot load {name}"})
    return vio


LEDGER_FILE = "ledger/REQUIREMENTS.json"


def ledger_error(args, detail):
    if args.json:
        print(json.dumps({"violations": [{"id": None, "step": None,
                                           "class": "invalid",
                                           "file": LEDGER_FILE,
                                           "detail": detail}]}))
    else:
        print(detail)
    _baklog(args.root, "3.9 trace-check", "trace-check", "fail", detail)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trace-check.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--step", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.step is not None and not re.match(r"^S[0-9]$", args.step):
        ap.error(f"argument --step: invalid choice: {args.step!r} "
                 "(choose from S0-S9)")
    root = Path(args.root)
    ledger = root / "ledger" / "REQUIREMENTS.json"
    log = root / "ledger" / "history" / "log.jsonl"
    if not ledger.is_file():
        return ledger_error(args, "LEDGER: REQUIREMENTS.json missing")
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        return ledger_error(args, "LEDGER: REQUIREMENTS.json unparsable")
    if not isinstance(data, dict):
        return ledger_error(args, "LEDGER: REQUIREMENTS.json must be a JSON object")
    if not log.is_file():
        return ledger_error(args, "LEDGER: history/log.jsonl missing")
    try:
        ops = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    except Exception:
        return ledger_error(args, "LEDGER: history/log.jsonl unparsable")
    items = data.get("items")
    if not isinstance(items, list):
        return ledger_error(args, "LEDGER: items is not a list")
    trace = data.get("trace", None)
    if trace is None:
        if args.json:
            print(json.dumps({"violations": [], "trace": "not enabled"}))
        else:
            print("trace: not enabled")
        _baklog(root, "3.9 trace-check", "trace-check", "info", "trace: not enabled")
        return 0
    if not isinstance(trace, dict) or trace.get("kind") not in ("code", "document") \
            or not isinstance(trace.get("since"), int) or isinstance(trace.get("since"), bool):
        return ledger_error(args, "LEDGER: trace must be null or {kind, since}")
    steps = [args.step] if args.step else list(STEPS)
    ledger_ids = {str(r.get("id")) for r in items if isinstance(r, dict)}
    row_status_of = {str(r.get("id")): r.get("status")
                     for r in items if isinstance(r, dict)}
    done_at = completed_at_map(ops)
    since = trace["since"]
    trace_dir = root / "trace"
    files = []
    if trace_dir.is_dir():
        for path in sorted(trace_dir.glob("*.json")):
            m = FILE_RE.match(path.name)
            if not m:
                continue
            files.append((path, "S" + m.group(1), m.group(2)))
    violations = []
    usable = {}
    raw_docs = {}
    for path, step, part in files:
        fname = f"trace/{path.name}"
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            if step in steps:
                violations.append({"id": None, "step": step, "class": "invalid",
                                   "file": fname,
                                   "detail": f"{fname}: invalid (file does not parse)"})
            continue
        raw_docs[fname] = content
    # F1: raw_docs holds every S3/S4 file even under --step S5, so the R10
    # cross-step rule below sees them; only the selected steps are validated.
    files = [f for f in files if f[1] in steps]
    if "S5" in steps:
        s3s4_paths = set()
        for fname, content in raw_docs.items():
            arts = content.get("artifacts") if isinstance(content, dict) else None
            step_of = content.get("step") if isinstance(content, dict) else None
            if step_of in ("S3", "S4") and isinstance(arts, dict) and arts \
                    and all(isinstance(k, str) and k
                            and isinstance(v, str) and v
                            for k, v in arts.items()):
                s3s4_paths.update(arts)
    else:
        s3s4_paths = set()
    for path, step, part in files:
        fname = f"trace/{path.name}"
        content = raw_docs.get(fname)
        if content is None:
            continue
        vio, valid = validate_file(root.resolve(), fname, step, part, content,
                                   s3s4_paths if step == "S5" else None)
        violations.extend(vio)
        if valid is None:
            continue
        per_id = {}
        for entry in valid["items"]:
            rid = entry["id"]
            if not ID_RE.match(rid):
                violations.append({"id": rid, "step": step, "class": "unknown-item",
                                   "file": fname,
                                   "detail": f"{rid}: unknown-item in {fname} "
                                             "(id is malformed)"})
                continue
            if rid not in ledger_ids:
                violations.append({"id": rid, "step": step, "class": "unknown-item",
                                   "file": fname,
                                   "detail": f"{rid}: unknown-item in {fname} "
                                             "(no such ledger row)"})
                continue
            row_status = row_status_of.get(rid)
            if entry["status"] == "present":
                rel, line = where_split(entry["where"])
                if rel not in valid["artifacts"] or line is None:
                    violations.append({"id": rid, "step": step,
                                       "class": "quote-not-found", "file": fname,
                                       "detail": f"{rid}: quote-not-found at {step} "
                                                 f"(quote not found at {entry['where']} "
                                                 f"in {fname})"})
                elif not quote_ok(entry["quote"], line, valid["texts"][rel]):
                    violations.append({"id": rid, "step": step,
                                       "class": "quote-not-found", "file": fname,
                                       "detail": f"{rid}: quote-not-found at {step} "
                                                 f"(quote not found at {entry['where']} "
                                                 f"in {fname})"})
                else:
                    per_id.setdefault(rid, []).append("present")
            elif entry["status"] == "missing":
                per_id.setdefault(rid, []).append("missing")
            else:
                if row_status not in ("dropped", "deferred-approved"):
                    violations.append({"id": rid, "step": step,
                                       "class": "cut-without-owner",
                                       "file": fname,
                                       "detail": f"{rid}: cut-without-owner at "
                                                 f"{step} (row status "
                                                 f"{row_status})"})
                per_id.setdefault(rid, []).append("cut")
        for cell in valid["extra"]:
            rel, line = where_split(cell["where"])
            if rel not in valid["artifacts"] or line is None \
                    or not quote_ok(cell["quote"], line, valid["texts"][rel]):
                violations.append({"id": None, "step": step,
                                   "class": "quote-not-found", "file": fname,
                                   "detail": f"{fname}: quote-not-found at "
                                             f"{cell['where']} (extra quote not found)"})
                continue
            note = cell["note"].strip() or cell["quote"][:40]
            violations.append({"id": None, "step": step, "class": "extra",
                               "file": fname,
                               "detail": f"{fname}: extra at {cell['where']} ({note})"})
        usable.setdefault(step, []).append(per_id)
    due = due_done_rows(data)
    if due is None:
        return ledger_error(args, "LEDGER: items is not a list")
    for row in due:
        rid = str(row.get("id", "?"))
        done_v = done_at.get(rid)
        if done_v is not None and done_v <= since:
            continue
        for step in [s for s in steps if s in STEPS]:  # R19: modules own S2, S7
            cells = []
            for per_id in usable.get(step, []):
                cells.extend(per_id.get(rid, []))
            if "present" in cells:
                continue
            if "missing" in cells:
                violations.append({"id": rid, "step": step, "class": "missing",
                                   "file": None,
                                   "detail": f"{rid}: missing at {step}"})
            elif "cut" in cells:
                continue
            else:
                violations.append({"id": rid, "step": step,
                                   "class": "not-checked", "file": None,
                                   "detail": f"{rid}: not-checked at {step}"})
    violations = [clean(cell) for cell in violations]
    violations.extend(load_extensions(__file__, root.resolve(), data,
                                      trace_dir, args.step))
    if args.json:
        print(json.dumps({"violations": violations}))
    else:
        for cell in violations:
            print(cell["detail"])
    hard = [c for c in violations if c["class"] not in ("extra", "info")]
    _baklog(root, "3.9 trace-check", "trace-check", "fail" if hard else "pass", "\n".join(str(c["detail"]) for c in hard) or "no hard violations")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
