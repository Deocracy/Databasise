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

**``__all__`` is the refusal catalogue (SEAM-14).** It lists every refusal type either transport
can return; each is defined in this module (``tests/seam/test_refusal_catalogue.py`` walks
``SeamRefusalError.__subclasses__()`` to prove it). ``refusal_body`` and ``refusal_from_errors``
are helpers and deliberately not in it. A refusal added later goes into ``__all__`` and gets a
factory in ``tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel


class SeamRefusalError(ValueError):
    """Base class for every typed refusal raised at the ``databasise.seam`` boundary. The engine sets
    a public ``trace_token`` attribute on a query refusal raised after the nodes ran (Phase 13 D-04),
    so the consumer can resolve the run that ended in it; a pre-dispatch refusal carries none."""


def _finite(value: Any) -> Any:
    """``value`` with every non-finite float (NaN, +/-inf) replaced by ``None``, recursively through
    dicts, lists and tuples. A refusal body must be strict JSON on both transports."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _finite(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_finite(item) for item in value]
    return value


def refusal_body(exc: SeamRefusalError) -> dict[str, Any]:
    """The one refusal body both transports return (09-01-PLAN.md, SEAM-02/D-01): the refusal's
    class name, its message, and every public attribute off ``vars(exc)``. A leading-underscore
    attribute is never exposed (CR-03: ``UnbudgetableParticipantError._internal_node_id`` is the
    machine's own node id; ``ForeignEngineRefusalError._cause`` is the foreign engine's stderr).
    A ``BaseModel`` value is dumped. A non-finite float in any value becomes ``None`` (CR-01):
    ``JSONResponse`` refuses NaN/inf and ``json.dumps`` would emit invalid JSON."""
    body: dict[str, Any] = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if key.startswith("_"):
            continue
        if isinstance(value, BaseModel):
            value = value.model_dump()
        body[key] = _finite(value)
    return body


def refusal_from_errors(errors: Iterable[Any]) -> SeamRefusalError | None:
    """The first ``SeamRefusalError`` a ``pydantic.ValidationError.errors()`` /
    ``RequestValidationError.errors()`` list carries on ``ctx["error"]`` (pydantic keeps the
    original exception object there when a validator raises), in list order; ``None`` if none."""
    for err in errors:
        original = (err.get("ctx") or {}).get("error")
        if isinstance(original, SeamRefusalError):
            return original
    return None


class EmptyQueryObjectError(SeamRefusalError):
    """Raised when a query object carries no set member at all (§18.1), or when its ``text`` is
    empty or whitespace-only (09-06-PLAN.md, SEAM-09, D-08) — refused before any wiring is
    resolved, never silently answered as an empty-text query."""

    def __init__(self, query_object: Any):
        self.query_object = query_object
        super().__init__(
            f"query object carries no set member, or its text is empty or whitespace-only: {query_object!r}"
        )


class NonFiniteNumberError(SeamRefusalError):
    """Raised at ``EvidenceRef`` / ``QueryObject`` validation (09 REVIEW CR-01) when ``field`` (``"score"``
    or ``"embedding"``) carries NaN or +/-infinity. JSON cannot represent them, so they are refused
    at the input boundary by name rather than echoed back in a body. ``field`` names the caller's own
    input slot, never the value."""

    def __init__(self, *, field: str):
        self.field = field
        # The literal class name is load-bearing: raised inside a pydantic validator.
        super().__init__(f"NonFiniteNumberError: field {field!r} must hold finite numbers (no NaN or infinity)")


class EmptyIngestDocumentError(SeamRefusalError):
    """Raised at ``IngestDocument`` validation when the one payload the caller set is empty
    (09-06-PLAN.md, SEAM-09, D-08): ``member`` is ``"text"`` for empty or whitespace-only text and
    ``"raw"`` for a zero-byte payload. Nothing is enqueued or written."""

    def __init__(self, *, member: str):
        self.member = member
        # The literal class name is load-bearing: raised inside a pydantic validator, so a caller
        # reading a wrapped ValidationError message needs the name to survive in the text.
        super().__init__(f"EmptyIngestDocumentError: the ingest document's {member} payload is empty")


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


class EmptyCapabilitySelectorError(SeamRefusalError):
    """Raised by ``resolve_selector`` and ``render_selector_key`` (09-07-PLAN.md, SEAM-10) for
    ``Selector(capability=[])``. An empty requested set is a subset of every wiring's effects, so it
    would resolve to the smallest wiring (bypass) and render an empty compare key; it is refused by
    name instead. Carries no caller value."""

    def __init__(self) -> None:
        super().__init__("EmptyCapabilitySelectorError: a capability selector must name at least one capability")


class InvalidPromotionAliasError(SeamRefusalError):
    """Raised by ``Databasise.promote`` (09-07-PLAN.md, SEAM-12) for an alias that is empty or
    shaped like an internal instance hash: no ``Selector`` could name it, so promoting it would
    write a ledger row nobody can select. Refused before any ledger touch. ``alias`` is the
    caller's own input."""

    def __init__(self, *, alias: str):
        self.alias = alias
        super().__init__(
            f"InvalidPromotionAliasError: alias {alias!r} is empty or shaped like an internal "
            "instance hash, so no selector could name it"
        )


