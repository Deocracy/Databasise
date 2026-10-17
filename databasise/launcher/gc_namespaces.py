"""Operator GC for quarantined namespaces (STOR-15, Phase 10 D-16).

``python -m databasise.launcher.gc_namespaces --store-root <root> quarantined-<hex> [...]``
removes each named ``<root>/<token>`` directory. It takes the per-store-root lock, so it refuses
to run while an engine holds the root. Only ``quarantined-*`` tokens are accepted, and every token
is validated before any directory is removed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from databasise.namespaces import gc_namespace, namespace_dir
from databasise.store_lock import StoreLockedError, store_lock

_QUARANTINED_PREFIX = "quarantined-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m databasise.launcher.gc_namespaces", description=__doc__)
    parser.add_argument("--store-root", required=True, type=Path)
    parser.add_argument("namespaces", nargs="+", metavar="NAMESPACE")
    args = parser.parse_args(argv)

    store_root: Path = args.store_root
    # store_lock creates a missing root, so refuse it before taking the lock.
    if not store_root.is_dir():
        parser.error(f"--store-root {store_root} is not an existing directory")

    targets: list[tuple[str, Path]] = []
    for token in args.namespaces:
        if not token.startswith(_QUARANTINED_PREFIX):
            print(f"refused namespace {token!r}: only {_QUARANTINED_PREFIX}* namespaces are GC'd", file=sys.stderr)
            return 1
        try:
            targets.append((token, namespace_dir(store_root, token)))
        except ValueError as exc:
            print(f"refused namespace {token!r}: {exc}", file=sys.stderr)
            return 1

    try:
        with store_lock(store_root):  # Phase 8 D-03: never GC a root a live engine holds
            for token, target in targets:
                if not target.exists() and not target.is_symlink():
                    print(f"absent {token}")
                    continue
                gc_namespace(store_root, token)
                print(f"removed {token}")
    except StoreLockedError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
