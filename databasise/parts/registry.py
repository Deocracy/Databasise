"""Explicit in-code part registry (D-13): an in-memory dict mapping ``name@version`` to a
``Part``. No dynamic-import fallback and no entry_points discovery — that is exactly the
extensibility D-13 rejects for this milestone: every part in this milestone is authored by this
project, so a plain dict costs nothing an editable install or entry_points-based approach would
have imposed for extensibility nothing needs yet. entry_points support can be added later
without changing the Part interface.

05-01-PLAN.md Task 2: this is the point where §8's "an opaque node's self-report is not trusted at
face value" becomes machine-enforced. ``register`` refuses an executable (``body is not None``)
opaque part carrying no admission record (``UnadmittedOpaquePartError``), and validates a present
record via ``databasise.parts.admission.validate_admission`` before filing it — a record that lies
is refused at registration time, never merely at run time. A declaration-only part (``body is
None``) carries no admission requirement at all, regardless of its ``kind``.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.admission import validate_admission
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


class UnadmittedOpaquePartError(RuntimeError):
    """Raised by ``PartRegistry.register`` when an executable (``body is not None``) opaque part
    carries no §8 admission record. Names the part; the message points at
    ``databasise.parts.admission.AdmissionRecord`` as where to supply one.
    """

    def __init__(self, name_at_version: str):
        self.name_at_version = name_at_version
        super().__init__(
            f"{name_at_version!r} is an executable opaque part with no §8 admission record; "
            "supply one via databasise.parts.admission.AdmissionRecord before registering it"
        )


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
        """Add ``part``, refusing a duplicate ``name_at_version`` rather than overwriting it.

        05-01-PLAN.md Task 2: an executable (``body is not None``) part whose ``kind`` is the
        literal ``"opaque"`` value with no admission record is refused
        (``UnadmittedOpaquePartError``); a present record is validated via ``validate_admission``
        before the part is filed, so an invalid record is refused here rather than surfacing only
        at run time. A declaration-only part (``body is None``) is exempt from both checks
        regardless of its ``kind``.

        Gated on ``kind``, not ``structural_depth`` — the two are independent fields (see
        ``databasise/parts/schema.py``'s own docstring): ``lightrag/embedder-index@0.1.0``
        (``databasise/parts_core/lightrag/embedder_index.py``) is an already-registered executable
        part with ``structural_depth="opaque"`` (CONTRACT §3's taint-rule depth ladder) but
        ``kind="embedder"`` — it is not itself an unverified-internals opaque *node* in §8's sense
        and must not be swept into this admission requirement. ``kind == "opaque"`` is exactly the
        literal value ``databasise.validator.execution_mode.derive_execution_mode`` already keys
        its own ``subprocess`` placement decision on, so the two checks agree on what "opaque"
        means.
        """
        if part.name_at_version in self._parts:
            raise DuplicatePartError(part.name_at_version)
        if part.body is not None and part.kind == "opaque":
            if part.admission is None:
                raise UnadmittedOpaquePartError(part.name_at_version)
            validate_admission(part, part.admission)
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
    """A registry preloaded with D-04's four executable ``parts_core`` reference parts, the two
    remaining declaration-only Falsifier-2 wiring placeholders (03-08-PLAN.md Task 3 retired the
    third, ``lightrag/query-side`` (version ``0.1.0``), once Phase 3 ported its real eighteen
    positions), (03-04-PLAN.md Task 2 onward) the fifteen ported LightRAG parts, and
    (06-01-PLAN.md) the tracer's five ported HippoRAG parts — no tracer-only parts.
    """
    # Local import: parts_core imports Part/Effect from parts.schema (not this module), so
    # importing it here keeps the registry/parts_core dependency direction one-way and obvious
    # at the one call site that needs it, rather than at every import of this module.
    from databasise.parts_core import PARTS
    from databasise.parts_core.declared_only import DECLARED_ONLY_PARTS
    from databasise.parts_core.hipporag import HIPPORAG_PARTS
    from databasise.parts_core.lightrag import LIGHTRAG_PARTS

    registry = PartRegistry(seed_tracer_parts=False)
    for part in (*PARTS, *DECLARED_ONLY_PARTS, *LIGHTRAG_PARTS, *HIPPORAG_PARTS):
        registry.register(part)
    return registry
