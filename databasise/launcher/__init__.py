"""Shared launcher plumbing for ``databasise-rest`` and ``databasise-mcp`` (08-01, RUN-05..07, D-01, D-11).

Imports neither fastapi, uvicorn nor mcp, so each launcher needs only its own extra. All
diagnostics go to stderr: stdout is the MCP stdio channel for the sibling launcher. No refusal
prints an env-file value; refusals name keys only (RUN-05).
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import socket
import sys
from pathlib import Path
from typing import Any

from databasise.clients.builder import (
    BUILDER_REFUSALS,
    build_clients,
    load_env_file,
)
from databasise.parity.import_index import DEFAULT_STORE_ROOT
from databasise.store_lock import StoreLockedError, acquire_store_lock

# The REST app has no authentication, so never bind all interfaces by default.
DEFAULT_HOST = "127.0.0.1"
# Host names always accepted in a Host header: the seam is a local surface (DNS-rebinding guard).
LOOPBACK_HOST_NAMES = ("localhost", "127.0.0.1", "[::1]")

# The literal RUN-06 names, the only populated store. Equals import_index._import_workspace() for the
# committed snapshot; hard-coded so serving the store never depends on the snapshot verifying.
DEFAULT_WORKSPACE = "shared-4fab18fef508b7bc3dda1cc2d8f12e36"

# No CorpusDriftError: the launcher never verifies the corpus snapshot.
LAUNCH_REFUSALS = (
    StoreLockedError,
    *BUILDER_REFUSALS,
    OSError,  # an unreadable --env-file or store root
    UnicodeDecodeError,  # an --env-file that is not UTF-8
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
    parser.add_argument(
        "--allow-remote-unauthenticated",
        action="store_true",
        help="bind a non-loopback --host although the seam has no authentication",
    )


def is_loopback_host(host: str) -> bool:
    """True for ``localhost`` and any 127.0.0.0/8 or ``::1`` address literal (brackets allowed)."""
    name = host.strip("[]")
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def _is_wildcard(host: str) -> bool:
    """True for every spelling the socket layer binds to all interfaces: ``0.0.0.0``, ``::``, an empty
    host, the short IPv4 forms (``0``, ``0.0``) and ``::ffff:0.0.0.0``."""
    name = host.strip("[]")
    if not name:
        return True
    try:
        ip = ipaddress.ip_address(name)
        return ip.is_unspecified or (ip.version == 6 and ip.ipv4_mapped is not None and ip.ipv4_mapped.is_unspecified)
    except ValueError:
        pass
    try:
        return socket.inet_aton(name) == bytes(4)  # inet_aton accepts the short forms ip_address rejects
    except OSError:
        return False


def bracketed(host: str) -> str:
    """The form a Host header carries: an IPv6 literal gets brackets."""
    name = host.strip("[]")
    return f"[{name}]" if ":" in name else name


def check_engine_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.env_file is None and not args.no_clients:
        parser.error("--env-file is required unless --no-clients is given (D-11)")
    # stdio (the MCP launcher only) opens no port; every other launch binds --host:--port.
    binds_a_port = getattr(args, "transport", None) != "stdio"
    if binds_a_port and not args.allow_remote_unauthenticated and not is_loopback_host(args.host):
        parser.error(
            f"--host {args.host} is not a loopback address and the seam has no authentication; "
            "bind 127.0.0.1, or pass --allow-remote-unauthenticated to accept that"
        )
    # WR-03: the Host allow-list names the bound host and no client sends Host: 0.0.0.0, so a wildcard
    # bind would answer every remote request with 400/421 even with the flag.
    if binds_a_port and _is_wildcard(args.host):
        parser.error(
            f"--host {args.host} is a wildcard bind and the Host allow-list could never match a remote "
            "client; name the interface address to bind (e.g. --host 192.168.1.5)"
        )


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
    # A decode error's text quotes bytes of the env file; name the file problem without them (RUN-05).
    detail = "the --env-file is not valid UTF-8" if isinstance(exc, UnicodeDecodeError) else exc
    print(f"databasise: {detail}", file=sys.stderr)
    return 1
