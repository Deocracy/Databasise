"""CONTRACT §9's budget as a splittable capability token, metered at each node's declared
boundary and never as a process-wide gate.

**Split arithmetic (Claude's Discretion within §9's multiplicative rule): a floor-division split.**
A fan-out of width N over an integer allowance A allocates ``A // N`` (floor division) to each
branch, and the remainder ``A % N`` is assigned to the lexicographically-first branch id, so the
allocations always sum to exactly A — no float arithmetic anywhere in the allocation path. This is
the stated tie-break; a split that does not state its tie-break is a split whose result depends on
dict iteration order.

**Share is report-only.** ``realised_budget_share`` (``realised_share()`` below) is spent over
allowance computed strictly *after* the fact. It is never fed back into ``split_allowance()`` or
``apportion()`` — keeping the ratio out of the allocation path is what keeps every allocation
exact, with no compounding rounding error across a nested split.

**Metering location.** ``meter()`` reads only the metered node's own declared ``effects`` and its
own ``TokenAccounting`` — never a dependency's. A node declaring one of the calling effects
(``calls_llm``/``calls_rerank``/``calls_embedding``) accrues its own spend; a node declaring none
of them accrues zero, even when it directly consumes an expensive node's output — the cost
belongs to the node that declared the boundary it crossed (CONTRACT §9).

**Merge-side apportionment (§9's D4 repair).** ``ApportionmentPolicy`` is declared at the
apportioning node — never the spending node — and is carried as an ordinary field inside that
node's own wiring ``config`` object (``config.apportionment_policy``), so ``identity.canon.
config_hash`` already covers it as part of that node's own config, verbatim, with no separate
identity mechanism minted here.

**Budget halt is first-class, never discarded (CONTRACT §9).** ``meter()`` returns a
``BudgetToken`` whose ``state`` is ``"halted"`` rather than raising — the caller decides how a
halted node's outcome is reflected in the run record (``runner/trace.py``'s honesty invariant).
``BudgetHalted`` is provided as an exception a caller MAY raise from that state where a hard stop
is what it wants, but ``meter()`` itself never raises for an over-budget spend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from databasise.runner.trace import TokenAccounting

BudgetState = Literal["within_budget", "halted", "degraded"]

# CONTRACT §9: only a node declaring one of these calling effects accrues LLM/rerank/embedding
# spend at all — the cost belongs to the node that declared the boundary it crossed.
_METERED_EFFECTS = frozenset({"calls_llm", "calls_rerank", "calls_embedding"})


class BudgetHalted(RuntimeError):
    """A node's realised spend exceeded its allowance. Not raised by ``meter()`` itself — meter()
    returns a ``BudgetToken`` with ``state="halted"`` instead, since a budget halt is a first-class
    traced outcome, not an error (CONTRACT §9). Available for a caller that wants to turn that
    state into a hard stop.
    """

    def __init__(self, node_id: str, allowance: int, spent: int):
        self.node_id = node_id
        self.allowance = allowance
        self.spent = spent
        super().__init__(f"node {node_id!r} spent {spent} tokens against an allowance of {allowance}")


@dataclass(frozen=True)
class Allowance:
    """An integer token allowance — CONTRACT §9's splittable capability token."""

    tokens: int

    def __post_init__(self) -> None:
        if self.tokens < 0:
            raise ValueError(f"allowance must be >= 0, got {self.tokens}")


@dataclass(frozen=True)
class BudgetToken:
    """One node's realised metering outcome at its own declared boundary."""

    node_id: str
    allowance: int
    spent: int
    state: BudgetState


@dataclass(frozen=True)
class ApportionmentPolicy:
    """Declared at the apportioning node — never the spending node (CONTRACT §9's D4 repair).
    Carried as an ordinary field inside that node's own wiring ``config``, so ``config_hash``
    already covers it without a separate identity mechanism.
    """

    apportioning_node: str
    branch_ids: tuple[str, ...]


def split_allowance(allowance: int, branch_ids: list[str]) -> dict[str, int]:
    """Floor-division split with the remainder assigned to the lexicographically-first branch id.
    Every returned value is an ``int``; the returned allocations always sum to exactly
    ``allowance``, with no float arithmetic anywhere in the path.
    """
    if not branch_ids:
        raise ValueError("split_allowance requires at least one branch id")
    width = len(branch_ids)
    base, remainder = divmod(allowance, width)
    allocations = dict.fromkeys(branch_ids, base)
    if remainder:
        allocations[min(branch_ids)] += remainder
    return allocations


def realised_share(spent: int, allowance: int) -> float:
    """``spent / allowance``, computed at report time only — never an allocation input. Returns
    ``0.0`` for a zero-allowance branch (nothing to spend, nothing realised) rather than dividing
    by zero, and is capped at ``1.0`` so an over-spend still reports a schema-legal ``[0, 1]``
    share (the halt itself is what ``meter()``'s ``state`` field carries).
    """
    if allowance <= 0:
        return 0.0
    return min(1.0, spent / allowance)


def apportion(policy: ApportionmentPolicy, spends: dict[str, int], allowance: int) -> dict[str, float]:
    """Each contributing branch's realised share of ``allowance``, per the apportioning node's own
    declared ``policy`` — the run-record stamp CONTRACT §9's D4 repair requires.
    """
    return {branch_id: realised_share(spends.get(branch_id, 0), allowance) for branch_id in policy.branch_ids}


def meter(node_id: str, effects: list[str], allowance: int, tokens: TokenAccounting) -> BudgetToken:
    """Meter spend at ``node_id``'s own declared boundary. A node declaring none of
    ``calls_llm``/``calls_rerank``/``calls_embedding`` accrues zero spend regardless of what its
    ``tokens`` object carries — the declared effect is what turns a boundary into a billable one,
    not the mere presence of a nonzero token count.
    """
    if _METERED_EFFECTS & set(effects):
        spent = tokens.prompt_tokens + tokens.completion_tokens
    else:
        spent = 0
    state: BudgetState = "within_budget" if spent <= allowance else "halted"
    return BudgetToken(node_id=node_id, allowance=allowance, spent=spent, state=state)
