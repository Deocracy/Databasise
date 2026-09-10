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


class NoWritePathForModalityError(SeamRefusalError):
    """Raised by ``Databasise.ingest()``/``Databasise.delete_document()`` (06-10-PLAN.md) when the
    caller's own selector resolves to a fitted modality that ships no
    ``databasise/wirings/<family>/corpus-<operation>.json`` file for the requested write operation.
    A write silently landing in a different modality's index than the caller selected is
    undetectable from the return value — this refusal exists precisely because that failure mode is
    worse than an explicit "no write path" error: refusing by name lets the caller know immediately,
    where a silent fallback would only surface later, as data that looks present but was actually
    routed somewhere the caller never asked for.

    Names only ``operation`` — never the resolved modality, wiring id, arm name, or node id —
    per this module's own no-enumeration house style (§18.2's closed set applied to this refusal).
    The literal ``NoWritePathForModalityError`` substring is load-bearing for the same reason
    ``AmbiguousIngestPayloadError``'s own docstring documents: a caller distinguishing this refusal
    from another by inspecting a wrapped error's own message needs the refusal's own name to
    survive in that message text.
    """

    def __init__(self, *, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"NoWritePathForModalityError: no write path exists for operation {operation!r}"
        )


class UnknownJobError(SeamRefusalError):
    """Raised by ``Databasise.get_job_status()`` (05-04-PLAN.md Task 1) when the foreign driver
    reports zero documents for the given job id — the raise-not-None behaviour
    ``databasise.seam.trace_store.TraceStore.resolve`` already established for an unknown trace
    reference, applied here to an unknown ingest job. Never raised for a job that genuinely has no
    documents on its *current page* (a caller-requested offset past the end of a real job) — only
    for a job id v1's own doc-status store reports no matching documents for at all.
    """

    def __init__(self, *, job_id: str):
        self.job_id = job_id
        super().__init__(f"job id {job_id!r} does not resolve to any known ingest job")


class PageSizeExceededError(SeamRefusalError):
    """Raised by ``databasise.seam.corpus.Page`` validation (05-04-PLAN.md Task 1) when
    ``limit`` exceeds ``databasise.seam.corpus.MAX_PAGE_SIZE`` — refused, never silently clamped
    down to the cap, per this codebase's refusals-over-silent-narrowing house style."""

    def __init__(self, *, requested: int, limit: int):
        self.requested = requested
        self.limit = limit
        # The literal "PageSizeExceededError" substring is load-bearing, mirroring
        # AmbiguousIngestPayloadError's own documented reason: pydantic's model_validator wraps
        # this exception into a pydantic.ValidationError at the Page construction call site
        # (losing the original exception object), so a caller distinguishing this refusal from
        # another by inspecting the wrapped error's own message needs the refusal's own name to
        # survive in that message text.
        super().__init__(
            f"PageSizeExceededError: requested page size {requested} exceeds the {limit}-entry cap"
        )


class MalformedBase64PayloadError(SeamRefusalError):
    """Raised by ``databasise.mcp.tools.IngestToolArgs.to_ingest_document()`` when ``field`` is
    not decodable in its declared base64 encoding — ``binascii.Error`` never escapes the tool body
    unnamed. ``field`` names the caller's own input slot only, per this module's own house style;
    it never carries the rejected payload's content or value, since a rejected payload may be
    arbitrarily large or hostile. Unlike ``PageSizeExceededError``/``AmbiguousIngestPayloadError``,
    this refusal is raised directly rather than inside a pydantic validator, so its own exception
    object is never lost to a wrapped ``pydantic.ValidationError`` — the class name is therefore
    not embedded in the message text (that convention exists only for the validator-raised pair).
    Lives in the seam rather than in the MCP transport for two reasons: the seam owns the refusal
    vocabulary both transports map generically (the same relationship ``rest.py``'s own
    ``_checked_page`` already has with ``PageSizeExceededError``), and a refusal defined inside
    ``databasise/mcp/`` would only be discovered by ``test_rest_transport.py``'s transitive
    ``SeamRefusalError`` subclass walk in runs where the ``mcp`` extra happens to be installed,
    making that parametrized proof depend on which extras were active.
    """

    def __init__(self, *, field: str):
        self.field = field
        super().__init__(f"field {field!r} is not decodable in its declared base64 encoding")


