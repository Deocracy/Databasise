"""``databasise.seam.corpus`` — the corpus-side seam DTOs: ``IngestDocument`` (the caller's input),
``IngestJob`` (the job handle ``Databasise.ingest()`` returns) and ``DeletionOutcome`` (the result
``Databasise.delete_document()`` returns, 05-03-PLAN.md Task 2), plus ``MAX_DOCUMENT_BYTES`` and
``generated_on_disk_name`` — the raw-upload path safety mechanism (05-01-PLAN.md Task 3).

``IngestDocument`` accepts exactly one of two input shapes — ``text`` (a structured, already-
extracted payload) or ``raw``+``content_type`` (an opaque byte blob v1's own parser handles) —
never both, never neither. ``file_name`` and ``content_type`` are not stored: of ``file_name`` only
the suffix validated by ``upload_suffix`` is kept, to choose v1's parser (11-05, D-09), and neither
is ever used to build a filesystem path or a citation name.
``generated_on_disk_name`` is what makes that true structurally: the on-disk name is derived only
from a ``document_id`` (server-minted or caller-supplied) plus that validated suffix, refusing any id that is not a non-empty
token of letters, digits, ``_`` or ``-`` (``InvalidDocumentIdError``) -- the same bare-token
discipline ``databasise/namespaces.py``'s ``_NAMESPACE_TOKEN_RE`` enforces for a namespace
directory name, matched with ``fullmatch`` so a trailing newline is not accepted.

**05-04-PLAN.md Task 1: the bounded read surface.** ``Page``/``MAX_PAGE_SIZE``,
``DocumentStatusEntry``, ``JobStatus``, ``CorpusStatus``, ``DocumentCounts`` and ``HealthReport``
are ``Databasise``'s corpus-introspection models (API-06) — every one of them is bounded at the
type level so a caller can never reach a full corpus or index dump through this surface: ``Page``
refuses (never clamps) a ``limit`` above ``MAX_PAGE_SIZE``, ``health()``/``document_counts()``
return fixed-size records with no per-document member at all, and ``corpus_status()`` returns at
most ``MAX_PAGE_SIZE`` document entries per call, each entry carrying only an identifier, a status,
a timestamp and an optional error message — never document text, chunk text, an embedding vector,
or a graph node payload.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from databasise.seam.envelope import SeamEvent
from databasise.seam.refusals import (
    AmbiguousIngestPayloadError,
    EmptyIngestDocumentError,
    InvalidDocumentIdError,
    OversizedDocumentError,
    PageBoundsError,
    PageSizeExceededError,
    UnsupportedUploadTypeError,
)

# API-06: the hard cap on any single page this seam will ever return — a caller requesting more
# is refused by name (PageSizeExceededError), never silently clamped down to this value.
MAX_PAGE_SIZE = 100

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

# A generated on-disk name is derived only from a server-minted OR caller-supplied document id —
# same bare-token *security* discipline databasise/namespaces.py's own _NAMESPACE_TOKEN_RE
# enforces (no path separator, no parent-directory reference, so a value handed to
# generated_on_disk_name() can never escape the corpus-inbox directory it is joined under), but
# widened to also permit underscore: unlike namespaces.py's own tokens (always machine-generated
# hex — config_hash, sha256, uuid.hex), a document_id may be caller-supplied (Databasise.ingest())
# or may name an already-ingested real-world document whose id legitimately contains underscores
# (05-03-PLAN.md Task 3's own corpus fixture ids — "a_kiss_for_corliss" and its siblings — are
# exactly this case). Underscore introduces no path-traversal risk; forbidding it was stricter
# than the actual security requirement.
# Used with ``fullmatch`` (09-03-PLAN.md, SEAM-07): ``$`` would let a trailing newline through.
_DOCUMENT_ID_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+")

_ON_DISK_SUFFIX = ".bin"

# 11-05 (D-09): the upload types v1's default (legacy) parser handles, copied from
# v1/lightrag/parser/registry.py's _LEGACY_SUFFIXES (lightrag cannot be imported here);
# tests/seam/test_upload_suffixes.py pins the copy to that literal with ast.
ACCEPTED_UPLOAD_SUFFIXES: frozenset[str] = frozenset(
    {
        ".bat", ".c", ".conf", ".cpp", ".css", ".csv", ".docx", ".epub", ".go", ".h", ".hpp", ".htm",
        ".html", ".ini", ".java", ".js", ".json", ".less", ".log", ".md", ".mdx", ".odt", ".pdf",
        ".php", ".pptx", ".properties", ".py", ".rb", ".rtf", ".scss", ".sh", ".sql", ".swift",
        ".tex", ".ts", ".txt", ".xlsx", ".xml", ".yaml", ".yml",
    }
)  # fmt: skip
_SUFFIX_RE = re.compile(r"\.[a-z0-9]{1,8}")


class IngestDocument(BaseModel):
    """The caller's ingest input. Exactly one of ``text``/``raw`` must be set — never both, never
    neither (``AmbiguousIngestPayloadError``, naming what was missing/duplicated). A ``raw``
    payload (or a ``text`` payload whose UTF-8 encoding) larger than ``MAX_DOCUMENT_BYTES`` is
    refused (``OversizedDocumentError``) before any bytes are written to disk and before the
    subprocess is launched. An empty payload is refused as ``EmptyIngestDocumentError`` (SEAM-09,
    D-08): whitespace-only ``text`` counts as empty; ``raw`` bytes are checked only for length 0.

    ``file_name`` and ``content_type`` are not stored (D-11). For a ``raw`` payload only the suffix
    of ``file_name`` that ``upload_suffix`` validates is kept, to choose v1's parser (11-05, D-09);
    the name itself is never used as a path or a citation name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    document_id: str | None = None
    file_name: str | None = Field(
        default=None,
        description=(
            "Advisory only and not stored: for a raw upload only its validated suffix is kept, to choose "
            "v1's parser; the name is never used as a path or a citation name."
        ),
    )
    raw: bytes | None = None
    content_type: str | None = Field(
        default=None, description="Advisory only and not stored: discarded at ingest."
    )

    @model_validator(mode="after")
    def _exactly_one_payload_shape_within_the_size_cap(self) -> "IngestDocument":
        set_members = [name for name in ("text", "raw") if getattr(self, name) is not None]
        if len(set_members) != 1:
            raise AmbiguousIngestPayloadError(set_members=set_members)

        if self.raw is not None and len(self.raw) > MAX_DOCUMENT_BYTES:
            raise OversizedDocumentError(actual_bytes=len(self.raw), limit_bytes=MAX_DOCUMENT_BYTES)
        if self.text is not None:
            actual_bytes = len(self.text.encode("utf-8"))
            if actual_bytes > MAX_DOCUMENT_BYTES:
                raise OversizedDocumentError(actual_bytes=actual_bytes, limit_bytes=MAX_DOCUMENT_BYTES)

        if self.text is not None and self.text.strip() == "":
            raise EmptyIngestDocumentError(member="text")
        if self.raw is not None and len(self.raw) == 0:
            raise EmptyIngestDocumentError(member="raw")
        return self


