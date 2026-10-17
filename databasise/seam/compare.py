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

This module holds no import back into ``databasise.seam.engine``. ``Databasise.compare`` (in
``engine.py``) uses :func:`comparison_keys` to refuse every key problem before any arm runs, then
executes the wirings it resolved once (09-08-PLAN.md, SEAM-11); :func:`compare_arms` remains the
public keys-first fan-out helper over any ``execute(query_object, selector)`` callable.

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
from databasise.seam.refusals import (
    DuplicateComparisonKeyError,
    EmptyCapabilitySelectorError,
    EmptyComparisonRequestError,
)
from databasise.seam.selectors import Selector

# The separator joining a multi-capability selector's own requested values, in the caller's own
# supplied order, into one comparison-response key. Declared here as a module constant per this
# plan's own flagged assumption (see module docstring) rather than inline, so a later rendering
# change is one edit.
CAPABILITY_KEY_SEPARATOR = "+"

# D-10 (09-08-PLAN.md): the response-shape rule, stated word for word in the compare docstring, the REST
# route description and the MCP tool docstring (a test keeps the three equal to this).
COMPARE_RESPONSE_SHAPE_RULE = (
    "One selector returns a single envelope; two or more return a map keyed by each selector's "
    "rendered value (alias or harness string, capabilities joined with '+', or 'default'). A "
    "consumer tells them apart by the number of selectors it sent, never by inspecting keys, so "
    "a key named 'answer' cannot make a map look like an envelope. Keys are not prefixed. A key "
    "collision is refused before any arm runs."
)


def render_selector_key(selector: Selector) -> str:
    """The caller's own selector value, rendered deterministically from the ``Selector`` model —
    never normalised, case-folded, sorted or deduplicated. An ``alias``/``harness`` selector
    renders as its own string value unchanged. A ``capability`` selector renders as its requested
    capability set, joined in the caller's own supplied order by :data:`CAPABILITY_KEY_SEPARATOR`
    — a bare string request renders as itself (a one-element join); an empty list raises
    :class:`~databasise.seam.refusals.EmptyCapabilitySelectorError` (SEAM-10) so no empty key is
    ever rendered. A selector with none of the
    three members set (the default selector, legal per ``Selector``'s own model but never produced
    by any candidate this module resolves today) renders as the literal ``"default"`` rather than
    raising, since declaring the behaviour now is cheaper than discovering it undefined later.
    """
    if selector.alias is not None:
        return selector.alias
    if selector.harness is not None:
        return selector.harness
    if selector.capability is not None:
        if selector.capability == []:
            raise EmptyCapabilitySelectorError()
        values = selector.capability if isinstance(selector.capability, list) else [selector.capability]
        return CAPABILITY_KEY_SEPARATOR.join(values)
    return "default"


def comparison_keys(selectors: Sequence[Selector]) -> list[str]:
    """Every selector's rendered comparison key, in the caller's own order (SEAM-11, D-09). Pure:
    nothing is resolved or executed. Zero selectors refuse with
    :class:`~databasise.seam.refusals.EmptyComparisonRequestError`; the first key that repeats an
    earlier one raises :class:`~databasise.seam.refusals.DuplicateComparisonKeyError`, so a
    comparison that will refuse does so before any arm spends an LLM call or persists a trace.
    Keys compare exactly as rendered (``"X"`` and ``"x"`` are distinct).
    """
    if not selectors:
        raise EmptyComparisonRequestError()
    keys: list[str] = []
    for selector in selectors:
        key = render_selector_key(selector)
        if key in keys:
            raise DuplicateComparisonKeyError(key=key)
        keys.append(key)
    return keys


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
    keys = comparison_keys(selectors)
    return {key: await execute(query_object, selector) for key, selector in zip(keys, selectors)}


__all__ = ["CAPABILITY_KEY_SEPARATOR", "COMPARE_RESPONSE_SHAPE_RULE", "compare_arms", "comparison_keys", "render_selector_key"]
