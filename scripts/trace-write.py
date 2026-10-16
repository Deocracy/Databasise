#!/usr/bin/env python3
"""The only adapter from a checker to a trace file (ruling R16).

Reads the checker's object on stdin and writes trace/<name>.json. It fills
bak_trace, step and part (from --path), ledger_version (the current ledger),
checker (from the flags) and the sha256 of every artifact or source path.
The checker may give artifacts or source as a list of paths or a map whose
values are ignored. A path outside trace/, a path with .. or an absolute
path, and malformed entries are refused.

--from-verdicts FILE converts a verify.js verdict file into an S7 file
(ruling R17): a PASS with a file:line evidence part becomes present, with
that file:line as where and the line's text (stripped) as quote; FAIL and
REVIEW become missing; every verdict keeps its verdict and evidence, and the
cited files are the artifacts."""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

PATH_RE = re.compile(
    r"^trace/(?:s2-([ab])|s([3457])(?:-([a-z0-9][a-z0-9-]{0,39}))?)\.json$")
HARNESS = ("claude-code", "dsh", "script")
CHECKLIST_WHERE_RE = re.compile(r"^checklist:[A-Za-z0-9][A-Za-z0-9-]*$")


class Refused(Exception):
    pass


def safe_rel(rel, label):
    if not isinstance(rel, str) or not rel:
        raise Refused(f"{label} path must be a non-empty string")
    if Path(rel).anchor or rel.startswith(("/", "\\")):
        raise Refused(f"{label} {rel} must be relative")
    segments = rel.replace("\\", "/").split("/")
    if ".." in segments:
        raise Refused(f"{label} {rel} must not contain ..")
    if "." in segments:
        raise Refused(f"{label} {rel} must not contain .")
    if "" in segments:
        raise Refused(f"{label} {rel} has an empty segment")


def hashes(root, paths, key, label):
    if isinstance(paths, dict):
        paths = list(paths)
    if not isinstance(paths, list) or not paths:
        raise Refused(f"{key} must be a non-empty list or map of paths")
    out = {}
    for rel in paths:
        safe_rel(rel, label)
        try:
            out[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        except OSError:
            raise Refused(f"{label} {rel} missing") from None
    return out


def _file_line_part(text):
    """A <relpath>:<line> evidence part, as check_where validates it."""
    head, sep, tail = text.rpartition(":")
    return bool(sep and head and tail.isascii() and tail.isdigit())


def check_where(where):
    # I2: validate as trace-check.py's where_split does: any <relpath>
    # (extensionless, with spaces) plus a colon and ASCII digits.
    if not isinstance(where, str):
        raise Refused(f"where {where} is not <relpath>:<line>")
    head, sep, tail = where.rpartition(":")
    if not sep or not head or not (tail.isascii() and tail.isdigit()):
        raise Refused(f"where {where} is not <relpath>:<line>")
    safe_rel(head, "where")


def check_candidates(cands):
    if not isinstance(cands, list):
        raise Refused("candidates must be a list")
    for cell in cands:
        if not isinstance(cell, dict) or not isinstance(cell.get("text"), str) \
                or not cell["text"].strip():
            raise Refused("candidate text must be a non-empty string")
        if not isinstance(cell.get("where"), str) or not cell["where"]:
            raise Refused("candidate where must be a string")
        if cell["where"].startswith("checklist:"):
            if not CHECKLIST_WHERE_RE.match(cell["where"]):
                raise Refused(f"where {cell['where']} is not <relpath>:<line>")
        else:
            check_where(cell["where"])
        if cell.get("quote") is not None and not isinstance(cell["quote"], str):
            raise Refused("candidate quote must be a string or null")
        if cell.get("id") is not None and not isinstance(cell["id"], str):
            raise Refused("candidate id must be a string or null")
        if cell.get("decision") not in (None, "not-a-requirement"):
            raise Refused("candidate decision must be null or not-a-requirement")
        if cell.get("decision") == "not-a-requirement" \
                and (not isinstance(cell.get("reason"), str) or not cell["reason"].strip()):
            raise Refused("candidate reason is required with not-a-requirement")
    return cands


def check_items(step, items, extra):
    if not isinstance(items, list) or not isinstance(extra, list):
        raise Refused("items and extra must be lists")
    seen = set()
    for entry in items:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) \
                or entry.get("status") not in ("present", "missing", "cut"):
            raise Refused("entry must hold id and status")
        if entry["id"] in seen:
            raise Refused(f"duplicate id {entry['id']}")
        seen.add(entry["id"])
        if entry["status"] == "present" and (not isinstance(entry.get("where"), str)
                                             or not isinstance(entry.get("quote"), str)):
            raise Refused("present entry needs where and quote")
        if entry["status"] == "present":
            check_where(entry["where"])
        if step == "S7":
            if entry.get("verdict") not in ("PASS", "FAIL", "REVIEW"):
                raise Refused("S7 entry needs verdict PASS, FAIL or REVIEW")
            if not isinstance(entry.get("evidence"), str):
                raise Refused("S7 entry needs evidence string")
    for cell in extra:
        if not isinstance(cell, dict) or not isinstance(cell.get("where"), str) \
                or not isinstance(cell.get("quote"), str) \
                or not isinstance(cell.get("note"), str):
            raise Refused("extra needs where, quote, note")
        check_where(cell["where"])
    return items, extra


