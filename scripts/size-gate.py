#!/usr/bin/env python3
"""Size gate: reject a plan with more than 20 items, 20 cited ledger IDs or
500 lines. Hook mode judges the text a Write, Edit or MultiEdit leaves in a
.planning/**/*-plan.md file; a change that grows none of the three measures
passes, so an oversized plan can be split step by step."""
import argparse
import json
import os
import re
import sys
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


MAX_ITEMS = 20
MAX_LINES = 500
CHECKBOX = re.compile(r"^\s*-\s\[[ xX]\]\s+\S")
TASK_HEADING = re.compile(r"^\s*#{1,6}\s+Task\s+\d+", re.IGNORECASE)
TASK_TAG = re.compile(r"<task[\s>]")
REQ_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")
FENCE = re.compile(r"^\s*```")
PARSE_MSG = "size-gate: cannot parse hook input"


def ledger_ids(root):
    """The IDs in ledger/REQUIREMENTS.json, or None when it cannot be read."""
    try:
        items = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json")
                           .read_text(encoding="utf-8"))["items"]
    except (OSError, ValueError, TypeError, KeyError):
        return None
    if not isinstance(items, list):
        return None
    return {row["id"] for row in items
            if isinstance(row, dict) and isinstance(row.get("id"), str)}


def measures(text, known):
    """(items, lines, cited IDs). Lines inside ``` fences are neither items nor
    citations; with a readable ledger only its own IDs count."""
    items, ids, fenced = 0, set(), False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            items += bool(CHECKBOX.match(line) or TASK_HEADING.match(line)
                          or TASK_TAG.search(line))
            ids.update(REQ_RE.findall(line))
    if known is not None:
        ids &= known
    return items, len(text.splitlines()), len(ids)


def verdict(counts):
    n, m, k = counts
    if n > MAX_ITEMS:
        return 2, f"SIZE GATE: plan has {n} items (max 20); split the phase"
    if k > MAX_ITEMS:
        return 2, f"SIZE GATE: plan cites {k} ledger IDs (max 20); split the phase"
    if m > MAX_LINES:
        return 2, f"SIZE GATE: plan has {m} lines (max 500); split the phase"
    return 0, f"SIZE GATE: ok ({n} items, {m} lines, {k} ledger IDs)"


def is_plan(raw):
    """A *-plan.md file (any case) below a .planning directory."""
    parts = re.split(r"[\\/]", raw.lower())
    return parts[-1].endswith("-plan.md") and ".planning" in parts[:-1]


def after_text(tool, tool_input, text):
    """The file text once the tool has run: Write's content, or the disk text
    with each Edit/MultiEdit replacement applied in order."""
    if tool == "write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else text
    edits = tool_input.get("edits") if tool == "multiedit" else [tool_input]
    for edit in edits if isinstance(edits, list) else []:
        if not isinstance(edit, dict):
            continue
        old, new = edit.get("old_string"), edit.get("new_string")
        if isinstance(old, str) and isinstance(new, str) and old in text:
            text = text.replace(old, new, -1 if edit.get("replace_all") else 1)
    return text


def hook(payload):
    tool = str(payload.get("tool_name", "")).lower()
    tool_input = payload.get("tool_input")
    if tool not in ("write", "edit", "multiedit") or not isinstance(tool_input, dict):
        _baklog(os.environ.get("CLAUDE_PROJECT_DIR") or (payload.get("cwd") if isinstance(payload.get("cwd"), str) else "") or ".", "4.2 size-gate", "size-gate", "pass", "not a plan write", session=payload.get("session_id"))
        return 0
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not is_plan(raw):
        _baklog(os.environ.get("CLAUDE_PROJECT_DIR") or (payload.get("cwd") if isinstance(payload.get("cwd"), str) else "") or ".", "4.2 size-gate", "size-gate", "pass", "not a plan write", session=payload.get("session_id"))
        return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    path = Path(cwd or root) / raw  # an absolute raw path replaces the base
    try:
        before = path.read_text(encoding="utf-8") if path.exists() else ""
    except (OSError, ValueError):
        if tool != "write":
            _baklog(root, "4.2 size-gate", "size-gate", "pass", "plan unreadable: an Edit fails open", target=raw, session=payload.get("session_id"))
            return 0  # an Edit's result needs the disk text: fail open, the agent keeps access
        before = ""  # a Write's result is its content: judge it from an empty baseline
    known = ledger_ids(root)
    old = measures(before, known)
    new = measures(after_text(tool, tool_input, before), known)
    code, line = verdict(new)
    if code and any(a > b for a, b in zip(new, old)):
        print(line, file=sys.stderr)
        _baklog(root, "4.2 size-gate", "size-gate", "fail", line, target=raw, session=payload.get("session_id"))
        return 2
    _baklog(root, "4.2 size-gate", "size-gate", "pass", line if not code else "no measure grew; " + line, target=raw, session=payload.get("session_id"))
    return 0


def main():
    ap = argparse.ArgumentParser(prog="size-gate.py")
    ap.add_argument("--plan", default=None)
    ap.add_argument("--root", default=".", help="project root holding ledger/")
    args = ap.parse_args()
    if args.plan is not None:
        try:
            text = Path(args.plan).read_text(encoding="utf-8")
        except (OSError, ValueError):
            print(f"size-gate: cannot read plan {args.plan}")
            _baklog(args.root, "4.2 size-gate", "size-gate", "fail", f"size-gate: cannot read plan {args.plan}", target=args.plan)
            return 2
        code, line = verdict(measures(text, ledger_ids(args.root)))
        print(line)
        _baklog(args.root, "4.2 size-gate", "size-gate", "pass" if code == 0 else "fail", line, target=args.plan)
        return code
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        print(PARSE_MSG, file=sys.stderr)
        _baklog(os.environ.get("CLAUDE_PROJECT_DIR") or ".", "4.2 size-gate", "size-gate", "fail", PARSE_MSG)
        return 2
    return hook(payload)


if __name__ == "__main__":
    raise SystemExit(main())
