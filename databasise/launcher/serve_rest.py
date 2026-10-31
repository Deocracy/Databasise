"""``databasise-rest``: serve the §18 REST app over the populated store with one worker (RUN-06, RUN-07)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from databasise.launcher import (
    LAUNCH_REFUSALS,
    add_engine_arguments,
    bracketed,
    check_engine_arguments,
    is_loopback_host,
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
    parser.add_argument(
        "--operator",
        action="store_true",
        help="mount the operator read routes (wiring names, aliases, trace tokens); loopback --host only",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        dest="log_file",
        default=None,
        help=(
            "write the server log, with its paths and tracebacks, to PATH; GET /log serves its tail "
            "and needs --operator too (D-18, D-19)"
        ),
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="serve the operator console at GET /console; loopback --host only, needs a fixed --port (D-01, D-02)",
    )
    return parser


_JS_SCRIPT_TYPES = ("", "text/javascript", "application/javascript", "module")


def console_csp(page: bytes) -> str:
    """The Content-Security-Policy for the shipped console page (T-18-06). It allows exactly the page's one
    executable inline script and one style block, by sha256 hash, so it holds no inline-allow keyword. A page
    with any other count raises, so the launcher refuses to start rather than serve a page its own policy
    would block. A non-JavaScript ``<script type=...>`` data block is not executed and needs no hash."""
    import base64
    import hashlib
    import re

    text = page.decode("utf-8")

    def source(body: str) -> str:
        return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode() + "'"

    scripts = [
        body
        for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", text, re.S)
        if (re.search(r"""\btype\s*=\s*["']?([^"'\s>]*)""", attrs) or [None, ""])[1].lower() in _JS_SCRIPT_TYPES
    ]
    styles = re.findall(r"<style[^>]*>(.*?)</style>", text, re.S)
    if len(scripts) != 1 or len(styles) != 1:
        raise RuntimeError(
            f"the console page must hold exactly one executable inline script and one style block, "
            f"found {len(scripts)} and {len(styles)}"
        )
    return (
        f"default-src 'none'; script-src {source(scripts[0])}; style-src {source(styles[0])}; "
        "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )


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
        operator=getattr(args, "operator", False),  # getattr: protected tests may hand-build a Namespace
        log_path=getattr(args, "log_file", None),
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

    if getattr(args, "console", False):
        import importlib.resources

        from fastapi import Response

        # Read once: a missing file fails at start-up, and the CSP hashes are computed from these bytes.
        page = importlib.resources.files("databasise.console").joinpath("operator-console.html").read_bytes()
        headers = {
            "Content-Security-Policy": console_csp(page),
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        }

        @app.get("/console", include_in_schema=False)
        async def get_console():
            return Response(page, media_type="text/html; charset=utf-8", headers=headers)

    return app


def log_config_for(path: str | Path) -> dict[str, Any]:
    """uvicorn's default ``LOGGING_CONFIG`` plus a file handler on ``uvicorn``, ``uvicorn.access`` and
    root (16-11, D-18). ``uvicorn`` and ``uvicorn.access`` do not propagate, so a root-only handler
    would miss the 500 tracebacks; ``disable_existing_loggers`` stays false because the engine logger
    is created at import, before uvicorn applies this config (16-RESEARCH Verified Point 1)."""
    import copy

    from uvicorn.config import LOGGING_CONFIG

    config = copy.deepcopy(LOGGING_CONFIG)
    config["disable_existing_loggers"] = False
    config["formatters"]["file"] = {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    config["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": str(path),
        "encoding": "utf-8",
        "formatter": "file",
    }
    config["loggers"]["uvicorn"]["handlers"].append("file")
    config["loggers"]["uvicorn.access"]["handlers"].append("file")
    config["root"] = {"handlers": ["file"], "level": "INFO"}
    return config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.workers != 1:
        parser.error(
            "--workers must be 1: one engine process per store root holds the store lock "
            "<store_root>/.engine.lock (G-36)"
        )
    if args.operator and not is_loopback_host(args.host):
        parser.error(
            "--operator needs a loopback --host, even with --allow-remote-unauthenticated: the operator "
            "routes expose wiring names and trace tokens"
        )
    if args.console and not is_loopback_host(args.host):
        parser.error(
            "--console needs a loopback --host, even with --allow-remote-unauthenticated: the console "
            "drives every route without authentication"
        )
    if args.console and args.port == 0:
        parser.error("--console needs a fixed --port: the Origin guard admits only http://127.0.0.1:<port>")
    from databasise.seam.rest import InvalidCorsOriginError, validate_cors_origin

    try:
        for origin in args.cors_origin or ():
            validate_cors_origin(origin)
    except InvalidCorsOriginError as exc:
        parser.error(str(exc))
    check_engine_arguments(parser, args)
    # 16-REVIEW-A WR-03: uvicorn's dictConfig would raise a traceback after the store lock is taken.
    # A missing parent, a directory, '' (Path('.')) and an unwritable path all fail this open.
    if args.log_file is not None:
        try:
            with open(args.log_file, "a", encoding="utf-8"):
                pass
        except OSError as exc:
            return refuse(OSError(f"--log-file {args.log_file} cannot be opened for append: {exc.strerror}"))
    try:
        fd, clients = open_engine(args)
    except LAUNCH_REFUSALS as exc:
        return refuse(exc)
    try:
        import uvicorn

        # No log_config kwarg without --log-file: log_config=None would switch uvicorn's own logging off.
        log_kwargs = {} if args.log_file is None else {"log_config": log_config_for(args.log_file)}
        uvicorn.run(build_app(args, clients), host=args.host, port=args.port, workers=1, **log_kwargs)
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
