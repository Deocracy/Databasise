"""``databasise-rest``: serve the §18 REST app over the populated store with one worker (RUN-06, RUN-07)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from databasise.launcher import (
    LAUNCH_REFUSALS,
    add_engine_arguments,
    check_engine_arguments,
    open_engine,
    refuse,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="databasise-rest", description=__doc__)
    add_engine_arguments(parser, default_port=8000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--cors-origin",
        action="append",
        dest="cors_origin",
        default=None,
        help="allow browser calls from this exact scheme://host:port origin (repeatable, never '*'; D-12)",
    )
    return parser


def build_app(args: argparse.Namespace, clients: dict[str, Any] | None):
    from databasise.seam.rest import create_app

    return create_app(
        store_root=args.store_root,
        workspace=args.workspace,
        clients=clients,
        cors_origins=args.cors_origin or (),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workers != 1:
        parser.error(
            "--workers must be 1: one engine process per store root holds the store lock "
            "<store_root>/.engine.lock (G-36)"
        )
    from databasise.seam.rest import InvalidCorsOriginError, validate_cors_origin

    try:
        for origin in args.cors_origin or ():
            validate_cors_origin(origin)
    except InvalidCorsOriginError as exc:
        parser.error(str(exc))
    check_engine_arguments(parser, args)
    try:
        fd, clients = open_engine(args)
    except LAUNCH_REFUSALS as exc:
        return refuse(exc)
    try:
        import uvicorn

        uvicorn.run(build_app(args, clients), host=args.host, port=args.port, workers=1)
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
