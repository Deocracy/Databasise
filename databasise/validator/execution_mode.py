"""``execution_mode`` derivation and D-08's named hosting refusals — CONTRACT §3.

CONTRACT §3, quoted verbatim: "``execution_mode`` is derived from a node's declared
``effects[]``, never requested by the component"; "an arm is always its own confined process
regardless of ``execution_mode``; only pure, non-iterative nodes MAY be hosted in-process."

CONTRACT §3 requires the derivation but does not freeze an exact effect-to-placement table beyond
that one in-process eligibility rule, so the mapping below is this plan's own documented choice
(Claude's Discretion, 01-CONTEXT.md), written down so a later phase amends a stated rule rather
than reverse-engineering one from behaviour:

    in-process          kind is neither ``fixpoint`` (iterative) nor ``opaque`` (unverified
                         internals), AND none of ``net``/``fs``/``self_storage``/``mutates_store``
                         is declared. The only placement this phase actually hosts (D-08).
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

D-08: Phase 1 hosts ``in-process`` only. ``host()`` refuses the other three placements by name;
the derivation above is always computed and stamped on the run record regardless of whether
``host()`` would refuse it — a refusal never suppresses the stamp.
"""

from __future__ import annotations

_NOT_IN_PROCESS_EFFECTS: frozenset[str] = frozenset(
    {"net", "fs", "self_storage", "mutates_store"}
)
_UNIMPLEMENTED_PLACEMENTS: frozenset[str] = frozenset(
    {"subprocess", "confined-unit", "long-lived-service"}
)
_ALL_PLACEMENTS: frozenset[str] = _UNIMPLEMENTED_PLACEMENTS | {"in-process"}


class UnimplementedPlacementError(RuntimeError):
    """A node's derived ``execution_mode`` placement has no hosting yet. Phase 1 implements
    ``in-process`` hosting only (D-08); ``subprocess``/``confined-unit``/``long-lived-service``
    are refused by name until Phase 5's real opaque-node admission forces the hosting to be built.
    The derivation itself already succeeded before this error is raised — only hosting is unbuilt.
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


def host(placement: str) -> None:
    """Host a node at its derived ``placement``. Phase 1 implements ``in-process`` only (D-08):
    every other known placement raises ``UnimplementedPlacementError`` naming itself explicitly,
    per 01-PATTERNS.md's "explicit, actionable refusal messages naming the missing capability"
    rule — never a bare ``NotImplementedError``.
    """
    if placement == "in-process":
        return
    if placement in _UNIMPLEMENTED_PLACEMENTS:
        raise UnimplementedPlacementError(
            f"execution_mode={placement!r} is not yet hosted. Phase 1's runner implements "
            "in-process hosting only (D-08); real opaque-node admission in Phase 5 is what "
            "earns this placement's hosting. The derivation itself already succeeded and is "
            "stamped on the run record — only hosting is unbuilt."
        )
    raise ValueError(
        f"unknown execution_mode placement {placement!r}; expected one of "
        f"{sorted(_ALL_PLACEMENTS)}"
    )
