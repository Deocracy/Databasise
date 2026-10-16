#!/usr/bin/env python3
"""Q2 runner (contract C7): plant faults in a copy of a project and report
which ones the gates find. No model runs here.

python3 plant-gaps.py --fixture DIR --plan PLAN.json [--root-out DIR]

PLAN.json lists {"fault", "id", "step"} objects, one fault per ID; the faults
and the output lines are described in skills/plant-gaps/SKILL.md. A
remove-text fault may carry "scope": "section" (default "line"): section
scope blanks the whole Markdown section that holds the quote, from the
nearest heading above it to the next heading of the same or a higher
level: the section's lines become empty lines, so later rows keep their
`where` line numbers. Lines inside ``` or ~~~ fenced code blocks never
count as headings. Ruling R29:
trace-check.py --json first runs on the unplanted copy (the baseline), and a
fault is found only by a hard violation at its own (id, step) that the
baseline lacks. A fault that cannot be planted is reported and the run goes
on. Changed artifacts are re-hashed in every trace file, so each fault is
left to the quote and coverage rules, not to the stale-hash rule. When the
fixture is a git work tree, the copy is made with `git clone --local`
(history, commits and ancestry kept), then the fixture's uncommitted files
are copied on top, so the copy is its own repository; any other fixture is
copied as before. The clone drops `origin`, so a push from the copy cannot
land in the owner's build repository. The copy keeps symlinks as links and leaves out .git
(unless cloned), .venv and node_modules at every level.
A planting run with --root-out writes the run record to
<copy>/.bak/plant-run.json. When the copy is a git clone, plant-gaps then
commits the planted state there
(`git add -A`, then commit as plant-gaps) and records that commit as
`planted_commit` in .bak/plant-run.json, so a reviewer's `record-run` in
the copy records `tree_clean: true`. plant-gaps.py --evaluate DIR scores such a copy
after fresh checkers re-checked it, and --markdown FILE writes the report.
The record maps each trace/s*.json in the copy after planting to its sha256
and its checker.session; --evaluate scores a planted fault as not-rechecked
when every step file for its step still has the recorded sha256 and session
(no fresh checker rewrote it), which counts as not found.
Exits 0 when every fault is planted and found, 1 when a planted fault is not
found, 2 on usage errors, when trace is not enabled, or when a fault could
not be planted.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KINDS = ("remove-text", "drop-entry", "alter-quote", "drop-from-plan")
SCOPES = ("line", "section")
EXPECTED = {"remove-text": "missing", "drop-entry": "not-checked",
            "alter-quote": "quote-not-found", "drop-from-plan": "missing"}
RECORD = Path(".bak") / "plant-run.json"
HERE = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns(".git", ".venv", "node_modules")


def is_git_work_tree(path):
    """True when path is itself the top level of a git work tree."""
    try:
        proc = subprocess.run(["git", "-C", str(path), "rev-parse",
                               "--show-toplevel"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    return Path(proc.stdout.strip()).resolve() == Path(path).resolve()


def fixture_head(fixture):
    """HEAD sha of the fixture, or None when it has no commit yet."""
    try:
        proc = subprocess.run(["git", "-C", str(fixture), "rev-parse",
                               "HEAD"],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def sync_tree(source, dest):
    """Copy source's files on top of dest, removing dest entries the source
    lacks (outside .git): the copy then matches the fixture's uncommitted
    state, including deleted files."""
    import os
    for current, dirnames, filenames in os.walk(dest, topdown=True,
                                                followlinks=False):
        rel = Path(current).relative_to(dest)
        if ".git" in rel.parts or rel == Path(".git"):
            dirnames[:] = []
            continue
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in list(dirnames):
            if not (source / rel / name).exists() \
                    and not (source / rel / name).is_symlink():
                target = Path(current) / name
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
                dirnames.remove(name)
        for name in filenames:
            if not (source / rel / name).exists() \
                    and not (source / rel / name).is_symlink():
                target = Path(current) / name
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
    for child in sorted(source.iterdir()):
        if child.name in (".git", ".venv", "node_modules"):
            continue
        target = dest / child.name
        if child.is_symlink():
            if target.exists() or target.is_symlink():
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            target.symlink_to(child.readlink())
        elif child.is_dir():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            shutil.copytree(child, target, symlinks=True, ignore=IGNORE)
        else:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            shutil.copy2(child, target)


def checkout_copy(out, want):
    """Check the clone out at the fixture's branch or HEAD. A failure is
    the exit-2 message, like the clone path."""
    try:
        subprocess.run(["git", "-C", str(out), "checkout", "--quiet",
                        want], check=True, capture_output=True,
                       text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        detail = exc.stderr.strip() if isinstance(
            exc, subprocess.CalledProcessError) and exc.stderr else exc
        print(f"plant-gaps: git checkout failed: {detail}",
              file=sys.stderr)
        raise SystemExit(2)


def copy_fixture(fixture, out):
    """Copy the fixture to out: when the fixture is a git work tree, clone
    it with `git clone --local` (history, commits and ancestry kept), then
    copy the fixture's uncommitted files on top, so the copy is its own
    repository; otherwise copy the tree as today."""
    if is_git_work_tree(fixture):
        try:
            subprocess.run(["git", "clone", "--local", "--quiet", str(fixture),
                            str(out)], check=True, capture_output=True,
                           text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as exc:
            detail = exc.stderr.strip() if isinstance(
                exc, subprocess.CalledProcessError) and exc.stderr else exc
            print(f"plant-gaps: git clone --local failed: {detail}",
                  file=sys.stderr)
            raise SystemExit(2)
        subprocess.run(["git", "-C", str(out), "remote", "remove", "origin"],
                       check=True, capture_output=True, text=True,
                       timeout=60)
        for name in (".venv", "node_modules"):
            target = out / name
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
        head = fixture_head(fixture)
        branch = None
        try:
            proc = subprocess.run(["git", "-C", str(fixture), "rev-parse",
                                   "--abbrev-ref", "HEAD"],
                                  capture_output=True, text=True, timeout=60)
            branch = proc.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            branch = None
        if head is not None and branch not in (None, "HEAD"):
            checkout_copy(out, branch)
        elif head is not None:
            checkout_copy(out, head)
        sync_tree(fixture, out)
        return
    shutil.copytree(fixture, out, symlinks=True, ignore=IGNORE)


def in_fence(line, fenced):
    """(fenced, fence line): toggle when the line opens or closes a ```
    or ~~~ fenced code block. A closing fence must use the same marker
    that opened the block; indented code is not a fence."""
    match = re.match(r"^(```|~~~)", line)
    if match:
        fence = match.group(1)
        if fenced is None:
            return fence, True
        if line.startswith(fenced):
            return None, True
    return fenced, False


