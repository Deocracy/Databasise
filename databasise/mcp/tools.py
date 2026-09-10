"""``databasise.mcp.tools`` — the five tool names and their argument models (05-07-PLAN.md
Task 1, action D). Every field here is the seam's own model, reused rather than re-declared:
``QueryToolArgs`` carries the identical ``QueryObject``/``Selector`` REST deserializes into,
``ResolveToolArgs`` carries the identical ``EvidenceRef`` ``/evidence/resolve`` deserializes into,
and ``IngestToolArgs`` converts to the identical ``IngestDocument`` ``/documents`` deserializes
into. No logic in this module beyond field declarations and the one base64 decode
(``IngestToolArgs.to_ingest_document``) — a decode is deserialization, not behaviour; the actual
exactly-one-of-text/raw validation stays inside ``IngestDocument`` itself, the single source of
truth REST and MCP both defer to.

**§18.5, per tool — why an operation, not a selector (the growth-invariant test's own subject):**

- ``ingest``: writes a document into the corpus. No selector can express "put this document in" —
  there is no candidate wiring to choose among, only one fixed operation to perform (mirrors
  ``Databasise.ingest``'s own docstring). 06-10-PLAN.md: ``selector`` does not make this tool a
  query — it names *which fitted modality's index* the write lands in, the same thing it already
  names for ``query``; the tool remains one fixed operation across every modality.
- ``query``: retrieves an answer for a query object. The one intention every consumer has
  regardless of which modality is fitted underneath — the selector argument picks a *wiring*, the
  tool itself never becomes modality-specific.
- ``delete``: removes a document from the corpus. §19.6 requires this be a separate port from
  ingest (different declared effect, ``mutates_store`` vs ``writes_artifact``) — and a mutation is
  not an answering variant a selector could express. 06-10-PLAN.md: ``selector`` names which fitted
  modality's index the delete reaches, exactly as it does for ``ingest`` — a modality with no
  delete wiring refuses by name (``NoWritePathForModalityError``) rather than silently deleting
  from a different modality's index.
- ``status``: bounded introspection (job/corpus/counts/health) — a liveness/status read, never a
  modality selection; the ``scope`` argument distinguishes four *shapes of the same intention*
  ("tell me what's happening"), not four operations.
- ``resolve``: follows an evidence or trace reference the ``query`` tool already returned. One
  intention ("follow this reference"), so one tool with a ``scope`` argument — never two tools for
  what is the selector-versus-tool test applied honestly (05-07-PLAN.md's own deviation note).
- ``compare`` (06-03-PLAN.md, API-08): one query against N selectors in one call. Not expressible
  as a ``query`` call with a selector — a selector picks *one* arm, and comparison fans out over
  N of them in a single call, returning per-arm results the caller cannot get by calling ``query``
  N times and reassembling them itself (no shared query-object validation, no single refusal
  covering the whole request). A genuinely new operation, not a per-modality tool: registering a
  second modality (HippoRAG) added zero tools to this roster, and ``compare`` itself is
  modality-agnostic — it names no wiring, arm or modality of its own, only caller-supplied
  selectors, exactly like ``query``.
"""

from __future__ import annotations

import base64
import binascii
from typing import Literal

from pydantic import BaseModel, ConfigDict

from databasise.seam.corpus import IngestDocument
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.seam.refusals import MalformedBase64PayloadError
from databasise.seam.selectors import Selector

# §18.5's growth rule, applied to this transport: this tuple — never the registry, never the
# wiring set — is what the MCP server actually registers. Registering a second modality changes
# neither its length nor its members (proven by databasise/tests/mcp/test_tool_growth_invariant.py).
# Grew from five to six members in 06-03-PLAN.md: ``compare`` is a genuinely new operation (see
# module docstring), not a per-modality tool — the roster still grows by one for one operation,
# never by one per modality.
TOOL_NAMES: tuple[str, ...] = ("ingest", "query", "delete", "status", "resolve", "compare")

StatusScope = Literal["job", "corpus", "counts", "health"]
ResolveScope = Literal["evidence", "trace"]


class _ToolArgs(BaseModel):
    """The shared strict base for this module's own tool-argument DTOs — mirrors
    ``databasise.seam.rest._RequestModel`` exactly (never the seam's own frozen models
    themselves, which stay exactly as their owning phases declared them)."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class IngestToolArgs(_ToolArgs):
    """Carries ``IngestDocument``'s own two input shapes verbatim, plus a base64 encoding for the
    raw-bytes shape (an MCP tool argument has no native bytes type). ``to_ingest_document``
    performs the one decode this module is allowed — validation of "exactly one of text/raw"
    happens inside ``IngestDocument`` itself, never re-implemented here.
    """

    text: str | None = None
    document_id: str | None = None
    file_name: str | None = None
    raw_base64: str | None = None
    content_type: str | None = None
    selector: Selector | None = None

    def to_ingest_document(self) -> IngestDocument:
        if self.raw_base64 is not None:
            try:
                raw = base64.b64decode(self.raw_base64)
            except binascii.Error as exc:
                raise MalformedBase64PayloadError(field="raw_base64") from exc
        else:
            raw = None
        return IngestDocument(
            text=self.text,
            document_id=self.document_id,
            file_name=self.file_name,
            raw=raw,
            content_type=self.content_type,
        )


class QueryToolArgs(_ToolArgs):
    """Carries the seam's own ``QueryObject``/``Selector`` unchanged — the identical models
    ``databasise.seam.rest.QueryRequest`` deserializes into."""

    query: QueryObject
    selector: Selector | None = None


class CompareToolArgs(_ToolArgs):
    """Carries the seam's own ``QueryObject`` unchanged plus a list of ``Selector``s — the
    identical shapes ``databasise.seam.rest.CompareRequest`` deserializes into."""

    query: QueryObject
    selectors: list[Selector]


class DeleteToolArgs(_ToolArgs):
    """Carries the document id plus an optional §18.4 selector (06-10-PLAN.md Task 2) — the
    identical shape ``databasise.seam.rest.DeleteRequest``/path-parameter pair carries."""

    document_id: str
    selector: Selector | None = None


class StatusToolArgs(_ToolArgs):
    """``scope`` selects which of ``Databasise``'s four bounded read methods this call reaches;
    ``job_id`` is required only for ``scope="job"`` and ``limit``/``offset`` are read only for
    ``scope`` in ``{"job", "corpus"}`` — enforced in ``databasise.mcp.server``, not here (this
    module declares fields only, never behaviour)."""

    scope: StatusScope
    job_id: str | None = None
    limit: int = 50
    offset: int = 0


class ResolveToolArgs(_ToolArgs):
    """``scope="evidence"`` requires ``evidence_ref``; ``scope="trace"`` requires
    ``trace_reference`` (with an optional ``debug`` flag) — enforced in
    ``databasise.mcp.server``, not here."""

    scope: ResolveScope
    evidence_ref: EvidenceRef | None = None
    trace_reference: str | None = None
    debug: bool = False


__all__ = [
    "TOOL_NAMES",
    "CompareToolArgs",
    "DeleteToolArgs",
    "IngestToolArgs",
    "QueryToolArgs",
    "ResolveScope",
    "ResolveToolArgs",
    "StatusScope",
    "StatusToolArgs",
]
