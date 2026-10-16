#!/usr/bin/env python3
"""Commit-gate filter (contract C11.7): run-checks.py summary minus baseline labels
minus rows not done or verified; unregistered labels are kept."""
import argparse
import json
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


# run-checks.py result lines (C11.4); PASS, the summary and nested output never match.
RESULT = re.compile(r"(FAIL|TIMEOUT) (.+?) (?:exit -?\d+|no output|after \S+s)")


def read(path, what):
    try:
        return Path(path).read_text(encoding="utf-8"), ""
    except OSError as exc:
        return None, f"gate-filter.py: cannot read {what} {path}: {exc}"


def filter_summary(args):
    """(exit code, kept lines, error)."""
    summary, err = read(args.summary, "summary")
    if summary is None:
        return 2, [], err
    label_ids = {}
    for arg in args.registry:
        for reg in (part for part in arg.split(",") if part):
            text, err = read(reg, "registry")
            if text is None:
                return 2, [], err
            for raw in text.splitlines():
                parts = raw.split("\t")
                if len(parts) < 3 or raw.lstrip().startswith("#"):
                    continue
                rid, label = parts[0].strip(), parts[1].rpartition("::")[2].strip()
                if rid and label:
                    label_ids.setdefault(label, []).append(rid)
    baseline = set()
    if args.baseline is not None:
        text, err = read(args.baseline, "baseline")
        if text is None:
            return 2, [], err
        baseline = {line.strip() for line in text.splitlines() if line.strip()}
    try:
        items = json.loads((Path(args.root) / "ledger" / "REQUIREMENTS.json")
                           .read_text(encoding="utf-8"))["items"]
        status = {row["id"]: row.get("status") for row in items
                  if isinstance(row, dict) and isinstance(row.get("id"), str)}
    except Exception:
        return 1, [], "LEDGER: REQUIREMENTS.json missing or unreadable"
    kept = []
    for raw in summary.splitlines():
        line = raw.strip()
        m = RESULT.fullmatch(line)
        if not m or m.group(2).strip() in baseline:
            continue
        ids = label_ids.get(m.group(2).strip())
        if ids is None:
            kept.append(line)  # unregistered: nothing says it may wait
            continue
        # A registry ID the ledger lacks is kept (fail closed).
        kept += [f"{line} ({rid})" for rid in ids
                 if status.get(rid, "done") in ("done", "verified")]
    return (1 if kept else 0), kept, ""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gate-filter.py")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--registry", action="append", required=True)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    code, kept, err = filter_summary(args)
    for line in kept:
        print(line)
    if err:
        print(err, file=sys.stderr)
    _baklog(args.root, "3.12 gate-filter", "gate-filter", "fail" if code else "pass",
            err or "\n".join(kept) or "no failures kept")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