def section_span(lines, n):
    """(start, end) 0-based half-open bounds of the Markdown section holding
    line n (1-based): from the nearest heading at or above it to the next
    heading of the same or a higher level. With no heading, the whole file
    is the section. `#` lines inside ``` or ~~~ fenced code blocks never
    count as headings."""
    start, level = 1, None
    fenced = None
    for i in range(1, n + 1):
        fenced, fence_line = in_fence(lines[i - 1], fenced)
        if fence_line:
            continue
        match = re.match(r"^(#{1,6})\s", lines[i - 1])
        if fenced is None and match:
            start, level = i, len(match.group(1))
    if level is None:
        return 0, len(lines)
    end = len(lines) + 1
    fenced = None
    for i in range(1, n + 1):
        fenced, _ = in_fence(lines[i - 1], fenced)
    for i in range(n + 1, len(lines) + 1):
        fenced, fence_line = in_fence(lines[i - 1], fenced)
        if fence_line:
            continue
        match = re.match(r"^(#{1,6})\s", lines[i - 1])
        if match and fenced is None and len(match.group(1)) <= level:
            end = i
            break
    return start - 1, end - 1


def step_files(root, step):
    name = re.compile(rf"^s{step[1]}(?:-[a-z0-9][a-z0-9-]{{0,39}})?\.json$")
    return [p for p in sorted((root / "trace").glob("*.json")) if name.match(p.name)]


