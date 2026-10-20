"""``execution_mode`` derivation and D-08's named hosting refusals — CONTRACT §3.

CONTRACT §3, quoted verbatim: "``execution_mode`` is derived from a node's declared
``effects[]``, never requested by the component"; "an arm is always its own confined process
regardless of ``execution_mode``; only pure, non-iterative nodes MAY be hosted in-process."

CONTRACT §3 requires the derivation but does not freeze an exact effect-to-placement table beyond
that one in-process eligibility rule, so the mapping below is this plan's own documented choice
(Claude's Discretion, 01-CONTEXT.md), written down so a later phase amends a stated rule rather
than reverse-engineering one from behaviour. This module is the only source of placement: the
runner calls :func:`derive_execution_mode` and no other copy exists:

    in-process          kind is neither ``fixpoint`` (iterative) nor ``opaque`` (unverified
                         internals), AND none of ``net``/``fs``/``self_storage``/``mutates_store``
                         is declared. Always hosted.
    long-lived-service   kind is ``fixpoint``, or the node declares ``net``. An iterative loop or
                         a network call is exactly the shape that wants a standing process rather
                         than a one-shot subprocess.
    subprocess           kind is ``opaque``, and neither of the two ``long-lived-service``
                         conditions applies. An opaque node's internals are unverified by
                         construction, so it is quarantined to its own OS process — the lightest
                         containment stronger than in-process.
    confined-unit        every other case reaching ``fs``/``self_storage``/``mutates_store``: a
                         store-boundary effect that must not share the runner's own process-wide
                         store handles, but is not iterative, networked, or opaque.

D-08: ``in-process`` is always hosted and ``subprocess`` is hosted when the node carries a declared
wall-clock ceiling: a node's own launch of an OS process under a foreign interpreter is the
containment, and the machine's own contribution is the ceiling §8 condition 4 requires. The
ceiling is the gate, so a subprocess node with no declared ceiling is refused by
:class:`~databasise.parts.admission.MissingWallClockCeilingError`, never silently hosted. The
derivation above is always computed and stamped on the run record regardless of whether ``host()``
would refuse it — a refusal never suppresses the stamp. ``confined-unit`` and
``long-lived-service`` have no hosting and are refused by name.

D-18: a node that calls a machine-owned LLM, embedding or rerank client (``calls_llm``,
``calls_embedding``, ``calls_rerank``, reached through ``ctx.clients``) is pure for placement and
derives ``in-process``, because the machine injects and meters the client (CONTRACT.md:72, 529,
599); only ``net``, ``fs``, ``self_storage`` and ``mutates_store`` move a node out of process.
"""

from __future__ import annotations

from databasise.parts.admission import MissingWallClockCeilingError

_NOT_IN_PROCESS_EFFECTS: frozenset[str] = frozenset(
    {"net", "fs", "self_storage", "mutates_store"}
)
_UNIMPLEMENTED_PLACEMENTS: frozenset[str] = frozenset(
    {"confined-unit", "long-lived-service"}
)
_ALL_PLACEMENTS: frozenset[str] = _UNIMPLEMENTED_PLACEMENTS | {"in-process", "subprocess"}


class UnimplementedPlacementError(RuntimeError):
    """A node's derived ``execution_mode`` placement has no hosting: ``confined-unit`` and
    ``long-lived-service`` are refused by name (D-08). ``in-process`` and a ceiling-bound
    ``subprocess`` are hosted. The derivation itself already succeeded before this error is
    raised — only hosting is unbuilt.
    """


def derive_execution_mode(effects: list[str], kind: str) -> str:
    """Pure function of declared ``effects`` and ``kind`` — never reads a self-declared placement
    field. Returns one of ``in-process``, ``subprocess``, ``confined-unit``, ``long-lived-service``
    (see the module docstring for the mapping).
    """
    effects_set = set(effects)

    if kind == "fixpoint" or "net" in effects_set:
        return "long-lived-service"
    if kind == "opaque":
        return "subprocess"
    if effects_set & _NOT_IN_PROCESS_EFFECTS:
        return "confined-unit"
    return "in-process"


def host(placement: str, *, wall_clock_ceiling_seconds: float | None = None) -> None:
    """Host a node at its derived ``placement``. ``in-process`` always succeeds. ``subprocess``
    succeeds only when ``wall_clock_ceiling_seconds`` is a positive number — the ceiling §8
    condition 4 requires — otherwise raises
    :class:`~databasise.parts.admission.MissingWallClockCeilingError`. Every other known placement
    raises ``UnimplementedPlacementError`` naming itself explicitly, per 01-PATTERNS.md's
    "explicit, actionable refusal messages naming the missing capability" rule — never a bare
    ``NotImplementedError``.
    """
    if placement == "in-process":
        return
    if placement == "subprocess":
        if wall_clock_ceiling_seconds is not None and wall_clock_ceiling_seconds > 0:
            return
        raise MissingWallClockCeilingError(wall_clock_ceiling_seconds)
    if placement in _UNIMPLEMENTED_PLACEMENTS:
        raise UnimplementedPlacementError(
            f"execution_mode={placement!r} is not hosted. The runner hosts in-process nodes and "
            "subprocess nodes that declare a wall-clock ceiling (D-08); this placement has no "
            "hosting. The derivation itself already succeeded and is stamped on the run "
            "record — only hosting is unbuilt."
        )
    raise ValueError(
        f"unknown execution_mode placement {placement!r}; expected one of "
        f"{sorted(_ALL_PLACEMENTS)}"
    )
