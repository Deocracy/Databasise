#!/usr/bin/env python3
"""S14 D3: plain file and reference check, with no ML.

Forward: every file a row points to must exist.
Reverse: every cited ID whose prefix the ledger uses must exist in the ledger.
"""
import argparse
import json
import re
from pathlib import Path

ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")
URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
LINE_SUFFIX_RE = re.compile(r":\d+(-\d+)?$")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache",
             "node_modules", "ledger", ".claude"}
SUFFIXES = {".py", ".ts", ".js", ".md", ".txt", ".yml", ".yaml", ".json"}
SKIP_FILES = {"REQUIREMENTS.json", "checksums.sha256", "log.jsonl"}
POINTER_FIELDS = ("spec_ref", "test_ref", "code_ref")
# The kit's own scripts (core/scripts/ in the kit, scripts/ once installed), whose
# example IDs are not the project's. tests/test_s14_link_recovery.py keeps this
# equal to core/scripts/*.py.
KIT_SCRIPT_NAMES = (
    "brainstorm_import.py", "check-commit-msg.py", "check-ledger.py", "deferral-scan.py",
    "expand-apply.py", "fresh-clone-verify.py", "install-worktree.py",
    "ledger-amend.py", "ledger-export.py", "ledger-report.py",
    "mockup-id-check.py", "phase-gate.py", "plan-gate.py", "question-queue.py",
    "s14_empty_cells.py", "s14_link_recovery.py", "size-gate.py", "verdict-check.py",
    "trace-check.py", "trace-write.py", "trace_s2.py", "trace_s7.py",
    "stall_time.py", "stall-locate.py",
    "debug-locate.py", "gate-loop.py", "prove-on-merge.py",
    "trace_s6.py", "merge-check.py", "plant-gaps.py",
    "baklog.py", "bak-init.py", "bak-status.py",
    "run-checks.py", "gate-filter.py",
)


def normalize_ref(raw):
    """Strip pytest node, anchor and :line suffixes from a ref cell."""
    v = raw.strip()
    if "::" in v:
        v = v.split("::", 1)[0]
    if "#" in v:
        v = v.split("#", 1)[0]
    m = LINE_SUFFIX_RE.search(v)
    if m:
        v = v[:m.start()]
    return v.strip()


def ref_exists(root, raw):
    """True when a ref cell points at something real under root.

    URLs are not files; they are skipped by the caller.
    Globs pass when they match at least one path.
    """
    v = normalize_ref(raw)
    if not v:
        return True
    if any(c in v for c in "*?["):
        try:
            return any(root.glob(v))
        except Exception:
            return False
    return (root / v).exists()


def iter_scanned(root):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if rel.parent == Path("scripts") and rel.name in KIT_SCRIPT_NAMES:
            continue
        if path.suffix not in SUFFIXES:
            continue
        yield path, rel.as_posix()


def main():
    ap = argparse.ArgumentParser(prog="s14_link_recovery.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--list-kit-scripts", action="store_true",
                    help="print the kit script names the ID scan skips in scripts/")
    args = ap.parse_args()
    if args.list_kit_scripts:
        print("\n".join(KIT_SCRIPT_NAMES))
        return 0
    root = Path(args.root)
    ledger = root / "ledger" / "REQUIREMENTS.json"
    if not ledger.is_file():
        print("LEDGER: REQUIREMENTS.json missing")
        return 1
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json unparsable")
        return 1
    if not isinstance(data, dict):
        print("LEDGER: REQUIREMENTS.json unparsable")
        return 1
    items = data.get("items")
    if not isinstance(items, list):
        print("LEDGER: items is not a list")
        return 1
    ids = set()
    for row in items:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            ids.add(row["id"])
    prefixes = {"REQ"}
    prefixes |= {rid.rsplit("-", 1)[0] for rid in ids if "-" in rid}
    out = []
    for row in items:
        if not isinstance(row, dict):
            out.append("?: row must be an object")
            continue
        rid = str(row.get("id", "?"))
        for field in POINTER_FIELDS:
            value = row.get(field, "")
            if not isinstance(value, str) or not value.strip():
                continue
            raw = value.strip()
            if URL_RE.match(raw):
                continue
            if not ref_exists(root, raw):
                out.append(f"{rid}: missing file {field} {raw}")
    seen = set()
    for path, rel in iter_scanned(root):
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, ValueError):
            continue
        for found in sorted(set(ID_RE.findall(text))):
            prefix = found.rsplit("-", 1)[0]
            if prefix not in prefixes:
                continue
            if found not in ids and (found, rel) not in seen:
                seen.add((found, rel))
                out.append(f"{found}: cited in {rel} but missing from ledger")
    for line in sorted(out):
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    raise SystemExit(main())