def write_json(path, doc):
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def plant(root, fault):
    """Apply one fault; return the artifact path it changed, or None."""
    rid, docs = fault["id"], [(p, json.loads(p.read_text(encoding="utf-8")))
                              for p in step_files(root, fault["step"])]
    if fault["fault"] == "drop-entry":
        hit = False
        for path, doc in docs:
            kept = [c for c in doc["items"] if c.get("id") != rid]
            if len(kept) < len(doc["items"]):
                doc["items"], hit = kept, True
                write_json(path, doc)
        if not hit:
            raise ValueError("no entry")
        return None
    cell, path, doc = next(((c, p, d) for p, d in docs for c in d["items"]
                            if c.get("id") == rid and c.get("status") == "present"),
                           (None, None, None))
    if cell is None:
        raise ValueError("no present entry")
    if fault["fault"] == "alter-quote":
        cell["quote"] += " (planted)"
        write_json(path, doc)
        return None
    rel, _, line = cell["where"].rpartition(":")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"{rel} is outside the project")
    lines = target.read_text(encoding="utf-8").split("\n")
    n = int(line)
    if not 1 <= n <= len(lines):
        raise ValueError(f"line {n} is outside {rel}")
    if fault["fault"] == "drop-from-plan":
        lines[n - 1] = ""
        target.write_text("\n".join(lines), encoding="utf-8")
        return rel
    text, quote = "\n".join(lines), cell["quote"]
    at = text.find(quote, len("\n".join(lines[:n - 1])))
    if at < 0:
        raise ValueError(f"quote not verbatim in {rel}")
    if fault.get("scope", "line") == "section":
        start, end = section_span(lines, n)
        for i in range(start, end):
            lines[i] = ""
        target.write_text("\n".join(lines), encoding="utf-8")
        return rel
    target.write_text(text[:at] + "\n" * quote.count("\n") + text[at + len(quote):],
                      encoding="utf-8")
    return rel


