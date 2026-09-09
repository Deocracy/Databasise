"""``databasise.mcp._sdk`` — a CWD-shadow-safe resolver for the third-party ``mcp`` SDK. Every
import of the real SDK anywhere in ``databasise/mcp/`` goes through :func:`import_sdk`, never a
bare ``import mcp``/``from mcp... import ...`` statement.

**The problem this module exists to solve (found empirically this session, not anticipated by the
plan).** ``databasise/mcp/`` — this package's own directory — sits directly inside this project's
package root (``databasise/``), the same directory CPython's own ``-c``/``-m``/REPL invocations
prepend to ``sys.path`` as the literal empty-string CWD entry (documented CPython behaviour, not a
bug in this project: https://docs.python.org/3/using/cmdline.html#cmdoption-c). Confirmed live this
session: ``cd databasise && python -c "import mcp; print(mcp.__file__)"`` resolves to *this
package's own* ``__init__.py``, never the installed SDK — because the CWD-shaped ``sys.path[0]``
entry is searched before site-packages, and this package's own directory now (as of this plan)
matches the SDK's own top-level name byte-for-byte. Every one of this plan's own acceptance
criteria that invokes ``uv run --extra mcp python -c "..."`` from ``cd databasise`` exercises
exactly this trap; a bare ``import mcp``/``from mcp.server.mcpserver import MCPServer`` anywhere in
``databasise/mcp/`` reproduces a circular-import ``ImportError`` under that invocation shape,
confirmed live before this fix existed. The same shadow *also* broke 05-06's own pre-existing
``codebase_memory_mcp_adapter.py`` lazy import and its two test files' ``importlib.util.find_spec
("mcp")`` guards — fixed alongside this module by
``databasise/foreign/_mcp_sdk_guard.py``, the shared, standalone (no ``databasise.mcp`` import)
implementation both that adapter and this module delegate to, so the one detection/import
mechanism is never duplicated.
"""

from __future__ import annotations

from types import ModuleType

from databasise.foreign._mcp_sdk_guard import import_real_mcp


def import_sdk(dotted_name: str) -> ModuleType:
    """Import ``dotted_name`` (``"mcp"``, ``"mcp.server.mcpserver"``,
    ``"mcp.server.mcpserver.exceptions"``, etc.) from the real, installed third-party package —
    never this project's own self-shadowed ``databasise/mcp/``. Raises ``ImportError`` naming the
    ``mcp`` extra if the real SDK genuinely is not installed (distinct from merely being
    shadowed) — see :func:`databasise.foreign._mcp_sdk_guard.import_real_mcp`, the shared
    implementation."""
    try:
        return import_real_mcp(dotted_name)
    except ModuleNotFoundError as exc:
        raise ImportError(
            f"{dotted_name!r} could not be resolved from the real 'mcp' SDK — it does not appear "
            "to be installed. Install it via: uv sync --extra mcp"
        ) from exc


__all__ = ["import_sdk"]
