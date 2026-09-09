"""``databasise.tests._ast_helpers`` — the AST-walking helper both
``databasise/tests/seam/test_rest_transport.py`` and
``databasise/tests/mcp/test_tool_growth_invariant.py`` import (05-07-PLAN.md Task 2, action D):
never two independently maintained copies of the same "what does this module's source directly
*call*" logic, so the two thin-adapter proofs (REST, MCP) cannot silently drift apart.

Lives directly under ``databasise/tests/`` (a namespace package, like the sibling
``databasise/tests/fixtures/`` support directory — neither carries an ``__init__.py``) rather than
under any single test subdirectory, since both of this helper's callers are siblings, not one the
other's parent.
"""

from __future__ import annotations

import ast


def called_names(source: str) -> set[str]:
    """Every function/method name a module's own source directly *calls* — never a name merely
    referenced as a type annotation or imported for re-export (an annotation or a bare import
    produces no ``ast.Call`` node, so neither contributes to this set)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


__all__ = ["called_names"]
