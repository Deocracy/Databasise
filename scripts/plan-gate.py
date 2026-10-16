#!/usr/bin/env python3
"""Plan-to-list gate and scope-lock check: fail a phase plan that drops a due
ledger ID, and fail a changed locked scope. Fail closed: a ledger, plans
directory or plan the check cannot read is a violation, never a pass."""
import argparse
import hashlib
import json
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


ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")
TASK_RE = re.compile(r"Task\s+(\d+)", re.IGNORECASE)
EDIT_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+)?\*{0,2}(Create|Modify|Test)\b[^:\n]*:\*{0,2}\s*(.+)$")
MERGE_ORDER_RE = re.compile(r"Merge order:\s*(.+)", re.IGNORECASE)
WAVE_TOKEN_RE = re.compile(r"wave-[A-Za-z0-9-]+", re.IGNORECASE)
BARE_LETTER_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Za-z])(?![A-Za-z0-9-])")
WAVE_FILE_RE = re.compile(r"(wave-[A-Za-z0-9-]+)-PLAN\.md$", re.IGNORECASE)


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


def load_ledger(root):
    ledger = Path(root) / "ledger" / "REQUIREMENTS.json"
    if not ledger.is_file():
        return None, "LEDGER: REQUIREMENTS.json missing"
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        return None, "LEDGER: REQUIREMENTS.json unparsable"
    if not isinstance(data.get("items"), list):
        return None, "LEDGER: items is not a list"
    return data, None


def effective_phase(args, data):
    raw = args.phase
    if raw is None or not str(raw).strip():
        cur = data.get("current_phase")
        raw = cur if isinstance(cur, str) and cur.strip() else None
    text = str(raw).strip() if raw is not None else ""
    return text if text else "unset"


def due_ids(data, phase_text):
    """Due set: open rows due under P5-1(a), every deferred-requested row, and
    deferred-approved rows whose target phase is at or below the planned phase
    (ruling I2: the deferral ends there, so the plan must cite the ID)."""
    cur_p = parse_phase(phase_text) if phase_text != "unset" else None
    due = []
    for row in data.get("items", []):
        if not isinstance(row, dict):
            continue
        status = row.get("status")
        rid = str(row.get("id", "?"))
        if status == "deferred-requested":
            due.append((rid, "deferred"))
        elif status == "open":
            rp = str(row.get("phase", ""))
            if rp.strip().lower() == "backlog":
                pass
            else:
                row_p = parse_phase(rp) if rp.strip() else None
                if not rp.strip() or cur_p is None or row_p is None or row_p <= cur_p:
                    due.append((rid, "open"))
        elif status == "deferred-approved":
            rp = str(row.get("phase", ""))
            if rp.strip().lower() == "backlog":
                pass
            else:
                row_p = parse_phase(rp)
                if cur_p is not None and row_p is not None and row_p <= cur_p:
                    due.append((rid, "open"))
    return due


def cited_ids(plans_dir):
    cited = set()
    for plan in sorted(plans_dir.glob("*-PLAN.md")):
        try:
            text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return None, f"PLAN: {plan.name} unreadable: {getattr(exc, 'strerror', None) or exc}"
        cited.update(ID_RE.findall(text))
    return cited, None


def run_coverage(args, data):
    plans_dir = Path(args.plans)
    if not plans_dir.is_dir():
        return [f"PLAN: plans directory missing: {args.plans}"]
    if not sorted(plans_dir.glob("*-PLAN.md")):
        return [f"PLAN: no plans found in {args.plans}"]
    cited, err = cited_ids(plans_dir)
    if err is not None:
        return [err]
    phase_text = effective_phase(args, data)
    out = []
    for rid, kind in due_ids(data, phase_text):
        if rid in cited and kind == "open":
            continue
        if kind == "deferred":
            out.append(f"{rid}: deferred-requested without user approval")
        else:
            out.append(f"{rid}: due but not cited in any plan (phase {phase_text})")
    if not out:
        total = len(due_ids(data, phase_text))
        out.append(f"plan gate passed: {total}/{total} IDs cited (phase {phase_text})")
    return out


