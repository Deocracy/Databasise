"""``databasise.seam.compare`` — API-08's fan-out over the seam's existing single-arm ``_execute()``
path (06-03-PLAN.md; D-05, §18.2/§18.3/§18.4).

**Pattern 4 (06-RESEARCH.md): a thin fan-out, never a second execution engine.**
:func:`compare_arms` awaits the identical bound ``Databasise._execute`` callable ``query()`` already
calls, once per caller-supplied selector, in the caller's own order. There is no second scheduler,
no second store-namespace-resolution path and no second envelope-assembly function here — every arm
goes through the one ``_execute()`` every single-arm call already proves clean against the leak
gate (``databasise/tests/seam/test_leak.py``), which is what makes the §4 ``provenance`` redaction
and the §18.2 closed-envelope rule apply to the comparison case by construction rather than by a
second copy of the rule (RIG.md ## §RUN.4's own anti-pattern warning, restated in 06-RESEARCH.md's
"Comparison as a thin fan-out" pattern).

This module holds no import back into ``databasise.seam.engine`` — ``Databasise.compare`` (in
``engine.py``) is the only caller, and it passes its own bound ``self._execute`` in rather than this
module reaching back into the engine module itself.

**Selector-key rendering (06-03-PLAN.md's own flagged assumption).** §18.4 names the four selectors
but never states how a multi-capability selector renders as a response key. The joined-in-
caller-order rendering here is this plan's own decision, declared as the module constant
:data:`CAPABILITY_KEY_SEPARATOR` so a later change is one edit rather than a search. The caller's
own selector value is never normalised, case-folded, sorted or deduplicated — two selectors
differing only in letter case render to two distinct keys and drive two separate runs.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.query import QueryObject
from databasise.seam.refusals import DuplicateComparisonKeyError
from databasise.seam.selectors import Selector

# The separator joining a multi-capability selector's own requested values, in the caller's own
# supplied order, into one comparison-response key. Declared here as a module constant per this
# plan's own flagged assumption (see module docstring) rather than inline, so a later rendering
# change is one edit.
CAPABILITY_KEY_SEPARATOR = "+"


def render_selector_key(selector: Selector) -> str:
    """The caller's own selector value, rendered deterministically from the ``Selector`` model —
    never normalised, case-folded, sorted or deduplicated. An ``alias``/``harness`` selector
    renders as its own string value unchanged. A ``capability`` selector renders as its requested
    capability set, joined in the caller's own supplied order by :data:`CAPABILITY_KEY_SEPARATOR`
    — a bare string request renders as itself (a one-element join). A selector with none of the
    three members set (the default selector, legal per ``Selector``'s own model but never produced
    by any candidate this module resolves today) renders as the literal ``"default"`` rather than
    raising, since declaring the behaviour now is cheaper than discovering it undefined later.
    """
    if selector.alias is not None:
        return selector.alias
    if selector.harness is not None:
        return selector.harness
    if selector.capability is not None:
        values = selector.capability if isinstance(selector.capability, list) else [selector.capability]
        return CAPABILITY_KEY_SEPARATOR.join(values)
    return "default"


async def compare_arms(
    execute: Callable[[QueryObject, Selector], Awaitable[ResponseEnvelope]],
    query_object: QueryObject,
    selectors: Sequence[Selector],
) -> dict[str, ResponseEnvelope]:
    """A pure async fan-out: awaits ``execute(query_object, selector)`` once per selector in
    ``selectors``, in the caller's own supplied order, and returns ``{selector_key: envelope}``.
    ``execute`` is the bound ``Databasise._execute`` callable — the identical path ``query()``
    already calls — so every arm receives the identical envelope assembly and redaction (see
    module docstring). Two selectors rendering to the same key refuse by name
    (:class:`~databasise.seam.refusals.DuplicateComparisonKeyError`) rather than silently
    collapsing into one entry. An exception raised by any arm (an unsatisfiable selector, most
    commonly) propagates immediately — the whole comparison refuses rather than returning a
    partial mapping with one arm silently missing, which is the one shape a consumer cannot
    distinguish from a modality that legitimately returned nothing.
    """
    results: dict[str, ResponseEnvelope] = {}
    for selector in selectors:
        key = render_selector_key(selector)
        if key in results:
            raise DuplicateComparisonKeyError(key=key)
        results[key] = await execute(query_object, selector)
    return results


__all__ = ["CAPABILITY_KEY_SEPARATOR", "compare_arms", "render_selector_key"]
