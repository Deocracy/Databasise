#!/usr/bin/env python3
"""Only writer for ledger/. One write path: validate, bump, log, write, sums."""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
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


_run = {"root": ".", "cmd": None, "id": None}  # this run's --root, subcommand and --id, for bak-log rows

ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
REQ_RE = re.compile(r"^REQ-([0-9]+)$")
STATUS_VALUES = ["open", "done", "verified", "deferred-requested",
                 "deferred-approved", "dropped", "disputed", "parked"]
ROW_FIELDS = ["id", "text", "status", "spec_ref", "test_ref", "code_ref",
              "evidence", "owner", "phase", "deferred_at", "reason"]
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
SOURCE_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SUMS_MISMATCH = ("ledger/ does not match checksums.sha256: it was changed outside "
                 "ledger-amend.py. Stop and ask the user to restore it (for example "
                 "`git checkout -- ledger/`).")
STAGING_REFUSED = ("import-runs: .bak/prove-ledger.importing holds runs that could "
                   "not be imported; the owner checks them and deletes the folder")
STAGING_IMPORTED = ("import-runs: the runs in .bak/prove-ledger.importing were "
                    "already imported; removed it")


def fail(msg):
    print(f"ledger-amend: error: {msg}", file=sys.stderr)
    _baklog(_run["root"], "1.1 ledger-amend", _run["cmd"], "block", msg, target=_run["id"])
    return 1


def ledger_paths(root):
    ledger = Path(root) / "ledger"
    return (ledger / "REQUIREMENTS.json", ledger / "checksums.sha256",
            ledger / "history" / "log.jsonl")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.date.today().isoformat()


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    os.chmod(path, 0o444)


def _rmtree(path):
    """Remove a tree whose ledger files are read-only (0o444)."""
    import shutil as _shutil

    def _chmod(p):
        try:
            os.chmod(p, 0o644)
        except OSError:
            pass

    def _onexc(func, p, _exc):
        _chmod(p)
        func(p)

    try:
        _shutil.rmtree(path, onexc=_onexc)
    except TypeError:  # Python < 3.12: onerror instead of onexc
        _shutil.rmtree(path, onerror=lambda f, p, e: (_chmod(p), f(p)))


def blank_row(id_, text, spec_ref):
    row = {k: "" for k in ROW_FIELDS}
    row.update({"id": id_, "text": text, "status": "open",
                "spec_ref": spec_ref, "kind": "requirement"})
    return row


