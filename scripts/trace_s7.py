"""S7 review rules (P2): verified rows need a PASS verdict with valid evidence."""
import importlib.util
import json
import re
from pathlib import Path


def load_p1():
    """trace-check.py beside this module: its line split, quote window, where
    parser, check_key and C1 rules are used as they are, never copied."""
    spec = importlib.util.spec_from_file_location(
        "bak_trace_check", Path(__file__).with_name("trace-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P1 = load_p1()
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
FILE_RE = re.compile(r"^s7(?:-([a-z0-9][a-z0-9-]{0,39}))?\.json$")
FILE_LINE_RE = re.compile(r"^[^:\s]+\.[A-Za-z0-9]+:[0-9]+$")
EXIT_RE = re.compile(r"exit\s*[:=]?\s*\d+", re.IGNORECASE)
EXIT0_RE = re.compile(r"exit\s*[:=]?\s*0\b", re.IGNORECASE)
SCREEN_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f  ]")


def clean(cell):
    """One line per violation; the shared copy in trace-check.py owns the rule."""
    return P1.clean(cell)


def resolve_under(root_r, rel):
    try:
        target = (root_r / rel).resolve()
    except Exception:
        return None
    try:
        if not target.is_relative_to(root_r):
            return None
    except Exception:
        return None
    return target


def file_line_ok(part, root_r):
    if not FILE_LINE_RE.match(part):
        return False
    path_s, _, line_s = part.rpartition(":")
    try:
        lineno = int(line_s)
    except ValueError:
        return False
    if lineno < 1:
        return False
    target = resolve_under(root_r, path_s.strip())
    if target is None or not target.is_file():
        return False
    try:
        with target.open(encoding="utf-8", errors="ignore") as fh:
            return lineno <= sum(1 for _ in fh)
    except OSError:
        return False


def screenshot_ok(part, root_r):
    text = part.strip()
    rel = text[2:] if text.startswith("./") else text
    low = rel.lower()
    if not rel.startswith("verifier/evidence/") \
            or not low.endswith(SCREEN_EXTS):
        return False
    target = resolve_under(root_r, rel)
    try:
        ev_dir = (root_r / "verifier" / "evidence").resolve()
    except Exception:
        return False
    try:
        if target is None or not target.is_relative_to(ev_dir):
            return False
    except Exception:
        return False
    try:
        return target.is_file()
    except OSError:
        return False


def split_parts(evidence):
    return [p.strip() for p in str(evidence).split(";") if p.strip()]


RUN_RE = re.compile(r"^run:(\d+)$")


def check_runs_by_version(root_r):
    """The ledger log's check-run ops by ledger version (C11.6)."""
    runs = {}
    for op in log_ops(root_r):
        if isinstance(op, dict) and op.get("op") == "check-run" \
                and isinstance(op.get("v"), int) and not isinstance(op.get("v"), bool):
            runs[op["v"]] = op
    return runs


def _is_ancestor(root_r, commit):
    """PB-R9: the S7 document's commit must be HEAD or an ancestor of HEAD."""
    try:
        import subprocess
        if not isinstance(commit, str) or not commit.strip():
            return False
        head = subprocess.run(["git", "-C", str(root_r), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30)
        if head.returncode != 0 or not head.stdout.strip():
            return False
        if head.stdout.strip() == commit.strip():
            return True
        anc = subprocess.run(["git", "-C", str(root_r), "merge-base",
                              "--is-ancestor", commit.strip(),
                              head.stdout.strip()],
                             capture_output=True, text=True, timeout=30)
        return anc.returncode == 0
    except Exception:
        return ""


def head_now(root_r):
    try:
        import subprocess
        proc = subprocess.run(["git", "-C", str(root_r), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        return ""


def _cmd_names_path(cmd, path_part):
    """PB-R9: the run's cmd must name the check path, as record-fail requires
    (the path in the command itself, not in a # comment)."""
    import shlex as _shlex
    if not isinstance(cmd, str) or not isinstance(path_part, str):
        return False
    if not path_part.strip():
        return False
    try:
        raw = _shlex.split(cmd, comments=False)
        tokens = []
        for token in raw:
            if token.startswith("#"):
                break
            tokens.append(token)
    except ValueError:
        return False
    return any(path_part in token for token in tokens)


def _row_test_ref(ledger, rid):
    for row in ledger.get("items", []) if isinstance(ledger, dict) else []:
        if isinstance(row, dict) and str(row.get("id")) == rid:
            ref = row.get("test_ref")
            return ref if isinstance(ref, str) else ""
    return ""


def _run_op_ok(op, rid, test_ref):
    """PB-R9: the run must be this row's own check run: same ref, cmd naming
    the check path, non-empty output."""
    if not isinstance(op, dict) or op.get("id") != rid:
        return False
    if not (op.get("exit") == 0 and op.get("tree_clean") is True):
        return False
    ref = op.get("ref")
    if not isinstance(ref, str) or not ref.strip():
        return False
    if not isinstance(test_ref, str) or not test_ref.strip():
        return False
    if ref != test_ref:
        return False
    path_part = test_ref.split("::", 1)[0].strip()
    if not _cmd_names_path(op.get("cmd"), path_part):
        return False
    out = op.get("output")
    return isinstance(out, str) and bool(out.strip())


def _is_document_kind(ledger):
    """R38: the ledger's trace kind is `document` (a text row has no test_ref,
    so no recorded run of its own check can exist)."""
    trace = ledger.get("trace") if isinstance(ledger, dict) else None
    return isinstance(trace, dict) and trace.get("kind") == "document"


def pass_kinds(evidence, root_r, arts, rid=None, ledger=None, doc_commit=None):
    """(file, exit0, screenshot, run): the kinds of PASS evidence cited. A
    run:<v> part counts when op v is this row's own check-run (PB-R9) that
    exited 0 on a clean tree with head equal to the S7 document's commit
    (C11.6, PB-R9), and that commit is HEAD or an ancestor of HEAD."""
    parts = split_parts(evidence) if isinstance(evidence, str) else []
    has_file = any(file_line_ok(p, root_r) and p.rpartition(":")[0] in arts
                   for p in parts)
    has_exit0 = any(EXIT0_RE.search(p) for p in parts)
    has_shot = any(screenshot_ok(p, root_r) for p in parts)
    has_run = False
    wanted = [int(m.group(1)) for m in map(RUN_RE.match, parts) if m]
    if wanted and isinstance(doc_commit, str) and doc_commit.strip() \
            and _is_ancestor(root_r, doc_commit):
        runs = check_runs_by_version(root_r)
        test_ref = _row_test_ref(ledger or {}, rid or "")
        for v in wanted:
            op = runs.get(v)
            if isinstance(op, dict) and (rid is None or op.get("id") == rid) \
                    and op.get("head") == doc_commit and _run_op_ok(op, rid, test_ref):
                has_run = True
    return has_file, has_exit0, has_shot, has_run


def pass_evidence_ok(evidence, root_r, arts, rid=None, ledger=None,
                     doc_commit=None):
    """R14: the file:line must be a key of artifacts, so it is hash-bound. The
    artifacts were already checked to be no BAK record and no S3/S4 document.
    R38: in a document project the hash-bound file:line alone is enough."""
    has_file, has_exit0, has_shot, has_run = pass_kinds(
        evidence, root_r, arts, rid, ledger, doc_commit)
    if _is_document_kind(ledger or {}):
        return has_file
    return has_file and (has_exit0 or has_shot or has_run)


def exit0_only(evidence, root_r, arts, rid=None, ledger=None, doc_commit=None):
    """A PASS whose only test evidence is typed `exit 0` text (C11.6)."""
    has_file, has_exit0, has_shot, has_run = pass_kinds(
        evidence, root_r, arts, rid, ledger, doc_commit)
    return has_file and has_exit0 and not has_shot and not has_run


def done_after_since(root_r, ledger, rid):
    """C11.6: with trace on, a row done after trace.since no longer takes typed
    `exit 0` as PASS evidence (set-status logs every move to done)."""
    trace = ledger.get("trace")
    since = trace.get("since") if isinstance(trace, dict) else None
    if not isinstance(since, int) or isinstance(since, bool):
        return False
    done_v = P1.completed_at_map(log_ops(root_r)).get(rid)
    return isinstance(done_v, int) and done_v > since


def fail_evidence_ok(evidence, root_r):
    if not isinstance(evidence, str):
        return False
    parts = split_parts(evidence)
    if not parts:
        return False
    for part in parts:
        if FILE_LINE_RE.match(part) and file_line_ok(part, root_r):
            return True
        if EXIT_RE.search(part):
            return True
        if screenshot_ok(part, root_r):
            return True
    return False


def evidence_ok(verdict, evidence, reason, root_r, arts, rid=None,
                ledger=None, doc_commit=None):
    if verdict == "PASS":
        return pass_evidence_ok(evidence, root_r, arts, rid, ledger,
                                doc_commit)
    if verdict == "FAIL":
        return fail_evidence_ok(evidence, root_r)
    return isinstance(reason, str) and bool(reason.strip())


def log_ops(root_r):
    try:
        text = (root_r / "ledger" / "history" / "log.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except Exception:
        return []


def due_verified_rows(root_r, ledger):
    """Verified rows that are due and not exempt: the C1 and due-phase rules
    of trace-check.py's coverage loop."""
    done_at = P1.completed_at_map(log_ops(root_r))
    trace = ledger.get("trace")
    since = trace.get("since") if isinstance(trace, dict) else None
    rows = []
    for row in P1.due_done_rows(ledger) or []:
        done_v = done_at.get(str(row.get("id", "?")))
        if row.get("status") != "verified" or (
                isinstance(since, int) and done_v is not None and done_v <= since):
            continue
        rows.append(row)
    return rows


def check(root, ledger, trace_dir):
    root_r = Path(root).resolve() if str(root) else Path(".").resolve()
    return [clean(cell) for cell in check_raw(root_r, ledger, trace_dir)]


def check_raw(root_r, ledger, trace_dir):
    vio = []
    try:
        base = Path(trace_dir)
        names = sorted(p.name for p in base.glob("*.json"))
    except OSError:
        return vio
    s3s4_docs = set()
    for name in names:
        mm = re.match(r"^s([34])(?:-([a-z0-9][a-z0-9-]{0,39}))?\.json$", name)
        if not mm:
            continue
        try:
            content = json.loads((base / name).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(content, dict) or content.get("step") not in ("S3", "S4"):
            continue
        arts = content.get("artifacts")
        if isinstance(arts, dict) and arts \
                and all(isinstance(k, str) and k
                        and isinstance(v, str) and v
                        for k, v in arts.items()):
            s3s4_docs.update(arts)
    usable = []
    for name in names:
        m = FILE_RE.match(name)
        if not m:
            continue
        fname = f"trace/{name}"
        part = m.group(1)
        try:
            data = json.loads((base / name).read_text(encoding="utf-8"))
        except Exception:
            vio.append({"id": None, "step": "S7", "class": "invalid",
                        "file": fname,
                        "detail": f"{fname}: invalid (file does not parse)"})
            continue
        if not isinstance(data, dict):
            vio.append({"id": None, "step": "S7", "class": "invalid",
                        "file": fname,
                        "detail": f"{fname}: invalid (top-level JSON must be an object)"})
            continue
        bad = None
        for key in ("bak_trace", "step", "part", "ledger_version",
                    "artifacts", "checker", "items", "extra"):
            if key not in data:
                bad = f"missing key \"{key}\""
        if bad is None and (data["bak_trace"] != 1
                            or isinstance(data["bak_trace"], bool)):
            bad = "bak_trace must be 1"
        if bad is None and (data["step"] != "S7" or data["part"] != part):
            bad = "step or part does not match file name"
        if bad is None and (not isinstance(data.get("ledger_version"), int)
                            or isinstance(data.get("ledger_version"), bool)):
            bad = "ledger_version must be an integer"
        arts = data.get("artifacts")
        if bad is None and (not isinstance(arts, dict) or not arts):
            bad = "artifacts must be a non-empty map"
        checker = data.get("checker")
        if bad is None and (not isinstance(checker, dict)
                            or checker.get("harness")
                            not in ("claude-code", "dsh", "script")
                            or not isinstance(checker.get("model"), str)
                            or not isinstance(checker.get("session"), str)):
            bad = "checker must name harness, model, session"
        if bad is None and (not isinstance(data.get("items"), list)
                            or not isinstance(data.get("extra"), list)):
            bad = "items and extra must be lists"
        if bad is not None:
            vio.append({"id": None, "step": "S7", "class": "invalid",
                        "file": fname, "detail": f"{fname}: invalid ({bad})"})
            continue
        stale = None
        for path, want in arts.items():
            try:
                P1.check_key(root_r, path)
            except ValueError as exc:
                stale = (path, str(exc))
                break
            target = root_r / Path(path)
            if not target.is_file():
                stale = (path, "missing")
                break
            if P1.file_sha(target) != want:
                stale = (path, "hash mismatch")
                break
        if stale is not None:
            path, reason = stale
            vio.append({"id": None, "step": "S7", "class": "stale",
                        "file": fname,
                        "detail": f"{fname}: stale (artifact {path} {reason})"})
            continue
        for path in sorted(arts):
            if P1.is_bak_record(path):
                vio.append({"id": None, "step": "S7", "class": "invalid",
                            "file": fname,
                            "detail": f"{fname}: invalid (artifact {path} "
                                      "is a BAK record, not work)"})
                stale = ("__invalid__", "")
                break
        if stale is not None and stale[0] == "__invalid__":
            continue
        for path in sorted(arts):
            if path in s3s4_docs:
                vio.append({"id": None, "step": "S7", "class": "invalid",
                            "file": fname,
                            "detail": f"{fname}: invalid (artifact {path} "
                                      "is an S3/S4 document and cannot be "
                                      "S7 evidence)"})
                stale = ("__invalid__", "")
                break
        if stale is not None and stale[0] == "__invalid__":
            continue
        texts = {}
        for path in arts:
            lines = P1.read_lines(root_r / Path(path))
            texts[path] = lines if lines is not None else []
        per_id = {}
        ok_file = True
        for entry in data["items"]:
            if not isinstance(entry, dict) \
                    or not isinstance(entry.get("id"), str) \
                    or entry.get("status") not in ("present", "missing", "cut"):
                vio.append({"id": None, "step": "S7", "class": "invalid",
                            "file": fname,
                            "detail": f"{fname}: invalid (entry must hold id and status)"})
                ok_file = False
                break
            rid = entry["id"]
            if rid in per_id:
                vio.append({"id": None, "step": "S7", "class": "invalid",
                            "file": fname,
                            "detail": f"{fname}: invalid (duplicate id {rid})"})
                ok_file = False
                break
            if not ID_RE.match(rid):
                vio.append({"id": rid, "step": "S7", "class": "unknown-item",
                            "file": fname,
                            "detail": f"{rid}: unknown-item in {fname} (id is malformed)"})
                per_id.setdefault(rid, []).append("bad")
                continue
            known = {str(r.get("id")) for r in ledger.get("items", [])
                     if isinstance(r, dict)}
            if rid not in known:
                vio.append({"id": rid, "step": "S7", "class": "unknown-item",
                            "file": fname,
                            "detail": f"{rid}: unknown-item in {fname} (no such ledger row)"})
                per_id.setdefault(rid, []).append("bad")
                continue
            if entry["status"] == "present":
                if not isinstance(entry.get("where"), str) \
                        or not isinstance(entry.get("quote"), str):
                    vio.append({"id": None, "step": "S7", "class": "invalid",
                                "file": fname,
                                "detail": f"{fname}: invalid (present entry needs where and quote)"})
                    ok_file = False
                    break
                rel, line = P1.where_split(entry["where"])
                if rel not in arts or line is None \
                        or not P1.quote_ok(entry["quote"], line, texts[rel]):
                    vio.append({"id": rid, "step": "S7",
                                "class": "quote-not-found", "file": fname,
                                "detail": f"{rid}: quote-not-found at S7 (quote not found "
                                          f"at {entry['where']} in {fname})"})
                    per_id.setdefault(rid, []).append("bad-quote")
                    continue
                if entry.get("verdict") not in ("PASS", "FAIL", "REVIEW") \
                        or not isinstance(entry.get("evidence"), str):
                    vio.append({"id": None, "step": "S7", "class": "invalid",
                                "file": fname,
                                "detail": f"{fname}: invalid ({rid} needs verdict and evidence)"})
                    ok_file = False
                    break
                doc_commit = data.get("commit")
                # R38: the "not a recorded run" refusal does not apply in a
                # document project, where the hash-bound file:line is enough.
                if entry["verdict"] == "PASS" \
                        and not _is_document_kind(ledger) \
                        and exit0_only(entry["evidence"], root_r, arts, rid,
                                       ledger, doc_commit) \
                        and done_after_since(root_r, ledger, rid):
                    vio.append({"id": rid, "step": "S7", "class": "invalid",
                                "file": fname,
                                "detail": f"{rid}: PASS evidence \"exit 0\" is not a "
                                          "recorded run (use run:<version>)"})
                    per_id.setdefault(rid, []).append("bad-evidence")
                    continue
                if not evidence_ok(entry["verdict"], entry["evidence"],
                                   entry.get("reason", ""), root_r, arts, rid,
                                   ledger, doc_commit):
                    vio.append({"id": None, "step": "S7", "class": "invalid",
                                "file": fname,
                                "detail": f"{fname}: invalid ({rid} {entry['verdict']} "
                                          "without valid evidence)"})
                    per_id.setdefault(rid, []).append("bad-evidence")
                    continue
                if entry["verdict"] == "PASS":
                    per_id.setdefault(rid, []).append("present")
                else:
                    per_id.setdefault(rid, []).append("verdict-" + entry["verdict"])
            elif entry["status"] == "missing":
                per_id.setdefault(rid, []).append("missing")
            else:
                per_id.setdefault(rid, []).append("cut")
        if ok_file:
            usable.append(per_id)
    for row in due_verified_rows(root_r, ledger):
        rid = str(row.get("id", "?"))
        cells = []
        for per_id in usable:
            cells.extend(per_id.get(rid, []))
        if "present" in cells or "bad-quote" in cells or "bad-evidence" in cells:
            if "present" in cells:
                continue
            if "bad-evidence" in cells and "present" not in cells:
                vio.append({"id": rid, "step": "S7", "class": "missing",
                            "file": None,
                            "detail": f"{rid}: missing at S7"})
                continue
            continue
        if "verdict-FAIL" in cells or "verdict-REVIEW" in cells:
            worst = "verdict-REVIEW" if "verdict-REVIEW" in cells else "verdict-FAIL"
            mark = worst.split("-", 1)[1]
            vio.append({"id": rid, "step": "S7", "class": "missing",
                        "file": None,
                        "detail": f"{rid}: missing at S7 (verdict {mark})"})
        elif "missing" in cells:
            vio.append({"id": rid, "step": "S7", "class": "missing",
                        "file": None, "detail": f"{rid}: missing at S7"})
        elif "cut" in cells:
            if row.get("status") in ("dropped", "deferred-approved"):
                continue
            vio.append({"id": rid, "step": "S7", "class": "cut-without-owner",
                        "file": None,
                        "detail": f"{rid}: cut-without-owner at S7 "
                                  f"(row status {row.get('status')})"})
        else:
            vio.append({"id": rid, "step": "S7", "class": "not-checked",
                        "file": None, "detail": f"{rid}: not-checked at S7"})
    return vio