class IngestJob(BaseModel):
    """The job handle ``Databasise.ingest()`` returns — ``job_id`` is v1's own ``track_id``, never
    a machine-internal wiring/node identity. ``seam_events`` (11-01-PLAN.md, LRAG-03) carries the
    MACH-11 events the committed run produced, exactly as ``DeletionOutcome.seam_events`` does for
    a delete; ingest persists no trace, so the returned job is where they are reported."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    enqueued: int
    seam_events: list[SeamEvent] = []


class DeletionOutcome(BaseModel):
    """The result ``Databasise.delete_document()`` returns (05-03-PLAN.md Task 2). ``status`` is
    drawn from v1's own four-value ``DeletionResult`` vocabulary (``v1/lightrag/base.py``) —
    imported conceptually rather than re-invented, since the machine never imports ``lightrag``
    itself (``databasise/tools/check_import_boundary.py``). Deleting an already-deleted or
    never-ingested document is a normal ``"not_found"`` outcome carried here, never a refusal — a
    caller deleting an id that no longer exists has asked a legitimate question and received a
    legitimate answer. ``seam_events`` carries the MACH-11 correlation this deletion produced
    (``databasise.seam.engine._mach11_events``) — empty when nothing was recorded, one entry when
    the deleting node's own ``mutates_store`` effect correlated against its recorded touches.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    status: Literal["success", "not_found", "not_allowed", "fail"]
    message: str
    seam_events: list[SeamEvent] = []

    @field_validator("message")
    @classmethod
    def _scrub_message(cls, value: str) -> str:
        # 09 REVIEW WR-03: v1's failure text (``str(e)``) can name storage paths.
        return scrub_error_message(value) or ""


