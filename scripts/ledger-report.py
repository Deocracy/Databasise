#!/usr/bin/env python3
"""Status summary: one line per row plus a totals line."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

STATUS_VALUES = ["open", "done", "verified", "deferred-requested",
                 "deferred-approved", "dropped", "parked"]
DEFERRAL_SET = {"deferred-requested", "deferred-approved"}


def age_days(raw):
    try:
        day = datetime.date.fromisoformat(str(raw))
    except ValueError:
        return "?"
    return str((datetime.date.today() - day).days)


def parse_phase_like(value):
    if isinstance(value, str) and value.strip().lower() == "backlog":
        return (10 ** 9,)
    try:
        parts = str(value).strip().split(".")
        if not parts or any(p == "" for p in parts):
            return None
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def snapshot_payload(data, digest):
    counts = {s: 0 for s in STATUS_VALUES}
    rows = []
    for row in data.get("items", []):
        if not isinstance(row, dict):
            continue
        if row.get("status") in counts:
            counts[row["status"]] += 1
        rows.append({"id": row.get("id", "?"), "status": row.get("status", "?"),
                     "text": str(row.get("text", ""))[:120]})
    cur = data.get("current_phase")
    return {"ledger_version": data.get("ledger_version"),
            "checksums_sha256": digest,
            "current_phase": cur if isinstance(cur, str) else None,
            "counts": counts, "rows": rows}


def write_snapshot(root, data, phase_dir):
    try:
        digest = hashlib.sha256((Path(root) / "ledger" / "checksums.sha256")
                                .read_bytes()).hexdigest()
    except OSError:
        print("LEDGER: checksums.sha256 missing or unreadable")
        return 1
    payload = snapshot_payload(data, digest)
    target = Path(root) / phase_dir / "LEDGER_SNAPSHOT.md"  # a relative --phase-dir is under --root
    target.parent.mkdir(parents=True, exist_ok=True)
    body = ("# LEDGER_SNAPSHOT\n\n"
            "Machine-readable ledger state for this GSD phase directory. "
            "The JSON block below is the contract; the prose above it is context.\n\n"
            f"ledger_version: {payload['ledger_version']} | "
            f"current_phase: {payload['current_phase']} | "
            f"rows: {len(payload['rows'])}\n\n"
            "```json\n" + json.dumps(payload, indent=2) + "\n```\n")
    target.write_text(body, encoding="utf-8")
    print(f"LEDGER: snapshot wrote {target}")
    return 0


def short_text(raw):
    return str(raw or "")[:60]


def notice_state(root):
    try:
        state = json.loads((Path(root) / ".bak" / "deferral-notice.json")
                           .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def park_counts(root):
    counts = {}
    log = Path(root) / "ledger" / "history" / "log.jsonl"
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        if not line.strip():
            continue
        try:
            op = json.loads(line)
        except ValueError:
            continue
        if isinstance(op, dict) and op.get("op") == "park" \
                and isinstance(op.get("id"), str):
            counts[op["id"]] = counts.get(op["id"], 0) + 1
    return counts


def header_reports_anything(text):
    """True when the DEFERRED header counts anything deferred, approved,
    parked or in backlog. A zero-only header means no notice to emit."""
    import re as _re
    first = (text or "").splitlines()[0] if (text or "").splitlines() else ""
    m = _re.match(r"^DEFERRED: (\d+) need your decision, (\d+) approved, "
                  r"(\d+) parked by the agent, (\d+) in backlog", first)
    if not m:
        return True
    return any(int(g) > 0 for g in m.groups())


def deferred_block(root, data, show_all):
    items = data.get("items", []) if isinstance(data, dict) else []
    decide = [row for row in items if isinstance(row, dict)
              and row.get("status") == "deferred-requested"]
    approved = [row for row in items if isinstance(row, dict)
                and row.get("status") == "deferred-approved"]
    parked_rows = [row for row in items if isinstance(row, dict)
                   and row.get("status") == "parked"]
    backlog_n = sum(1 for row in items if isinstance(row, dict)
                    and str(row.get("phase", "")).strip().lower() == "backlog"
                    and row.get("status") in ("parked", "deferred-approved"))
    decide_ids = sorted(str(row.get("id", "?")) for row in decide)
    state = notice_state(root)
    since_v = state.get("ledger_version") if isinstance(state, dict) else None
    counts = park_counts(root)
    if isinstance(since_v, int) and since_v and not show_all:
        parked_shown = []
        log = Path(root) / "ledger" / "history" / "log.jsonl"
        try:
            ops = [json.loads(line) for line in
                   log.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError):
            ops = []
        recent = {op.get("id") for op in ops if isinstance(op, dict)
                  and op.get("op") in ("park", "add-follow-up")
                  and isinstance(op.get("v"), int) and op["v"] > since_v}
        for row in parked_rows:
            if str(row.get("id", "?")) in recent:
                parked_shown.append(row)
    else:
        parked_shown = list(parked_rows)
    decide_lines = []
    for row in sorted(decide, key=lambda r: str(r.get("id", "?"))):
        rid = str(row.get("id", "?"))
        target = str(row.get("phase", "")).strip() or "unset"
        requested = str(row.get("deferred_at", "")).strip() or "unknown date"
        decide_lines.append(
            f"DECIDE  {rid}  {short_text(row.get('text', ''))}  "
            f"(requested {requested}, target {target})  "
            f"APPROVE {rid} | REJECT {rid} <reason>")
    parked_lines = []
    for row in sorted(parked_shown, key=lambda r: str(r.get("id", "?"))):
        rid = str(row.get("id", "?"))
        target = str(row.get("phase", "")).strip() or "unset"
        parked_lines.append(
            f"PARKED  {rid}  {short_text(row.get('text', ''))}  "
            f"(by the agent, target {target}, parked {counts.get(rid, 0)} times)  "
            f"REJECT {rid} <reason> builds it now")
    header = (f"DEFERRED: {len(decide)} need your decision, {len(approved)} approved, "
              f"{len(parked_rows)} parked by the agent, {backlog_n} in backlog")
    full_items = decide_lines + parked_lines
    if show_all:
        shown = list(full_items)
        hidden = 0
    else:
        shown = list(decide_lines)
        room = 12 - len(shown)
        shown += parked_lines[:max(room, 0)]
        hidden = len(full_items) - len(shown)
    lines = [header] + shown
    if hidden > 0:
        lines.append(f"...  {hidden} more: python3 scripts/ledger-report.py --deferred --all")
    return "\n".join(lines) + "\n", "\n".join([header] + full_items) + "\n", decide_ids


def write_deferred(root, data, show_all):
    shown, full, _decide_ids = deferred_block(root, data, show_all)
    if not header_reports_anything(shown):
        print(shown, end="")
        return 0
    target = Path(root) / "debug" / "DEFERRED.md"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(full, encoding="utf-8")
    except OSError:
        print("LEDGER: debug/DEFERRED.md unwritable")
        return 1
    print(shown, end="")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="ledger-report.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--export-gsd", action="store_true",
                    help="write LEDGER_SNAPSHOT.md into --phase-dir")
    ap.add_argument("--phase-dir", default=None)
    ap.add_argument("--deferred", action="store_true",
                    help="print the DEFERRED owner summary and rewrite debug/DEFERRED.md")
    ap.add_argument("--all", action="store_true",
                    help="with --deferred, show every PARKED line")
    args = ap.parse_args()
    if args.export_gsd and not args.phase_dir:
        ap.error("--export-gsd needs --phase-dir DIR")
    ledger = Path(args.root) / "ledger" / "REQUIREMENTS.json"
    if not ledger.is_file():
        print("LEDGER: REQUIREMENTS.json missing")
        return 1
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json unparsable")
        return 1
    items = data.get("items")
    if not isinstance(items, list):
        print("LEDGER: items is not a list")
        return 1
    if args.export_gsd:
        return write_snapshot(args.root, data, args.phase_dir)
    if args.deferred:
        return write_deferred(args.root, data, args.all)
    counts = {s: 0 for s in STATUS_VALUES}
    for row in items:
        rid = str(row.get("id", "?"))
        status = str(row.get("status", "?"))
        text = str(row.get("text", ""))[:80]
        line = f"{rid}  {status}  {text}"
        if status in DEFERRAL_SET:
            line += (f"  owner={row.get('owner', '')} "
                     f"phase={row.get('phase', '')} "
                     f"age={age_days(row.get('deferred_at', ''))}d")
        print(line)
        if status in counts:
            counts[status] += 1
    parts = [f"{s}={counts[s]}" for s in STATUS_VALUES if counts[s]]
    tail = ", ".join(parts) if parts else "none"
    cur = data.get("current_phase")
    phase_str = cur.strip() if isinstance(cur, str) and cur.strip() else "unset"
    cur_p = parse_phase_like(cur) if isinstance(cur, str) and cur.strip() else None
    due = 0
    for row in items:
        if not isinstance(row, dict) or row.get("status") != "open":
            continue
        rp = str(row.get("phase", ""))
        if rp.strip().lower() == "backlog":
            continue
        row_p = parse_phase_like(rp) if rp.strip() else None
        if not rp.strip() or cur_p is None or row_p is None or row_p <= cur_p:
            due += 1
    print(f"{len(items)} rows: {tail} | phase={phase_str} due={due}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
