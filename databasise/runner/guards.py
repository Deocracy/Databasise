"""Declared data guards (CONTRACT §19.8, D-10): a node MAY be data-guarded provided the wiring
declares the guard, its evaluating node, the socket value emitted when the guard does not fire,
the ``signal`` (the boolean key of the evaluating node's output mapping that carries the guard's
state, WIRE-08, D-19) and — mandatorily — its granularity as exactly one of ``per-query`` or ``per-instance``. The two
granularities are not interchangeable and neither subsumes the other: a per-instance guard's
firing is knowable at wire time from the resolved config alone (an ordinary ``config_hash``
mismatch is what a divergence there already is, per CONTRACT §1), while a per-query guard's
firing is knowable only from the run record after the query executes — exactly what CONTRACT
§5's tenth refusal condition (arms differing in which guards fired) reads.

A guard declaration is carried as an ordinary field on the guarded node's own wiring ``config``
(``config.guards``), so ``identity.canon.config_hash`` already covers it — two wirings differing
only in a guard are two identities, never one identity carrying two behaviours. This module mints
no separate identity mechanism for that; it only supplies the declaration shape and the
run-record-facing firing evaluation.

**Scope fence.** This module supplies the declaration and firing-evaluation instruments only; it
does not implement CONTRACT §5's refusal conditions themselves — Phase 1 supplies the
instruments, Phase 2's gate reads them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

GuardGranularity = Literal["per-query", "per-instance"]

_ADMISSIBLE_GRANULARITIES: tuple[GuardGranularity, ...] = ("per-query", "per-instance")


class GuardDeclarationError(ValueError):
    """A guard declaration is refused before dispatch: an inadmissible granularity (the two
    granularities are mandatory and mutually exclusive, CONTRACT §19.8), an entry that is not a
    mapping with exactly the ``declare_guard`` keys, a ``config.guards`` that is not a list, a
    non-string ``name`` or ``evaluating_node``, a missing or non-string ``signal``, an
    ``evaluating_node`` that is neither the guarded node nor one of its transitive dependencies, or
    (at evaluation) an evaluating node whose output is not a mapping carrying the signal key
    (WIRE-08, D-19). ``node_id`` names the
    guarded node once the scheduler knows it; it is private to the machine (the seam refusal that
    wraps this error never exposes it). ``problem`` replaces the granularity message for the
    non-granularity cases.
    """

    def __init__(
        self, guard_name: str, granularity: Any, *, node_id: str | None = None, problem: str | None = None
    ):
        self.guard_name = guard_name
        self.granularity = granularity
        self.node_id = node_id
        super().__init__(
            problem
            or f"guard {guard_name!r} declares granularity {granularity!r}; must be exactly one of "
            f"{_ADMISSIBLE_GRANULARITIES!r}"
        )


@dataclass(frozen=True)
class GuardDeclaration:
    """One declared data guard: its name, the node whose runtime output it evaluates, the socket
    value emitted when it does NOT fire, its mandatory granularity, and the ``signal`` key of that
    node's output mapping whose value is compared with ``value_when_not_fired``.
    """

    name: str
    evaluating_node: str
    value_when_not_fired: Any
    granularity: GuardGranularity
    signal: str


def declare_guard(
    name: str,
    evaluating_node: str,
    value_when_not_fired: Any,
    granularity: str,
    signal: str | None = None,
) -> GuardDeclaration:
    """Construct a :class:`GuardDeclaration`, refusing a granularity outside the two admissible
    values by name — a declaration missing its granularity is refused, not defaulted. ``signal`` is
    defaulted only so a four-keyword call reaches its granularity check first (the granularity is
    validated before the signal); a missing or non-string signal is then refused too (D-19).
    """
    if granularity not in _ADMISSIBLE_GRANULARITIES:
        raise GuardDeclarationError(name, granularity)
    # 13 REVIEW B-WR-02: after the granularity check, so a four-keyword call still reaches it first.
    if not isinstance(name, str) or not isinstance(evaluating_node, str):
        raise GuardDeclarationError(
            str(name), granularity, problem=f"guard {name!r} must declare string name and evaluating_node"
        )
    if not isinstance(signal, str) or not signal:
        raise GuardDeclarationError(
            name, granularity, problem=f"guard {name!r} must declare a non-empty string signal key"
        )
    return GuardDeclaration(
        name=name,
        evaluating_node=evaluating_node,
        value_when_not_fired=value_when_not_fired,
        granularity=granularity,
        signal=signal,
    )


def evaluate_guards(guards: list[GuardDeclaration], runtime_values: dict[str, Any]) -> list[str]:
    """The names of every declared guard that fired this run, in declaration order — never
    absent; an empty list, not ``None``, when nothing fired. A guard fires when the declared
    ``signal`` key of its evaluating node's output mapping (looked up in ``runtime_values`` by
    ``evaluating_node``) differs from the guard's own declared ``value_when_not_fired`` sentinel.
    An evaluating node with no output, a non-mapping output or no such key raises
    :class:`GuardDeclarationError` (``node_id`` = the evaluating node) and never counts as a fire
    (D-19). This is the instrument CONTRACT §5's tenth refusal condition reads, via
    ``NodeTrace.guards_fired``.
    """
    fired: list[str] = []
    for guard in guards:
        output = runtime_values.get(guard.evaluating_node)
        if not isinstance(output, Mapping) or guard.signal not in output:
            raise GuardDeclarationError(
                guard.name,
                guard.granularity,
                node_id=guard.evaluating_node,
                problem=f"guard {guard.name!r}: node {guard.evaluating_node!r} emitted no "
                f"{guard.signal!r} signal",
            )
        if output[guard.signal] != guard.value_when_not_fired:
            fired.append(guard.name)
    return fired