def norm_plan_path(value):
    text = str(value or "").strip().strip("`'\"(),;:")
    text = text.strip()
    if not text or text.startswith("#"):
        return ""
    while text.startswith("./"):
        text = text[2:].strip()
    text = text.strip().rstrip(".,;:!?)")
    if not text or text == ".." or text.startswith("-") or " " in text:
        return ""
    if text.startswith("../") or Path(text).anchor:
        return ""
    return Path(text).as_posix()


def extract_plan_paths(text):
    found = []
    for span in re.findall(r"`([^`]+)`", text):
        norm = norm_plan_path(span)
        if norm and ("/" in norm or "." in norm):
            found.append(norm)
    bare = re.sub(r"`[^`]*`", " ", text)
    for tok in re.split(r"[\s,]+", bare):
        norm = norm_plan_path(tok)
        if norm and "/" in norm:
            found.append(norm)
    return found


def strip_dot_slash(value):
    text = str(value or "").strip()
    while text.startswith("./"):
        text = text[2:].strip()
    return text


def plan_protected_sets(data):
    files = set()
    folders = set()
    for row in data.get("items", []):
        if not isinstance(row, dict):
            continue
        ref = row.get("test_ref", "")
        if not isinstance(ref, str) or not ref.strip():
            continue
        part = strip_dot_slash(ref.split("::", 1)[0]) or ref.strip()
        if part:
            files.add(Path(part).as_posix())
    locks = data.get("check_locks")
    if isinstance(locks, dict) and isinstance(locks.get("files"), dict):
        for key in locks["files"]:
            if isinstance(key, str) and key.strip():
                files.add(Path(key.strip()).as_posix())
    guard = data.get("check_guard") or []
    if isinstance(guard, list):
        for entry in guard:
            if isinstance(entry, str) and entry.strip():
                norm = Path(strip_dot_slash(entry) or entry.strip()).as_posix()
                files.add(norm)
                folders.add(norm)
    grants = set()
    raw_grants = data.get("check_edit_grants") or {}
    if isinstance(raw_grants, dict):
        for key in raw_grants:
            if isinstance(key, str) and key.strip():
                grants.add(Path(strip_dot_slash(key) or key.strip()).as_posix())
    return files, folders, grants


def is_plan_protected(rel, files, folders):
    if rel in files:
        return rel
    for folder in folders:
        if rel == folder or rel.startswith(folder.rstrip("/") + "/"):
            return rel
    return None


def run_check_edits(args, data):
    plans_dir = Path(args.plans)
    if not plans_dir.is_dir():
        return [f"PLAN: plans directory missing: {args.plans}"], False
    plans = sorted(plans_dir.glob("*-PLAN.md"))
    if not plans:
        return [f"PLAN: no plans found in {args.plans}"], False
    files, folders, grants = plan_protected_sets(data)
    out = []
    for plan in plans:
        try:
            text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return [f"PLAN: {plan.name} unreadable: {getattr(exc, 'strerror', None) or exc}"], False
        current = None
        for line in text.splitlines():
            task = TASK_RE.search(line)
            if task and line.lstrip().startswith("#"):
                current = task.group(1)
                continue
            if task and current is None:
                current = task.group(1)
            edit = EDIT_LINE_RE.match(line)
            if edit is None or current is None:
                continue
            for path in extract_plan_paths(edit.group(2)):
                hit = is_plan_protected(path, files, folders)
                if hit is None:
                    continue
                if path in grants or hit in grants:
                    continue
                out.append(f"{plan.name}: Task {current} edits {path} (no owner grant)")
    if out:
        return out, False
    return ["check-edits passed"], True


def stall_deadlock(root, target, text):
    """PS-R6: one C12.5 deadlock line in debug/stalls.jsonl per
    merge-order-versus-Needs refusal. Never raises."""
    try:
        import os
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from stall_time import iso_now
        entry = {"ts": iso_now(), "key": f"deadlock:4.1 plan-gate:{target}",
                 "class": "deadlock", "part": "4.1 plan-gate", "target": target,
                 "count": 1, "budget": 0, "action": "alarm", "verdict": None,
                 "route": None, "evidence": [text], "session": "",
                 "harness": os.environ.get("BAK_HARNESS", "cli")}
        path = Path(root) / "debug" / "stalls.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def norm_wave(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if text.startswith("wave-"):
        return text
    if len(text) == 1 and text.isalpha():
        return "wave-" + text
    return text


