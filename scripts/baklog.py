#!/usr/bin/env python3
"""9.1 journal appender: one line per hook or gate decision (contract C8)."""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

DECISIONS = ("allow", "block", "pass", "fail", "alarm", "info")


def append(root, part, event, decision, reason, target=None, session=None):
    """Append one JSON line to <root>/.bak/bak-log.jsonl. Never raises."""
    try:
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {','.join(DECISIONS)}")
        log_dir = Path(root) / ".bak"
        log_dir.mkdir(parents=True, exist_ok=True)
        ignore = log_dir / ".gitignore"
        try:
            if not ignore.is_file():
                ignore.write_text("*\n", encoding="utf-8")
        except OSError:
            pass
        harness = os.environ.get("BAK_HARNESS", "cli") or "cli"
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        row = {"ts": ts, "part": str(part), "harness": harness,
               "event": str(event), "session": session,
               "decision": decision, "reason": str(reason), "target": target}
        line = json.dumps(row, ensure_ascii=False)
        log_path = log_dir / "bak-log.jsonl"
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return line
    except Exception:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="baklog.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--part", required=True)
    ap.add_argument("--event", required=True)
    ap.add_argument("--decision", required=True, choices=list(DECISIONS))
    ap.add_argument("--reason", required=True)
    ap.add_argument("--target", default=None)
    ap.add_argument("--session", default=None)
    args = ap.parse_args(argv)
    line = append(args.root, args.part, args.event, args.decision,
                  args.reason, target=args.target, session=args.session)
    if line is None:
        print("baklog: cannot write bak-log.jsonl", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