class MultiMemberSelectorError(SeamRefusalError):
    """Raised at ``Selector`` model validation (09-01-PLAN.md, SEAM-02) when more than one of
    ``alias``/``capability``/``harness`` is set -- the three selector forms are mutually exclusive.
    ``set_members`` names which members the caller set. Names only the caller's own member names,
    never a candidate wiring."""

    def __init__(self, *, set_members: list[str]):
        self.set_members = list(set_members)
        # The literal class name is load-bearing for the same reason as PageSizeExceededError's.
        super().__init__(
            "MultiMemberSelectorError: a selector may set at most one of alias, capability, "
            f"harness; got {self.set_members!r} set"
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


class InvalidDocumentIdError(SeamRefusalError):
    """Raised by ``databasise.seam.corpus.generated_on_disk_name`` (09-03-PLAN.md, SEAM-07, D-06)
    when a caller-supplied ``document_id`` is not a non-empty token of letters, digits, ``_`` or
    ``-`` (so ``''``, ``'../x'``, ``'a.b'`` and ``'a\\n'`` are all refused). Raised by
    ``Databasise.ingest()`` and ``Databasise.delete_document()`` before any file is written or any
    wiring is loaded. Names only the caller's own value.
    """

    def __init__(self, *, document_id: str):
        self.document_id = document_id
        super().__init__(
            f"InvalidDocumentIdError: document id {document_id!r} must be a non-empty token of "
            "letters, digits, '_' or '-'"
        )


class DuplicateDocumentIdError(SeamRefusalError):
    """Raised by ``Databasise.ingest()`` (09 REVIEW WR-04) when a raw upload's staged file for
    ``document_id`` already exists in the inbox: an earlier upload with that id may still be parsed
    by v1, and overwriting it would make that job parse the newer bytes. Delete the document first
    (``delete_document`` releases the staged file) to re-upload the id. The inbox is per store, not
    per workspace, so a staged upload in another workspace of the same store also refuses.
    ``document_id`` is the caller's own input."""

    def __init__(self, *, document_id: str):
        self.document_id = document_id
        super().__init__(
            f"DuplicateDocumentIdError: document id {document_id!r} has a staged upload in this store; "
            "delete the document first to re-upload it"
        )


class UnknownDocumentError(SeamRefusalError):
    """A well-formed document id that does not exist in the corpus. A malformed id is
    :class:`InvalidDocumentIdError`, never this. Raised by ``Databasise.retry_document()``
    (11-08, D-08) when v1 holds no row for the id. Delete still reports an unknown id as a normal
    ``"not_found"`` status carried in ``databasise.seam.corpus.DeletionOutcome.status``.
    """

    def __init__(self, *, document_id: str):
        self.document_id = document_id
        super().__init__(f"document id {document_id!r} does not exist in the corpus")


class DocumentNotInterruptedError(SeamRefusalError):
    """Raised by ``Databasise.retry_document()`` (11-08, D-08, LRAG-07) when the named document is
    not interrupted: only a document v1 left mid-pipeline with no write in flight can be retried.
    ``document_id`` is the caller's own input; ``status`` is the document's reported status."""

    def __init__(self, *, document_id: str, status: str):
        self.document_id = document_id
        self.status = status
        super().__init__(
            f"DocumentNotInterruptedError: document id {document_id!r} has status {status!r}, not "
            "'interrupted'; ingest it again or delete it instead"
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


class NoRawUploadPathForModalityError(SeamRefusalError):
    """Raised by ``Databasise.ingest()`` (06-REVIEW.md CR-01) when a raw-bytes
    ``IngestDocument`` is submitted against a selector whose resolved corpus-ingest wiring's
    target node is not an ``opaque`` node. ``ingest()`` stamps a raw upload's real bytes only
    into ``file_paths``/``docs_format`` — a convention only an ``opaque`` node (a v1 subprocess
    that parses the file itself, e.g. ``lightrag/full-ingest``) knows how to read; a non-opaque
    target node (e.g. ``hipporag/chunker-embedder``, which reads only ``document["text"]``) always
    sees an empty string for a raw upload, silently indexing nothing while the operation still
    reports a normal-looking success. Refusing by name before any node config is stamped is
    strictly better than that silent data loss.

    Names only ``operation`` — never the resolved modality, wiring id, arm name, or node id —
    per this module's own no-enumeration house style, mirroring
    ``NoWritePathForModalityError``. The literal ``NoRawUploadPathForModalityError`` substring is
    load-bearing for the same reason ``NoWritePathForModalityError``'s own docstring documents: a
    caller distinguishing this refusal from another by inspecting a wrapped error's own message
    needs the refusal's own name to survive in that message text.
    """

    def __init__(self, *, operation: str) -> None:
        self.operation = operation
        super().__init__(
            "NoRawUploadPathForModalityError: no raw-upload path exists for operation "
            f"{operation!r}"
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


class PageBoundsError(SeamRefusalError):
    """Raised by ``databasise.seam.corpus.Page`` validation and ``checked_page`` (09-03-PLAN.md,
    SEAM-08, D-07) when ``limit`` is below 1 or ``offset`` is negative. Refused, never clamped or
    widened, so a negative limit can never slice the whole corpus. ``limit`` above
    ``MAX_PAGE_SIZE`` stays :class:`PageSizeExceededError`."""

    def __init__(self, *, limit: int, offset: int):
        self.limit = limit
        self.offset = offset
        # The literal class name is load-bearing for the same reason as PageSizeExceededError's:
        # Page's validator raises this, and pydantic wraps it into a ValidationError message.
        super().__init__(
            "PageBoundsError: page limit must be at least 1 and offset must be non-negative; "
            f"got limit={limit}, offset={offset}"
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


class MissingScopeArgumentError(SeamRefusalError):
    """Raised by the MCP ``status`` and ``resolve`` tools (09-04-PLAN.md, SEAM-03, D-02) when the
    chosen ``scope`` needs an argument the call left out (``status`` scope ``job`` needs ``job_id``,
    ``resolve`` scope ``evidence`` needs ``evidence_ref``, scope ``trace`` needs
    ``trace_reference``). ``tool``, ``scope`` and ``argument`` name only the tool's own vocabulary,
    never a caller-supplied value."""

    def __init__(self, *, tool: str, scope: str, argument: str):
        self.tool = tool
        self.scope = scope
        self.argument = argument
        super().__init__(f"MissingScopeArgumentError: the {tool} tool's scope {scope!r} requires {argument}")


class MalformedSelectorPayloadError(SeamRefusalError):
    """Raised by ``databasise.seam.rest``'s ``POST /documents/upload`` route (CR-02 gap closure)
    when the ``selector`` multipart form field is not valid JSON matching ``Selector``'s own
    shape. ``selector`` arrives as a JSON-encoded form field parsed manually via
    ``Selector.model_validate_json`` — never inside a pydantic validator — so, exactly like
    ``MalformedBase64PayloadError`` above, this refusal must be raised directly rather than let a
    raw ``pydantic.ValidationError`` escape uncaught (which the registered ``SeamRefusalError``
    handler cannot map, producing an unhandled 500 instead of the documented 422). ``field`` names
    only the caller's own input slot, per this module's own house style; it never carries the
    rejected payload's content.
    """

    def __init__(self, *, field: str):
        self.field = field
        super().__init__(f"field {field!r} is not valid JSON matching the expected selector shape")


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
    building one. The public ``component`` names only the excluded capability, ``mutates_store``
    (13 REVIEW A-WR-01, the D-15 rule for ``SeamEvent.component``): a part ``name@version`` names
    the fitted modality, which `CONTRACT.md` §18.3 keeps out of every consumer field, so it stays on
    the private ``_component`` and goes to the server log only. Never another candidate wiring, arm
    name or node id either (§18.2's closed-set rule).

    Checked in the comparison path for every selector count, one included (13-07, WIRE-17, D-11):
    `CONTRACT.md §14.4` point 3 refuses before any node runs, so ``compare()`` with one selector
    resolves it, runs this check, and only then returns the bare envelope of a run (RIG `§RUN.3`'s
    degenerate-width rule). ``query()`` is not a comparison and never raises this.

    Currently unreachable with the query candidates: no wiring in ``all_wirings()`` declares
    ``mutates_store``. It is exercised only by ``tests/seam/test_mutable_store_exclusion.py``,
    which adds the codebase-memory-mcp wiring to the candidate pool.
    """

    def __init__(self, *, component: str) -> None:
        self.component = "mutates_store"
        self._component = component  # private: a part name@version names the fitted modality
        super().__init__(
            "MutableStoreComparisonExcludedError: a selected wiring declares mutates_store and is "
            "excluded from §5 parity/determinism comparisons per the recorded disposition in "
            "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md"
        )


class EmptyPromotionTraceIdsError(SeamRefusalError):
    """Raised by ``databasise.seam.promotion.resolve_single_arm`` (07-01-PLAN.md, D-04) when a
    ``promote()`` call supplies an empty ``promotion_trace_ids`` list. CONTRACT §6's cross-field
    rule (``promotion_trace_ids`` non-empty iff ``promotion_provenance == "operator_asserted"``)
    has no SQL-level CHECK constraint to enforce it — this refusal is what makes the rule real,
    firing before any ledger read or write. Names only the caller's own ``alias`` — never a
    candidate mutation id or wiring name.
    """

    def __init__(self, *, alias: str):
        self.alias = alias
        super().__init__(
            f"EmptyPromotionTraceIdsError: promotion for alias {alias!r} was given no trace ids "
            "to derive the target wiring from"
        )


class DisagreeingPromotionTraceIdsError(SeamRefusalError):
    """Raised by ``databasise.seam.promotion.resolve_single_arm`` (07-01-PLAN.md, D-04) when the
    supplied trace ids resolve to more than one distinct wiring — refused rather than silently
    promoting whichever record happened to be read first or last, since that would promote a
    wiring the caller never actually named. Names only the caller's own ``trace_ids`` — never the
    resolved arm names, per this module's own no-enumeration house style.
    """

    def __init__(self, *, trace_ids: list[str]):
        self.trace_ids = list(trace_ids)
        super().__init__(
            "DisagreeingPromotionTraceIdsError: trace ids "
            f"{self.trace_ids!r} resolve to more than one distinct wiring; a promotion target "
            "must be named by trace ids that all agree on exactly one"
        )


class InvalidChangeOriginError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-08) when ``change_origin`` is absent
    (``None``) or is not one of CONTRACT §7's two enumerated values (``human_edit``,
    ``machine_mutation``) — never defaulted, never inferred from absence. Names only the caller's
    own supplied value; the message does not enumerate the accepted set as a menu the caller could
    pattern-match against, and does not imply a default exists.
    """

    def __init__(self, *, change_origin: Any):
        self.change_origin = change_origin
        super().__init__(
            f"InvalidChangeOriginError: change_origin {change_origin!r} is not a recognised value"
        )


class UnrecognisedPromotionVerbError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-04-PLAN.md, D-09, closing 07-REVIEW.md CR-01) when
    ``verb`` is not one of ``databasise.seam.promotion.PromotionVerb``'s six declared literals.
    Checked before trace-id resolution runs (07-VERIFICATION.md's `missing:` item 1) — an unknown
    verb refuses immediately, the identical position ``GateVerbNotBuiltError`` already occupies for
    a known-but-unbuilt verb. Both transports type ``verb`` as ``str``, so a non-string verb
    (None, a number, an object) never reaches ``promote()`` over REST (FastAPI validation error)
    or MCP (argument validation error); only a non-member string does. The attribute is typed
    ``Any`` so an in-process caller passing a non-string still gets a refusal naming whatever
    arrived. Per this
    module's own house style, the message names only the caller's own value — it does not
    enumerate the accepted verb set as a menu to pattern-match against, and does not imply a
    default exists.
    """

    def __init__(self, *, verb: Any):
        self.verb = verb
        super().__init__(
            f"UnrecognisedPromotionVerbError: verb {verb!r} is not a recognised promotion verb"
        )


class GateVerbNotBuiltError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09) when ``verb`` is ``check``,
    ``preview``, or ``run`` — no gate implementation exists in this milestone, and Phase 7 does
    not build one. Refused immediately, before any trace resolution or class derivation runs,
    since there is nothing yet to resolve. One shared refusal type parameterized by ``verb``,
    mirroring ``UnsatisfiableSelectorError``'s own ``selector_kind`` parameterization, rather than
    three near-identical exception classes for the same "not built" fact. Names only the caller's
    own ``verb``.
    """

    def __init__(self, *, verb: str):
        self.verb = verb
        super().__init__(f"GateVerbNotBuiltError: verb {verb!r} is not built in this milestone")


class MeasurementPostureRefusalError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09/D-11) when ``promote-next`` or
    ``promote-now`` is called against a mutation classed ``answer-level`` or ``index-side`` —
    measurement-gated promotion is off by default for both classes (RIG.md §F3.2), and this
    refusal is what keeps that default posture true at the runtime gate rather than merely
    documented. Names only the caller's own ``verb`` and the machine-derived ``mutation_class`` —
    never a wiring name, arm name, or node id.
    """

    def __init__(self, *, verb: str, mutation_class: str):
        self.verb = verb
        self.mutation_class = mutation_class
        super().__init__(
            f"MeasurementPostureRefusalError: verb {verb!r} refuses for mutation class "
            f"{mutation_class!r}: measurement-gated promotion is off by default for this class "
            "per RIG.md §F3.2"
        )


class UncalibratedFloorRefusalError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09/D-11) when ``promote-next`` or
    ``promote-now`` is called against a mutation classed ``retrieval-side`` — this class is
    measurement-gated ON by default (RIG.md §F3.2), but no calibrated A/A floor exists yet
    (MACH-03 Pending): a null whose cache-bypass status is unknown is not usable as a floor
    (RIG.md §AA.2). Names only the caller's own ``verb`` and the machine-derived
    ``mutation_class``.
    """

    def __init__(self, *, verb: str, mutation_class: str):
        self.verb = verb
        self.mutation_class = mutation_class
        super().__init__(
            f"UncalibratedFloorRefusalError: verb {verb!r} refuses for mutation class "
            f"{mutation_class!r}: no calibrated A/A floor exists yet per RIG.md §AA.2"
        )


class UnknownGenerationVersionError(SeamRefusalError):
    """Raised by ``Databasise.rollback()``/``Databasise.retire()`` (07-02-PLAN.md, D-05/D-07) when
    ``version`` names no generation ``alias`` has ever minted or acted on
    (``Ledger.generation_state`` returns ``None``). Covers both "this alias never minted that
    version" and "that version was minted under a different alias" as the same refusal — from the
    caller's own vocabulary both are the fact that *this alias has no such generation*; naming the
    other alias would disclose a generation the caller did not ask about. Names only the caller's
    own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"UnknownGenerationVersionError: alias {alias!r} has no generation at version "
            f"{version!r}"
        )


class TombstonedGenerationError(SeamRefusalError):
    """Raised by ``Databasise.rollback()``/``Databasise.retire()`` (07-02-PLAN.md, D-05/D-07) when
    the named generation's latest ledger state (``Ledger.generation_state``) is a tombstone — RIG
    §PR.2 and CONTRACT §0.4: a retired generation is not reachable again, whether by rolling back
    to it or by retiring it a second time (a silent second tombstone would be indistinguishable
    from a real retirement to the caller). Checked by reading the *latest* record for the specific
    ``(alias, version)`` generation, never by scanning history for a tombstone anywhere — a wiring
    legitimately retired once and later re-promoted must stay promotable under its new generation.
    Names only the caller's own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"TombstonedGenerationError: alias {alias!r} version {version!r} is tombstoned and "
            "is not reachable again"
        )


class ActiveGenerationRetirementError(SeamRefusalError):
    """Raised by ``Databasise.retire()`` (07-02-PLAN.md, D-07) when the named generation is
    ``alias``'s own currently active generation (``Ledger.by_alias(alias).minted_version ==
    version``). Retiring it would leave the alias resolving to a wiring just declared ineligible,
    and CONTRACT §16.2 already refuses pins to tombstoned artifacts. The operator rolls back
    first, then retires — ``by_alias`` walking backward to the most recent non-retired generation
    would be a second alias-lifecycle mechanism CONTEXT.md states is "not required and not asked
    for". Names only the caller's own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"ActiveGenerationRetirementError: alias {alias!r} version {version!r} is the "
            "currently active generation; roll back first, then retire"
        )


class UnknownTraceReferenceError(SeamRefusalError):
    """Raised when a trace reference names no record the trace store currently holds. Never returns
    ``None`` and never a partial record (API-10's own truth: an unknown reference resolves to a
    named refusal, never a partial or empty record) — an untrusted reference handed back to the
    seam gets a raise, not a value a caller could mistake for "the run had no trace"."""

    def __init__(self, trace_reference: str):
        self.trace_reference = trace_reference
        super().__init__(
            f"trace reference {trace_reference!r} does not resolve to any stored run record"
        )


class UnresolvableEvidenceReferenceError(SeamRefusalError):
    """Raised when an ``EvidenceRef`` names a record its own namespace's store does not currently
    hold (§4's deref-raising discipline, T-04-08's mitigation). Never returns ``None`` and never an
    empty result — either would be indistinguishable from evidence that was legitimately empty.
    ``ref`` is annotated ``Any`` because importing ``EvidenceRef`` here would create an import
    cycle; ``refusal_body`` dumps it with ``model_dump()``."""

    def __init__(self, ref: Any):
        self.ref = ref
        super().__init__(
            f"evidence reference {ref.ref!r} in namespace {ref.namespace!r} does not resolve to "
            "any record the store currently holds"
        )


class InvalidEvidenceNamespaceError(SeamRefusalError):
    """Raised by ``databasise.seam.evidence.validate_evidence_namespace`` (09-06-PLAN.md, SEAM-01,
    D-05) when an ``EvidenceRef`` namespace is not a non-empty token of letters, digits or ``-``.
    The namespace becomes a directory name under ``<store_root>/<workspace>``, so a path-like value
    must be refused before any store is opened. ``namespace`` is the caller's own input."""

    def __init__(self, *, namespace: str):
        self.namespace = namespace
        super().__init__(
            f"InvalidEvidenceNamespaceError: evidence namespace {namespace!r} must be a non-empty "
            "token of letters, digits or '-'"
        )


class UnbudgetableParticipantError(SeamRefusalError):
    """Raised when a run contains a node whose own ``TokenAccounting.counted_by`` reports the
    ``unbudgetable`` sentinel (§8 opaque-node admission). No envelope is produced on this path, and
    no token number is substituted or estimated in its place (D-08, T-04-10's mitigation — a
    plausible-looking fabricated count is worse than a refusal because it reads as measured).

    **CR-03: never names the machine's own node id.** Every other refusal in this package names
    only the consumer's own input (this module's own docstring). ``node_id`` here is the
    *machine's* internal wiring-node identity, never something the consumer supplied — so, unlike
    every other refusal's named attribute, it is stored on a leading-underscore attribute rather
    than a plain one. ``refusal_body`` skips leading-underscore attributes when it dumps
    ``vars(exc)`` into a transport body for exactly this reason: this is the one refusal in the
    package whose own offending value must never reach a consumer, in the message or the body.
    """

    def __init__(self, node_id: str):
        self._internal_node_id = node_id  # never exposed via the message or vars()
        super().__init__("a participant is admitted unbudgetable; no token comparison may include it")


# The public vocabulary of ``ForeignEngineRefusalError.failure_class`` (D-04). Keyed by the cause's
# type name so this module imports nothing from ``databasise.foreign``; any other cause type is
# ``UnclassifiedEngineFailure``, never its own class name (an unknown class name could be sensitive).
_FOREIGN_FAILURE_CLASSES: dict[str, str] = {
    "MissingV1InterpreterError": "MissingV1InterpreterError",
    "CorpusOpSubprocessError": "CorpusOpSubprocessError",
    "CorpusOpTimeoutError": "CorpusOpTimeoutError",
    "V1NotConfiguredError": "V1NotConfigured",
    "CorpusOpMalformedOutputError": "MalformedDriverOutput",
    "JSONDecodeError": "MalformedDriverOutput",
    "UnicodeDecodeError": "MalformedDriverOutput",
    "ExtractionFailedError": "ExtractionFailed",
}

# Phase 12 D-08: the only text an ExtractionFailed refusal may carry is a closed reason code.
_EXTRACTION_REASON_CODE = re.compile(r"unparseable_response|llm_call_failed:[A-Za-z_][A-Za-z0-9_]{0,63}")
_MAX_FAILURE_REASONS = 10


class ForeignEngineRefusalError(SeamRefusalError):
    """A machine fault, not a caller refusal (09-05-PLAN.md, SEAM-05, D-04). One fault type covers
    every engine-side failure: the v1 engine failed, was unavailable or returned malformed output
    (the v1 classes above); a store failed inside a node or during the flush (``StoreFault``, or
    ``StoreCorrupted``); or the run stopped early with no exception (``RunIncomplete``, Phase 10
    D-06, D-13). The class name is historical; a store fault is not a v1 failure. ``operation``
    names the seam operation that was attempted (e.g. ``"ingest"``); ``failure_class`` is the
    allow-listed public name of what went wrong. REST answers 503 when v1 is unavailable and 502
    for every other class. ``EnvironmentDigestUnavailable`` (Phase 13 D-22) is raised when the
    resolved-environment digest cannot be computed before a run; the machine cannot name the run's
    identity, so REST answers 503.

    The underlying exception is private: stored on ``_cause`` (so ``refusal_body`` never exposes it),
    readable in-process through the read-only ``cause`` property, and logged in full by the engine
    (``databasise.seam.engine._foreign_fault``). The message names only the operation and the failure
    class, never stderr, a traceback, a server path or an env-var name; no flag exposes the cause
    while seam authentication is undecided. The failing node id (``_node_id``, read through ``node_id``)
    is private the same way: it is the machine's internal wiring identity (CONTRACT section 18.2
    low-entropy identity, WIRE-03), so it never enters the message or a transport body (Phase 12 D-09).

    Phase 11 D-12 is the single place a refusal may name configuration keys: only the
    ``V1NotConfigured`` class adds public ``missing_keys`` and ``unsupported_keys`` (key names,
    never values). Phase 12 D-08 adds the second class with public attributes: ``ExtractionFailed``
    carries ``failed_chunks`` and ``failure_reasons`` (a count and closed codes, never text). Every
    other class keeps exactly ``operation`` and ``failure_class``, except that a refusal of a query
    raised after its nodes ran also carries the public ``trace_token`` (Phase 13 D-04).
    """

    def __init__(
        self,
        *,
        operation: str,
        cause: BaseException,
        failure_class: str | None = None,
        node_id: str | None = None,
    ):
        self.operation = operation
        self.failure_class = failure_class or _FOREIGN_FAILURE_CLASSES.get(
            type(cause).__name__, "UnclassifiedEngineFailure"
        )
        if self.failure_class == "V1NotConfigured":
            self.missing_keys = sorted(str(key) for key in getattr(cause, "missing_keys", ()))
            self.unsupported_keys = sorted(str(key) for key in getattr(cause, "unsupported_keys", ()))
        elif self.failure_class == "ExtractionFailed":
            self.failed_chunks = int(getattr(cause, "failed_chunks", 0))
            self.failure_reasons = [
                reason
                for reason in getattr(cause, "failure_reasons", ())
                if isinstance(reason, str) and _EXTRACTION_REASON_CODE.fullmatch(reason)
            ][:_MAX_FAILURE_REASONS]
        self._cause = cause
        self._node_id = node_id
        super().__init__(
            f"ForeignEngineRefusalError: operation {operation!r} failed ({self.failure_class})"
        )

    @property
    def cause(self) -> BaseException:
        return self._cause

    @property
    def node_id(self) -> str | None:
        """The wiring node whose exception caused the refusal, or ``None`` when no node did."""
        return self._node_id


class StoreBusyError(SeamRefusalError):
    """Raised before any node runs when a store this call needs is held by another OS process, or by
    an open that cannot share the in-process client (Phase 10 D-01), or (``"corpus"``, 11-06 D-07)
    when another LightRAG write holds this workspace's v1 working dir. REST answers 409 (D-02): the
    request is fine, the store is busy. Only ``store_kind`` (``"graph"`` or ``"corpus"``) is public;
    the store path and namespace are never named, and the cause is logged server-side once."""

    def __init__(self, *, store_kind: str):
        self.store_kind = store_kind
        super().__init__(
            f"StoreBusyError: the {store_kind} store is held by another process or write; "
            "retry once it is released"
        )


class EmptyNamespaceError(SeamRefusalError):
    """Raised by ``Databasise.query`` (and ``compare``) after the stores open and before any node
    runs, when a retrieval node of the arm reads a vector namespace that has never been populated
    (11-10, D-15, LRAG-16), so no keyword or embedding call is spent on an empty store. REST answers
    422. Only ``store_kind`` is public; the namespace and the store path are never named. A namespace
    that was populated and then emptied by a delete is not refused: it answers as no match."""

    def __init__(self, *, store_kind: str):
        self.store_kind = store_kind
        super().__init__(
            f"EmptyNamespaceError: the {store_kind} store this query reads has never been "
            "populated; ingest documents before querying"
        )


class AmbiguousAnswerPositionError(SeamRefusalError):
    """Raised by ``Databasise.query`` (and ``compare``) after the nodes ran, when the wiring's
    ``provides`` positions include more than one node that produced a completion (Phase 13 D-04).
    The seam has no tie-break between two answers, so it refuses instead of picking one. REST answers
    422. No attribute is public and the message names no node; the refusal carries the run's
    ``trace_token``, whose debug trace names the nodes."""

    def __init__(self) -> None:
        super().__init__(
            "AmbiguousAnswerPositionError: the wiring declares more than one answering provides "
            "position, so the seam cannot choose one answer"
        )


class UnsupportedUploadTypeError(SeamRefusalError):
    """Raised by ``Databasise.ingest`` for a raw upload whose ``file_name`` has no suffix, or one
    v1's default parser does not handle, before anything is written (11-05, D-09). REST answers 422.
    ``suffix`` is the lower-cased suffix, or ``""`` when there is none or it is not a plain token;
    no path or file name is ever named."""

    def __init__(self, *, suffix: str):
        self.suffix = suffix
        super().__init__(
            f"UnsupportedUploadTypeError: upload type {suffix or '(no suffix)'!r} is not accepted; "
            "upload a text, markup, source-code, PDF or office document with its usual suffix"
        )


class UnparseableWiringError(SeamRefusalError):
    """Raised by ``Databasise.query``/``ingest``/``delete_document``/``retry_document`` (and every
    path through ``_execute_resolved``) when the resolved wiring's parse report is not ok or its
    dependency graph is cyclic, before any store is built (Phase 10 D-15, research Q5; Phase 13
    WIRE-05, D-07). REST answers 422. ``violations`` carries the sorted unique violation codes only
    (a cycle is ``cyclic-wiring``), never node ids, pointers or messages: those stay on the private
    ``_details`` list of ``(code, pointer, message)`` and in the server log (D-25)."""

    def __init__(self, *, violations: list[str]):
        self.violations = sorted(set(violations))
        self._details: list[tuple[str, str, str]] = []  # private: pointers and messages embed node ids
        super().__init__(
            "UnparseableWiringError: the resolved wiring was refused at parse "
            f"({', '.join(self.violations)})"
        )


class InvalidNodeSettingError(SeamRefusalError):
    """Raised before any node is dispatched when a wiring node declares a ``max_concurrency`` or
    ``token_allowance`` that is not a valid true integer in range (WIRE-05, D-07). REST answers 422.
    ``setting`` is the public setting name (``max_concurrency`` or ``token_allowance``); the value
    and the declaring node id are the machine's own wiring content and stay private (``_node_id``),
    in the message and the body both."""

    def __init__(self, setting: str, *, node_id: str):
        self.setting = setting
        self._node_id = node_id
        super().__init__(f"InvalidNodeSettingError: the wiring declares an invalid {setting!r} setting")


class InvalidGuardDeclarationError(SeamRefusalError):
    """Raised before any node is dispatched when a wiring node's guard declaration is malformed: a
    bad entry shape, an inadmissible granularity or an evaluating node that is neither the guarded
    node nor one of its dependencies (WIRE-08, D-19). REST answers 422. No public attribute: the
    guarded node id is the machine's internal wiring identity and stays on ``_node_id``.

    Also raised on the query path after dispatch when a guard's evaluating node emitted no declared
    ``signal`` key (D-19: a refusal, never a fire; 13 REVIEW B-WR-04). That run is persisted first,
    so this refusal then carries the run's ``trace_token`` (D-04)."""

    def __init__(self, *, node_id: str | None):
        self._node_id = node_id
        super().__init__("InvalidGuardDeclarationError: the wiring declares a malformed guard")


__all__ = [
    "SeamRefusalError",
    "EmptyQueryObjectError",
    "NonFiniteNumberError",
    "UnconsumableQueryMemberError",
    "UnsatisfiableSelectorError",
    "ForbiddenSelectorInputError",
    "MultiMemberSelectorError",
    "EmptyCapabilitySelectorError",
    "InvalidPromotionAliasError",
    "AmbiguousIngestPayloadError",
    "OversizedDocumentError",
    "InvalidDocumentIdError",
    "DuplicateDocumentIdError",
    "UnknownDocumentError",
    "DocumentNotInterruptedError",
    "NoWritePathForModalityError",
    "NoRawUploadPathForModalityError",
    "UnknownJobError",
    "PageSizeExceededError",
    "PageBoundsError",
    "MalformedBase64PayloadError",
    "MissingScopeArgumentError",
    "MalformedSelectorPayloadError",
    "EmptyComparisonRequestError",
    "DuplicateComparisonKeyError",
    "MutableStoreComparisonExcludedError",
    "ForeignEngineRefusalError",
    "StoreBusyError",
    "EmptyNamespaceError",
    "AmbiguousAnswerPositionError",
    "UnsupportedUploadTypeError",
    "UnparseableWiringError",
    "EmptyPromotionTraceIdsError",
    "DisagreeingPromotionTraceIdsError",
    "InvalidChangeOriginError",
    "UnrecognisedPromotionVerbError",
    "GateVerbNotBuiltError",
    "MeasurementPostureRefusalError",
    "UncalibratedFloorRefusalError",
    "UnknownGenerationVersionError",
    "TombstonedGenerationError",
    "ActiveGenerationRetirementError",
    "UnknownTraceReferenceError",
    "UnresolvableEvidenceReferenceError",
    "InvalidEvidenceNamespaceError",
    "EmptyIngestDocumentError",
    "UnbudgetableParticipantError",
    "InvalidNodeSettingError",
    "InvalidGuardDeclarationError",
]