def from_verdicts(root, vpath):
    try:
        payload = json.loads((root / vpath).read_text(encoding="utf-8"))
        verdicts = payload["verdicts"]
    except Exception:
        raise Refused(f"{vpath} is not a verdict file") from None
    if not isinstance(verdicts, list):
        raise Refused(f"{vpath} is not a verdict file")
    commit = payload.get("commit")
    items, cited = [], {}
    for v in verdicts:
        if not isinstance(v, dict) or not isinstance(v.get("id"), str) \
                or v.get("verdict") not in ("PASS", "FAIL", "REVIEW") \
                or not isinstance(v.get("evidence"), str):
            raise Refused("verdict needs id, verdict PASS, FAIL or REVIEW, and evidence")
        entry = {"id": v["id"], "status": "missing", "verdict": v["verdict"],
                 "evidence": v["evidence"]}
        if isinstance(v.get("reason"), str):
            entry["reason"] = v["reason"]
        parts = [p.strip() for p in v["evidence"].split(";")
                 if _file_line_part(p.strip())]
        for part in parts:
            rel = part.rpartition(":")[0]
            safe_rel(rel, "artifact")
            if (root / rel).is_file():
                cited[rel] = None
        if v["verdict"] == "PASS":
            if not parts:
                raise Refused(f"{v['id']} PASS has no file:line evidence")
            rel, _, num = parts[0].rpartition(":")
            try:  # the line split of trace-check.py: CR and LF only
                lines = (root / rel).read_text(encoding="utf-8", errors="replace") \
                    .replace("\r\n", "\n").replace("\r", "\n").split("\n")
            except OSError:
                raise Refused(f"artifact {rel} missing") from None
            if not 1 <= int(num) <= len(lines):
                raise Refused(f"{v['id']} cites {parts[0]}, past the end of {rel}")
            entry.update(status="present", where=parts[0],
                         quote=lines[int(num) - 1].strip())
        items.append(entry)
    if not cited:
        raise Refused("the verdicts cite no file to hash")
    out = {"artifacts": list(cited), "items": items, "extra": []}
    if isinstance(commit, str) and commit.strip():
        out["commit"] = commit
    return out


def build(args, root):
    rel = args.path
    safe_rel(rel, "path")
    m = PATH_RE.match(rel)
    if m is None:
        raise Refused(f"path {rel} is not a trace file under trace/")
    step = "S2" if m.group(1) else "S" + m.group(2)
    part = m.group(1) or m.group(3)
    if not args.model.strip() or not args.session.strip():
        raise Refused("--model and --session must be non-empty")
    try:
        version = json.loads((root / "ledger" / "REQUIREMENTS.json").read_text(
            encoding="utf-8"))["ledger_version"]
    except Exception:
        raise Refused("ledger/REQUIREMENTS.json has no readable ledger_version") from None
    if not isinstance(version, int) or isinstance(version, bool):
        raise Refused("ledger_version in ledger/REQUIREMENTS.json must be an integer")
    if args.from_verdicts is not None:
        if step != "S7":
            raise Refused("--from-verdicts writes only trace/s7.json or trace/s7-<part>.json")
        want = from_verdicts(root, args.from_verdicts)
    else:
        try:
            want = json.load(sys.stdin)
        except Exception:
            raise Refused("stdin is not JSON") from None
    if not isinstance(want, dict):
        raise Refused("top-level JSON must be an object")
    fmt = want.get("bak_trace", 1)
    if fmt != 1 or isinstance(fmt, bool):
        raise Refused("bak_trace must be 1")
    if want.get("step", step) != step:
        raise Refused(f"step {want.get('step')} does not match file name {rel}")
    if want.get("part", part) != part:
        raise Refused(f"part does not match file name {rel}")
    doc = {"bak_trace": 1, "step": step, "part": part, "ledger_version": version}
    checker = {"harness": args.harness, "model": args.model, "session": args.session}
    if step == "S2":
        doc["source"] = hashes(root, want.get("source"), "source", "source")
        doc["checker"] = checker
        doc["candidates"] = check_candidates(want.get("candidates"))
    else:
        doc["artifacts"] = hashes(root, want.get("artifacts"), "artifacts", "artifact")
        doc["checker"] = checker
        doc["items"], doc["extra"] = check_items(step, want.get("items"),
                                                 want.get("extra"))
        if step == "S7" and isinstance(want.get("commit"), str) \
                and want["commit"].strip():
            doc["commit"] = want["commit"]
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trace-write.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--path", required=True)
    ap.add_argument("--harness", required=True, choices=HARNESS)
    ap.add_argument("--model", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--from-verdicts", default=None, metavar="FILE")
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        doc = build(args, root)
        full = root / args.path
        if (root / "trace").is_symlink() or full.is_symlink():
            raise Refused(f"path {args.path} must not be a symlink")
    except Refused as exc:
        print(f"trace-write: {exc}", file=sys.stderr)
        return 1
    full.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(full.parent),
                               prefix=full.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, full)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
