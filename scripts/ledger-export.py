#!/usr/bin/env python3
"""CSV export from the JSON ledger (read-only)."""
import argparse
import csv
import json
import sys
from pathlib import Path

COLUMNS = ["id", "text", "status", "spec_ref", "test_ref", "code_ref",
           "evidence", "owner", "phase", "deferred_at", "reason"]


def main():
    ap = argparse.ArgumentParser(prog="ledger-export.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--csv", action="store_true",
                    help="write the ledger as CSV")
    ap.add_argument("--out", default=None, help="output file (default stdout)")
    args = ap.parse_args()
    if not args.csv:
        ap.error("only --csv export exists")
    ledger = Path(args.root) / "ledger" / "REQUIREMENTS.json"
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
    rows = []
    for row in items:
        if not isinstance(row, dict):
            print("LEDGER: row must be an object")
            return 1
        rows.append([str(row.get(col, "")) for col in COLUMNS])
    if args.out is None:
        sys.stdout.reconfigure(encoding="utf-8", newline="")
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    else:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(COLUMNS)
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
