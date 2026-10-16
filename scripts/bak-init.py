#!/usr/bin/env python3
"""Per-project setup for the Build Assurance Kit (contract C8 /bak:init)."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TRACE_NEXT = "next step: python3 scripts/ledger-amend.py enable-trace --kind code|document"
LEFTHOOK_NEXT = "next step: run lefthook install"

LEFTHOOK_YML = """pre-commit:
  parallel: true
  commands:
    bak-complete:
      run: python3 scripts/check-ledger.py --root . --complete
"""


def kit_root():
    return Path(__file__).resolve().parents[2]


def _append_unique(path: Path, line: str):
    existing = []
    if path.is_file():
        existing = path.read_text(encoding="utf-8").splitlines()
    if line in existing:
        return
    with path.open("a", encoding="utf-8") as fh:
        if path.stat().st_size > 0:
            with path.open("rb") as rf:
                rf.seek(-1, 2)
                if rf.read(1) != b"\n":
                    fh.write("\n")
        fh.write(line + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bak-init.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--kind", default=None, choices=["code", "document"])
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        kit = kit_root()
        scripts = root / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        for src in sorted((kit / "core" / "scripts").glob("*.py")):
            dest = scripts / src.name
            if not dest.is_file() or args.force:
                shutil.copy(src, dest)
        for src in sorted((kit / "core" / "templates").glob("implied-items-*.json")):
            dest = scripts / src.name
            if not dest.is_file() or args.force:
                shutil.copy(src, dest)
        gitattributes = root / ".gitattributes"
        rule = "debug/loss-log.jsonl merge=union"
        existing_lines = []
        if gitattributes.is_file():
            existing_lines = gitattributes.read_text(encoding="utf-8").splitlines()
        if rule not in existing_lines:
            with gitattributes.open("a", encoding="utf-8") as fh:
                if gitattributes.stat().st_size > 0:
                    with gitattributes.open("rb") as rf:
                        rf.seek(-1, 2)
                        if rf.read(1) != b"\n":
                            fh.write("\n")
                fh.write(rule + "\n")
        _append_unique(gitattributes, "debug/stalls.jsonl merge=union")  # C12.5
        ledger = root / "ledger" / "REQUIREMENTS.json"
        if not ledger.is_file():
            amend = scripts / "ledger-amend.py"
            proc = subprocess.run([sys.executable, str(amend), "--root", str(root), "init"],
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
                return 1
        if args.kind is not None:
            amend = scripts / "ledger-amend.py"
            proc = subprocess.run([sys.executable, str(amend), "--root", str(root),
                                   "enable-trace", "--kind", args.kind],
                                  capture_output=True, text=True)
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0 and "already enabled" not in out:
                print(out.strip(), file=sys.stderr)
                return 1
            if "already enabled" in out:
                print(out.strip())
        else:
            print(TRACE_NEXT)
        for name in ("trace", "debug"):
            (root / name).mkdir(parents=True, exist_ok=True)
        bak = root / ".bak"
        bak.mkdir(parents=True, exist_ok=True)
        (bak / ".gitignore").write_text("*\n", encoding="utf-8")
        ci = root / ".github" / "workflows"
        ci.mkdir(parents=True, exist_ok=True)
        gate = ci / "bak-gate.yml"
        if not gate.is_file() or args.force:
            template = kit / "core" / "ci" / "completion-gate.yml"
            text = template.read_text(encoding="utf-8")
            text = text.replace("name: completion-gate", "name: bak-gate", 1)
            text = text.replace("\n  ledger:\n", "\n  bak-gate:\n", 1)
            gate.write_text(text, encoding="utf-8")
        hook_cfg = root / "lefthook.yml"
        if not hook_cfg.is_file() or args.force:
            src_hook = kit / "core" / "templates" / "lefthook.yml"
            if src_hook.is_file():
                shutil.copy(src_hook, hook_cfg)
            else:
                hook_cfg.write_text(LEFTHOOK_YML, encoding="utf-8")
        print(LEFTHOOK_NEXT)
        _append_unique(scripts / ".gitignore", "__pycache__/")
        try:
            from baklog import append as _append
        except Exception:
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("baklog", str(scripts / "baklog.py"))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _append = mod.append
            except Exception:
                _append = None
        if _append is not None:
            try:
                _append(str(root), "8.1 bak-init", "bak:init", "info", "project initialized")
            except Exception:
                pass
        return 0
    except Exception as exc:
        print(f"bak-init: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
