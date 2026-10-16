#!/usr/bin/env python3
"""Off-ledger deferral scan: marker lines in build notes with no ledger ID fail."""
import argparse
import glob
import json
import posixpath
import re
from pathlib import Path

ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")
MARKERS = ("(deferred)", "deferred", "parked", "follow-up", "out of scope",
           "later phase", "not fixed", "left as is", "wontfix")
DEFAULT_GLOBS = (".superpowers/sdd/**/progress.md",
                 ".superpowers/sdd/**/*review*.md",
                 ".superpowers/sdd/**/*report*.md",
                 "verifier/*.md")
VIOLATION = ("deferral not in the ledger (add-follow-up, "
             "or set-status deferred-requested for a requirement)")


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


def _normalize_source_path(raw, root):
    """Root-relative POSIX form of a spec_ref path (PD-R2).

    A ./-prefixed path collapses to the same file via normpath; an
    absolute path that resolves under root is made relative to root.
    Returns None when it cannot name a file under root."""
    s = raw.strip()
    if not s:
        return None
    if Path(s).anchor:
        try:
            root_r = Path(root).resolve()
        except OSError:
            return None
        try:
            target = Path(s).resolve()
        except OSError:
            return None
        try:
            key = target.relative_to(root_r).as_posix()
        except ValueError:
            return None
        return posixpath.normpath(key)
    return posixpath.normpath(s)


def _source_pair(ref, root):
    """Split a PATH:LINE source into (root-relative path, line), or None."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    path_part, sep, line_part = ref.rpartition(":")
    if not sep or not path_part.strip() or not line_part.strip():
        return None
    try:
        line_no = int(line_part.strip())
    except ValueError:
        return None
    norm = _normalize_source_path(path_part.strip(), root)
    if norm is None:
        return None
    return (norm, line_no)


def import_sources(root):
    """(note_path, line) pairs already imported into the ledger.

    add-follow-up --source PATH:LINE stores that source in the row's
    spec_ref; a finding row may carry its source in finding.source.
    The path is the root-relative POSIX note path (PD-R2); an absolute
    or ./-prefixed spec_ref that resolves to the same file is accepted."""
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json")
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    found = set()
    for row in items:
        if not isinstance(row, dict):
            continue
        if row.get("kind") not in ("follow-up", "finding"):
            continue
        pair = _source_pair(row.get("spec_ref", ""), root)
        if pair is not None:
            found.add(pair)
        finding = row.get("finding")
        if isinstance(finding, dict):
            pair = _source_pair(str(finding.get("source", "")), root)
            if pair is not None:
                found.add(pair)
    return found


def load_ids(root):
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json")
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    return {str(row.get("id", "")) for row in items if isinstance(row, dict)}


def note_files(root, patterns):
    found = []
    for pattern in patterns:
        for match in sorted(glob.glob(pattern, root_dir=str(root), recursive=True)):
            path = Path(root) / match
            if path.is_file() and match not in found:
                found.append(match)
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(prog="deferral-scan.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--notes", nargs="*", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root)
    ids = load_ids(root)
    if ids is None:
        print("LEDGER: REQUIREMENTS.json missing or unparsable")
        _baklog(root, "1.4 deferral-scan", "deferral-scan", "fail",
                "LEDGER: REQUIREMENTS.json missing or unparsable")
        return 1
    patterns = list(args.notes) if args.notes else list(DEFAULT_GLOBS)
    imported = import_sources(root)
    if imported is None:
        print("LEDGER: REQUIREMENTS.json missing or unparsable")
        _baklog(root, "1.4 deferral-scan", "deferral-scan", "fail",
                "LEDGER: REQUIREMENTS.json missing or unparsable")
        return 1
    out = []
    for rel in note_files(root, patterns):
        try:
            with open(Path(root) / rel, "rb") as fh:
                raw = fh.read()
        except OSError:
            try:
                shown = Path(rel).as_posix()
            except Exception:
                shown = str(rel)
            out.append(f"{shown}: unreadable (run the scan with --notes, fix or cite the note)")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                shown = Path(rel).as_posix()
            except Exception:
                shown = str(rel)
            out.append(f"{shown}: unreadable (run the scan with --notes, fix or cite the note)")
            continue
        lines = text.splitlines()
        for number, line in enumerate(lines, start=1):
            lowered = line.lower()
            if not any(marker in lowered for marker in MARKERS):
                continue
            cited = ID_RE.findall(line)
            if any(cid in ids for cid in cited):
                continue
            shown = Path(rel).as_posix()
            if imported and (posixpath.normpath(shown), number) in imported:
                continue
            out.append(f"{shown}:{number}: {VIOLATION}")
    for line in out:
        print(line)
    failed = bool(out)
    _baklog(root, "1.4 deferral-scan", "deferral-scan",
            "fail" if failed else "pass", "\n".join(out) or "no violations")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
