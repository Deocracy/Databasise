#!/usr/bin/env python3
"""Checks-before-code gate: every claimed due row names a check; done and verified due rows prove it failed first."""
import argparse
import hashlib
import json
import os
import re
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


DONE = ("done", "verified")


def parse_phase(value):
    if isinstance(value, str) and value.strip().lower() == "backlog":
        return (10 ** 9,)
    try:
        parts = str(value).strip().split(".")
        if not parts or any(p == "" for p in parts):
            return None
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def due_rows(data):
    cur_raw = data.get("current_phase")
    cur_p = parse_phase(cur_raw) if isinstance(cur_raw, str) and cur_raw.strip() else None
    rows = []
    items = data.get("items")
    if not isinstance(items, list):
        return None
    for row in items:
        if not isinstance(row, dict):
            continue
        if row.get("status") not in ("open", "done", "verified"):
            continue
        rp_raw = str(row.get("phase", ""))
        if rp_raw.strip().lower() == "backlog":
            if row.get("status") == "open":
                continue
            row_p = parse_phase(rp_raw)
            if row_p is not None and (cur_p is None or row_p <= cur_p):
                rows.append(row)
            continue
        row_p = parse_phase(rp_raw) if rp_raw.strip() else None
        if not rp_raw.strip() or cur_p is None or row_p is None or row_p <= cur_p:
            rows.append(row)
    return rows


def check_key(root, path_part):
    """Canonical key of a test_ref path part: the path resolved under root, relative
    to root, in POSIX form. phase-gate.py and ledger-amend.py hold this same code. Raises
    ValueError with the violation text for an absolute path, one that leaves root, or
    one that passes through a symlink (its resolved and lexically normalized paths differ)."""
    if Path(path_part).anchor:
        raise ValueError("check path must be relative")
    try:
        root_r = Path(root).resolve()
        target = (root_r / path_part).resolve()
        key = target.relative_to(root_r).as_posix()
    except (OSError, RuntimeError, ValueError):
        raise ValueError("check not found") from None
    if target != Path(os.path.normpath(root_r / path_part)):
        raise ValueError("check path must not pass through a symlink")
    return key


def check_id(root, ref):
    """(key, canonical check) of a test_ref: the check key plus any stripped ::node, so
    aliases such as `./x`, `a//x` or a trailing space name one check. Raises as check_key."""
    path_part, _, node = ref.partition("::")
    key = check_key(root, path_part.strip())
    return key, key + ("::" + node.strip() if node.strip() else "")


def names_test(text, path, node):
    """True when text still holds the test's node as a whole name after every occurrence
    of the check path and of its basename is removed, so a crash trace that prints only
    the file does not count, and a sibling test whose name starts with the node's
    (`test_create_duplicate` for `test_create`) does not either. The full id
    `<file>::<node>` goes first: pytest echoes it for a test it never ran (`found no
    collectors for`, `not found:`). A class node `A::b` is also named by pytest's `A.b`
    failure header. An empty node is always named.
    Nothing from `[A-Za-z0-9_]` may come directly before the node, and nothing from
    `[A-Za-z0-9_-]` directly after it: `verify-x: FAIL` names `verify-x` but a
    sibling named `verify-x-2` does not, while `test_y[1]` still names `test_y`.
    phase-gate.py and ledger-amend.py hold this same code."""
    if node and Path(path).name:
        full = f"{Path(path).name}::{node}"
        text = text.replace(full, "")
    for part in (path, Path(path).name):
        if part:
            text = text.replace(part, "")

    def whole(n):
        return (re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_-])", text)
                is not None)
    return (whole(node) or whole(node.replace("::", "."))) if node else True


