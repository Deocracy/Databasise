"""``databasise-mcp``: serve the §18 MCP tools over the populated store, one engine per store root (RUN-06, RUN-07, D-02).

Nothing is ever written to stdout here: in ``--transport stdio`` mode stdout is the protocol channel,
so every diagnostic goes to stderr through :func:`databasise.launcher.refuse`.
"""

from __future__ import annotations

import argparse
import os
import sys

from databasise.launcher import (
    LAUNCH_REFUSALS,
    LOOPBACK_HOST_NAMES,
    add_engine_arguments,
    bracketed,
    check_engine_arguments,
    open_engine,
    refuse,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="databasise-mcp", description=__doc__)
    add_engine_arguments(parser, default_port=8001)
    parser.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    return parser


def build_transport_security(args: argparse.Namespace):
    """DNS-rebinding protection for sse/streamable-http: loopback names and the bound host, bare and
    with the bound port; origins are any loopback page plus the bound host (this launcher has no
    ``--cors-origin``)."""
    from databasise.mcp._sdk import import_sdk

    bound = bracketed(args.host)
    hosts = list(dict.fromkeys([*LOOPBACK_HOST_NAMES, bound]))
    origins = [f"http://{name}{suffix}" for name in LOOPBACK_HOST_NAMES for suffix in ("", ":*")]
    origins.append(f"http://{bound}:{args.port}")
    return import_sdk("mcp.server.transport_security").TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[value for name in hosts for value in (name, f"{name}:{args.port}")],
        allowed_origins=list(dict.fromkeys(origins)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    check_engine_arguments(parser, args)
    try:
        fd, clients = open_engine(args)
    except LAUNCH_REFUSALS as exc:
        return refuse(exc)
    try:
        from databasise.mcp import create_server

        server = create_server(store_root=args.store_root, workspace=args.workspace, clients=clients)
        if args.transport == "stdio":
            server.run("stdio")
        else:
            server.run(
                args.transport,
                host=args.host,
                port=args.port,
                transport_security=build_transport_security(args),
            )
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