def validate(data):
    errs = []
    if not isinstance(data.get("ledger_version"), int) or data["ledger_version"] < 1:
        errs.append("ledger_version must be an int >= 1")
    frozen = data.get("frozen_at")
    if frozen is not None and (not isinstance(frozen, str) or not DATE_RE.match(frozen)):
        errs.append("frozen_at must be null or YYYY-MM-DD")
    for key in ("current_phase", "check_cmd"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            errs.append(f"{key} must be a string or null")
    mf = data.get("mockup_freeze")
    if mf is not None and (not isinstance(mf, dict)
                           or not isinstance(mf.get("variant"), str)
                           or not isinstance(mf.get("path"), str)
                           or not isinstance(mf.get("sha256"), str)):
        errs.append("mockup_freeze must be null or {variant, path, sha256} strings")
    lock = data.get("scope_lock")
    if lock is not None:
        if not isinstance(lock, dict) or not isinstance(lock.get("phase"), str) or not all(
                isinstance(lock.get(k), str) and lock.get(k, "").strip()
                for k in ("source", "sha256")):
            errs.append("scope_lock must be null or {phase, source, sha256} strings")
    if "stall_budgets" in data and data["stall_budgets"] is not None:
        _sb = data["stall_budgets"]
        _keys = {"repeat_block", "same_rounds", "no_progress_min",
                 "hang_min", "owner_wait_h"}
        if not isinstance(_sb, dict) or set(_sb) - _keys \
                or any(not isinstance(_sb.get(k), int) or _sb.get(k) <= 0
                       for k in _sb):
            errs.append("stall_budgets must be an object of positive integers or null")
    if "check_locks" in data and data["check_locks"] is not None:
        locks = data["check_locks"]
        if not isinstance(locks, dict) or not isinstance(locks.get("commit"), str) \
                or not isinstance(locks.get("files"), dict) \
                or any(not isinstance(k, str) or not isinstance(v, str)
                       for k, v in locks["files"].items()) \
                or not isinstance(locks.get("also", []), list) \
                or any(not isinstance(p, str) for p in locks.get("also", [])):
            errs.append("check_locks must be an object or null")
    base = data.get("check_baseline")
    if base is not None and (not isinstance(base, int) or isinstance(base, bool)):
        errs.append("check_baseline must be an integer or null")
    trace = data.get("trace", "absent")
    if trace != "absent" and trace is not None:
        if not isinstance(trace, dict) or trace.get("kind") not in ("code", "document") \
                or not isinstance(trace.get("since"), int) or isinstance(trace.get("since"), bool):
            errs.append("trace must be null or {kind, since}")
    if "check_guard" in data and data["check_guard"] is not None:
        if not isinstance(data["check_guard"], list) \
                or any(not isinstance(p, str) for p in data["check_guard"]):
            errs.append("check_guard must be a list or null")
    if "check_edit_grants" in data and data["check_edit_grants"] is not None:
        grants = data["check_edit_grants"]
        if not isinstance(grants, dict) \
                or any(not isinstance(k, str) or not isinstance(v, dict)
                       or not isinstance(v.get("reason"), str)
                       or not isinstance(v.get("granted_at"), int)
                       or isinstance(v.get("granted_at"), bool)
                       for k, v in grants.items()):
            errs.append("check_edit_grants must be an object or null")
    items = data.get("items")
    if not isinstance(items, list):
        return ["items must be a list"]
    seen = set()
    for row in items:
        rid = str(row.get("id", "?")) if isinstance(row, dict) else "?"
        if not isinstance(row, dict):
            errs.append(f"{rid}: row must be an object")
            continue
        finding = row.get("finding")
        if finding is not None:
            if not isinstance(finding, dict) \
                    or not isinstance(finding.get("source"), str) \
                    or not finding.get("source", "").strip() \
                    or not isinstance(finding.get("key"), str) \
                    or not finding.get("key", "").strip() \
                    or finding.get("severity") not in ("critical", "important"):
                errs.append(f"{rid}: finding must be {{source, key, severity}}")
        for k in ROW_FIELDS:
            if k not in row:
                errs.append(f"{rid}: missing field {k}")
            elif not isinstance(row[k], str):
                errs.append(f"{rid}: field {k} must be a string")
        if rid in seen:
            errs.append(f"{rid}: duplicate id")
        seen.add(rid)
        if not ID_RE.match(rid):
            errs.append(f"{rid}: malformed id")
        if not row.get("text", ""):
            errs.append(f"{rid}: empty text")
        if row.get("status") not in STATUS_VALUES:
            errs.append(f"{rid}: bad status")
        kind = row.get("kind", "requirement")
        if kind not in ("requirement", "finding", "follow-up"):
            errs.append(f"{rid}: bad kind {kind}")
        if row.get("status") == "parked" and kind != "follow-up":
            errs.append(f"{rid}: parked needs kind follow-up")
    if data.get("notify_cmd") is not None and not isinstance(data.get("notify_cmd"), str):
        errs.append("notify_cmd must be a string or null")
    return errs


def read_log(log_path):
    ops = []
    if Path(log_path).is_file():
        for line in Path(log_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                ops.append(json.loads(line))
    return ops


def next_req_id(ops):
    best = 0
    for op in ops:
        if isinstance(op, dict) and op.get("op") in ("add", "add-follow-up",
                                                     "add-finding"):
            m = REQ_RE.match(str(op.get("id", "")))
            if m:
                best = max(best, int(m.group(1)))
    return f"REQ-{best + 1:03d}"


def ever_added(ops, items, rid):
    if any(isinstance(r, dict) and r.get("id") == rid for r in items):
        return True
    return any(isinstance(op, dict) and op.get("op") in ("add", "add-follow-up",
                                                         "add-finding")
               and op.get("id") == rid for op in ops)


def commit(root, data, op, rid, extra, more=()):
    """`more` holds further (op, id, extra) entries, one version each, that go
    into the same single write of each file. A failure between the file
    writes leaves the files out of step with checksums.sha256, which the
    checksum check reports loudly."""
    entries = [(op, rid, extra), *more]
    base = int(data.get("ledger_version", 0))
    data["ledger_version"] = base + len(entries)
    errs = validate(data)
    if errs:
        return fail("; ".join(errs))
    ledger_file, sums_file, log_path = ledger_paths(root)
    try:
        ops = read_log(log_path)
    except (ValueError, OSError) as exc:
        return fail(f"history/log.jsonl unparsable: {exc}")
    ts = utc_now()
    for v, (entry_op, entry_id, entry_extra) in enumerate(entries, start=base + 1):
        ops.append({"v": v, "ts": ts, "op": entry_op, "id": entry_id, **entry_extra})
    atomic_text(ledger_file, json.dumps(data, indent=2) + "\n")
    atomic_text(log_path, "".join(json.dumps(o) + "\n" for o in ops))
    d1 = hashlib.sha256(ledger_file.read_bytes()).hexdigest()
    d2 = hashlib.sha256(log_path.read_bytes()).hexdigest()
    atomic_text(sums_file, f"{d1}  REQUIREMENTS.json\n{d2}  history/log.jsonl\n")
    _baklog(root, "1.1 ledger-amend", _run["cmd"] or op, "pass", f"committed ledger_version {data['ledger_version']}", target=None if more else rid or None)
    return 0


def sums_match(ledger_file, sums_file, log_path):
    """True when checksums.sha256 matches both files, so a write never seals an out-of-band change."""
    try:
        want = {}
        for line in sums_file.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                want[parts[1]] = parts[0]
        return all(want.get(name) == hashlib.sha256(path.read_bytes()).hexdigest()
                   for name, path in (("REQUIREMENTS.json", ledger_file),
                                      ("history/log.jsonl", log_path)))
    except OSError:
        return False


def find_row(data, rid):
    for row in data.get("items", []):
        if isinstance(row, dict) and row.get("id") == rid:
            return row
    return None


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


def import_staging(root, data, staging):
    """Consume a stranded .bak/prove-ledger.importing left by a kill between
    the rename and the delete (or a commit failure before the delete).

    A staging copy that still begins where the ledger log does imports like
    the main copy and is then deleted. When the log prefix no longer holds
    because the ops were already committed, the copy is dropped only if every
    extra op is already in the ledger as a check-run op with the same id,
    ref, head, exit and output_sha256."""
    stag = Path(staging)
    _, _, log_path = ledger_paths(root)
    s_ledger, s_sums, s_log = ledger_paths(stag)
    if not sums_match(s_ledger, s_sums, s_log):
        return fail(STAGING_REFUSED)
    try:
        mine = log_path.read_bytes() if log_path.is_file() else b""
        theirs = s_log.read_bytes()
        mine_ops = [json.loads(line) for line in
                    mine.decode("utf-8").splitlines() if line.strip()]
        staged_ops = [json.loads(line) for line in
                      theirs.decode("utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return fail(STAGING_REFUSED)
    shared = 0
    for mine_op, staged_op in zip(mine_ops, staged_ops):
        if mine_op != staged_op:
            break
        shared += 1
    staged_extra = staged_ops[shared:]
    if theirs.startswith(mine):
        try:
            extra_ops = [json.loads(line) for line in
                         theirs[len(mine):].decode("utf-8").splitlines()
                         if line.strip()]
        except ValueError:
            return fail(STAGING_REFUSED)
        entries = []
        for op in extra_ops:
            name = op.get("op") if isinstance(op, dict) else None
            if name != "check-run":
                return fail(STAGING_REFUSED)
            rid = str(op.get("id", ""))
            if find_row(data, rid) is None:
                return fail(STAGING_REFUSED)
            fields = {k: op[k] for k in ("ref", "cmd", "exit", "output_sha256",
                                         "output", "head", "tree_clean")
                      if k in op}
            if "timed_out" in op:
                fields["timed_out"] = op["timed_out"]
            entries.append(("check-run", rid, fields))
        if entries:
            rc = commit(root, data, *entries[0], more=entries[1:])
            if rc:
                return rc
        else:
            print(STAGING_IMPORTED)
        try:
            _rmtree(stag)
        except OSError:
            return fail("import-runs: the runs were imported but the staged copy "
                        "could not be deleted; the owner deletes it "
                        "(for example `rm -rf .bak/prove-ledger.importing`) "
                        "and re-runs import-runs")
        return 0
    if not staged_extra or all_already_imported(mine_ops, staged_extra):
        try:
            _rmtree(stag)
        except OSError as exc:
            return fail(f"import-runs: cannot delete the staged copy: {exc}")
        print(STAGING_IMPORTED)
        return 0
    return fail(STAGING_REFUSED)


def all_already_imported(mine_ops, staged_extra):
    """True when every staged extra op already sits in the ledger log as a
    check-run op with the same id, ref, head, exit and output_sha256."""
    keys = ("id", "ref", "head", "exit", "output_sha256")
    seen = set()
    for op in mine_ops:
        if isinstance(op, dict) and op.get("op") == "check-run":
            seen.add(tuple(op.get(k) for k in keys))
    return all(isinstance(op, dict) and op.get("op") == "check-run"
               and tuple(op.get(k) for k in keys) in seen
               for op in staged_extra)


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


def phase_move_allowed(current, existing, new):
    """True when a frozen-ledger phase write does not push the row later.

    Empty stays allowed (due now). Otherwise the new phase must parse and be
    at or below the larger of the ledger's current_phase and the row's
    existing phase; with no parsable baseline any parsable phase is allowed
    (the row stays due while the current phase is unset)."""
    if isinstance(new, str) and not new.strip():
        return True
    new_p = parse_phase_like(new)
    if new_p is None:
        return False
    cap = None
    if isinstance(current, str) and current.strip():
        cap = parse_phase_like(current)
    if isinstance(existing, str) and existing.strip():
        ex_p = parse_phase_like(existing)
        if ex_p is not None and (cap is None or ex_p > cap):
            cap = ex_p
    if cap is None:
        return True
    return new_p <= cap


def handoff_state_path(root):
    return Path(root) / ".claude" / "ledger-state" / "handoff.json"


def current_handoff(root, ledger_file, sums_file, data):
    try:
        digest = hashlib.sha256(sums_file.read_bytes()).hexdigest()
    except OSError as exc:
        return fail(f"cannot read checksums.sha256: {exc}")
    return {"ledger_version": data.get("ledger_version"),
            "checksums_sha256": digest, "recorded_at": utc_now()}


def handoff_tripped(root):
    """True when the SessionStart hook marked the pause record tripped."""
    try:
        record = json.loads(handoff_state_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("tripped") is True


def write_handoff(root, record):
    state = handoff_state_path(root)
    ignore = state.parent / ".gitignore"
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
        tmp_fd, tmp = tempfile.mkstemp(dir=str(state.parent),
                                       prefix="handoff.", suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record, indent=2) + "\n")
        os.replace(tmp, state)
    except OSError as exc:
        return fail(f"cannot write handoff state: {exc}")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger-amend.py")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p_add = sub.add_parser("add")
    p_add.add_argument("--text", required=True)
    p_add.add_argument("--id", default=None)
    p_add.add_argument("--spec-ref", default="")
    p_set = sub.add_parser("set")
    p_set.add_argument("--id", required=True)
    p_set.add_argument("--spec-ref", default=None)
    p_set.add_argument("--test-ref", default=None)
    p_set.add_argument("--code-ref", default=None)
    p_set.add_argument("--evidence", default=None)
    p_set.add_argument("--phase", default=None)
    p_st = sub.add_parser("set-status")
    p_st.add_argument("--id", required=True)
    p_st.add_argument("--status", required=True)
    p_st.add_argument("--reason", default=None)
    p_st.add_argument("--owner", default=None)
    p_st.add_argument("--phase", default=None)
    p_ap = sub.add_parser("approve")
    p_ap.add_argument("--id", required=True)
    p_ap.add_argument("--quote", required=True)
    p_ap.add_argument("--source", default=None)
    p_rj = sub.add_parser("reject")
    p_rj.add_argument("--id", required=True)
    p_rj.add_argument("--reason", required=True)
    p_rj.add_argument("--quote", required=True)
    p_rj.add_argument("--source", default=None)
    p_dr = sub.add_parser("drop")
    p_dr.add_argument("--id", required=True)
    p_dr.add_argument("--reason", required=True)
    p_dr.add_argument("--quote", required=True)
    p_dr.add_argument("--source", default=None)
    p_fu = sub.add_parser("add-follow-up")
    p_fu.add_argument("--text", required=True)
    p_fu.add_argument("--source", required=True)
    p_fu.add_argument("--to", required=True)
    p_fu.add_argument("--id", default=None)
    p_pk = sub.add_parser("park")
    p_pk.add_argument("--id", required=True)
    p_pk.add_argument("--to", required=True)
    p_pk.add_argument("--reason", required=True)
    p_sk = sub.add_parser("set-kind")
    p_sk.add_argument("--id", required=True)
    p_sk.add_argument("--kind", required=True)
    p_sn = sub.add_parser("set-notify")
    p_sn.add_argument("--cmd", dest="notify_cmd_value", default=None)
    p_sn.add_argument("--clear", action="store_true")
    p_sp = sub.add_parser("set-phase")
    p_sp.add_argument("--phase", required=True)
    p_sc = sub.add_parser("set-check")
    p_sc.add_argument("--cmd", dest="check_cmd_value", required=True)
    p_fv = sub.add_parser("freeze-variant")
    p_fv.add_argument("--variant", required=True)
    p_fv.add_argument("--path", required=True)
    p_ls = sub.add_parser("lock-scope")
    p_ls.add_argument("--phase", required=False, default=None)
    p_ls.add_argument("--source", required=False, default=None)
    p_rf = sub.add_parser("record-fail")
    p_rf.add_argument("--id", required=True)
    p_rf.add_argument("--cmd", dest="fail_cmd", required=True)
    p_rf.add_argument("--timeout", type=int, default=300)
    p_rf.add_argument("--at", default=None)
    p_sb = sub.add_parser("set-budgets")
    p_sb.add_argument("--repeat-block", type=int, default=None)
    p_sb.add_argument("--same-rounds", type=int, default=None)
    p_sb.add_argument("--no-progress-min", type=int, default=None)
    p_sb.add_argument("--hang-min", type=int, default=None)
    p_sb.add_argument("--owner-wait-h", type=int, default=None)
    p_pl = sub.add_parser("record-plants")
    p_pl.add_argument("--id", required=True)
    p_pl.add_argument("--timeout", type=int, default=300)
    p_af = sub.add_parser("add-finding")
    p_af.add_argument("--id", required=True)
    p_af.add_argument("--text", required=True)
    p_af.add_argument("--source", required=True)
    p_af.add_argument("--key", required=True)
    p_af.add_argument("--severity", required=True, choices=["critical", "important"])
    p_rr = sub.add_parser("record-run")
    p_rr.add_argument("--id", required=True)
    p_rr.add_argument("--cmd", dest="run_cmd", required=True)
    p_rr.add_argument("--timeout", type=int, default=300)
    p_rr.add_argument("--cwd", default=None)
    sub.add_parser("import-runs")  # PB-R6: no path; it reads only <root>/.bak/prove-ledger
    p_lc = sub.add_parser("lock-checks")
    p_lc.add_argument("--commit", required=True)
    p_lc.add_argument("--also", action="append", default=None)
    p_dc = sub.add_parser("dispute-check")
    p_dc.add_argument("--id", required=True)
    p_dc.add_argument("--check-lines", required=True)
    p_dc.add_argument("--code-path", required=True)
    p_dc.add_argument("--proposed", required=True)
    p_dc.add_argument("--reason", required=True)
    p_gp = sub.add_parser("guard-paths")
    p_gp.add_argument("--add", default=None)
    p_gp.add_argument("--remove", default=None)
    p_gc = sub.add_parser("grant-check-edit")
    p_gc.add_argument("--file", required=True)
    p_gc.add_argument("--reason", required=True)
    sub.add_parser("baseline-checks")
    p_et = sub.add_parser("enable-trace")
    p_et.add_argument("--kind", required=True, choices=["code", "document"])
    p_rg = sub.add_parser("resume-gate")
    p_rg.add_argument("--reason", required=True)
    p_rg.add_argument("--quote", required=True)
    p_ib = sub.add_parser("import-brainstorm")
    p_ib.add_argument("--file", required=True)
    sub.add_parser("freeze")
    sub.add_parser("record-handoff")
    sub.add_parser("acknowledge-handoff")
    args = ap.parse_args(argv)
    _run.update(root=args.root, cmd=args.cmd, id=getattr(args, "id", None))
    source = {}  # who recorded a user decision, such as the UltraDogmatic panel
    if args.cmd in ("approve", "reject", "drop") and args.source is not None:
        if not SOURCE_RE.fullmatch(args.source):
            return fail("--source must be a short lowercase name (such as panel)")
        source = {"source": args.source}
    ledger_file, sums_file, log_path = ledger_paths(args.root)
    if args.cmd == "init":
        if ledger_file.exists():
            return fail("ledger already exists")
        data = {"ledger_version": 0, "frozen_at": None, "items": [],
                "current_phase": None, "check_cmd": None,
                "mockup_freeze": None, "scope_lock": None,
                "check_locks": None, "trace": None,
                "stall_budgets": {"repeat_block": 3, "same_rounds": 2,
                                  "no_progress_min": 60, "hang_min": 10,
                                  "owner_wait_h": 24},
                "check_guard": [], "check_edit_grants": {},
                "notify_cmd": None}
        return commit(args.root, data, "init", "", {})
    try:
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"cannot read ledger: {exc}")
    if not sums_match(ledger_file, sums_file, log_path):
        return fail(SUMS_MISMATCH)
    try:
        ops = read_log(log_path)
    except (ValueError, OSError) as exc:
        return fail(f"history/log.jsonl unparsable: {exc}")
    if not isinstance(data.get("items"), list):
        return fail("items must be a list")
    if args.cmd == "add":
        rid = args.id or next_req_id(ops)
        if not ID_RE.match(rid):
            return fail(f"{rid}: malformed id")
        if ever_added(ops, data["items"], rid):
            return fail(f"{rid}: id was already added")
        row = blank_row(rid, args.text, args.spec_ref)
        data["items"].append(row)
        return commit(args.root, data, "add", rid, {"row": row})
    if args.cmd == "set":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        given = {k: v for k, v in
                 (("spec_ref", args.spec_ref), ("test_ref", args.test_ref),
                  ("code_ref", args.code_ref), ("evidence", args.evidence))
                 if v is not None}
        if args.phase is not None:
            if row.get("phase", ""):
                return fail(f"{args.id}: set --phase needs an empty phase "
                            f"(found {row.get('phase', '')})")
            if args.phase.strip().lower() == "backlog":
                return fail(f"{args.id}: set --phase cannot set backlog")
            if parse_phase_like(args.phase) is None:
                return fail(f"{args.id}: set --phase must be a phase number "
                            "(such as 4 or 2.1)")
            if row.get("phase", "") != args.phase:
                given["phase"] = args.phase
            if data.get("frozen_at") is not None \
                    and not phase_move_allowed(data.get("current_phase"),
                                               "", args.phase):
                return fail(f"{args.id}: moving phase later is a deferral; "
                            "use set-status deferred-requested and wait for "
                            "the user's APPROVE")
        if not given:
            return fail("set needs at least one of --spec-ref/--test-ref/--code-ref/--evidence/--phase")
        changes = {k: [row.get(k, ""), v] for k, v in given.items()
                   if row.get(k, "") != v}
        for k, v in given.items():
            row[k] = v
        return commit(args.root, data, "set", args.id, {"changes": changes})
    if args.cmd == "set-status":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if args.status not in STATUS_VALUES:
            return fail(f"{args.id}: bad status {args.status}")
        if args.status in ("deferred-approved", "dropped"):
            return fail(f"{args.id}: set-status cannot set {args.status}; "
                         "only the user approval path (approve/drop) reaches it")
        if args.status == "parked":
            return fail(f"{args.id}: set-status cannot set parked; "
                         "use park for a follow-up")
        if args.status == "disputed":
            return fail(f"{args.id}: set-status cannot set disputed; "
                         "use dispute-check to dispute a row")
        if row.get("status") == "disputed":
            return fail(f"{args.id}: set-status cannot leave disputed; "
                         "the owner answers with approve or reject")
        changes = {}
        if args.status == "deferred-requested":
            if not args.owner or not args.phase or not args.reason:
                return fail(f"{args.id}: deferral needs --owner, --phase and --reason")
            if parse_phase_like(args.phase) is None:
                return fail(f"{args.id}: deferral phase must be a phase number or backlog (such as 4, 2.1 or backlog)")
            for k, v in (("owner", args.owner), ("phase", args.phase),
                         ("reason", args.reason)):
                if row.get(k, "") != v:
                    changes[k] = [row.get(k, ""), v]
                row[k] = v
            if row.get("deferred_at", "") != today():
                changes["deferred_at"] = [row.get("deferred_at", ""), today()]
            row["deferred_at"] = today()
        else:
            for k, v in (("reason", args.reason), ("owner", args.owner),
                         ("phase", args.phase)):
                if v is not None and row.get(k, "") != v:
                    if k == "phase" and data.get("frozen_at") is not None \
                            and not phase_move_allowed(data.get("current_phase"),
                                                       row.get("phase", ""), v):
                        return fail(f"{args.id}: moving phase later is a deferral; "
                                    "use set-status deferred-requested and wait for "
                                    "the user's APPROVE")
                    changes[k] = [row.get(k, ""), v]
                    row[k] = v
            if row.get("status") in ("deferred-requested", "deferred-approved",
                                     "parked") and args.status in ("open", "done",
                                                                   "verified"):
                cur = data.get("current_phase")
                want = cur.strip() if isinstance(cur, str) and cur.strip() else ""
                if row.get("phase", "") != want:
                    if data.get("frozen_at") is not None \
                            and not phase_move_allowed(data.get("current_phase"),
                                                       row.get("phase", ""), want):
                        return fail(f"{args.id}: moving phase later is a deferral; "
                                    "use set-status deferred-requested and wait for "
                                    "the user's APPROVE")
                    changes["phase"] = [row.get("phase", ""), want]
                row["phase"] = want
        if row.get("status", "") != args.status:
            changes["status"] = [row.get("status", ""), args.status]
        row["status"] = args.status
        return commit(args.root, data, "set-status", args.id, {"changes": changes})
    if args.cmd == "approve":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if row.get("status") == "disputed":
            if not isinstance(args.quote, str) or not args.quote.strip():
                return fail(f"{args.id}: approve needs --quote with the user's quoted text")
            proposed = None
            try:
                for op in read_log(ledger_paths(args.root)[2]):
                    if isinstance(op, dict) and op.get("op") == "dispute-check" \
                            and op.get("id") == args.id \
                            and isinstance(op.get("proposed"), str):
                        proposed = op["proposed"]
            except (ValueError, OSError):
                proposed = None
            if not proposed:
                return fail(f"{args.id}: approve found no dispute-check proposal")
            changes = {"status": [row.get("status", ""), "open"]}
            if row.get("test_ref", "") != proposed:
                changes["test_ref"] = [row.get("test_ref", ""), proposed]
            row["status"] = "open"
            row["test_ref"] = proposed
            return commit(args.root, data, "approve", args.id,
                          {"quote": args.quote, **source, "dispute": "approved",
                           "changes": changes})
        if row.get("status") != "deferred-requested":
            return fail(f"{args.id}: approve needs status deferred-requested or disputed "
                        f"(found {row.get('status')})")
        if not isinstance(args.quote, str) or not args.quote.strip():
            return fail(f"{args.id}: approve needs --quote with the user's quoted text")
        changes = {"status": [row.get("status", ""), "deferred-approved"]}
        row["status"] = "deferred-approved"
        return commit(args.root, data, "approve", args.id,
                      {"quote": args.quote, **source, "changes": changes})
    if args.cmd == "reject":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if row.get("status") == "disputed":
            if not isinstance(args.reason, str) or not args.reason.strip():
                return fail(f"{args.id}: reject needs --reason")
            if not isinstance(args.quote, str) or not args.quote.strip():
                return fail(f"{args.id}: reject needs --quote with the user's quoted text")
            changes = {"status": [row.get("status", ""), "open"]}
            if row.get("reason", "") != args.reason:
                changes["reason"] = [row.get("reason", ""), args.reason]
            row["status"] = "open"
            row["reason"] = args.reason
            return commit(args.root, data, "reject", args.id,
                          {"quote": args.quote, **source, "changes": changes})
        if row.get("status") not in ("deferred-requested", "parked"):
            return fail(f"{args.id}: reject needs status deferred-requested or parked "
                        f"(found {row.get('status')})")
        if not isinstance(args.reason, str) or not args.reason.strip():
            return fail(f"{args.id}: reject needs --reason")
        if not isinstance(args.quote, str) or not args.quote.strip():
            return fail(f"{args.id}: reject needs --quote with the user's quoted text")
        changes = {"status": [row.get("status", ""), "open"]}
        if row.get("reason", "") != args.reason:
            changes["reason"] = [row.get("reason", ""), args.reason]
        if row.get("status") == "parked":
            cur = data.get("current_phase")
            want = cur.strip() if isinstance(cur, str) and cur.strip() else ""
            if row.get("phase", "") != want:
                changes["phase"] = [row.get("phase", ""), want]
            row["phase"] = want
        else:
            old_phase = row.get("phase", "")
            if old_phase != "":
                changes["phase"] = [old_phase, ""]
                row["phase"] = ""
        row["status"] = "open"
        row["reason"] = args.reason
        return commit(args.root, data, "reject", args.id,
                      {"quote": args.quote, **source, "changes": changes})
    if args.cmd == "drop":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if row.get("status") == "dropped":
            return fail(f"{args.id}: already dropped")
        if not isinstance(args.reason, str) or not args.reason.strip():
            return fail(f"{args.id}: drop needs --reason")
        if not isinstance(args.quote, str) or not args.quote.strip():
            return fail(f"{args.id}: drop needs --quote with the user's quoted text")
        changes = {"status": [row.get("status", ""), "dropped"]}
        if row.get("reason", "") != args.reason:
            changes["reason"] = [row.get("reason", ""), args.reason]
        row["status"] = "dropped"
        row["reason"] = args.reason
        return commit(args.root, data, "drop", args.id,
                      {"quote": args.quote, **source, "changes": changes})
    if args.cmd == "add-follow-up":
        rid = args.id or next_req_id(ops)
        if not ID_RE.match(rid):
            return fail(f"{rid}: malformed id")
        if ever_added(ops, data["items"], rid):
            return fail(f"{rid}: id was already added")
        if not args.text.strip():
            return fail(f"{rid}: add-follow-up needs --text")
        if not args.source.strip():
            return fail(f"{rid}: add-follow-up needs --source")
        target = args.to.strip()
        if parse_phase_like(target) is None:
            return fail(f"{rid}: target phase must be a phase number or backlog (such as 4, 2.1 or backlog)")
        row = blank_row(rid, args.text, args.source)
        # blank_row defaults kind requirement (C13.1 optional-kind); follow-ups override it.
        row["kind"] = "follow-up"
        row["status"] = "parked"
        row["phase"] = target
        data["items"].append(row)
        return commit(args.root, data, "add-follow-up", rid, {"row": row})
    if args.cmd == "park":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if row.get("kind", "requirement") != "follow-up":
            return fail(f"{args.id}: park needs a follow-up row (kind follow-up)")
        if row.get("status") not in ("open", "parked"):
            return fail(f"{args.id}: park needs status open or parked "
                        f"(found {row.get('status')})")
        if not isinstance(args.reason, str) or not args.reason.strip():
            return fail(f"{args.id}: park needs --reason")
        target = args.to.strip()
        if parse_phase_like(target) is None:
            return fail(f"{args.id}: target phase must be a phase number or backlog (such as 4, 2.1 or backlog)")
        parks = sum(1 for op in ops if isinstance(op, dict)
                    and op.get("op") == "park" and op.get("id") == args.id)
        if parks >= 2:
            old = row.get("status", "")
            owner = row.get("owner", "") or "agent"
            changes = {"status": [old, "deferred-requested"]}
            if row.get("phase", "") != target:
                changes["phase"] = [row.get("phase", ""), target]
            if owner != row.get("owner", ""):
                changes["owner"] = [row.get("owner", ""), owner]
            if row.get("reason", "") != args.reason:
                changes["reason"] = [row.get("reason", ""), args.reason]
            row["status"] = "deferred-requested"
            row["phase"] = target
            row["owner"] = owner
            row["reason"] = args.reason
            if row.get("deferred_at", "") != today():
                changes["deferred_at"] = [row.get("deferred_at", ""), today()]
            row["deferred_at"] = today()
            rc = commit(args.root, data, "park", args.id,
                        {"changes": changes, "escalated": True})
            if rc == 0:
                print(f"{args.id}: parked twice already; the owner decides now "
                      f"(APPROVE {args.id} or REJECT {args.id} <reason>)")
            return rc
        changes = {}
        if row.get("phase", "") != target:
            changes["phase"] = [row.get("phase", ""), target]
        if row.get("reason", "") != args.reason:
            changes["reason"] = [row.get("reason", ""), args.reason]
        if row.get("status", "") != "parked":
            changes["status"] = [row.get("status", ""), "parked"]
        row["phase"] = target
        row["reason"] = args.reason
        row["status"] = "parked"
        return commit(args.root, data, "park", args.id, {"changes": changes})
    if args.cmd == "set-kind":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if args.kind not in ("requirement", "finding", "follow-up"):
            return fail(f"{args.id}: bad kind {args.kind}")
        old = row.get("kind", "requirement")
        row["kind"] = args.kind
        changes = {"kind": [old, args.kind]} if old != args.kind else {}
        return commit(args.root, data, "set-kind", args.id, {"changes": changes})
    if args.cmd == "set-notify":
        if args.clear and args.notify_cmd_value is not None:
            return fail("set-notify needs either --cmd CMD or --clear, not both")
        if not args.clear and (args.notify_cmd_value is None or not args.notify_cmd_value.strip()):
            return fail("set-notify needs --cmd CMD or --clear")
        old = data.get("notify_cmd")
        data["notify_cmd"] = None if args.clear else args.notify_cmd_value
        changes = {"notify_cmd": [old, data["notify_cmd"]]} if old != data["notify_cmd"] else {}
        return commit(args.root, data, "set-notify", "", {"changes": changes})
    if args.cmd == "set-phase":
        new = args.phase.strip() if isinstance(args.phase, str) else ""
        if not new:
            return fail("set-phase needs --phase with a phase value")
        if isinstance(new, str) and new.strip().lower() == "backlog":
            return fail("set-phase refuses backlog as the current phase "
                        "(backlog is never due, so the ledger could not move "
                        "to a numbered phase again)")
        if parse_phase_like(new) is None:
            return fail(f"current_phase must be a number such as 3 or 2.1: {new}")
        cur = data.get("current_phase")
        if isinstance(cur, str) and cur.strip():
            new_p = parse_phase_like(new)
            cur_p = parse_phase_like(cur)
            if new_p is not None and cur_p is not None and new_p < cur_p:
                return fail(f"set-phase refuses backwards move "
                            f"(current phase {cur}, requested {new})")
        old = data.get("current_phase")
        data["current_phase"] = new
        changes = {"current_phase": [old, new]} if old != new else {}
        return commit(args.root, data, "set-phase", "",
                      {"changes": changes})
    if args.cmd == "set-check":
        raw = args.check_cmd_value
        cmd = raw.strip() if isinstance(raw, str) else ""
        value = cmd if cmd else None
        old = data.get("check_cmd")
        data["check_cmd"] = value
        changes = {"check_cmd": [old, value]} if old != value else {}
        return commit(args.root, data, "set-check", "",
                      {"changes": changes})
    if args.cmd == "freeze-variant":
        variant = args.variant.strip() if isinstance(args.variant, str) else ""
        rel = args.path.strip() if isinstance(args.path, str) else ""
        if not variant:
            return fail("freeze-variant needs --variant with a variant ID")
        if not rel:
            return fail("freeze-variant needs --path with the frozen mockup path")
        try:
            root_resolved = Path(args.root).resolve()
            target_resolved = (root_resolved / rel).resolve()
        except OSError:
            return fail(f"freeze-variant: mockup file not found: {rel}")
        try:
            target_resolved.relative_to(root_resolved)
        except ValueError:
            return fail(f"freeze-variant: path must be inside the project root: {rel}")
        rel = target_resolved.relative_to(root_resolved).as_posix()
        target = root_resolved / rel
        if not target.is_file():
            return fail(f"freeze-variant: mockup file not found: {rel}")
        try:
            blob = target.read_bytes()
        except OSError:
            return fail(f"freeze-variant: mockup file not found: {rel}")
        value = {"variant": variant, "path": rel,
                 "sha256": hashlib.sha256(blob).hexdigest()}
        old = data.get("mockup_freeze")
        data["mockup_freeze"] = value
        changes = {"mockup_freeze": [old, value]} if old != value else {}
        return commit(args.root, data, "freeze-variant", "",
                      {"changes": changes})
    def extract_phase_field(section, label):
        import re as _re
        lab = _re.escape(label)
        m = _re.search(r"\*\*" + lab + r"(?::\*\*|\*\*\s*:?)\s*([^\n]+)",
                       section, _re.IGNORECASE)
        if not m:
            return None
        first = m.group(1).strip()
        cont = []
        for raw in section[m.end():].split("\n")[1:]:
            if not raw.strip():
                break
            if _re.match(r"\s*\*\*[A-Z][A-Za-z ]*:?(\*\*)?:?\s", raw):
                break
            if _re.match(r"\s*#{1,4}\s", raw):
                break
            if _re.match(r"\s*\|", raw):
                break
            cont.append(raw.strip())
        val = " ".join([first] + cont).strip()
        return val or None

    def scope_prose_of(text, phase):
        import re as _re
        head = r"^#{2,4}\s*(?:\[[^\]]+\]\s*)?Phase\s+"
        blocks = _re.findall(r"(?m)" + head + _re.escape(phase) + r"(?![0-9.])[\s\S]*?"
                             r"(?=" + head + r"|\Z)", text, _re.IGNORECASE)
        if not blocks:
            return None, "block"
        if len(blocks) > 1:
            return None, "ambiguous"
        section = blocks[0]
        goal = extract_phase_field(section, "Goal")
        if goal is None:
            return None, "Goal"
        reqs = extract_phase_field(section, "Requirements")
        if reqs is None:
            return None, "Requirements"
        norm = lambda t: " ".join(t.split())
        blob = f"{norm(goal)}\n{norm(reqs)}".encode("utf-8")
        return hashlib.sha256(blob).hexdigest(), None

    if args.cmd == "lock-scope":
        raw_p = args.phase.strip() if isinstance(args.phase, str) else ""
        if args.phase is not None and parse_phase_like(raw_p) is None:
            return fail("lock-scope needs --phase with a phase value (such as 3 or 2.1)")
        if args.source is None:
            src = "ROADMAP.md" if raw_p else ""
            if src and not (Path(args.root) / src).exists() \
                    and (Path(args.root) / ".planning" / "ROADMAP.md").is_file():
                src = ".planning/ROADMAP.md"  # GSD layout
        else:
            src = args.source.strip() if isinstance(args.source, str) else ""
        if not src:
            return fail("lock-scope needs --source with the scope file path")
        target = Path(args.root) / src
        try:
            content = target.read_bytes()
        except OSError:
            return fail(f"lock-scope: scope file not found: {src}")
        if raw_p:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return fail(f"lock-scope: scope file not found: {src}")
            digest, missing = scope_prose_of(text, raw_p)
            if missing == "block":
                return fail(f"lock-scope: phase block not found: phase {raw_p} in {src}")
            if missing == "ambiguous":
                return fail(f"lock-scope: phase block ambiguous: phase {raw_p} in {src}")
            if missing in ("Goal", "Requirements"):
                return fail(f"lock-scope: scope field missing: {missing} (locked phase {raw_p})")
        else:
            digest = hashlib.sha256(content).hexdigest()
        old = data.get("scope_lock")
        data["scope_lock"] = {"phase": raw_p, "source": src, "sha256": digest}
        rc = commit(args.root, data, "lock-scope", "",
                    {"changes": {"scope_lock": [old, data["scope_lock"]]}})
        if rc == 0 and isinstance(old, dict) and old.get("phase") \
                and parse_phase_like(old["phase"]) != parse_phase_like(raw_p):
            print(f"replaced lock on phase {old['phase']}")
        return rc
    if args.cmd == "record-fail":
        import hashlib as _hl
        import os as _os
        import shlex as _shlex
        import signal as _sig
        import subprocess as _sp
        from pathlib import Path as _Path
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        ref = row.get("test_ref", "")
        ref = ref if isinstance(ref, str) else ""
        if not ref.strip():
            return fail(f"{args.id}: missing check (empty test_ref)")
        path_part = ref.split("::", 1)[0].strip()
        node = ref.partition("::")[2].strip()
        try:
            root = _Path(args.root).resolve()
            test_file = root / check_key(root, path_part)
            digest = _hl.sha256(test_file.read_bytes()).hexdigest()
        except ValueError as exc:
            return fail(f"{args.id}: {exc} ({ref})")
        except OSError:
            return fail(f"{args.id}: check not found ({ref})")
        cmd = args.fail_cmd if isinstance(args.fail_cmd, str) else ""
        try:  # the path must be in the command itself, not in a # comment.
            # Like bash, only a # that starts a token begins a comment: a # inside
            # a word (such as an SPA hash route) is part of the token.
            raw = _shlex.split(cmd, comments=False)
            tokens = []
            for token in raw:
                if token.startswith("#"):
                    break
                tokens.append(token)
        except ValueError:
            tokens = []
        if not any(path_part in token for token in tokens):
            return fail(f"{args.id}: record-fail needs --cmd containing the check path")
        try:
            timeout = int(args.timeout)
        except (TypeError, ValueError):
            return fail(f"{args.id}: record-fail needs --timeout as seconds")
        if timeout <= 0:
            return fail(f"{args.id}: record-fail needs --timeout as seconds")
        run_dir, at_commit = str(root), ""
        _at_old = {}  # restored handlers; filled only on the --at path
        if args.at is not None:  # C11.1: run the current check on the pre-fix code
            import atexit as _atexit
            import shutil as _shutil
            import tempfile as _tf
            try:  # M4: a root outside a git work tree names the problem, not the commit
                _gitdir = _sp.run(["git", "-C", str(root), "rev-parse", "--git-dir"],
                                  capture_output=True, text=True, timeout=30)
            except (OSError, _sp.SubprocessError):
                _gitdir = None
            if _gitdir is None or _gitdir.returncode != 0:
                return fail(f"{args.id}: record-fail --at needs a git work tree")
            try:
                rev = _sp.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet",
                               f"{args.at.strip()}^{{commit}}"],
                              capture_output=True, text=True, timeout=30)
                at_commit = rev.stdout.strip() if rev.returncode == 0 else ""
            except (OSError, _sp.SubprocessError):
                at_commit = ""
            if not at_commit:
                return fail(f"{args.id}: record-fail --at unknown commit {args.at}")
            run_dir = _tf.mkdtemp(prefix="bak-at-")

            def _drop_worktree():  # PB3-6: runs on every exit path
                _sp.run(["git", "-C", str(root), "worktree", "remove", "--force", run_dir],
                        capture_output=True)
                _shutil.rmtree(run_dir, ignore_errors=True)
                _sp.run(["git", "-C", str(root), "worktree", "prune"], capture_output=True)
            _atexit.register(_drop_worktree)
            added = _sp.run(["git", "-C", str(root), "worktree", "add", "--detach",
                             run_dir, at_commit], capture_output=True, text=True)
            if added.returncode != 0:
                return fail(f"{args.id}: record-fail --at cannot check out {at_commit}: "
                            f"{added.stderr.strip()}")
            staged = _Path(run_dir) / test_file.relative_to(root)
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(test_file.read_bytes())  # the current check, on the old code
            _control = {"proc": None}  # I5 (--at half): a SIGTERM/SIGINT/SIGHUP
            # kills the running child group and raises SystemExit(143), so the
            # _drop_worktree atexit cleanup runs.

            def _on_at_term(_signum, _frame):
                proc = _control["proc"]
                if proc is not None and proc.poll() is None:
                    try:
                        if hasattr(_os, "killpg"):
                            _os.killpg(proc.pid, _sig.SIGKILL)
                        else:
                            proc.kill()
                    except OSError:
                        pass
                raise SystemExit(143)

            _at_old = {}
            for _name in ("SIGTERM", "SIGINT", "SIGHUP"):
                if hasattr(_sig, _name):
                    try:
                        _at_old[_name] = _sig.signal(getattr(_sig, _name), _on_at_term)
                    except (OSError, ValueError, RuntimeError):
                        pass

            def _run_tree(_dir):  # run cmd in one worktree dir; returns (text, code)
                _child = _sp.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=str(_dir),
                                   stdout=_sp.PIPE, stderr=_sp.STDOUT,
                                   start_new_session=True, text=True, errors="replace")
                _control["proc"] = _child
                try:
                    _text, _ = _child.communicate(timeout=timeout)
                except _sp.TimeoutExpired:
                    try:
                        if hasattr(_os, "killpg"):
                            _os.killpg(_child.pid, _sig.SIGKILL)
                        else:
                            _child.kill()
                    except OSError:
                        pass
                    try:
                        _child.communicate(timeout=5)
                    except _sp.TimeoutExpired:
                        pass
                    return None, "timeout"
                finally:
                    _control["proc"] = None
                return _text, _child.returncode

            # I6 (C11.1 control run, PB-R11): the same command with the same
            # overlay must pass in a second temporary worktree at HEAD before
            # the --at failure is recorded. Otherwise the --at "proof" may be
            # a bare-worktree environment failure (missing untracked files).
            _head_dir = _tf.mkdtemp(prefix="bak-at-control-")

            def _drop_control():  # PB3-6: remove both worktrees on every exit path
                _sp.run(["git", "-C", str(root), "worktree", "remove", "--force", _head_dir],
                        capture_output=True)
                _shutil.rmtree(_head_dir, ignore_errors=True)
                _sp.run(["git", "-C", str(root), "worktree", "prune"], capture_output=True)

            _atexit.register(_drop_control)
            _head_c = _sp.run(["git", "-C", str(root), "worktree", "add", "--detach",
                               _head_dir, "HEAD"], capture_output=True, text=True)
            if _head_c.returncode != 0:
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
                return fail(f"{args.id}: record-fail --at cannot check out HEAD: "
                            f"{_head_c.stderr.strip()}")
            _head_staged = _Path(_head_dir) / test_file.relative_to(root)
            _head_staged.parent.mkdir(parents=True, exist_ok=True)
            _head_staged.write_bytes(test_file.read_bytes())
            # Copy sibling untracked files (helpers, fixtures) into both
            # worktrees so a passing HEAD tree stays passing there: the
            # control run distinguishes a real pre-fix failure (fails at
            # COMMIT, passes at HEAD) from an environment failure (fails in
            # both). Tracked files come from the checkout. Ignored outputs
            # (node_modules, .venv, build dirs) are skipped by asking git for
            # untracked files without ignored ones; explicit paths that look
            # like dependency or build output are skipped too.
            _tracked = set()
            try:
                _ls = _sp.run(["git", "-C", str(root), "ls-files", "-z"],
                              capture_output=True, text=True, timeout=30)
                if _ls.returncode == 0:
                    _tracked = set(_ls.stdout.split("\0"))
            except (OSError, _sp.SubprocessError):
                _tracked = set()
            try:
                _un = _sp.run(["git", "-C", str(root), "status", "--porcelain=v1",
                               "--untracked-files=all", "--no-renames", "--", "."],
                              capture_output=True, text=True, timeout=30)
                _raw = _un.stdout if _un.returncode == 0 else ""
                _untracked = [e for e in _raw.split("\0") if e]
                if len(_untracked) == 1 and "\n" in _untracked[0]:
                    _untracked = [e for e in _untracked[0].splitlines() if e]
            except (OSError, _sp.SubprocessError):
                _untracked = []
            for _entry in _untracked:
                if len(_entry) < 4 or _entry[2] != " ":
                    continue
                _rel = _entry[3:].strip().strip('"')
                if _rel.startswith('"') and _rel.endswith('"') and len(_rel) >= 2:
                    _rel = _rel[1:-1]
                if not _rel or _rel.startswith(".git/") or _rel == ".git":
                    continue
                if " -> " in _rel:  # a rename entry names two paths; take the target
                    _rel = _rel.rsplit(" -> ", 1)[1].strip().strip('"')
                if _rel in _tracked:
                    continue
                try:
                    _src = root / _rel
                    _resolved = _src.resolve()
                    _resolved.relative_to(root)
                    if not _resolved.is_file():
                        continue
                    _blob = _resolved.read_bytes()
                except (OSError, ValueError, RuntimeError):
                    continue
                for _base in (run_dir, _head_dir):
                    try:
                        _dst = _Path(_base) / _rel
                        if _dst.exists():
                            continue
                        _dst.parent.mkdir(parents=True, exist_ok=True)
                        _dst.write_bytes(_blob)
                    except OSError:
                        pass
            # Handlers stay installed through the rest of this subcommand so a
            # SIGTERM/SIGINT/SIGHUP at any point still runs the atexit cleanup.
            _control_text, _control_code = _run_tree(_head_dir)
            if _control_code == "timeout":
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
                return fail(f"{args.id}: check command timed out after {timeout}s")
            if _control_code != 0:
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
                return fail(f"record-fail --at: the check also fails at HEAD in a clean "
                            f"worktree (exit {_control_code}); the failure may come from "
                            f"missing untracked files (dependencies, build output), so it "
                            f"is not a pre-fix proof")
            text, code = _run_tree(run_dir)
            if code == "timeout":
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
                return fail(f"{args.id}: check command timed out after {timeout}s")
        else:
            try:
                child = _sp.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=run_dir,
                                  stdout=_sp.PIPE, stderr=_sp.STDOUT,
                                  start_new_session=True, text=True, errors="replace")
            except OSError:
                return fail("check_cmd could not run: bash not found")
            try:
                text, _ = child.communicate(timeout=timeout)
            except _sp.TimeoutExpired:
                try:
                    if hasattr(_os, "killpg"):
                        _os.killpg(child.pid, _sig.SIGKILL)
                    else:  # no process groups (Windows): kill the shell itself
                        child.kill()
                except OSError:
                    pass
                try:
                    child.communicate(timeout=5)
                except _sp.TimeoutExpired:
                    pass
                return fail(f"{args.id}: check command timed out after {timeout}s")
            code = child.returncode
        if code == 0:
            if at_commit:
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
            print(f"{args.id}: check passed, so it cannot prove a failure; "
                  f"record-fail needs a failing run before the code exists",
                  file=sys.stderr)
            _baklog(args.root, "1.1 ledger-amend", "record-fail", "block", f"{args.id}: check passed, so it cannot prove a failure; record-fail needs a failing run before the code exists", target=args.id)
            return 1
        lines = [line for line in (text or "").splitlines() if line.strip()]
        tail = lines[-20:]
        if not tail:
            if at_commit:
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
            return fail(f"{args.id}: check failed with no output, so the failure cannot be shown")
        named = next((line for line in lines if names_test(line, path_part, node)), None)
        if named is None:
            if at_commit:
                for _name, _handler in _at_old.items():
                    try:
                        _sig.signal(getattr(_sig, _name), _handler)
                    except (OSError, ValueError, RuntimeError):
                        pass
            fail(f"{args.id}: the failing run never names its test {node}, so it may have "
                 "failed for another reason; fix the run and record it again")
            print("\n".join(tail), file=sys.stderr)
            return 1
        if not names_test("\n".join(tail), path_part, node):
            tail = [named] + tail  # keep what phase-gate.py judges equal to what was judged here
        # The run can take minutes. Re-read everything it could have changed and commit
        # from the fresh data, so an amend made meanwhile survives and nothing that
        # changed out of band gets sealed (commit() re-reads the log itself).
        try:
            data = json.loads(ledger_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return fail(f"cannot read ledger: {exc}")
        if not sums_match(ledger_file, sums_file, log_path):
            return fail(SUMS_MISMATCH)
        row = find_row(data, args.id)
        if row is None or row.get("test_ref") != ref:
            return fail(f"{args.id}: test_ref changed while the check ran")
        try:
            after = _hl.sha256(test_file.read_bytes()).hexdigest()
        except OSError:
            after = None
        if after != digest:
            return fail(f"{args.id}: test file changed while the check ran")
        try:
            head_c = _sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
            head = head_c.stdout.strip() if head_c.returncode == 0 else ""
        except Exception:
            head = ""
        if at_commit:  # C11.1: the proof names the pre-fix commit it ran on
            head = at_commit
        for _name, _handler in _at_old.items():
            try:
                _sig.signal(getattr(_sig, _name), _handler)
            except (OSError, ValueError, RuntimeError):
                pass
        return commit(args.root, data, "check-fail", args.id,
                      {"ref": ref, "cmd": cmd, "exit": code,
                       "output": "\n".join(tail), "head": head,
                       "sha256": digest, **({"at": at_commit} if at_commit else {})})
    if args.cmd == "record-plants":
        import base64 as _b64
        import signal as _sig
        import subprocess as _sp
        root = Path(args.root).resolve()
        marker = root / ".bak" / f"plants-{args.id}.json"
        # PB-R11 restore guard: the marker is agent-writable, so a restore
        # touches only files the ID's current plants/<ID>.json lists, only
        # when the saved bytes match their saved hash, and never a protected
        # path. A refused file prints a line and is left unchanged.
        try:
            _payload = json.loads((root / "plants" / f"{args.id}.json")
                                  .read_text(encoding="utf-8"))
            _entries = _payload.get("plants") if isinstance(_payload, dict) \
                and _payload.get("id") == args.id else None
        except (OSError, ValueError):
            _entries = None
        listed = set()
        if isinstance(_entries, list):
            for _p in _entries:
                if isinstance(_p, dict) and isinstance(_p.get("file"), str):
                    try:
                        listed.add(check_key(root, _p["file"]))
                    except ValueError:
                        pass
        listed_fold = {c.casefold() for c in listed}
        protected = set()
        for _row in data.get("items", []):
            if not isinstance(_row, dict):
                continue
            _ref = _row.get("test_ref", "")
            _part = _ref.split("::", 1)[0].strip() if isinstance(_ref, str) else ""
            if _part:
                try:
                    protected.add(check_key(root, _part))
                except ValueError:
                    pass
        _locks = data.get("check_locks")
        if isinstance(_locks, dict) and isinstance(_locks.get("files"), dict):
            for _k in _locks["files"]:
                if isinstance(_k, str) and _k.strip():
                    protected.add(_k.strip())
        _folders = []
        _guard = data.get("check_guard") or []
        if isinstance(_guard, list):
            for _entry in _guard:
                if not isinstance(_entry, str) or not _entry.strip():
                    continue
                _norm = _entry.strip()
                while _norm.startswith("./"):
                    _norm = _norm[2:].strip()
                _norm = Path(_norm).as_posix() if _norm else ""
                if not _norm or _norm == ".." or _norm.startswith("../"):
                    continue
                protected.add(_norm)
                _folders.append(_norm)

        def _restore_protected(pkey):
            if pkey.split("/")[0].lower() in ("ledger", ".bak"):
                return True
            low = pkey.casefold()
            for _name in protected:
                if not isinstance(_name, str):
                    continue
                _n = _name.casefold()
                if low == _n or low.startswith(_n.rstrip("/") + "/") \
                        or _n.startswith(low + "/"):
                    return True
            for _folder in _folders:
                _f = _folder.casefold().rstrip("/")
                if low == _f or low.startswith(_f + "/"):
                    return True
            return False

        # PB3-4: a run killed while a plant was applied left this marker. Put back
        # files that still hold planted bytes, before anything else.
        try:
            left = json.loads(marker.read_text(encoding="utf-8"))["files"]
        except (OSError, ValueError, KeyError, TypeError):
            left = {}
        for rel, saved in (left.items() if isinstance(left, dict) else ()):
            reason, pkey, orig = None, None, None
            if not isinstance(rel, str):
                reason = "bad path"
            else:
                try:
                    pkey = check_key(root, rel)
                except ValueError:
                    reason = "bad path"
            if reason is None and _restore_protected(pkey):
                reason = "protected path"
            if reason is None and pkey.casefold() not in listed_fold:
                reason = f"not listed in plants/{args.id}.json"
            if reason is None:
                try:
                    orig = _b64.b64decode(saved["orig"])
                except (ValueError, TypeError, KeyError, AttributeError):
                    orig = None
                if orig is None or not isinstance(saved, dict) \
                        or not isinstance(saved.get("sha256"), str) \
                        or hashlib.sha256(orig).hexdigest() != saved["sha256"]:
                    reason = "saved bytes do not match their hash"
            if reason is not None:
                print(f"record-plants: refused to restore {rel} from an "
                      f"interrupted run ({reason})")
                continue
            try:
                target = root / pkey
                if hashlib.sha256(target.read_bytes()).hexdigest() in saved["planted"]:
                    target.write_bytes(orig)
                    print(f"record-plants: restored {rel} from an interrupted run")
            except (OSError, ValueError, KeyError, TypeError):
                pass
        try:
            marker.unlink(missing_ok=True)
        except OSError:
            pass
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        ref = row.get("test_ref", "")
        ref = ref if isinstance(ref, str) else ""
        if not ref.strip():
            return fail(f"{args.id}: missing check (empty test_ref)")
        path_part = ref.split("::", 1)[0].strip()
        node = ref.partition("::")[2].strip()
        if args.timeout <= 0:
            return fail(f"{args.id}: record-plants needs --timeout as seconds")
        try:
            key = check_key(root, path_part)
            check_sha = hashlib.sha256((root / key).read_bytes()).hexdigest()
        except ValueError as exc:
            return fail(f"{args.id}: {exc} ({ref})")
        except OSError:
            return fail(f"{args.id}: check not found ({ref})")
        try:
            payload = json.loads((root / "plants" / f"{args.id}.json")
                                 .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = None
        plants = payload.get("plants") if isinstance(payload, dict) \
            and payload.get("id") == args.id else None
        if not isinstance(plants, list) or not plants or not all(
                isinstance(p, dict) and all(isinstance(p.get(k), str)
                                            for k in ("file", "find", "replace"))
                for p in plants):
            return fail(f"{args.id}: plants/{args.id}.json needs "
                        '{"id": ID, "plants": [{"file", "find", "replace"}]}')
        originals, planned = {}, []
        for p in plants:
            rel = p["file"]
            try:
                pkey = check_key(root, rel)
                raw = originals.get(pkey) or (root / pkey).read_bytes()
                text = raw.decode("utf-8")
            except (ValueError, OSError, UnicodeDecodeError):
                return fail(f"{args.id}: plant file not found ({rel})")
            if pkey == key or pkey.split("/")[0].lower() == "ledger":
                return fail(f"{args.id}: a plant must break the code, not the check "
                            f"or the ledger ({rel})")
            if text.count(p["find"]) != 1:
                return fail(f"{args.id}: plant find must occur exactly once in {rel}")
            try:
                st = _sp.run(["git", "-C", str(root), "status", "--porcelain", "--", pkey],
                             capture_output=True, text=True, timeout=30)
            except (OSError, _sp.SubprocessError):
                st = None
            if st is None or st.returncode != 0:
                return fail(f"{args.id}: record-plants needs a git work tree to see "
                            f"uncommitted changes in {rel}")
            if st.stdout.strip():
                return fail(f"{args.id}: plant file {rel} has uncommitted changes")
            originals[pkey] = raw
            planned.append((rel, pkey, text.replace(p["find"], p["replace"]).encode("utf-8")))
        cmd = ""
        for op in ops:  # the counting run: the latest check-fail that names the test
            if isinstance(op, dict) and op.get("op") == "check-fail" \
                    and op.get("id") == args.id and op.get("ref") == ref \
                    and isinstance(op.get("cmd"), str) and op["cmd"].strip() \
                    and isinstance(op.get("exit"), int) and op["exit"] != 0 \
                    and isinstance(op.get("output"), str) and op["output"].strip() \
                    and names_test(op["output"], path_part, node):
                cmd = op["cmd"]
        if not cmd:
            return fail(f"{args.id}: no counting check-fail to run the plants with "
                        "(record-fail first)")
        try:
            head_c = _sp.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
            head = head_c.stdout.strip() if head_c.returncode == 0 else ""
        except (OSError, _sp.SubprocessError):
            head = ""
        variants = {}
        for _rel, pkey, planted in planned:
            variants.setdefault(pkey, []).append(hashlib.sha256(planted).hexdigest())
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"id": args.id, "files": {
                k: {"sha256": hashlib.sha256(v).hexdigest(),
                    "orig": _b64.b64encode(v).decode("ascii"), "planted": variants[k]}
                for k, v in originals.items()}}) + "\n", encoding="utf-8")
        except OSError as exc:
            return fail(f"{args.id}: cannot write the restore marker {marker}: {exc}")
        results = []
        _child = {"proc": None}  # PB-R11: SIGTERM/SIGINT/SIGHUP kills the
        # current child's group, then raises SystemExit(143) so the finally
        # restore above runs.

        def _on_term(_signum, _frame):
            proc = _child["proc"]
            if proc is not None and proc.poll() is None:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(proc.pid, _sig.SIGKILL)
                    else:
                        proc.kill()
                except OSError:
                    pass
            raise SystemExit(143)

        _old = {}
        for _name in ("SIGTERM", "SIGINT", "SIGHUP"):
            if hasattr(_sig, _name):
                try:
                    _old[_name] = _sig.signal(getattr(_sig, _name), _on_term)
                except (OSError, ValueError, RuntimeError):
                    pass
        try:
            for n, (rel, pkey, planted) in enumerate(planned, start=1):
                (root / pkey).write_bytes(planted)
                try:
                    child = _sp.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=str(root),
                                      stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                                      start_new_session=True)
                    _child["proc"] = child
                    try:
                        code, hung = child.wait(timeout=args.timeout), False
                    except _sp.TimeoutExpired:
                        try:
                            if hasattr(os, "killpg"):
                                os.killpg(child.pid, _sig.SIGKILL)
                            else:  # no process groups (Windows): kill the shell itself
                                child.kill()
                        except OSError:
                            pass
                        child.wait()
                        code, hung = 124, True
                    finally:
                        _child["proc"] = None
                finally:
                    (root / pkey).write_bytes(originals[pkey])  # each plant runs alone
                results.append({"n": n, "file": rel, "exit": code,
                                "killed": code != 0 and not hung})
        except OSError as exc:
            return fail(f"{args.id}: record-plants could not run a plant: {exc}")
        finally:
            for _name, _handler in _old.items():
                try:
                    _sig.signal(getattr(_sig, _name), _handler)
                except (OSError, ValueError, RuntimeError):
                    pass
            for k, v in originals.items():
                try:
                    if (root / k).read_bytes() != v:
                        (root / k).write_bytes(v)
                except OSError:
                    pass
            try:
                marker.unlink(missing_ok=True)
            except OSError:
                pass
        # The runs can take minutes: commit from fresh data, as record-fail does.
        try:
            data = json.loads(ledger_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return fail(f"cannot read ledger: {exc}")
        if not sums_match(ledger_file, sums_file, log_path):
            return fail(SUMS_MISMATCH)
        return commit(args.root, data, "plant-run", args.id,
                      {"ref": ref, "check_sha256": check_sha,
                       "plants_sha256": hashlib.sha256(
                           (root / "plants" / f"{args.id}.json").read_bytes()).hexdigest()
                       if (root / "plants" / f"{args.id}.json").is_file() else "",
                       "head": head, "results": results})
    if args.cmd == "lock-checks":
        import re as _re
        import subprocess as _sp
        sha = args.commit.strip() if isinstance(args.commit, str) else ""
        if not _re.fullmatch(r"[0-9a-fA-F]{4,64}", sha):
            return fail("lock-checks needs --commit with a hex commit id")
        try:
            rev = _sp.run(["git", "-C", str(args.root), "rev-parse", "--verify", "--quiet",
                           f"{sha}^{{commit}}"], capture_output=True, text=True, timeout=30)
        except Exception:
            return fail(f"lock-checks: unknown commit {sha}")
        full = rev.stdout.strip()
        if rev.returncode != 0 or not full:
            return fail(f"lock-checks: unknown commit {sha}")

        def locked_sha(key):
            try:
                # ./ reads the path from --root, not the repo top; --filters gives the
                # working-tree form (eol, smudge), which is what phase-gate.py hashes.
                child = _sp.run(["git", "-C", str(args.root), "cat-file", "--filters",
                                 f"{full}:./{key}"], capture_output=True, timeout=30)
            except Exception:
                raise ValueError(f"lock-checks: cannot read {key} at commit {full}") from None
            if child.returncode != 0:
                raise ValueError(f"lock-checks: missing file {key} at commit {full}")
            return hashlib.sha256(child.stdout).hexdigest()

        cur_raw = data.get("current_phase")
        cur_p = parse_phase_like(cur_raw) if isinstance(cur_raw, str) and cur_raw.strip() else None
        files = {}
        for row in data.get("items", []):
            if not isinstance(row, dict) or row.get("status") not in ("open", "done", "verified"):
                continue
            rp_raw = str(row.get("phase", ""))
            row_p = parse_phase_like(rp_raw) if rp_raw.strip() else None
            if rp_raw.strip() and cur_p is not None and row_p is not None and row_p > cur_p:
                continue
            ref = row.get("test_ref", "")
            if not isinstance(ref, str) or not ref.strip():
                continue
            path_part = ref.split("::", 1)[0].strip()
            if not path_part:
                continue
            try:
                key = check_key(args.root, path_part)
            except ValueError as exc:
                return fail(f"{row.get('id')}: {exc} ({ref})")
            try:
                files[key] = locked_sha(key)
            except ValueError as exc:
                return fail(str(exc))
        old = data.get("check_locks")
        # Helper files the checks import: every file under each --also path at the commit.
        # Without --also the stored list is reused; a file added later waits for the next lock.
        also = args.also if args.also is not None else (old or {}).get("also", [])
        for path in also:
            # An empty --also becomes ./ and locks the whole tree; refuse it and
            # anything else that resolves to the project root.
            root_r = Path(args.root).resolve()
            try:
                target = (root_r / path).resolve() if path else root_r
                is_root = target == root_r
            except OSError:
                is_root = False
            if not path.strip() or is_root:
                return fail("lock-checks: --also needs a path below the project root")
            try:
                child = _sp.run(["git", "-C", str(args.root), "ls-tree", "-r", "-z",
                                 "--name-only", full, "--", f"./{path}"],
                                capture_output=True, text=True, timeout=30)
                names = [n for n in child.stdout.split("\0") if n] if child.returncode == 0 else []
            except Exception:
                names = []
            if not names:
                return fail(f"lock-checks: --also {path} not found at commit {full}")
            for name in names:
                try:
                    key = check_key(args.root, name)
                except ValueError as exc:
                    return fail(f"lock-checks: {exc} ({name})")
                try:
                    files[key] = locked_sha(key)
                except ValueError as exc:
                    return fail(str(exc))
        new = {"commit": full, "files": files}
        if also:
            new["also"] = list(also)
        before = (old or {}).get("files", {})
        for key, digest in files.items():  # what the user approves by this lock
            if before.get(key) != digest:
                print(f"lock-checks: {'changed' if key in before else 'new'} {key}")
        for key in before:  # a row dropped or moved, or --also replaced
            if key not in files:
                print(f"lock-checks: removed {key}")
        data["check_locks"] = new
        changes = {"check_locks": [old, new]} if old != new else {}
        old_grants = data.get("check_edit_grants", {})
        if old_grants:
            changes["check_edit_grants"] = [old_grants, {}]
        data["check_edit_grants"] = {}
        return commit(args.root, data, "lock-checks", "", {"commit": full, "changes": changes})
    if args.cmd == "dispute-check":
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        if row.get("status") != "open":
            return fail(f"{args.id}: dispute-check needs status open "
                        f"(found {row.get('status')})")
        for field, flag in ((args.check_lines, "--check-lines"),
                            (args.code_path, "--code-path"),
                            (args.proposed, "--proposed"),
                            (args.reason, "--reason")):
            if not isinstance(field, str) or not field.strip():
                return fail(f"{args.id}: dispute-check needs {flag} with text")
        code_raw = args.code_path.strip()
        code_file, _, _line = code_raw.rpartition(":")
        if not code_file.strip() or not _line.strip():
            return fail(f"{args.id}: dispute-check --code-path must be FILE:LINE")
        proposed_raw = args.proposed.strip()
        try:
            root_r = Path(args.root).resolve()
        except OSError:
            return fail(f"{args.id}: dispute-check could not resolve the project root")
        for rel, kind in ((code_file.strip(), "code"), (proposed_raw, "proposed")):
            if Path(rel).anchor:
                return fail(f"{args.id}: dispute-check {kind} path must be relative")
            try:
                target = (root_r / rel).resolve()
                target.relative_to(root_r)
            except (OSError, RuntimeError, ValueError):
                return fail(f"{args.id}: dispute-check {kind} file not found ({rel})")
            if not target.is_file():
                return fail(f"{args.id}: dispute-check {kind} file not found ({rel})")
        row["status"] = "disputed"
        return commit(args.root, data, "dispute-check", args.id,
                      {"check_lines": args.check_lines, "code_path": code_raw,
                       "proposed": proposed_raw, "reason": args.reason,
                       "changes": {"status": ["open", "disputed"]}})
    if args.cmd == "guard-paths":
        add = args.add.strip() if isinstance(args.add, str) else ""
        remove = args.remove.strip() if isinstance(args.remove, str) else ""
        if bool(add) == bool(remove):
            return fail("guard-paths needs exactly one of --add PATH or --remove PATH")
        rel = add or remove
        if Path(rel).anchor:
            return fail(f"guard-paths: path must be relative ({rel})")
        guard = data.get("check_guard")
        if guard is None:
            guard = []
        if not isinstance(guard, list):
            return fail("LEDGER: check_guard must be a list or null")
        old = list(guard)
        norm = rel.strip()
        while norm.startswith("./"):
            norm = norm[2:].strip()
        norm = Path(norm).as_posix() if norm else ""
        if not norm or norm == ".." or norm.startswith("../"):
            return fail(f"guard-paths: path must be inside the project ({rel})")
        if add:
            if norm not in guard:
                guard.append(norm)
        else:
            if norm not in guard:
                return fail(f"guard-paths: not guarded ({norm})")
            guard = [p for p in guard if p != norm]
        data["check_guard"] = guard
        return commit(args.root, data, "guard-paths", "",
                      {"changes": {"check_guard": [old, guard]}})
    if args.cmd == "grant-check-edit":
        rel = args.file.strip() if isinstance(args.file, str) else ""
        if not rel:
            return fail("grant-check-edit needs --file with a path")
        if Path(rel).anchor:
            return fail(f"grant-check-edit: path must be relative ({rel})")
        if not isinstance(args.reason, str) or not args.reason.strip():
            return fail("grant-check-edit needs --reason with text")
        grants = data.get("check_edit_grants")
        if grants is None:
            grants = {}
        if not isinstance(grants, dict):
            return fail("LEDGER: check_edit_grants must be an object or null")
        norm = rel.strip()
        while norm.startswith("./"):
            norm = norm[2:].strip()
        norm = Path(norm).as_posix() if norm else ""
        if not norm or norm == ".." or norm.startswith("../"):
            return fail(f"grant-check-edit: path must be inside the project ({rel})")
        old = dict(grants)
        base_v = int(data.get("ledger_version", 0))
        grants[norm] = {"reason": args.reason, "granted_at": base_v + 1}
        data["check_edit_grants"] = grants
        return commit(args.root, data, "grant-check-edit", "",
                      {"file": norm, "changes": {"check_edit_grants": [old, grants]}})
    if args.cmd == "enable-trace":
        if args.kind not in ("code", "document"):
            return fail("enable-trace needs --kind code or document")
        cur = data.get("trace")
        if isinstance(cur, dict) and cur.get("kind") in ("code", "document"):
            return fail(f"enable-trace: trace is already enabled (kind {cur.get('kind')})")
        if cur is not None:
            return fail("enable-trace: trace is already enabled (kind unknown)")
        base_v = int(data.get("ledger_version", 0))
        new_trace = {"kind": args.kind, "since": base_v + 1}
        data["trace"] = new_trace
        return commit(args.root, data, "enable-trace", "",
                      {"changes": {"trace": [None, new_trace]}})
    if args.cmd == "resume-gate":
        # Owner-only (kept off the agent allowlist, like approve/drop): ends a
        # gate hand-off so a new round series can start (ruling R13).
        if not isinstance(args.reason, str) or not args.reason.strip():
            return fail("resume-gate needs --reason")
        if not isinstance(args.quote, str) or not args.quote.strip():
            return fail("resume-gate needs --quote with the user's quoted text")
        return commit(args.root, data, "resume-gate", "",
                      {"reason": args.reason, "quote": args.quote})
    if args.cmd == "baseline-checks":
        # User-only (kept off the agent allowlist). Rows completed at or before this
        # version need a resolving check but no failure proof in phase-gate.py.
        top = max((op["v"] for op in ops if isinstance(op, dict)
                   and isinstance(op.get("v"), int) and not isinstance(op["v"], bool)), default=0)
        old = data.get("check_baseline")
        data["check_baseline"] = top
        changes = {"check_baseline": [old, top]} if old != top else {}
        return commit(args.root, data, "baseline-checks", "", {"changes": changes})
    if args.cmd == "import-brainstorm":
        if data.get("frozen_at") is not None:
            return fail("import-brainstorm: ledger is already frozen")
        parser_file = Path(__file__).with_name("brainstorm_import.py")
        if not parser_file.is_file():
            return fail("import-brainstorm: brainstorm_import.py not found beside ledger-amend.py")
        import importlib.util  # loaded here only: no other subcommand needs the parser

        spec = importlib.util.spec_from_file_location("brainstorm_import", parser_file)
        brainstorm_import = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brainstorm_import)
        try:  # spec_ref is a file pointer (s14_link_recovery.py): root-relative, POSIX
            source = Path(args.file).resolve().relative_to(
                Path(args.root).resolve()).as_posix()
        except ValueError:
            return fail(f"import-brainstorm: --file {args.file} is outside --root {args.root}")
        try:
            text = Path(args.file).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            return fail(f"import-brainstorm: cannot read file {args.file}: {exc}")
        rows, skipped, error = brainstorm_import.plan_import(text, source, ops, data["items"])
        if error is not None:
            return fail(error)
        entries = []
        for rid, rtext, spec_ref in rows:
            row = blank_row(rid, rtext, spec_ref)
            data["items"].append(row)
            entries.append(("add", rid, {"row": row}))
        rc = commit(args.root, data, *entries[0], more=entries[1:])
        if rc != 0:
            return rc
        for rid, rtext, spec_ref in rows:
            print(f"{rid}: {rtext} [{spec_ref}]")
        sys.stdout.flush()  # the review list first, then what the import left out
        for line in skipped:
            print(f"skipped {line}", file=sys.stderr)
        return 0
    if args.cmd == "add-finding":
        if not ID_RE.match(args.id):
            return fail(f"{args.id}: malformed id")
        if ever_added(ops, data["items"], args.id):
            return fail(f"{args.id}: id was already added")
        if not isinstance(args.text, str) or not args.text.strip():
            return fail(f"{args.id}: add-finding needs --text")
        if not isinstance(args.source, str) or not args.source.strip():
            return fail(f"{args.id}: add-finding needs --source")
        if not isinstance(args.key, str) or not args.key.strip():
            return fail(f"{args.id}: add-finding needs --key")
        row = blank_row(args.id, args.text, "")
        row["kind"] = "finding"
        row["finding"] = {"source": args.source, "key": args.key,
                          "severity": args.severity}
        data["items"].append(row)
        return commit(args.root, data, "add-finding", args.id, {"row": row})
    if args.cmd == "record-run":
        import hashlib as _hl
        import os as _os
        import signal as _sig
        import subprocess as _sp
        from pathlib import Path as _Path
        row = find_row(data, args.id)
        if row is None:
            return fail(f"{args.id}: unknown id")
        cmd = args.run_cmd if isinstance(args.run_cmd, str) else ""
        if not cmd.strip():
            return fail(f"{args.id}: record-run needs --cmd")
        try:
            timeout = int(args.timeout)
        except (TypeError, ValueError):
            return fail(f"{args.id}: record-run needs --timeout as seconds")
        if timeout <= 0:
            return fail(f"{args.id}: record-run needs --timeout as seconds")
        try:
            root = _Path(args.root).resolve()
            cwd = (_Path(args.cwd) if args.cwd else root).resolve()
        except OSError:
            return fail(f"{args.id}: record-run could not resolve the run directory")
        ref = row.get("test_ref", "")
        ref = ref if isinstance(ref, str) else ""
        try:
            child = _sp.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=str(cwd),
                              stdout=_sp.PIPE, stderr=_sp.STDOUT,
                              start_new_session=True)
        except OSError:
            return fail("check_cmd could not run: bash not found")
        timed_out = False
        try:
            blob, _ = child.communicate(timeout=timeout)
        except _sp.TimeoutExpired:
            try:
                if hasattr(_os, "killpg"):
                    _os.killpg(child.pid, _sig.SIGKILL)
                else:
                    child.kill()
            except OSError:
                pass
            try:
                blob, _ = child.communicate(timeout=5)
            except _sp.TimeoutExpired:
                blob = b""
            timed_out = True
        if blob is None:
            blob = b""
        code = child.returncode
        text = blob.decode("utf-8", errors="replace")
        lines = [line for line in text.splitlines() if line.strip()]
        tail = lines[-20:]
        if timed_out:
            code = 124
        try:
            head_c = _sp.run(["git", "-C", str(cwd), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
            head = head_c.stdout.strip() if head_c.returncode == 0 else ""
        except Exception:
            head = ""
        try:
            st_c = _sp.run(["git", "-C", str(cwd), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=30)
            if st_c.returncode != 0:
                tree_clean = False
            else:
                # L5: record-run's own ledger write must not dirty the tree.
                # Ignore root-level BAK record paths only (the BAK_DIRS set
                # in trace-check.py); src/debug/ still counts as dirty, and
                # a rename counts by both of its paths.
                # M3: the status paths are relative to the repository root,
                # so prefix them with rev-parse --show-prefix when the BAK
                # project sits in a subdirectory of its repository.
                try:
                    pfx_c = _sp.run(["git", "-C", str(cwd), "rev-parse",
                                     "--show-prefix"],
                                    capture_output=True, text=True, timeout=30)
                    prefix = pfx_c.stdout.strip() if pfx_c.returncode == 0 else ""
                except Exception:
                    prefix = ""
                bak_prefixes = tuple(prefix + b for b in
                                     ("ledger/", "trace/", "debug/",
                                      "verifier/", ".bak/"))
                dirty = False
                for line in st_c.stdout.splitlines():
                    if not line.strip():
                        continue
                    path = line[3:] if len(line) > 3 else ""
                    parts = path.split(" -> ") if " -> " in path else (path,)
                    for part in parts:
                        part = part.strip().strip('"')
                        if not part.startswith(bak_prefixes):
                            dirty = True
                            break
                    if dirty:
                        break
                tree_clean = not dirty
        except Exception:
            tree_clean = False
        try:
            data = json.loads(ledger_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return fail(f"cannot read ledger: {exc}")
        if not sums_match(ledger_file, sums_file, log_path):
            return fail(SUMS_MISMATCH)
        if find_row(data, args.id) is None:
            return fail(f"{args.id}: unknown id")
        extra = {"ref": ref, "cmd": cmd, "exit": code,
                 "output_sha256": _hl.sha256(blob).hexdigest(),
                 "output": "\n".join(tail), "head": head,
                 "tree_clean": tree_clean}
        if timed_out:
            extra["timed_out"] = True
        rc = commit(args.root, data, "check-run", args.id, extra)
        if timed_out:
            print(f"{args.id}: check command timed out after {timeout}s",
                  file=sys.stderr)
            return 1
        return rc
    if args.cmd == "import-runs":
        # PB-R5: append the check-run ops a prove-on-merge.py --in-place run
        # recorded in its ledger copy, then delete the copy. PB-R6: the copy is
        # always <root>/.bak/prove-ledger, so one built elsewhere cannot be named.
        copy = Path(args.root) / ".bak" / "prove-ledger"
        staging = Path(args.root) / ".bak" / "prove-ledger.importing"
        if not copy.exists():
            if staging.exists():
                return import_staging(args.root, data, staging)
            return 0
        c_ledger, c_sums, c_log = ledger_paths(copy)
        if not sums_match(c_ledger, c_sums, c_log):
            return fail("import-runs: the copy does not match its checksums.sha256")
        try:
            mine = log_path.read_bytes() if log_path.is_file() else b""
            theirs = c_log.read_bytes()
        except OSError as exc:
            return fail(f"import-runs: cannot read the logs: {exc}")
        if not theirs.startswith(mine):
            return fail("import-runs: the copy's log does not begin with the ledger's log")
        try:
            extra_ops = [json.loads(line) for line in
                         theirs[len(mine):].decode("utf-8").splitlines() if line.strip()]
        except ValueError as exc:
            return fail(f"import-runs: the copy's log is unparsable: {exc}")
        entries = []
        for op in extra_ops:
            name = op.get("op") if isinstance(op, dict) else None
            if name != "check-run":
                return fail(f"import-runs: {name} ops cannot be imported")
            rid = str(op.get("id", ""))
            if find_row(data, rid) is None:
                return fail(f"{rid}: unknown id")
            fields = {k: op[k] for k in ("ref", "cmd", "exit", "output_sha256",
                                         "output", "head", "tree_clean")
                      if k in op}
            if "timed_out" in op:
                fields["timed_out"] = op["timed_out"]
            entries.append(("check-run", rid, fields))
        try:
            if staging.exists():
                _rmtree(staging)
        except OSError as exc:
            return fail(f"import-runs: cannot stage the copy: {exc}")
        try:
            os.replace(copy, staging)
        except OSError as exc:
            return fail(f"import-runs: cannot stage the copy: {exc}")
        if entries:
            rc = commit(args.root, data, *entries[0], more=entries[1:])
            if rc:
                return rc
        try:
            _rmtree(staging)
        except OSError:
            return fail("import-runs: the runs were imported but the staged copy "
                        "could not be deleted; the owner deletes it "
                        "(for example `rm -rf .bak/prove-ledger.importing`) "
                        "and re-runs import-runs")
        return 0
    if args.cmd == "set-budgets":
        given = {"repeat_block": args.repeat_block, "same_rounds": args.same_rounds,
                 "no_progress_min": args.no_progress_min, "hang_min": args.hang_min,
                 "owner_wait_h": args.owner_wait_h}
        picked = {k: v for k, v in given.items() if v is not None}
        if not picked:
            return fail("set-budgets needs at least one flag")
        if any(not isinstance(v, int) or v <= 0 for v in picked.values()):
            return fail("set-budgets takes positive integers")
        cur = data.get("stall_budgets")
        if not isinstance(cur, dict):
            cur = {"repeat_block": 3, "same_rounds": 2, "no_progress_min": 60,
                   "hang_min": 10, "owner_wait_h": 24}
        old = dict(cur)
        cur.update(picked)
        data["stall_budgets"] = cur
        return commit(args.root, data, "set-budgets", "",
                      {"changes": {"stall_budgets": [old, dict(cur)]}})
    if args.cmd == "freeze":
        if data.get("frozen_at") is not None:
            return fail("ledger is already frozen")
        old = data.get("frozen_at")
        data["frozen_at"] = today()
        extra = {"changes": {"frozen_at": [old, data["frozen_at"]]}}
        words = Path(args.root) / "trace" / "s1-words.md"
        if words.is_file():  # R18: the freeze binds the owner's words
            try:
                extra["words_sha256"] = hashlib.sha256(words.read_bytes()).hexdigest()
            except OSError as exc:
                return fail(f"freeze: cannot read trace/s1-words.md: {exc}")
        elif isinstance(data.get("trace"), dict) and data["trace"].get("kind") \
                in ("code", "document"):  # R26: no words file leaves them unbound
            return fail("freeze: trace is on; save the owner's words to "
                        "trace/s1-words.md first (ruling R26)")
        return commit(args.root, data, "freeze", "", extra)
    if args.cmd == "record-handoff":
        if handoff_tripped(args.root):
            return fail("record-handoff: a tripped hand-off is waiting for "
                        "the user's acknowledge-handoff")
        record = current_handoff(args.root, ledger_file, sums_file, data)
        if isinstance(record, int):
            return record
        err = write_handoff(args.root, record)
        if isinstance(err, int):
            return err
        print(f"LEDGER: handoff recorded (ledger_version={record['ledger_version']})")
        _baklog(args.root, "1.1 ledger-amend", "record-handoff", "pass", f"LEDGER: handoff recorded (ledger_version={record['ledger_version']})")
        return 0
    if args.cmd == "acknowledge-handoff":
        try:
            handoff_state_path(args.root).unlink()
        except FileNotFoundError:
            print("LEDGER: no hand-off record")
            _baklog(args.root, "1.1 ledger-amend", "acknowledge-handoff", "pass", "LEDGER: no hand-off record")
            return 0
        except OSError as exc:
            return fail(f"cannot remove handoff state: {exc}")
        print(f"LEDGER: handoff acknowledged (ledger_version={data.get('ledger_version')})")
        _baklog(args.root, "1.1 ledger-amend", "acknowledge-handoff", "pass", f"LEDGER: handoff acknowledged (ledger_version={data.get('ledger_version')})")
        return 0
    return fail("unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