def run_check_order(args, data):
    _ = data
    plans_dir = Path(args.plans)
    if not plans_dir.is_dir():
        return [f"PLAN: plans directory missing: {args.plans}"], False
    plans = sorted(plans_dir.glob("*-PLAN.md"))
    if not plans:
        return [f"PLAN: no plans found in {args.plans}"], False
    order = None
    for plan in plans:
        try:
            text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return [f"PLAN: {plan.name} unreadable: {getattr(exc, 'strerror', None) or exc}"], False
        for line in text.splitlines():
            found = MERGE_ORDER_RE.search(line)
            if found and order is None:
                entries = [norm_wave(p) for p in found.group(1).split(",")]
                entries = [p for p in entries if p and p != "wave-"]
                if entries:
                    order = entries
    needs = []
    for plan in plans:
        wave = None
        match = WAVE_FILE_RE.search(plan.name)
        if match:
            wave = match.group(1).lower()
        try:
            text = plan.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return [f"PLAN: {plan.name} unreadable: {getattr(exc, 'strerror', None) or exc}"], False
        current = None
        seen = set()
        for line in text.splitlines():
            task = TASK_RE.search(line)
            if task and line.lstrip().startswith("#"):
                current = task.group(1)
            if current is None:
                continue
            if "needs:" not in line.lower():
                continue
            rest = line.split(":", 1)[1] if ":" in line else line
            targets = [norm_wave(t) for t in WAVE_TOKEN_RE.findall(rest)]
            for bare in BARE_LETTER_RE.findall(rest):
                wave_form = norm_wave(bare)
                if wave_form not in targets:
                    targets.append(wave_form)
            for target in targets:
                key = (wave or "wave-?", current, target)
                if key not in seen:
                    seen.add(key)
                    needs.append(key)
    if order is None:
        if needs:
            return ['merge order: no "Merge order:" line'], False
        return ["check-order passed"], True
    pos = {wave: i for i, wave in enumerate(order)}
    out = []
    for source, num, target in needs:
        if source not in pos or target not in pos:
            continue
        if pos[source] < pos[target]:
            out.append(f"merge order: {source} merges before {target}, "
                       f"but {source} Task {num} needs {target}")
            stall_deadlock(args.root, f"{source} then {target}", out[-1])
    if out:
        return out, False
    return ["check-order passed"], True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plan-gate.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--phase", default=None)
    ap.add_argument("--plans", default=None)
    ap.add_argument("--check-scope", action="store_true")
    ap.add_argument("--assign-phases", action="store_true")
    ap.add_argument("--check-edits", action="store_true")
    ap.add_argument("--check-order", action="store_true")
    args = ap.parse_args(argv)
    if args.plans is None and not args.check_scope \
            and not args.check_edits and not args.check_order:
        print("plan-gate.py: need --plans PLANDIR and/or --check-scope")
        return 2
    if (args.check_edits or args.check_order) and args.plans is None:
        print("plan-gate.py: --check-edits and --check-order need --plans PLANDIR")
        return 2
    if args.phase is not None and args.phase.strip() and parse_phase(args.phase) is None:
        print(f"plan-gate.py: --phase needs a phase value (such as 3 or 2.1): {args.phase}")
        return 2
    data, err = load_ledger(args.root)
    if err is not None:
        print(err)
        _baklog(args.root, "4.1 plan-gate", "plan-gate", "fail", err)
        return 1
    if args.assign_phases:
        if args.plans is None or args.phase is None or not str(args.phase).strip():
            print("plan-gate.py: --assign-phases needs --plans PLANDIR and --phase P")
            return 2
        if parse_phase(args.phase) is None:
            print(f"plan-gate.py: --phase needs a phase value (such as 3 or 2.1): {args.phase}")
            return 2
        cited, err = cited_ids(Path(args.plans))
        if err is not None:
            print(err)
            _baklog(args.root, "4.1 plan-gate", "plan-gate --assign-phases", "fail", err)
            return 1
        printed = []
        for row in data.get("items", []):
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id", "?"))
            if rid in cited and not str(row.get("phase", "")).strip():
                line = f"python3 scripts/ledger-amend.py set --id {rid} --phase {str(args.phase).strip()}"
                print(line)
                printed.append(line)
        _baklog(args.root, "4.1 plan-gate", "plan-gate --assign-phases", "pass",
                "\n".join(printed) or "no rows needed a phase")
        return 0
    out = []
    failed = False
    if args.plans is not None and not args.check_edits and not args.check_order:
        lines = run_coverage(args, data)
        if len(lines) == 1 and (lines[0].startswith("plan gate passed")):
            print(lines[0])
        else:
            out.extend(lines)
            failed = True
    if args.check_edits:
        lines, ok = run_check_edits(args, data)
        if ok:
            print(lines[0])
        else:
            out.extend(lines)
            failed = True
    if args.check_order:
        lines, ok = run_check_order(args, data)
        if ok:
            print(lines[0])
        else:
            out.extend(lines)
            failed = True
    if args.check_scope:
        lines, ok = run_scope(args, data)
        if ok and len(lines) == 1 and lines[0].startswith("scope check passed"):
            print(lines[0])
        elif ok:
            print(lines[0])
        else:
            out.extend(lines)
            failed = True
    for line in out:
        print(line)
    _baklog(args.root, "4.1 plan-gate", "plan-gate", "fail" if failed else "pass", "\n".join(out) or "no violations")
    return 1 if failed else 0