class Page(BaseModel):
    """A bounded page request (API-06) — a ``limit`` outside 1..``MAX_PAGE_SIZE`` or a negative
    ``offset`` is refused, never clamped, per this codebase's refusals-over-silent-narrowing house
    style (SEAM-08, D-07): ``limit`` above the cap is ``PageSizeExceededError``, ``limit`` below 1
    or a negative ``offset`` is ``PageBoundsError``. An in-process caller constructing ``Page``
    directly receives a ``pydantic.ValidationError`` whose message contains the refusal class name
    (``PageSizeExceededError`` or ``PageBoundsError``); :func:`checked_page` raises the refusal
    itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    limit: int = 50
    offset: int = 0

    @model_validator(mode="after")
    def _bounded(self) -> "Page":
        if self.limit > MAX_PAGE_SIZE:
            raise PageSizeExceededError(requested=self.limit, limit=MAX_PAGE_SIZE)
        if self.limit < 1 or self.offset < 0:
            raise PageBoundsError(limit=self.limit, offset=self.offset)
        return self


def checked_page(limit: int, offset: int) -> Page:
    """The one page check both transports call (SEAM-08, D-07). Raises ``PageSizeExceededError``
    for ``limit`` above ``MAX_PAGE_SIZE``, then ``PageBoundsError`` for ``limit`` below 1 or a
    negative ``offset``, directly -- never by letting ``Page``'s own ``model_validator`` raise
    them: pydantic wraps a validator-raised exception into a ``pydantic.ValidationError`` at the
    construction call site (the same behaviour ``AmbiguousIngestPayloadError``'s module docstring
    documents for ``IngestDocument``), and Starlette's exception middleware matches by
    ``type(exc).__mro__`` against the registered ``SeamRefusalError`` handler, so the wrapped error
    would be an unhandled 500 instead of the documented 422. The upper cap is checked before the
    lower bounds, so ``limit=101, offset=-1`` is ``PageSizeExceededError``.
    """
    if limit > MAX_PAGE_SIZE:
        raise PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)
    if limit < 1 or offset < 0:
        raise PageBoundsError(limit=limit, offset=offset)
    return Page(limit=limit, offset=offset)


MAX_ERROR_MESSAGE_CHARS = 200

# Where a filesystem path starts: a Windows drive, a UNC share, ``~``/``~user``, ``./``, ``../`` or
# an absolute ``/``. The lookbehind keeps ``a/b`` (a word character before the slash) untouched.
_PATH_START = r"(?:[A-Za-z]:[\\/]|\\\\|~[\w.-]*/|\.{1,2}/|/)"
_PATH_RE = re.compile(rf"""(?<![\w.~-]){_PATH_START}[^\s'"`<>()\[\],;]*""")
# The same path inside matching quotes, which may hold spaces (``'/home/u/my docs/a b.bin'``).
_QUOTED_PATH_RE = re.compile(rf"""(?P<q>['"])(?P<p>{_PATH_START}[^'"\n]*)(?P=q)""")
# Any ``<scheme chars>://...`` token, scheme validity not required (``1http://u:p@h`` must go too).
# The lookbehind starts a match only at the head of a scheme-character run, so each run is scanned
# once (linear); a bare ``\b`` retried at every ``.``/``-`` boundary and went quadratic.
_URL_RE = re.compile(r"""(?<![a-z0-9+.-])[a-z0-9+.-]*://[^\s'"`<>()\[\],;]*""", re.IGNORECASE)


def _basename(path: str) -> str:
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1] or "<path>"


