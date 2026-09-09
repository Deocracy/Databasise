"""``databasise.foreign._mcp_sdk_guard`` — a CWD-shadow-safe availability check and import helper
for the third-party ``mcp`` SDK, used by ``codebase_memory_mcp_adapter.py``'s own lazy import.

**Why this exists (05-07-PLAN.md's own regression, fixed within this same plan — Rule 1).**
05-06-PLAN.md's ``codebase_memory_mcp_adapter.py`` and its own test files (
``databasise/tests/parts_core/test_codebase_memory_mcp_admission.py``,
``databasise/tests/evidence/test_falsifier4_evidence.py``) each detect whether the ``mcp`` extra is
installed via a bare ``importlib.util.find_spec("mcp")``. 05-07-PLAN.md's own new
``databasise/mcp/`` package (a sibling of this ``databasise/foreign/`` directory, sharing the
identical top-level name as the real SDK) makes that bare lookup unreliable — confirmed live this
session in **two independently reproducing shapes**, not one:

1. **The CWD-shaped shape.** CPython's own ``-c``/``-m``/REPL invocations prepend the literal
   empty-string CWD entry to ``sys.path``, and when this project's own root (``databasise/``,
   directly containing ``mcp/``) is the working directory, that entry resolves ``mcp`` to this
   package's regular ``__init__.py``.
2. **The namespace-package shape (found only once ``databasise/tests/mcp/`` — this project's own
   *test* directory for this transport, deliberately carrying no ``__init__.py`` for a different,
   unrelated reason — existed).** pytest's own "prepend" import mode inserts a test file's
   *basedir* onto ``sys.path`` for collection (e.g. ``databasise/tests/`` for any file under a
   ``tests/<subpackage>/__init__.py`` chain that stops there). ``databasise/tests/mcp/`` — a
   directory with ``.py`` files but no ``__init__.py`` — is then eligible for PEP 420 implicit
   namespace-package treatment as bare top-level ``mcp`` the moment ``databasise/tests/`` is on
   ``sys.path``, which happens for ordinary test collection with no ``-c``/``-m`` involved at all.
   Confirmed live: ``importlib.util.find_spec("mcp")`` inside an actual pytest run returned a
   namespace spec (``origin=None``) rooted at ``databasise/tests/mcp``.

Both shapes share one property the real SDK never has: **the resolved module's origin (a regular
package) or every one of its namespace search locations (a namespace package) sits somewhere
inside this project's own ``databasise/`` root.** The real, installed SDK always lives under
``.venv/.../site-packages/mcp/``, never inside this project's source tree. :func:`mcp_sdk_is_installed`
and :func:`import_real_mcp` both check exactly this — never a narrower, single-directory check —
so any future subdirectory of ``databasise/`` that happens to collide with ``mcp`` (by accident or
by a later plan) is caught the same way, not merely the two shapes found this session.

This module is intentionally standalone (no import of ``databasise.mcp`` at all) so it stays
exactly as lightweight and lazy as ``codebase_memory_mcp_adapter.py``'s own pre-existing design
requires: importing this module — or calling either function when the extra is genuinely absent —
never requires the ``mcp`` extra to be installed. ``databasise/mcp/_sdk.py`` delegates to this
module rather than duplicating it.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

# databasise/foreign/_mcp_sdk_guard.py -> databasise/ (this project's own package root — see
# module docstring: nothing under here is ever the real, installed third-party SDK)...
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# ...*except* the active virtualenv's own site-packages, which this project's own layout nests
# directly under databasise/.venv/ — the real, legitimately installed SDK lives there, and a
# naive "anywhere under databasise/" check would misclassify it as shadowed too (found live this
# session: `sys.prefix` resolves inside `_PROJECT_ROOT`, so the real SDK's own `__file__` does as
# well). Excluded first, before the broader project-root check.
_VENV_ROOT = Path(sys.prefix).resolve()


def _resolves_inside_project(path_str: str) -> bool:
    """True if ``path_str`` — a ``sys.path`` entry, a module's ``__file__``, or a namespace
    package's search location — resolves to somewhere inside :data:`_PROJECT_ROOT` but *outside*
    the active virtualenv (:data:`_VENV_ROOT`, where every legitimately installed package,
    including the real SDK, actually lives). An empty string or ``'.'`` (CPython's own CWD-shaped
    ``sys.path`` entries) resolves via ``Path.cwd()``, exactly as the interpreter itself resolves
    them."""
    try:
        resolved = Path(path_str).resolve() if path_str not in ("", ".") else Path.cwd().resolve()
    except OSError:
        return False
    if resolved == _VENV_ROOT or _VENV_ROOT in resolved.parents:
        return False
    return resolved == _PROJECT_ROOT or _PROJECT_ROOT in resolved.parents


def mcp_sdk_is_installed() -> bool:
    """True only if the real third-party ``mcp`` package is importable — never true merely
    because some part of this project's own source tree happens to shadow the bare top-level name
    ``mcp`` (module docstring, both known shapes)."""
    spec = importlib.util.find_spec("mcp")
    if spec is None:
        return False
    if spec.origin:
        return not _resolves_inside_project(spec.origin)
    # A namespace package (no single origin file) — the real SDK is a regular package (it ships
    # its own __init__.py) and is therefore never resolved this way; any namespace resolution is
    # this project's own shadow, not the real SDK.
    return False


def import_real_mcp(dotted_name: str) -> ModuleType:
    """Import ``dotted_name`` from the real SDK, never from anywhere inside this project's own
    source tree — see the module docstring for the mechanism: evict a wrongly cached shadow entry,
    strip every project-internal ``sys.path`` entry (not merely the CWD-shaped ones) for the
    duration of the lookup, restore unconditionally.
    """
    top_level = dotted_name.split(".", 1)[0]
    cached = sys.modules.get(top_level)
    if cached is not None:
        cached_file = getattr(cached, "__file__", None)
        cached_shadowed = (
            _resolves_inside_project(cached_file)
            if cached_file
            else any(_resolves_inside_project(loc) for loc in getattr(cached, "__path__", []) or [])
        )
        if cached_shadowed:
            for key in [k for k in sys.modules if k == top_level or k.startswith(top_level + ".")]:
                del sys.modules[key]

    saved_path = list(sys.path)
    sys.path[:] = [entry for entry in saved_path if not _resolves_inside_project(entry)]
    try:
        return importlib.import_module(dotted_name)
    finally:
        sys.path[:] = saved_path


__all__ = ["import_real_mcp", "mcp_sdk_is_installed"]