def extract_scope_field(section, label):
    lab = re.escape(label)
    m = re.search(r"\*\*" + lab + r"(?::\*\*|\*\*\s*:?)\s*([^\n]+)",
                  section, re.IGNORECASE)
    if not m:
        return None
    first = m.group(1).strip()
    cont = []
    for raw in section[m.end():].split("\n")[1:]:
        if not raw.strip():
            break
        if re.match(r"\s*\*\*[A-Z][A-Za-z ]*:?(\*\*)?:?\s", raw):
            break
        if re.match(r"\s*#{1,4}\s", raw):
            break
        if re.match(r"\s*\|", raw):
            break
        cont.append(raw.strip())
    val = " ".join([first] + cont).strip()
    return val or None


def scope_prose_digest(text, phase):
    head = r"^#{2,4}\s*(?:\[[^\]]+\]\s*)?Phase\s+"
    blocks = re.findall(r"(?m)" + head + re.escape(phase) + r"(?![0-9.])[\s\S]*?"
                        r"(?=" + head + r"|\Z)", text, re.IGNORECASE)
    if not blocks:
        return None, "block"
    if len(blocks) > 1:
        return None, "ambiguous"
    section = blocks[0]
    goal = extract_scope_field(section, "Goal")
    if goal is None:
        return None, "Goal"
    reqs = extract_scope_field(section, "Requirements")
    if reqs is None:
        return None, "Requirements"
    norm = lambda t: " ".join(t.split())
    blob = f"{norm(goal)}\n{norm(reqs)}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), None


def run_scope(args, data):
    lock = data.get("scope_lock")
    if lock is None:
        return ["scope check skipped (no locked scope; S8-lean: gates on checkable items only)"], True
    if not isinstance(lock, dict) or not isinstance(lock.get("phase"), str) \
            or not all(isinstance(lock.get(k), str) and lock.get(k, "").strip()
                       for k in ("source", "sha256")):
        return ["LEDGER: scope_lock must be an object or null"], False
    phase, source = lock["phase"], lock["source"]
    target = Path(args.root) / source
    if phase and source == "ROADMAP.md" and not target.exists():
        target = Path(args.root) / ".planning" / "ROADMAP.md"  # GSD layout
    try:
        blob = target.read_bytes()
    except OSError:
        return [f"scope file missing: {source} (locked phase {phase})"], False
    if not phase:
        if hashlib.sha256(blob).hexdigest() != lock["sha256"]:
            return [f"scope changed since lock: {source} (locked phase {phase})"], False
        return [f"scope check passed (phase {phase})"], True
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError:
        return [f"scope file missing: {source} (locked phase {phase})"], False
    digest, missing = scope_prose_digest(text, phase)
    if missing == "block":
        return [f"scope phase missing: phase {phase} in {source} (locked phase {phase})"], False
    if missing == "ambiguous":
        return [f"phase block ambiguous: phase {phase} in {source}"], False
    if missing in ("Goal", "Requirements"):
        return [f"scope field missing: {missing} (locked phase {phase})"], False
    if digest != lock["sha256"]:
        return [f"scope changed since lock: {source} (locked phase {phase})"], False
    return [f"scope check passed (phase {phase})"], True


if __name__ == "__main__":
    raise SystemExit(main())
