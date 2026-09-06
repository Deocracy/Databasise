"""``databasise.seam.tokens`` — API-11's ``counted_by``-tagged token breakdown (D-08,
04-RESEARCH.md Pitfall 5) and the ``unbudgetable`` participant's explicit refusal (§8, §9), 04-02's
Task 3 deliverable.

**Never a single merged scalar (Pitfall 5).** Per-node ``TokenAccounting.counted_by`` values
legitimately disagree within one run — a real LLM call sets it to a resolved model identity or a
provider tokenizer id, a pinned-replay node sets it to ``"pinned-replay"``, and a node with no
tokenizer involvement defaults to ``"none"``. §4 forbids treating differently-counted token numbers
as comparable; summing them into one envelope-level total under one ``counted_by`` commits that
same conflation one level down. This module's breakdown is a list with one entry per distinct
``counted_by`` value a run's nodes actually reported, each entry's counts summed only within its
own group.

**The ``unbudgetable`` sentinel (this module's own convention).** §8's opaque-node admission
vocabulary marks a participant ``unbudgetable`` when its own token spend cannot be counted
(CONTRACT.md §4/§8) — no dedicated field exists on ``TokenAccounting`` for this label, since no
opaque node is registered anywhere in this milestone's parts registry. This module detects it
through the same ``counted_by`` string field every node already uses to report its own tokenizer
identity, reserving the literal value ``"unbudgetable"`` as a sentinel a node's own body sets to
mean "this participant's tokens cannot be counted" — distinct from ``"none"`` (a real, honestly
reported zero: no tokenizer counted anything because no LLM call happened at all).  The two are
never conflated: ``"none"`` flows into the breakdown as an ordinary zero-count entry, while
``"unbudgetable"`` short-circuits the whole breakdown into a refusal before any envelope is
produced — spend is never conflated with an admission label (D-08, §9).
"""

from __future__ import annotations

from databasise.runner.trace import NodeTrace
from databasise.seam._base import _StrictModel
from databasise.seam.refusals import SeamRefusalError

# See module docstring: a node's own body sets counted_by to this literal value to report that its
# tokens cannot be counted at all — never inferred from a zero count, which is a different, real
# fact ("none" — no tokenizer counted anything because there was no call to count).
UNBUDGETABLE_SENTINEL = "unbudgetable"


class TokenBreakdownEntry(_StrictModel):
    """One breakdown entry per distinct ``counted_by`` value a run's nodes actually reported —
    never a single merged scalar (Pitfall 5). No field on this model names an allowance, a budget
    share, or a capacity: those describe what a branch was handed, not what it spent, and §9 keeps
    the two separate (T-04-09's mitigation)."""

    counted_by: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_read_tokens: int = 0
    call_count: int = 0


class UnbudgetableParticipantError(SeamRefusalError):
    """Raised when a run contains a node whose own ``TokenAccounting.counted_by`` reports the
    ``unbudgetable`` sentinel (§8 opaque-node admission). No envelope is produced on this path, and
    no token number is substituted or estimated in its place (D-08, T-04-10's mitigation — a
    plausible-looking fabricated count is worse than a refusal because it reads as measured)."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        super().__init__(
            f"node {node_id!r} is admitted unbudgetable; no token comparison may include it"
        )


def assemble_token_breakdown(nodes: list[NodeTrace]) -> list[TokenBreakdownEntry]:
    """Group ``nodes`` by their own ``TokenAccounting.counted_by`` value, copied verbatim, summing
    counts only within a group. Returns entries sorted by ``counted_by`` — deterministic across two
    assemblies of the same run, never dependent on dict/node iteration order. Raises
    :class:`UnbudgetableParticipantError` — before constructing any entry — if any node reports the
    ``unbudgetable`` sentinel; a real zero (``counted_by="none"``) is never confused with it.
    """
    for node in nodes:
        if node.tokens.counted_by == UNBUDGETABLE_SENTINEL:
            raise UnbudgetableParticipantError(node.node_id)

    totals: dict[str, dict[str, int]] = {}
    for node in nodes:
        counted_by = node.tokens.counted_by
        bucket = totals.setdefault(
            counted_by,
            {"prompt_tokens": 0, "completion_tokens": 0, "cached_read_tokens": 0, "call_count": 0},
        )
        bucket["prompt_tokens"] += node.tokens.prompt_tokens
        bucket["completion_tokens"] += node.tokens.completion_tokens
        bucket["cached_read_tokens"] += node.tokens.cached_read_tokens
        bucket["call_count"] += node.tokens.call_count

    return [TokenBreakdownEntry(counted_by=key, **totals[key]) for key in sorted(totals)]


__all__ = [
    "UNBUDGETABLE_SENTINEL",
    "TokenBreakdownEntry",
    "UnbudgetableParticipantError",
    "assemble_token_breakdown",
]
