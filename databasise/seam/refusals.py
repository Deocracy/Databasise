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


class UnsatisfiableSelectorError(SeamRefusalError):
    """Raised when no fitted modality satisfies a §18.4 selector (D-10) — an alias absent from
    the registry, a capability set no candidate wiring's registered parts jointly declare, a
    harness name no candidate declares, or (for the default form) a candidate set with nothing
    eligible left after the opaque exclusion (§8 condition 7). Never answered by the nearest
    satisfiable wiring instead (a near-miss fallback is worse than a refusal — see this module's
    docstring), and the message below names only ``selector_kind``/``requested`` — the consumer's
    own input — never a candidate wiring id, arm name, or node id.
    """

    def __init__(self, *, selector_kind: str, requested: Any):
        self.selector_kind = selector_kind
        self.requested = requested
        super().__init__(
            f"no fitted modality satisfies the {selector_kind!r} selector: {requested!r}"
        )


class ForbiddenSelectorInputError(SeamRefusalError):
    """Raised at ``Selector`` model validation (before any resolution runs) when a legal member's
    value has the shape of an internal identity — an instance hash — rather than a consumer-facing
    alias/capability/harness name. ``extra="forbid"`` already refuses a selector naming a wiring
    id, arm name, or node position as its own key (04-01); this refusal covers the narrower case
    of an internal identity smuggled in as the *value* of an otherwise-legal member.
    """

    def __init__(self, *, member_name: str, value: str):
        self.member_name = member_name
        self.value = value
        super().__init__(
            f"selector member {member_name!r} carries a value shaped like an internal identity: "
            f"{value!r}"
        )


class AmbiguousIngestPayloadError(SeamRefusalError):
    """Raised at ``IngestDocument`` validation when both ``text`` and ``raw`` are set, or when
    neither is — ``set_members`` names which of the two mutually-exclusive members were actually
    set (empty for "neither")."""

    def __init__(self, *, set_members: list[str]):
        self.set_members = list(set_members)
        # The literal "AmbiguousIngestPayload" substring is load-bearing: pydantic's
        # model_validator wraps this exception into a pydantic.ValidationError at the
        # IngestDocument construction call site (losing the original exception object), so a
        # caller distinguishing this refusal from another by inspecting the wrapped error's own
        # message needs the refusal's own name to survive in that message text.
        super().__init__(
            "AmbiguousIngestPayloadError: an ingest document must set exactly one of "
            f"'text'/'raw'; got {self.set_members!r} set"
        )


class OversizedDocumentError(SeamRefusalError):
    """Raised at ``IngestDocument`` validation when a ``raw`` payload (or a ``text`` payload's
    UTF-8 encoding) exceeds ``databasise.seam.corpus.MAX_DOCUMENT_BYTES`` — before any bytes are
    written to disk and before the subprocess is launched."""

    def __init__(self, *, actual_bytes: int, limit_bytes: int):
        self.actual_bytes = actual_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"ingest document is {actual_bytes} bytes, exceeding the {limit_bytes}-byte cap"
        )


class UnknownDocumentError(SeamRefusalError):
    """Raised by ``Databasise.delete_document()`` (05-03-PLAN.md Task 2) when ``document_id``
    fails the machine's own token discipline — the same bare-token rule
    ``databasise.seam.corpus.generated_on_disk_name`` already enforces for a raw-upload's on-disk
    name. Never raised for an id that is well-formed but simply does not exist in the corpus — v1
    itself reports that case as a normal ``"not_found"`` status carried in
    ``databasise.seam.corpus.DeletionOutcome.status``, not a refusal.
    """

    def __init__(self, *, document_id: str):
        self.document_id = document_id
        super().__init__(
            f"document id {document_id!r} fails the machine's own token discipline"
        )


class ForeignEngineRefusalError(SeamRefusalError):
    """The seam-facing wrapper for a foreign-engine subprocess failure
    (``databasise.foreign.CorpusOpSubprocessError``/``CorpusOpTimeoutError``) — so
    ``rest.py``'s existing generic ``SeamRefusalError`` handler maps it without a new
    endpoint-level branch. ``operation`` names the seam operation that was attempted (e.g.
    ``"ingest"``); ``cause`` carries the underlying foreign-engine exception. The message never
    enumerates this machine's own wirings, arms or node ids, per this module's own docstring rule.
    """

    def __init__(self, *, operation: str, cause: BaseException):
        self.operation = operation
        self.cause = cause
        super().__init__(f"the foreign engine refused operation {operation!r}: {cause}")


__all__ = [
    "SeamRefusalError",
    "EmptyQueryObjectError",
    "UnconsumableQueryMemberError",
    "UnsatisfiableSelectorError",
    "ForbiddenSelectorInputError",
    "AmbiguousIngestPayloadError",
    "OversizedDocumentError",
    "UnknownDocumentError",
    "ForeignEngineRefusalError",
]
