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

import re
from typing import Any, get_args

from databasise.parts.admission import validate_admission
from databasise.parts.schema import ArtifactScope, Depth, Effect, NodeContext, Part


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


class UnknownPartEffectError(ValueError):
    """Raised by ``PartRegistry.register`` for effects outside the frozen 17-member ``Effect``
    literal (WIRE-16, D-10)."""

    def __init__(self, name_at_version: str, effects: list[str]):
        self.name_at_version = name_at_version
        self.effects = effects
        super().__init__(
            f"part {name_at_version!r} declares effects outside the frozen Effect vocabulary: {effects}"
        )


class InvalidPartFieldError(ValueError):
    """Raised by ``PartRegistry.register`` for a ``structural_depth`` outside the ``Depth`` literal,
    an ``artifact_scope`` outside the ``ArtifactScope`` literal, or a ``kind`` that is not a slug
    matching ``^[a-z][a-z0-9-]*$`` (TOOL-16, D-17)."""

    def __init__(self, name_at_version: str, *, field: str, value: Any):
        self.part_name_at_version = name_at_version
        self.field = field
        self.value = value
        super().__init__(f"part {name_at_version!r} declares an invalid {field}: {value!r}")


class InvalidReadNamespaceTokenError(ValueError):
    """Raised by ``PartRegistry.register`` for a ``reads_namespaces`` token that is not
    ``<reads_kv|reads_vector|reads_graph>:<namespace>`` with that effect declared in the part's own
    ``effects`` and a ``[A-Za-z0-9-]+`` namespace (WIRE-01, D-01).
    """

    def __init__(self, name_at_version: str, token: str):
        self.name_at_version = name_at_version
        self.token = token
        super().__init__(f"part {name_at_version!r} declares an invalid read-namespace token {token!r}")


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
    A ``None`` body makes the part un-executable, never a silent no-op. No part in
    :func:`default_registry` has one today; the refusal guards a registry built with such a part.
    """

    def __init__(self, name_at_version: str):
        self.name_at_version = name_at_version
        super().__init__(
            f"{name_at_version!r} is a declaration-only part with no body; it cannot execute"
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


_READ_EFFECTS = ("reads_kv", "reads_vector", "reads_graph")

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
    for an empty registry, which is what :func:`default_registry` uses so it holds only the parts
    it registers. ``keys()`` lists the contents; this docstring states no count, so it cannot go
    stale when a part is added.
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
        at run time. A declaration-only part (``body is None``) is exempt from both admission
        checks regardless of its ``kind``.

        A ``structural_depth`` outside ``Depth``, an ``artifact_scope`` outside ``ArtifactScope``
        and a ``kind`` that is not a ``^[a-z][a-z0-9-]*$`` slug are refused
        (``InvalidPartFieldError``, TOOL-16). An effect outside the frozen ``Effect`` literal is refused (``UnknownPartEffectError``,
        WIRE-16), declaration-only parts included, so no registration can make a query member
        beyond that vocabulary consumable. Each ``reads_namespaces`` token is validated too
        (``InvalidReadNamespaceTokenError``, WIRE-01).

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
        if part.structural_depth not in get_args(Depth):
            raise InvalidPartFieldError(part.name_at_version, field="structural_depth", value=part.structural_depth)
        if part.artifact_scope is not None and part.artifact_scope not in get_args(ArtifactScope):
            raise InvalidPartFieldError(part.name_at_version, field="artifact_scope", value=part.artifact_scope)
        if not isinstance(part.kind, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", part.kind):
            raise InvalidPartFieldError(part.name_at_version, field="kind", value=part.kind)
        unknown = [effect for effect in part.effects if effect not in get_args(Effect)]
        if unknown:
            raise UnknownPartEffectError(part.name_at_version, unknown)
        for token in part.reads_namespaces:
            effect, _, namespace = token.partition(":")
            if (
                effect not in _READ_EFFECTS
                or effect not in part.effects
                or not re.fullmatch(r"[A-Za-z0-9-]+", namespace)
            ):
                raise InvalidReadNamespaceTokenError(part.name_at_version, token)
        if part.body is not None and part.kind == "opaque":
            if part.admission is None:
                raise UnadmittedOpaquePartError(part.name_at_version)
            validate_admission(part, part.admission)
        self._parts[part.name_at_version] = part

    def keys(self) -> list[str]:
        return list(self._parts.keys())


async def dispatch(part: Part, ctx: NodeContext) -> Any:
    """Invoke ``part.body(ctx)``, refusing a declaration-only Part (``body is None``)
    explicitly. ``databasise/runner/scheduler.py`` calls this for every node it runs, so the
    refusal applies to every dispatched node.
    """
    if part.body is None:
        raise DeclarationOnlyPartError(part.name_at_version)
    return await part.body(ctx)


def default_registry() -> PartRegistry:
    """A registry preloaded with the ``parts_core`` reference parts, the parts of
    ``parts_core/declared_only.py``, the ported LightRAG parts and the ported HippoRAG parts
    (index-side and query-side) — no tracer-only parts. Every opaque part is checked at load by
    ``admit_registry`` before the registry is returned. ``keys()`` on the result lists the
    contents; no count is stated here.
    """
    # Local import: parts_core imports Part/Effect from parts.schema (not this module), so
    # importing it here keeps the registry/parts_core dependency direction one-way and obvious
    # at the one call site that needs it, rather than at every import of this module.
    from databasise.parts_core import PARTS
    from databasise.parts_core.declared_only import DECLARED_ONLY_PARTS
    from databasise.parts_core.hipporag import HIPPORAG_CORPUS_PARTS, HIPPORAG_PARTS
    from databasise.parts_core.lightrag import LIGHTRAG_PARTS

    registry = PartRegistry(seed_tracer_parts=False)
    for part in (*PARTS, *DECLARED_ONLY_PARTS, *LIGHTRAG_PARTS, *HIPPORAG_PARTS, *HIPPORAG_CORPUS_PARTS):
        registry.register(part)
    # Local import, same reason as above; admission needs the full registry and the wirings, so it
    # runs after registration rather than inside ``register``.
    from databasise.parts.admission import admit_registry

    admit_registry(registry)
    return registry