def scrub_error_message(text: str | None) -> str | None:
    """09 REVIEW WR-03/WR-02: a best-effort scrub of v1's free-text failure message before it goes
    to a caller. It is a regex heuristic, not an allow-list, and does not guarantee that no server
    detail remains (an unquoted path containing spaces keeps its tail, for one). It cuts a
    traceback, keeps the first line, replaces each ``file://`` or ``http(s)://`` URL with
    ``<url>``, replaces each absolute, ``~``, UNC or ``./``/``../`` path (quoted paths may hold
    spaces) with its basename (``<path>`` when it has none) and caps the length. The one helper
    every transport reaches through ``DocumentStatusEntry`` and ``DeletionOutcome``."""
    if text is None:
        return None
    first = next((ln.strip() for ln in text.split("Traceback (most recent call last)")[0].splitlines() if ln.strip()), "")
    scrubbed = _URL_RE.sub("<url>", first)
    scrubbed = _QUOTED_PATH_RE.sub(lambda m: f"{m['q']}{_basename(m['p'])}{m['q']}", scrubbed)
    scrubbed = _PATH_RE.sub(lambda m: _basename(m.group(0)), scrubbed)
    if len(scrubbed) > MAX_ERROR_MESSAGE_CHARS:
        scrubbed = scrubbed[: MAX_ERROR_MESSAGE_CHARS - 1] + "…"
    return scrubbed or None


class DocumentStatusEntry(BaseModel):
    """One document's status within a ``JobStatus``/``CorpusStatus`` page — carries only an
    identifier, a status, a timestamp and an optional error message. No field here ever carries
    document text, chunk text, an embedding vector, or a graph node payload (API-06). The error
    message is v1's text passed through :func:`scrub_error_message`, a best-effort scrub (paths
    and URLs replaced, no traceback, bounded length), not a guarantee."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    status: str
    updated_at: str
    error_message: str | None = None

    @field_validator("error_message")
    @classmethod
    def _scrub_error_message(cls, value: str | None) -> str | None:
        return scrub_error_message(value)


class JobStatus(BaseModel):
    """The result ``Databasise.get_job_status()`` returns (05-04-PLAN.md Task 1, API-01's polling
    half). ``documents`` carries one ``DocumentStatusEntry`` per document in this job's own page;
    ``counts`` is v1's own whole-corpus status counts (v1 exposes no per-job counts); ``next_offset``
    is ``None`` on the last page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    documents: list[DocumentStatusEntry]
    counts: dict[str, int]
    next_offset: int | None = None


class CorpusStatus(BaseModel):
    """The result ``Databasise.corpus_status()`` returns (05-04-PLAN.md Task 1, API-06) — a
    bounded, paginated document list, never a full corpus dump. ``next_offset`` is ``None`` on the
    last page; a caller requesting a page beyond ``MAX_PAGE_SIZE`` is refused by
    ``Page``'s own validator before this method is ever called."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: list[DocumentStatusEntry]
    counts: dict[str, int]
    total: int
    next_offset: int | None = None


class DocumentCounts(BaseModel):
    """The result ``Databasise.document_counts()`` returns (05-04-PLAN.md Task 1, API-06) — a
    fixed-size record, never a per-document list. ``by_status`` keys are exactly v1's own status
    names; ``total`` equals their sum."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    by_status: dict[str, int]
    total: int


