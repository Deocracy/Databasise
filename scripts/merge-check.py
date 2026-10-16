#!/usr/bin/env python3
"""G5 merge check (contract C7): write trace/s6.json from the merge sides.

The sides are the parents of --merge C, or --base B and --head H for a squash
merge. Each side's present S5 quote of a due, non-exempt done or verified row
(trace_s6's filter) must occur (normalized as in C2 V4) in the same path of
the merged tree, which is the working tree at --root. An ID is present when
any side's quote is found. The file's checker session is the full sha of HEAD
at --root (ruling R28): the merge commit, or for --base/--head the squashed
result; trace_s6 checks the file only while that commit is HEAD. The file is
written through a temporary file in trace/ and os.replace, and a symlinked
trace/ or trace/s6.json is refused (exit 2), so a committed link cannot
redirect the write.
Prints "<ID>: missing at S6" per lost item; exits 1 if any, 2 on usage errors.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

S5_RE = re.compile(r"^trace/s5(?:-[a-z0-9][a-z0-9-]{0,39})?\.json$")


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


def load_s6():
    """trace_s6.py beside this script: its due-row filter and its loader of
    trace-check.py are used as they are, never copied."""
    spec = importlib.util.spec_from_file_location(
        "trace_s6", Path(__file__).with_name("trace_s6.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args):
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return proc.stdout


def side_quotes(root, sha, core):
    """[(id, path, quote)] of the present items in the side's S5 files."""
    found = []
    for name in git(root, "ls-tree", "--name-only", sha, "trace/").splitlines():
        if not S5_RE.match(name):
            continue
        doc = json.loads(git(root, "show", f"{sha}:./{name}"))
        items = doc.get("items") if isinstance(doc, dict) else None
        for entry in items if isinstance(items, list) else []:
            if isinstance(entry, dict) and entry.get("status") == "present" \
                    and all(isinstance(entry.get(k), str) for k in ("id", "where", "quote")):
                rel, _ = core.where_split(entry["where"])
                if rel is not None:
                    found.append((entry["id"], rel, entry["quote"]))
    return found


def merged_lines(core, root_r, rel, artifacts):
    """Lines of rel in the merged tree, recording its sha256; None when rel is
    not a regular file inside the root or is a BAK record."""
    try:
        core.check_key(root_r, rel)
    except ValueError:
        return None
    path = root_r / rel
    if core.is_bak_record(rel) or not path.is_file():
        return None
    artifacts[rel] = core.file_sha(path)
    return core.read_lines(path)


def find_line(core, quote, lines):
    """First line the quote starts on, else the first line whose C2 V4 window
    holds it (a quote re-wrapped over more lines), else None."""
    want = core.normalize(quote)
    span = len(quote.split("\n"))
    for n in range(1, len(lines) + 1):
        if want and want in core.normalize("\n".join(lines[n - 1:n - 1 + span])):
            return n
    return next((n for n in range(1, len(lines) + 1)
                 if core.quote_ok(quote, n, lines)), None)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="merge-check.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--merge", default=None)
    ap.add_argument("--base", default=None)
    ap.add_argument("--head", default=None)
    args = ap.parse_args(argv)
    if args.merge is not None and (args.base or args.head) \
            or args.merge is None and not (args.base and args.head):
        ap.error("give --merge COMMIT, or both --base SHA and --head SHA")
    root = Path(args.root)
    for name in ("trace", "trace/s6.json"):
        if (root / name).is_symlink():
            print(f"merge-check: {name} must not be a symlink", file=sys.stderr)
            return 2
    s6 = load_s6()
    core = s6.load_core()
    try:
        data = json.loads((root / "ledger" / "REQUIREMENTS.json").read_text(encoding="utf-8"))
        version = data["ledger_version"]
        due = set(s6.due_ids(core, root.resolve(), data))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print("LEDGER: REQUIREMENTS.json missing or unreadable")
        _baklog(args.root, "3.11 merge-check", "merge-check", "fail",
                "LEDGER: REQUIREMENTS.json missing or unreadable")
        return 1
    try:
        if args.merge:
            sides = git(root, "rev-list", "--parents", "-n", "1", args.merge).split()[1:]
        else:
            sides = [git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
                     for ref in (args.base, args.head)]
        session = git(root, "rev-parse", "--verify", "HEAD").strip()  # R28
    except RuntimeError as exc:
        ap.error(str(exc))
    if len(sides) < 2:
        ap.error(f"{args.merge} is not a merge commit (use --base and --head "
                 "for a squash merge)")
    wanted = {}
    try:
        for sha in sides:
            for rid, rel, quote in side_quotes(root, sha, core):
                if rid in due:
                    wanted.setdefault(rid, []).append((rel, quote))
    except (RuntimeError, ValueError):
        print(f"merge-check: cannot read trace/s5*.json on {sha}")
        _baklog(args.root, "3.11 merge-check", "merge-check", "fail",
                f"merge-check: cannot read trace/s5*.json on {sha}")
        return 1
    if not wanted:
        print("merge-check: no present S5 items of due done or verified rows "
              "on the merge sides")
        _baklog(args.root, "3.11 merge-check", "merge-check", "pass",
                "merge-check: no present S5 items of due done or verified rows "
                "on the merge sides")
        return 0
    root_r = root.resolve()
    artifacts, items, missing = {}, [], []
    for rid, cands in wanted.items():
        hit = None
        for rel, quote in cands:
            lines = merged_lines(core, root_r, rel, artifacts)
            line = find_line(core, quote, lines) if lines is not None else None
            if line is not None:
                hit = {"id": rid, "status": "present", "where": f"{rel}:{line}",
                       "quote": quote}
                break
        items.append(hit or {"id": rid, "status": "missing"})
        if hit is None:
            missing.append(rid)
    if artifacts:
        trace = root / "trace"
        trace.mkdir(exist_ok=True)
        doc = {"bak_trace": 1, "step": "S6", "part": None, "ledger_version": version,
               "artifacts": artifacts,
               "checker": {"harness": "script", "model": "merge-check.py",
                           "session": session},
               "items": items, "extra": []}
        fd, tmp = tempfile.mkstemp(dir=trace, prefix="s6.json.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(doc, indent=2) + "\n")
            os.replace(tmp, trace / "s6.json")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    for rid in missing:
        print(f"{rid}: missing at S6")
    _baklog(args.root, "3.11 merge-check", "merge-check",
            "fail" if missing else "pass",
            "\n".join(f"{rid}: missing at S6" for rid in missing) or "no violations")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
