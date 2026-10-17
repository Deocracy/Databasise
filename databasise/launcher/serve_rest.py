"""``databasise-rest``: serve the §18 REST app over the populated store with one worker (RUN-06, RUN-07)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from databasise.launcher import (
    LAUNCH_REFUSALS,
    add_engine_arguments,
    bracketed,
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
    """Wraps ``create_app`` with the launcher's transport guards (D-13). The TrustedHost 400 and the
    Origin-guard 403 ``{"detail": ...}`` are transport-level defences in front of the seam and keep
    their own shapes; every refusal the seam raises (``create_app`` routes, MCP tools) uses the one
    refusal body documented in ``databasise/seam/rest.py``."""
    from databasise.seam.rest import create_app
    from fastapi.responses import JSONResponse
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app = create_app(
        store_root=args.store_root,
        workspace=args.workspace,
        clients=clients,
        cors_origins=args.cors_origin or (),
    )
    # DNS-rebinding guard, launcher-only so create_app keeps accepting any Host. Starlette compares the
    # Host header up to its first ":", so ports are moot and every bracketed IPv6 literal reduces to "[";
    # an IP literal cannot be rebound, so that is accepted.
    allowed = ["localhost", "127.0.0.1", "[", args.host.strip("[]")]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

    # WR-01: CORS only hides the response from a foreign page; a form POST (/documents/upload) still runs.
    # Refuse a state-changing request whose Origin is neither listed nor this loopback/bound host. No Origin
    # (curl, MCP, agents) passes: browsers always send one on a cross-site POST.
    own = {f"http://{name}:{args.port}" for name in ("localhost", "127.0.0.1", "[::1]", bracketed(args.host))}
    permitted = own | set(args.cors_origin or ())

    @app.middleware("http")
    async def origin_guard(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None and origin not in permitted:
            return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
        return await call_next(request)

    return app


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
