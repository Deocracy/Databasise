"""Typed refusal exception hierarchy for the ``databasise.seam`` boundary (D-10/D-14), following
the house style already established by ``databasise.wirings.resolve.UnknownArmError`` and
``databasise.parity.run_arm``'s own named refusals: every refusal names exactly what was wrong in
its constructor and message, and stores the offending value on a named attribute, rather than
letting a bare ``ValueError``/``KeyError`` propagate.

**No seam refusal enumerates this machine's registered arms, wirings, or node ids.** Unlike
``UnknownArmError``'s ``"known arms: [...]"`` suffix, a seam refusal names only the consumer's own
input — enumerating the machine's own candidate set in a consumer-visible message is exactly the
identity disclosure §18.2 forbids. The selector refusals 04-03 adds to this module (an
unsatisfiable alias/capability/harness selector) depend on this same rule: name what the consumer
asked for, never what the machine has.
"""

from __future__ import annotations

from typing import Any


class SeamRefusalError(ValueError):
    """Base class for every typed refusal raised at the ``databasise.seam`` boundary."""


class EmptyQueryObjectError(SeamRefusalError):
    """Raised when a query object carries no set member at all (§18.1) — refused before any
    wiring is resolved, never silently answered as an empty-text query."""

    def __init__(self, query_object: Any):
        self.query_object = query_object
        super().__init__(f"query object carries no set member: {query_object!r}")


class UnconsumableQueryMemberError(SeamRefusalError):
    """Raised when a query object carries a set member no fitted modality can consume (D-14) —
    named explicitly, never silently dropped so the remainder answers from what is left."""

    def __init__(self, member_name: str):
        self.member_name = member_name
        super().__init__(f"query member {member_name!r} cannot be consumed")


__all__ = ["SeamRefusalError", "EmptyQueryObjectError", "UnconsumableQueryMemberError"]
