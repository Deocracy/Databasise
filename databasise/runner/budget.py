"""CONTRACT §9's budget, metered at each node's declared boundary and never as a process-wide gate.

**Share is report-only.** ``realised_budget_share`` (``realised_share()`` below) is spent over
allowance computed strictly *after* the fact. It is never an input to any allocation.

**Metering location.** ``meter()`` reads only the metered node's own declared ``effects`` and its
own ``TokenAccounting`` — never a dependency's. A node declaring one of the calling effects
(``calls_llm``/``calls_rerank``/``calls_embedding``) accrues its own spend; a node declaring none
of them accrues zero, even when it directly consumes an expensive node's output — the cost
belongs to the node that declared the boundary it crossed (CONTRACT §9).

**Budget halt is first-class, never discarded (CONTRACT §9).** ``meter()`` returns a
``BudgetToken`` whose ``state`` is ``"halted"`` rather than raising — the caller decides how a
halted node's outcome is reflected in the run record (``runner/trace.py``'s honesty invariant).

**No apportionment (D-17).** Each node carries its own integer allowance from its wiring
``config``; nothing splits one allowance across branches. CONTRACT §9 D4's merge-side
apportionment MUST is therefore vacuous while no node apportions a metered budget. The split and
apportion helpers that once lived here had no production caller and are deleted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from databasise.runner.trace import TokenAccounting

BudgetState = Literal["within_budget", "halted"]

# CONTRACT §9: only a node declaring one of these calling effects accrues LLM/rerank/embedding
# spend at all — the cost belongs to the node that declared the boundary it crossed.
_METERED_EFFECTS = frozenset({"calls_llm", "calls_rerank", "calls_embedding"})


@dataclass(frozen=True)
class BudgetToken:
    """One node's realised metering outcome at its own declared boundary."""

    node_id: str
    allowance: int
    spent: int
    state: BudgetState


def realised_share(spent: int, allowance: int) -> float:
    """``spent / allowance``, computed at report time only — never an allocation input. Returns
    ``0.0`` for a zero-allowance branch (nothing to spend, nothing realised) rather than dividing
    by zero, and is capped at ``1.0`` so an over-spend still reports a schema-legal ``[0, 1]``
    share (the halt itself is what ``meter()``'s ``state`` field carries).
    """
    if allowance <= 0:
        return 0.0
    return min(1.0, spent / allowance)


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