def file_sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="phase-gate.py")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.root)
    ledger = root / "ledger" / "REQUIREMENTS.json"
    log = root / "ledger" / "history" / "log.jsonl"
    if not ledger.is_file():
        print("LEDGER: REQUIREMENTS.json missing")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: REQUIREMENTS.json missing")
        return 1
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json unparsable")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: REQUIREMENTS.json unparsable")
        return 1
    if not log.is_file():
        print("LEDGER: history/log.jsonl missing")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: history/log.jsonl missing")
        return 1
    try:
        ops = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    except Exception:
        print("LEDGER: history/log.jsonl unparsable")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: history/log.jsonl unparsable")
        return 1
    items = data.get("items")
    if not isinstance(items, list):
        print("LEDGER: items is not a list")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: items is not a list")
        return 1
    root_r = root.resolve()
    # C11.3: a check file that had a grant; lock-checks clears the grant, the log keeps it.
    grants = data.get("check_edit_grants")
    granted = set(grants) if isinstance(grants, dict) else set()
    granted |= {op["file"] for op in ops if isinstance(op, dict)
                and op.get("op") == "grant-check-edit" and isinstance(op.get("file"), str)}

    def grant_covers(gpath, ckey):
        """M3: grant matching casefolds like the guard, and a granted folder
        covers the files under it."""
        glow = str(gpath).strip().rstrip("/")
        if not glow or glow == ".." or glow.startswith("../"):
            return False
        glow = glow.casefold()
        low = ckey.casefold()
        gdir = glow.rstrip("/")
        return low == gdir or low.startswith(gdir + "/")
    # C11.1: rows whose replacement check the owner approved (PB1's approve on a dispute).
    dispute_approved = {op["id"] for op in ops if isinstance(op, dict)
                        and op.get("op") == "approve" and op.get("dispute") == "approved"
                        and isinstance(op.get("id"), str)}
    failed = {}  # row id -> [(canonical check, proof)], in log order
    completed_at = {}
    repointed = set()  # rows whose test_ref changed after the last lock-checks
    for op in ops:
        if not isinstance(op, dict):
            continue
        changes = op.get("changes")
        if op.get("op") == "lock-checks":
            repointed = set()
        elif isinstance(changes, dict) and "test_ref" in changes:
            repointed.add(op.get("id"))
        moved = changes.get("status") if isinstance(changes, dict) else None
        # The row's last move into done/verified; done -> verified is not a new completion.
        if isinstance(moved, list) and len(moved) == 2 and moved[0] not in DONE \
                and moved[1] in DONE and isinstance(op.get("v"), int):
            completed_at[op.get("id")] = op["v"]
        if op.get("op") == "check-fail" and isinstance(op.get("id"), str) \
                and isinstance(op.get("ref"), str) and op.get("ref").strip() \
                and isinstance(op.get("cmd"), str) and op.get("cmd").strip() \
                and isinstance(op.get("exit"), int) and op["exit"] != 0 \
                and isinstance(op.get("output"), str) and op.get("output").strip() \
                and isinstance(op.get("sha256"), str) and op.get("sha256").strip() \
                and isinstance(op.get("head"), str):
            try:
                failed.setdefault(op["id"], []).append((check_id(root_r, op["ref"])[1], op))
            except ValueError:
                pass
    locks = data.get("check_locks")
    if locks is not None and not (
            isinstance(locks, dict) and isinstance(locks.get("commit"), str)
            and isinstance(locks.get("files"), dict)
            and all(isinstance(v, str) for v in locks["files"].values())):
        print("LEDGER: check_locks must be an object or null")
        _baklog(root, "3.2 phase-gate", "phase-gate", "fail", "LEDGER: check_locks must be an object or null")
        return 1
    lock_files = locks["files"] if locks is not None else {}
    baseline = data.get("check_baseline")
    if not isinstance(baseline, int) or isinstance(baseline, bool):
        baseline = None
    out = []
    owners = {}  # canonical check (key plus any ::node part) -> first due row naming it
    for row in due_rows(data):
        rid = str(row.get("id", "?"))
        status = row.get("status")
        ref = row.get("test_ref", "")
        ref = ref if isinstance(ref, str) else ""
        if not ref.strip():
            out.append(f"{rid}: missing check (empty test_ref)")
            continue
        path_part, _, node = ref.partition("::")
        try:
            key, check = check_id(root_r, ref)
        except ValueError as exc:
            out.append(f"{rid}: {exc} ({ref})")
            continue
        if check in owners:
            out.append(f"{rid}: check {ref} is also the check of {owners[check]}; "
                       "each row needs its own test")
        else:
            owners[check] = rid
        if not (root_r / key).is_file():
            out.append(f"{rid}: check not found ({ref})")
            continue
        if status == "open":
            continue
        # The lock approves each row's check, not only its file: a re-point needs a new lock.
        if locks is not None and (key not in lock_files or rid in repointed):
            out.append(f"{rid}: check not locked ({ref}); the user reviews it and runs lock-checks")
        cur_check_sha = (lock_files[key] if key in lock_files
                         else file_sha(root_r / key))
        # C11.3: a done row with a plants file needs every plant killed on the current check.
        # I2: the plant rules run for every non-open due row, baseline or not.
        plants_file = root_r / "plants" / f"{rid}.json"
        plants_sha = file_sha(plants_file) if plants_file.is_file() else None
        granted_row = any(grant_covers(gpath, key) for gpath in granted)
        plant_runs = [op for op in ops if isinstance(op, dict) and op.get("op") == "plant-run"
                      and op.get("id") == rid and op.get("check_sha256") == cur_check_sha
                      and isinstance(op.get("plants_sha256"), str)
                      and op["plants_sha256"] == plants_sha
                      and isinstance(op.get("results"), list) and op["results"]]
        if granted_row and plants_sha is None:
            out.append(f"{rid}: check edited under a grant needs plants/{rid}.json")
        if plants_sha is not None and not plant_runs:
            out.append(f"{rid}: no plant run for the current check")
        elif plants_sha is not None and plant_runs:
            results = plant_runs[-1]["results"]
            survived = sum(1 for r in results
                           if not (isinstance(r, dict) and r.get("killed") is True))
            if survived:
                out.append(f"{rid}: check not proven by plants "
                           f"({survived} of {len(results)} survived)")
        # I2: the baseline waives the failure proof only; the plant rules
        # above already ran. Non-proof lines (lock, change-after-first-run)
        # still apply, so only the proof block is skipped.
        done_v = completed_at.get(rid)
        baseline_row = (baseline is not None and done_v is not None and done_v <= baseline
                        and not isinstance(row.get("finding"), dict))
        row_proofs = failed.get(rid, [])
        proofs = [p for c, p in row_proofs if c == check]
        # A run whose output never names the ref's ::node may have failed for another reason.
        counting = [p for p in proofs if names_test(p["output"], path_part.strip(), node.strip())]
        if not baseline_row:
            if not proofs:
                out.append(f"{rid}: check never failed (no recorded failure for {ref})")
            elif not counting:
                out.append(f"{rid}: recorded failure never reached its test ({ref}); "
                           "the run failed for another reason")
            elif counting[-1]["sha256"] != cur_check_sha:
                out.append(f"{rid}: recorded failure is stale (test file changed since the failing run for {ref})")
            elif rid in dispute_approved and not any(
                    isinstance(p.get("at"), str) and p["at"].strip()
                    and p.get("sha256") == cur_check_sha
                    for p in counting):
                out.append(f"{rid}: replacement check has no failing run on the pre-fix code "
                           "(record-fail --at)")

        # Re-recording a changed check is the agent's own call until the user's lock covers it.
        # Every (check, file version) the row was proven on: an alias of the ref or a
        # re-point to another test is a change too.
        versions = len({(c, p["sha256"]) for c, p in row_proofs})
        if locks is None and versions > 1:  # after a lock, `check not locked` covers it
            out.append(f"{rid}: check changed after its first failing run ({versions} versions "
                       f"recorded for {ref}); the user approves the change by running lock-checks")
    for key, locked in lock_files.items():
        now = file_sha(root_r / key)
        if now is None:
            out.append(f"locked check missing: {key}")
            continue
        if now != locked:
            out.append(f"{key}: test file changed (locked {locked}, now {now})")
    for line in out:
        print(line)
    _baklog(root, "3.2 phase-gate", "phase-gate", "fail" if out else "pass", "\n".join(out) or "no violations")
    return 1 if out else 0


if __name__ == "__main__":
    raise SystemExit(main())
