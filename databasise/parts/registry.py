"""Explicit in-code part registry (D-13): an in-memory dict mapping ``name@version`` to a
``Part``. No dynamic-import fallback and no entry_points discovery — that is exactly the
extensibility D-13 rejects for this milestone: every part in this milestone is authored by this
project, so a plain dict costs nothing an editable install or entry_points-based approach would
have imposed for extensibility nothing needs yet. entry_points support can be added later
without changing the Part interface.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part


class UnknownPartError(KeyError):
    """Raised by ``PartRegistry.get`` for a ``name@version`` with no registered Part."""

    def __init__(self, name_at_version: str, known: list[str]):
        self.name_at_version = name_at_version
        self.known = sorted(known)
        super().__init__(
            f"unknown part {name_at_version!r}; registered parts: {self.known}"
        )


class DuplicatePartError(ValueError):
    """Raised by ``PartRegistry.register`` when ``name_at_version`` is already registered — the
    registry never silently overwrites an existing entry.
    """

    def __init__(self, name_at_version: str):
        self.name_at_version = name_at_version
        super().__init__(f"part {name_at_version!r} is already registered")


class DeclarationOnlyPartError(RuntimeError):
    """Raised by :func:`dispatch` when a declaration-only Part (``body is None``) is dispatched.
    D-04 ships these so Phase 2 has a registry to compute over without waiting on Phase 3 — a
    ``None`` body MUST make the part un-executable, never a silent no-op.
    """

    def __init__(self, name_at_version: str):
        self.name_at_version = name_at_version
        super().__init__(
            f"{name_at_version!r} is a declaration-only Phase 1 entry with no body; "
            "execution awaits its Phase 3 port"
        )


async def _passthrough_body(ctx: NodeContext) -> dict[str, Any]:
    """The tracer's zero-effect reference part: relays its inputs verbatim."""
    return {"node_id": ctx.node_id, "inputs": dict(ctx.inputs)}


async def _kv_writer_body(ctx: NodeContext) -> dict[str, Any]:
    """The tracer's writes_kv reference part: writes its own output to the run's KV store."""
    store = ctx.stores["kv"]
    value = {"node_id": ctx.node_id, "inputs": dict(ctx.inputs)}
    await store.upsert({ctx.node_id: value})
    return value


_TRACER_PARTS: dict[str, Part] = {
    "core/passthrough@1.0.0": Part(
        name_at_version="core/passthrough@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=_passthrough_body,
    ),
    "core/kv-writer@1.0.0": Part(
        name_at_version="core/kv-writer@1.0.0",
        kind="kv-writer",
        structural_depth="stage",
        effects=["writes_kv"],
        upstream_ref=None,
        body=_kv_writer_body,
    ),
}


class PartRegistry:
    """In-memory dict mapping ``name@version -> Part`` (D-13). Bare ``PartRegistry()`` keeps
    plan 01-02's tracer default (a passthrough and a kv-writer, unchanged — ``databasise``'s
    public ``run_wiring`` and the tracer fixture depend on it). Pass ``seed_tracer_parts=False``
    for an empty registry, which is what :func:`default_registry` uses so it holds exactly
    D-04's seven Phase-1 entries and nothing else.
    """

    def __init__(self, *, seed_tracer_parts: bool = True) -> None:
        self._parts: dict[str, Part] = dict(_TRACER_PARTS) if seed_tracer_parts else {}

    def get(self, name_at_version: str) -> Part:
        try:
            return self._parts[name_at_version]
        except KeyError:
            raise UnknownPartError(name_at_version, list(self._parts.keys())) from None

    def register(self, part: Part) -> None:
        """Add ``part``, refusing a duplicate ``name_at_version`` rather than overwriting it."""
        if part.name_at_version in self._parts:
            raise DuplicatePartError(part.name_at_version)
        self._parts[part.name_at_version] = part

    def keys(self) -> list[str]:
        return list(self._parts.keys())


async def dispatch(part: Part, ctx: NodeContext) -> Any:
    """Invoke ``part.body(ctx)``, refusing a declaration-only Part (``body is None``)
    explicitly. This is the seam a later runner plan wires into the scheduler's own
    node-dispatch call site (``databasise/runner/scheduler.py``, out of this plan's scope);
    today it is exercised directly by ``tests/parts/test_registry.py``.
    """
    if part.body is None:
        raise DeclarationOnlyPartError(part.name_at_version)
    return await part.body(ctx)


def default_registry() -> PartRegistry:
    """A registry preloaded with exactly D-04's seven Phase-1 entries: the four executable
    ``parts_core`` reference parts plus the three declaration-only Falsifier-2 wiring
    placeholders — no tracer-only parts.
    """
    # Local import: parts_core imports Part/Effect from parts.schema (not this module), so
    # importing it here keeps the registry/parts_core dependency direction one-way and obvious
    # at the one call site that needs it, rather than at every import of this module.
    from databasise.parts_core import PARTS
    from databasise.parts_core.declared_only import DECLARED_ONLY_PARTS

    registry = PartRegistry(seed_tracer_parts=False)
    for part in (*PARTS, *DECLARED_ONLY_PARTS):
        registry.register(part)
    return registry
