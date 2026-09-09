"""``databasise.mcp`` — API-07's second transport: five intention-level tools over the identical
``Databasise`` engine object the REST transport (``databasise.seam.rest``) already wraps. This
package holds no logic of its own — no selector resolution, no redaction, no envelope assembly
(the same separation ``databasise.seam.rest``'s own module docstring states, verified the same way:
``databasise/tests/mcp/test_tool_growth_invariant.py``'s AST walk).

**A name collision this package must never have.** ``databasise.mcp`` (this package, a submodule
of ``databasise``) and ``mcp`` (the third-party Model Context Protocol SDK, the optional dependency
this package is built against) are two different, independent modules — every import in this
package and in ``databasise.mcp.server``/``databasise.mcp.tools`` is an absolute import
(``from mcp.server.mcpserver import MCPServer``, never a bare relative ``from . import`` that could
shadow the SDK), so the two never bind to the same object in the same process
(``databasise/tests/mcp/test_dual_transport_parity.py`` proves this directly by import identity).

Never imported at module scope by ``databasise/__init__.py`` — only a consumer who has installed
the ``mcp`` extra, and who explicitly imports this module, pays that dependency's cost.
"""

from __future__ import annotations

from databasise.mcp.server import create_server
from databasise.mcp.tools import TOOL_NAMES

__all__ = ["TOOL_NAMES", "create_server"]