class EmptyComparisonRequestError(SeamRefusalError):
    """Raised by ``Databasise.compare()`` (06-03-PLAN.md, API-08) when zero selectors are
    supplied — a comparison needs at least one arm to compare (or run, at exactly one; a
    single-selector request never reaches this refusal, since RIG §RUN.3's degenerate-width rule
    means it is answered as a run instead). Names only the fact that the input was empty, never a
    candidate wiring — §18.2's closed-set rule applied to this refusal path. The literal class-name
    substring is load-bearing for the same reason ``AmbiguousIngestPayloadError``'s own docstring
    documents: this refusal is raised directly inside ``Databasise.compare()``, never inside a
    pydantic validator, so it is not itself at risk of the wrapping this note otherwise warns
    about — the substring is kept anyway for a uniform "name your own type in your own message"
    house style across every refusal in this module.
    """

    def __init__(self) -> None:
        super().__init__(
            "EmptyComparisonRequestError: a comparison request must supply at least one selector"
        )


class DuplicateComparisonKeyError(SeamRefusalError):
    """Raised by ``databasise.seam.compare.compare_arms()`` (06-03-PLAN.md) when two supplied
    selectors render to the same comparison-response key — refused by name rather than silently
    collapsed into one entry. A partial mapping with a silently-absent arm is the one shape a
    consumer cannot distinguish from a modality that legitimately returned nothing, so a key
    collision refuses the whole comparison instead. Names only the colliding key value, never a
    candidate wiring or selector's own internal resolution.
    """

    def __init__(self, *, key: str) -> None:
        self.key = key
        super().__init__(
            f"DuplicateComparisonKeyError: two selectors both render to comparison key {key!r}"
        )


class MutableStoreComparisonExcludedError(SeamRefusalError):
    """Raised by ``Databasise.compare()`` (06-09-PLAN.md, MACH-10/F-07) when a comparison's
    selectors resolve to a wiring whose parts declare ``mutates_store``. `CONTRACT.md §14.4`
    point 3 requires this exclusion to be an explicit refusal, never a silent skip or a filter
    that quietly drops the arm: a node that mutates its own backing store is not safely
    re-runnable for a `§5` parity/determinism comparison without a defined snapshot/reset
    protocol, and this project's own recorded decision
    (``databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md``) is permanent exclusion rather than
    building one. Names only the excluded component's own ``name@version`` — never another
    candidate wiring, arm name, or node id — per `§18.2`'s closed-set rule applied to this refusal
    path, the same discipline every other refusal in this module already follows.

    Checked in the comparison path only (two or more selectors); a single-selector call is a run
    under RIG `§RUN.3`'s degenerate-width rule, and `§14.4` point 3 excludes the component from
    `§5`'s parity/determinism *comparisons*, not from being run — ``query()`` and the one-selector
    ``compare()`` path never raise this.
    """

    def __init__(self, *, component: str) -> None:
        self.component = component
        super().__init__(
            "MutableStoreComparisonExcludedError: component "
            f"{component!r} declares mutates_store and is excluded from §5 parity/determinism "
            "comparisons per the recorded disposition in "
            "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md"
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
    "NoWritePathForModalityError",
    "UnknownJobError",
    "PageSizeExceededError",
    "MalformedBase64PayloadError",
    "EmptyComparisonRequestError",
    "DuplicateComparisonKeyError",
    "MutableStoreComparisonExcludedError",
    "ForeignEngineRefusalError",
]
