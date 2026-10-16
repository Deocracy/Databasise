#!/usr/bin/env python3
"""C3 extension module for S6, the merge check (contract C7).

The core of trace-check.py reads only s3/s4/s5 files, so this module checks
trace/s6.json and trace/s6-<part>.json itself, with the core's own C2
helpers: V1 to V4, plus an S6 checker harness of "script" (merge-check.py
is the only S6 writer). Once any S6 file exists, every due, non-exempt done
or verified row that is present in a valid S5 file must be present in a
valid S6 file, else "<ID>: missing at S6".

Ruling R28: an S6 file belongs to the commit merge-check.py wrote it at (its
checker session). In a git work tree, an S6 file whose session is not HEAD
gives one info line and is not checked; the S6 rules apply to the rest, and
to every S6 file outside a git work tree.
"""
import importlib.util
import json
import re
import subprocess
from pathlib import Path

FILE_RE = re.compile(r"^s([3456])(?:-([a-z0-9][a-z0-9-]{0,39}))?\.json$")


def load_core():
    spec = importlib.util.spec_from_file_location(
        "trace_check_core", Path(__file__).with_name("trace-check.py"))
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def head_of(root_r):
    """HEAD of the git work tree holding root_r ("" before the first commit),
    or None when root_r is in no work tree or git cannot run."""
    try:
        inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                                cwd=str(root_r), capture_output=True, text=True,
                                timeout=10)
        if inside.stdout.strip() != "true":
            return None
        head = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"],
                              cwd=str(root_r), capture_output=True, text=True,
                              timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return head.stdout.strip() if head.returncode == 0 else ""


def other_commit(content, head):
    """The checker session of an S6 file written at a commit other than HEAD,
    else None. With head None (no git work tree) every S6 file is checked."""
    checker = content.get("checker") if isinstance(content, dict) else None
    session = checker.get("session") if isinstance(checker, dict) else None
    if head is None or not isinstance(session, str) or session == head:
        return None
    return session


def due_ids(core, root_r, ledger):
    """IDs of the due done or verified rows that are not exempt (C1), in
    ledger order: the rows the S6 rule covers. merge-check.py imports this
    filter (ruling R28)."""
    log = root_r / "ledger" / "history" / "log.jsonl"
    done_at = core.completed_at_map(
        [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
         if line.strip()])
    trace = ledger.get("trace")
    since = trace.get("since") if isinstance(trace, dict) else None
    ids = []
    for row in core.due_done_rows(ledger) or []:
        rid = str(row.get("id", "?"))
        done_v = done_at.get(rid)
        if not (isinstance(since, int) and done_v is not None and done_v <= since):
            ids.append(rid)
    return ids


def present_ids(core, root_r, fname, step, part, content, s3s4, ledger_ids):
    """(violations, ids present with a verified quote) for one S5 or S6 file."""
    vio, valid = core.validate_file(root_r, fname, step, part, content, s3s4)
    if valid is None:
        return vio, set()
    if step == "S6" and content["checker"]["harness"] != "script":
        return vio + [{"id": None, "step": step, "class": "invalid", "file": fname,
                       "detail": f"{fname}: invalid (S6 checker harness must be script)"}], set()
    ids = set()
    for entry in valid["items"]:
        rid = entry["id"]
        if not core.ID_RE.match(rid) or rid not in ledger_ids:
            why = "no such ledger row" if core.ID_RE.match(rid) else "id is malformed"
            vio.append({"id": rid, "step": step, "class": "unknown-item", "file": fname,
                        "detail": f"{rid}: unknown-item in {fname} ({why})"})
            continue
        if entry["status"] != "present":
            continue
        rel, line = core.where_split(entry["where"])
        if rel in valid["artifacts"] and line is not None \
                and core.quote_ok(entry["quote"], line, valid["texts"][rel]):
            ids.add(rid)
        else:
            vio.append({"id": rid, "step": step, "class": "quote-not-found", "file": fname,
                        "detail": f"{rid}: quote-not-found at {step} (quote not found "
                                  f"at {entry['where']} in {fname})"})
    return vio, ids


def check(root, ledger, trace_dir):
    trace_dir = Path(trace_dir)
    files = []
    if trace_dir.is_dir():
        for path in sorted(trace_dir.glob("s*.json")):
            m = FILE_RE.match(path.name)
            if m:
                files.append((path, "S" + m.group(1), m.group(2)))
    if not any(step == "S6" for _, step, _ in files):
        return []
    core = load_core()
    root_r = Path(root).resolve()
    ledger_ids = {str(r.get("id")) for r in ledger["items"] if isinstance(r, dict)}
    head = head_of(root_r)
    docs, vio, checked = [], [], False
    for path, step, part in files:
        fname = f"trace/{path.name}"
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            if step == "S6":
                checked = True
                vio.append({"id": None, "step": step, "class": "invalid", "file": fname,
                            "detail": f"{fname}: invalid (file does not parse)"})
            continue
        if step == "S6":
            session = other_commit(content, head)
            if session is not None:
                vio.append({"id": None, "step": step, "class": "info", "file": fname,
                            "detail": f"{fname}: info (from commit {session[:12]}, "
                                      "not HEAD; not checked)"})
                continue
            checked = True
        docs.append((fname, step, part, content))
    if not checked:
        return vio
    s3s4 = set()
    for _, _, _, content in docs:
        arts = content.get("artifacts") if isinstance(content, dict) else None
        if isinstance(content, dict) and content.get("step") in ("S3", "S4") \
                and isinstance(arts, dict) and arts \
                and all(isinstance(k, str) and k and isinstance(v, str) and v
                        for k, v in arts.items()):
            s3s4.update(arts)
    present = {"S5": set(), "S6": set()}
    for fname, step, part, content in docs:
        if step not in present:
            continue
        found, ids = present_ids(core, root_r, fname, step, part, content,
                                 s3s4 if step == "S5" else None, ledger_ids)
        present[step] |= ids
        if step == "S6":
            vio.extend(found)
    for rid in due_ids(core, root_r, ledger):
        if rid in present["S5"] and rid not in present["S6"]:
            vio.append({"id": rid, "step": "S6", "class": "missing", "file": None,
                        "detail": f"{rid}: missing at S6"})
    return vio
