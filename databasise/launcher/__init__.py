"""Shared launcher plumbing for ``databasise-rest`` and ``databasise-mcp`` (08-01, RUN-05..07, D-01, D-11).

Imports neither fastapi, uvicorn nor mcp, so each launcher needs only its own extra. All
diagnostics go to stderr: stdout is the MCP stdio channel for the sibling launcher. No refusal
prints an env-file value; refusals name keys only (RUN-05).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from databasise.clients.builder import (
    MissingParityEnvError,
    MissingParityEnvKeyError,
    UnparseableProviderRoutingError,
    build_clients,
    load_env_file,
)
from databasise.parity.import_index import DEFAULT_STORE_ROOT
from databasise.store_lock import StoreLockedError, acquire_store_lock

# The REST app has no authentication, so never bind all interfaces by default.
DEFAULT_HOST = "127.0.0.1"
# The literal RUN-06 names, the only populated store. Equals import_index._import_workspace() for the
# committed snapshot; hard-coded so serving the store never depends on the snapshot verifying.
DEFAULT_WORKSPACE = "shared-4fab18fef508b7bc3dda1cc2d8f12e36"

# No CorpusDriftError: the launcher never verifies the corpus snapshot.
LAUNCH_REFUSALS = (
    StoreLockedError,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    UnparseableProviderRoutingError,
)


def add_engine_arguments(parser: argparse.ArgumentParser, *, default_port: int) -> None:
    parser.add_argument("--store-root", type=Path, default=DEFAULT_STORE_ROOT)
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    # No default env file (RESEARCH Open Question 4): a served process is never silently tied to
    # parity credentials.
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--no-clients", action="store_true")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=default_port)


def check_engine_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.env_file is None and not args.no_clients:
        parser.error("--env-file is required unless --no-clients is given (D-11)")


def open_engine(args: argparse.Namespace) -> tuple[int, dict[str, Any] | None]:
    """Take the store lock FIRST, then build clients; returns ``(lock_fd, clients)``."""
    fd = acquire_store_lock(args.store_root)
    if args.no_clients:
        return fd, None
    try:
        return fd, build_clients(load_env_file(args.env_file))
    except BaseException:
        os.close(fd)
        raise


def refuse(exc: BaseException) -> int:
    print(f"databasise: {exc}", file=sys.stderr)
    return 1
