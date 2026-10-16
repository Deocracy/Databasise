#!/usr/bin/env python3
"""S14 D1: report ledger rows whose evidence cells are empty for their status."""
import argparse
import json
from pathlib import Path

REQUIRED = {
    "done": ("code_ref", "test_ref", "evidence"),
    "verified": ("code_ref", "test_ref", "evidence"),
}


def main():
    ap = argparse.ArgumentParser(prog="s14_empty_cells.py")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
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
    out = []
    for row in items:
        if not isinstance(row, dict):
            out.append("?: row must be an object")
            continue
        rid = str(row.get("id", "?"))
        status = str(row.get("status", ""))
        for field in REQUIRED.get(status, ()):
            value = row.get(field, "")
            if not isinstance(value, str) or not value.strip():
                out.append(f"{rid}: empty {field} for status {status}")
    for line in out:
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    raise SystemExit(main())