def rehash(root, changed):
    for path in sorted((root / "trace").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        arts = doc.get("artifacts") if isinstance(doc, dict) else None
        hits = sorted(changed & set(arts)) if isinstance(arts, dict) else []
        for rel in hits:
            arts[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        if hits:
            write_json(path, doc)


def file_sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def checker_session(path):
    """checker.session of a trace file, or None when it has none."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    checker = doc.get("checker") if isinstance(doc, dict) else None
    session = checker.get("session") if isinstance(checker, dict) else None
    return session if isinstance(session, str) else None


def step_snapshot(root, step):
    """{file name: (sha256, checker.session)} of the step's trace files."""
    return {p.name: (file_sha(p), checker_session(p))
            for p in step_files(root, step)}


def unchanged(root, fault, saved):
    """True when every step file for the fault's step still has the recorded
    sha256 and session: no fresh checker rewrote it."""
    current = step_snapshot(root, fault["step"])
    names = saved.get(fault["step"], {})
    if not names:
        return False
    for name, pair in names.items():
        want = (pair.get("sha256"), pair.get("session")) \
            if isinstance(pair, dict) else tuple(pair)
        if current.get(name) != want:
            return False
    return True


DOWNSTREAM_AFTER = {"S3": ("S4", "S5", "S6", "S7"),
                    "S4": ("S5", "S6", "S7"),
                    "S5": ("S6", "S7")}


def downstream_ids(planted, baseline):
    """{(id, step)} of hard violations that are correct later-step
    detections of a planted fault (I2): the planted id at a step after the
    planted step (S3 -> S4 to S7, S4 -> S5 to S7, S5 -> S6 and S7)."""
    ids = set()
    for fault in planted:
        for step in DOWNSTREAM_AFTER.get(fault["step"], ()):
            ids.add((fault["id"], step))
    base = {(b["id"], b["step"]) for b in baseline}
    return ids - base


def debugger_notes(root, ids):
    """{id: "<class> <gate>"} from debug-locate.py, or None when it is absent
    or any call fails."""
    script = HERE / "debug-locate.py"
    if not script.is_file():
        return None
    notes = {}
    for rid in ids:
        try:
            proc = subprocess.run([sys.executable, str(script), "--root", str(root),
                                   "--id", rid], capture_output=True, text=True,
                                  timeout=60)
            finding = json.loads(proc.stdout)
            notes[rid] = f"{finding['class']} {finding['gate']}"
        except Exception:
            return None
    return notes


def hard_violations(root):
    """(hard violations, the "trace" marker) of trace-check.py --json at root,
    or None after printing why there are none to read."""
    try:
        proc = subprocess.run([sys.executable, str(HERE / "trace-check.py"), "--root",
                               str(root), "--json"], capture_output=True, text=True,
                              timeout=120)
    except subprocess.TimeoutExpired:
        print("plant-gaps: trace-check.py timed out after 120 s")
        return None
    try:
        body = json.loads(proc.stdout)
        return [v for v in body["violations"]
                if v.get("class") not in ("extra", "info")], body.get("trace")
    except (ValueError, KeyError, TypeError, AttributeError):
        print("plant-gaps: trace-check.py --json gave no violations object")
        return None


def class_at(hard, fault):
    """Class of the first hard violation at the fault's (id, step), or None."""
    return next((v["class"] for v in hard if v.get("id") == fault["id"]
                 and v.get("step") == fault["step"]), None)


def score_run(baseline, planted, hard, rechecked=None):
    """(lines, results, found) scoring the planted faults against the hard
    violations after planting: a fault is found only by a hard violation at
    its own (id, step) that the baseline lacks. results holds one
    (fault, result, reported) tuple per planted fault, in plan order.
    rechecked maps each fault index to False when its step files are
    unchanged since planting (I1); such a fault scores not-rechecked and
    counts as not found, even when the violation is still there."""
    lines, results, found = [], [], 0
    for pos, fault in enumerate(planted):
        was = next((b["class"] for b in baseline if b["id"] == fault["id"]
                    and b["step"] == fault["step"]), None)
        now = class_at(hard, fault)
        if rechecked is not None and not rechecked.get(pos, True):
            lines.append(f"not-rechecked {fault['id']} at {fault['step']}")
            results.append((fault, "not-rechecked", now))
        elif was:
            lines.append(f"baseline {fault['id']} {was} at {fault['step']}")
            results.append((fault, "baseline", was))
        elif now:
            found += 1
            lines.append(f"found {fault['id']} {now} at {fault['step']}")
            results.append((fault, "found", now))
        else:
            lines.append(f"missed {fault['id']} at {fault['step']}")
            results.append((fault, "missed", None))
    return lines, results, found


def count_expected(results):
    """Faults scored found with the expected class for their kind (M5): the
    reported class equals EXPECTED for the fault's kind."""
    return sum(1 for fault, result, reported in results
               if result == "found" and EXPECTED[fault["fault"]] == reported)


def print_run(faults, planted, not_planted, lines, found, notes, results):
    for fault, reason in not_planted:
        print(f"not-planted {fault['id']} at {fault['step']} ({reason})")
    print(f"found {found}/{len(planted)} ({count_expected(results)} as expected)")
    for fault, line in zip(planted, lines):
        note = f" (debugger: {notes[fault['id']]})" if notes is not None else ""
        print(line + note)
    if notes is None:
        print("debugger: unavailable")
    return 1 if found < len(planted) else 2 if len(planted) < len(faults) else 0


def commit_planted_state(root, changed):
    """Commit the planted state in a cloned copy and return the commit sha:
    with the planted artifact faults committed, a reviewer's `record-run`
    in the copy records `tree_clean: true`. With no artifact change (a
    drop-entry or alter-quote plan), the trace-file rehash is committed
    instead: the rehash digest update is exactly what checkers would have
    produced, and it keeps the working tree clean for the reviewers.
    Raises OSError or SystemExit(2)."""
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                            capture_output=True, text=True, timeout=60)
    if status.returncode != 0:
        print(f"plant-gaps: git commit failed: {status.stderr.strip()}",
              file=sys.stderr)
        raise SystemExit(2)
    if not status.stdout.strip():
        proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            print("plant-gaps: git commit failed: "
                  f"{proc.stderr.strip()}", file=sys.stderr)
            raise SystemExit(2)
        return proc.stdout.strip()
    try:
        subprocess.run(["git", "-C", str(root), "add", "-A"],
                       check=True, capture_output=True, text=True,
                       timeout=120)
        subprocess.run(["git", "-C", str(root), "-c",
                        "user.name=plant-gaps", "-c",
                        "user.email=plant-gaps@localhost", "commit",
                        "--quiet", "-m", "plant-gaps: planted faults"],
                       check=True, capture_output=True, text=True,
                       timeout=120)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() if exc.stderr else exc
        print(f"plant-gaps: git commit failed: {detail}", file=sys.stderr)
        raise SystemExit(2)
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        print("plant-gaps: git commit failed: "
              f"{proc.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return proc.stdout.strip()


def write_record(root, faults, planted, not_planted, baseline,
                 planted_commit=None):
    bak = root / ".bak"
    bak.mkdir(parents=True, exist_ok=True)
    steps = sorted({f["step"] for f in planted})
    write_json(bak / "plant-run.json", {
        "faults": faults,
        "planted": planted,
        "not_planted": [{"fault": f["fault"], "id": f["id"], "step": f["step"],
                         "reason": reason} for f, reason in not_planted],
        "baseline": [{"id": b["id"], "step": b["step"], "class": b["class"]}
                     for b in baseline],
        "planted_commit": planted_commit,
        "step_files": {step: {name: {"sha256": sha, "session": session}
                              for name, (sha, session)
                              in step_snapshot(root, step).items()}
                       for step in steps},
    })


def write_markdown(path, planted, not_planted, results, found, hard,
                   baseline, notes):
    rows = []
    for fault, result, reported in results:
        note = notes.get(fault["id"]) if notes is not None else None
        rows.append((fault, result, reported or "-", note or "-"))
    for fault, _reason in not_planted:
        rows.append((fault, "not-planted", "-", "-"))
    lines = ["| fault | id | step | expected | result | reported | debugger |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for fault, result, reported, note in rows:
        lines.append(f"| {fault['fault']} | {fault['id']} | {fault['step']} | "
                     f"{EXPECTED[fault['fault']]} | {result} | {reported} | "
                     f"{note} |")
    lines.append("")
    lines.append("## Downstream of a plant")
    lines.append("")
    down = downstream_ids(planted, baseline)
    downs = [v for v in hard if (v.get("id"), v.get("step")) in down]
    if downs:
        lines.extend(f"- {v.get('id') or '-'} {v.get('class')} "
                     f"at {v.get('step')}: {v.get('detail')}" for v in downs)
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Violations with no plant")
    lines.append("")
    base = {(b["id"], b["step"]) for b in baseline}
    ids = {(f["id"], f["step"]) for f in planted}
    strays = [v for v in hard if (v.get("id"), v.get("step")) not in ids
              and (v.get("id"), v.get("step")) not in base
              and (v.get("id"), v.get("step")) not in down]
    if strays:
        lines.extend(f"- {v.get('id') or '-'} {v.get('class')} "
                     f"at {v.get('step')}: {v.get('detail')}" for v in strays)
    else:
        lines.append("None.")
    lines.append("")
    lines.append(f"found {found}/{len(planted)} ({count_expected(results)} as expected)")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_plan(root, faults, markdown=None, git_copy=False):
    base = hard_violations(root)
    if base is None:
        return 1
    baseline, trace = base
    if trace == "not enabled":
        print("trace: not enabled")
        return 2
    planted, not_planted, changed = [], [], set()
    for fault in faults:
        try:
            rel = plant(root, fault)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            not_planted.append((fault, str(exc)))
            continue
        planted.append(fault)
        if rel is not None:
            changed.add(rel)
    rehash(root, changed)
    after = hard_violations(root)
    if after is None:
        return 1
    hard = after[0]
    lines, results, found = score_run(baseline, planted, hard)
    notes = debugger_notes(root, [f["id"] for f in planted])
    planted_commit = commit_planted_state(root, changed) if git_copy else None
    write_record(root, faults, planted, not_planted, baseline,
                 planted_commit)
    if markdown is not None:
        write_markdown(markdown, planted, not_planted, results, found, hard,
                       baseline, notes)
    return print_run(faults, planted, not_planted, lines, found, notes, results)


def evaluate(root):
    """Score a copy planted with --root-out, without planting again: read
    the run record, run trace-check.py --json on the copy, and return
    (exit code, scoring). A planted fault whose step files still have the
    recorded sha256 and session scores not-rechecked (I1): it counts as not
    found, and the run exits 1. Raises ValueError when the record is
    missing or unreadable."""
    path = root / RECORD
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        faults, planted = record["faults"], record["planted"]
        not_planted = [({"fault": f["fault"], "id": f["id"], "step": f["step"]},
                         f["reason"]) for f in record["not_planted"]]
        baseline = [{"id": b["id"], "step": b["step"], "class": b["class"]}
                    for b in record["baseline"]]
        step_files = record.get("step_files", {})
        for fault, _reason in not_planted:
            fault["fault"], fault["id"], fault["step"]
        for fault in faults + planted:
            fault["fault"], fault["id"], fault["step"]
        for cell in baseline:
            cell["id"], cell["step"], cell["class"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ValueError(path)
    after = hard_violations(root)
    if after is None:
        return 1, None
    hard = after[0]
    rechecked = {pos: not unchanged(root, fault, step_files)
                 for pos, fault in enumerate(planted)}
    lines, results, found = score_run(baseline, planted, hard, rechecked)
    notes = debugger_notes(root, [f["id"] for f in planted])
    code = print_run(faults, planted, not_planted, lines, found, notes, results)
    scored = (planted, not_planted, results, found, hard, baseline, notes)
    return code, scored


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plant-gaps.py")
    ap.add_argument("--fixture", default=None)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--root-out", default=None)
    ap.add_argument("--evaluate", default=None)
    ap.add_argument("--markdown", default=None)
    args = ap.parse_args(argv)
    if args.evaluate is not None:
        if args.fixture is not None or args.plan is not None \
                or args.root_out is not None:
            ap.error("--evaluate cannot be combined with --fixture, "
                     "--plan or --root-out")
        target = Path(args.evaluate)
        try:
            code, scored = evaluate(target)
        except ValueError:
            print(f"plant-gaps: {target / RECORD} missing; "
                  "plant with --root-out first", file=sys.stderr)
            return 2
        if scored is not None and args.markdown is not None:
            planted, not_planted, results, found, hard, baseline, notes = \
                scored
            write_markdown(args.markdown, planted, not_planted, results,
                           found, hard, baseline, notes)
        return code
    if args.fixture is None or args.plan is None:
        ap.error("the following arguments are required: --fixture, --plan")
    fixture = Path(args.fixture)
    if not (fixture / "ledger" / "REQUIREMENTS.json").is_file():
        ap.error(f"--fixture {fixture} has no ledger/REQUIREMENTS.json")
    try:
        faults = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ap.error(f"--plan {args.plan} is not readable JSON")
    if not isinstance(faults, list) or not faults:
        ap.error('--plan must be a JSON list of {"fault", "id", "step"} objects')
    for f in faults:
        if not (isinstance(f, dict) and f.get("fault") in KINDS
                and isinstance(f.get("id"), str)
                and re.fullmatch(r"S[3-7]", str(f.get("step")))):
            ap.error('--plan must be a JSON list of {"fault", "id", "step"} objects')
        if f.get("scope", "line") not in SCOPES:
            ap.error(f"--plan fault {f.get('id')} has unknown scope {f.get('scope')!r}")
    ids = [f["id"] for f in faults]
    repeated = next((rid for rid in ids if ids.count(rid) > 1), None)
    if repeated is not None:
        print(f"plant-gaps: {repeated} appears in more than one fault", file=sys.stderr)
        return 2
    keep = args.root_out is not None
    git_copy = is_git_work_tree(fixture)
    if keep:
        out = Path(args.root_out)
        if out.exists():
            ap.error(f"--root-out {out} already exists")
        copy_fixture(fixture, out)
        return run_plan(out, faults, markdown=args.markdown, git_copy=git_copy)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "project"
        copy_fixture(fixture, out)
        return run_plan(out, faults, markdown=args.markdown)


if __name__ == "__main__":
    raise SystemExit(main())
