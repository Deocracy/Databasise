"""D-04's fixpoint reference part: wraps a sub-DAG in its own bounded loop, the EXECUTOR owning
the halt condition per CONTRACT §2 ("Iterative components MUST be hosted as fixpoint nodes; the
executor, not the component, owns every loop and its halt condition"). It carries a declared
maximum round count and reports which of the two termination reasons applied — the halt
condition being met, or the round bound being hit first, so a condition that never becomes true
halts at the bound rather than looping forever.

Its ``kind`` is ``"fixpoint"``, so ``validator.depth.derive_execution_mode`` derives
``"subprocess"`` for it rather than ``"in-process"`` — this part is therefore also the concrete
case exercising D-08's named refusal path from the part side (Phase 1's runner implements
in-process only; subprocess hosting is an explicit, unimplemented refusal until a later phase).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_DEFAULT_MAX_ROUNDS = 10


async def _fixpoint_body(ctx: NodeContext) -> dict[str, Any]:
    """Loop until ``halt_at`` rounds have run or ``max_rounds`` is reached, whichever first.
    ``halt_at=None`` (a halt condition that never becomes true) exercises the round bound itself.
    """
    config = ctx.config or {}
    halt_at = config.get("halt_at")
    max_rounds = int(config.get("max_rounds", _DEFAULT_MAX_ROUNDS))

    rounds_run = 0
    halted_on = "max_rounds_reached"
    while rounds_run < max_rounds:
        rounds_run += 1
        if halt_at is not None and rounds_run >= halt_at:
            halted_on = "halt_condition_met"
            break

    return {"rounds_run": rounds_run, "halted_on": halted_on}


FIXPOINT_BODY_PART = Part(
    name_at_version="parts-core/fixpoint-body@1.0.0",
    kind="fixpoint",
    structural_depth="stage",
    effects=[],
    upstream_ref=None,
    body=_fixpoint_body,
)
