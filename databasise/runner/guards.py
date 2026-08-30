"""Declared data guards (CONTRACT §19.8, D-10): a node MAY be data-guarded provided the wiring
declares the guard, its evaluating node, the socket value emitted when the guard does not fire,
and — mandatorily — its granularity as exactly one of ``per-query`` or ``per-instance``. The two
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

from dataclasses import dataclass
from typing import Any, Literal

GuardGranularity = Literal["per-query", "per-instance"]

_ADMISSIBLE_GRANULARITIES: tuple[GuardGranularity, ...] = ("per-query", "per-instance")


class GuardDeclarationError(ValueError):
    """A guard declaration is missing, or names, an inadmissible granularity — the two
    granularities are mandatory and mutually exclusive (CONTRACT §19.8).
    """

    def __init__(self, guard_name: str, granularity: Any):
        self.guard_name = guard_name
        self.granularity = granularity
        super().__init__(
            f"guard {guard_name!r} declares granularity {granularity!r}; must be exactly one of "
            f"{_ADMISSIBLE_GRANULARITIES!r}"
        )


@dataclass(frozen=True)
class GuardDeclaration:
    """One declared data guard: its name, the node whose runtime output it evaluates, the socket
    value emitted when it does NOT fire, and its mandatory granularity.
    """

    name: str
    evaluating_node: str
    value_when_not_fired: Any
    granularity: GuardGranularity


def declare_guard(
    name: str, evaluating_node: str, value_when_not_fired: Any, granularity: str
) -> GuardDeclaration:
    """Construct a :class:`GuardDeclaration`, refusing a granularity outside the two admissible
    values by name — a declaration missing its granularity is refused, not defaulted.
    """
    if granularity not in _ADMISSIBLE_GRANULARITIES:
        raise GuardDeclarationError(name, granularity)
    return GuardDeclaration(
        name=name,
        evaluating_node=evaluating_node,
        value_when_not_fired=value_when_not_fired,
        granularity=granularity,
    )


def evaluate_guards(guards: list[GuardDeclaration], runtime_values: dict[str, Any]) -> list[str]:
    """The names of every declared guard that fired this run, in declaration order — never
    absent; an empty list, not ``None``, when nothing fired. A guard fires when its evaluating
    node's actual runtime value (looked up in ``runtime_values`` by ``evaluating_node``) differs
    from the guard's own declared ``value_when_not_fired`` sentinel. This is the instrument
    CONTRACT §5's tenth refusal condition reads, via ``NodeTrace.guards_fired``.
    """
    return [
        guard.name
        for guard in guards
        if runtime_values.get(guard.evaluating_node) != guard.value_when_not_fired
    ]