class HealthReport(BaseModel):
    """The result ``Databasise.health()`` returns (05-04-PLAN.md Task 1, API-06) — a fixed-size
    record: an overall ``status``, a per-store state map (``stores``), the foreign engine's own
    liveness fields (``engine``, keyed by ``"interpreter_present"``/``"working_dir_present"``/
    ``"v1_reachable"``, 11-09 D-14) and a client presence map (``clients``, keyed by ``"llm"``/
    ``"embedding"``/``"rerank"``, 08-05 D-08): whether a client is wired under each key — never a
    URL, model name or key, never a live probe. ``status`` is ``ok`` only when both the ``llm`` and
    ``embedding`` clients are wired (11-09 D-14 amends Phase 8 D-08); ``rerank`` stays optional.

    ``engine_reason`` (11-09, research Q5, D-12) is ``None`` when nothing is wrong, else short fixed
    text joined by ``"; "``, e.g. ``"v1 not configured: missing EMBEDDING_DIM"`` or ``"model
    clients not configured"``. It names configuration keys only, never their values.

    ``stores`` (Phase 10 D-14, Q3) is keyed ``"<kind>:<namespace>"`` over every namespace of every
    shipped wiring, e.g. ``"kv:text_chunks"``, ``"graph:chunk_entity_relation"``,
    ``"vector:chunks"``. Each value is ``ok``, ``absent`` (nothing on disk yet), ``corrupted`` or
    ``busy`` (held by another process). The probes are read-only and create nothing. Any store that
    is not ``ok`` makes ``status`` ``degraded``, so a fresh install is all ``absent`` and
    ``degraded``; there is no separate not-initialized state. A single-modality install reads
    ``degraded`` while the other modality's stores are ``absent`` (11-09 D-14: health reports every
    shipped namespace). Never raises for an unreachable store
    or an unreachable foreign engine — an unreachable participant is reported as unreachable, which
    is what a health check is for."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok", "degraded"]
    stores: dict[str, Literal["ok", "absent", "corrupted", "busy"]]
    engine: dict[str, bool]
    clients: dict[str, bool]
    engine_reason: str | None = None


def generated_on_disk_name(document_id: str, suffix: str = _ON_DISK_SUFFIX) -> str:
    """The on-disk file name for a raw-upload document, built only from ``document_id`` (server-
    minted or caller-supplied) and ``suffix`` (``.bin`` by default; the engine passes the value
    ``upload_suffix`` returned). Raises :class:`InvalidDocumentIdError` for any ``document_id`` that
    is not a non-empty token of letters, digits, ``_`` or ``-`` -- no path separator, no dot, no
    newline, so the returned name can never resolve outside the directory it is joined under.
    """
    if not _DOCUMENT_ID_TOKEN_RE.fullmatch(document_id):
        raise InvalidDocumentIdError(document_id=document_id)
    return f"{document_id}{suffix}"


def upload_suffix(file_name: str | None) -> str:
    """11-05 (D-09, T-11-09): the lower-cased suffix of ``file_name``'s basename (backslashes read
    as separators, so ``..\\a.PDF`` gives ``.pdf`` and ``a.[mineru].pdf`` gives ``.pdf``, dropping
    v1's parser hint). Raises :class:`UnsupportedUploadTypeError` unless it is a plain
    ``\\.[a-z0-9]{1,8}`` token in :data:`ACCEPTED_UPLOAD_SUFFIXES`; the refusal names the suffix
    only when it is such a token, otherwise ``""``, so no caller text is echoed."""
    suffix = PurePosixPath((file_name or "").replace("\\", "/")).suffix.lower()
    if not _SUFFIX_RE.fullmatch(suffix):
        raise UnsupportedUploadTypeError(suffix="")
    if suffix not in ACCEPTED_UPLOAD_SUFFIXES:
        raise UnsupportedUploadTypeError(suffix=suffix)
    return suffix


__all__ = [
    "MAX_DOCUMENT_BYTES",
    "MAX_PAGE_SIZE",
    "IngestDocument",
    "IngestJob",
    "DeletionOutcome",
    "Page",
    "checked_page",
    "DocumentStatusEntry",
    "MAX_ERROR_MESSAGE_CHARS",
    "scrub_error_message",
    "JobStatus",
    "CorpusStatus",
    "DocumentCounts",
    "HealthReport",
    "generated_on_disk_name",
    "ACCEPTED_UPLOAD_SUFFIXES",
    "upload_suffix",
]
