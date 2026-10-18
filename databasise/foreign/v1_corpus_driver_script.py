"""Subprocess entry point for LightRAG's corpus-side operations: ``ingest``, ``delete``, ``status``
and ``health`` — the protocol of ``lightrag/full-ingest@0.2.0`` and ``lightrag/full-delete@0.2.0``
(11-03-PLAN.md, D-06; pinned by ``tests/parts_core/lightrag/test_full_ingest_compat.py``).

Lives under ``databasise/foreign/`` (a directory owned by the decomposed side) but is executed
**by v1's own interpreter** (``v1/.venv/bin/python``), never by the interpreter running
``databasise/``'s own code. This split exists because the machine-side adapter
(``databasise/foreign/v1_corpus_adapter.py``) needs a caller-side driver that lives alongside its
own package, while the actual v1 facade construction and pipeline calls must run inside v1's own
Python environment — v1's ``lightrag`` package is neither installed in nor importable from
``databasise/``'s environment, and ``databasise/tools/check_import_boundary.py`` forbids that
import anywhere under ``databasise/`` regardless (D-14).

This module is therefore a **leaf**: it imports only v1's own packages (``lightrag``) and the
standard library. Nothing under ``databasise/`` ever imports it with a Python ``import`` —
``databasise/foreign/v1_corpus_adapter.py`` reaches it only by launching it as a subprocess with a
job JSON on stdin, mirroring ``databasise/parity/v1_driver_script.py``'s own precedent for the
query side exactly.

Protocol: read one JSON object ``{"op": str, "working_dir": str, ...}`` from stdin. This module
implements exactly ``ingest``, ``delete``, ``status`` and ``health``; any other ``op`` (the removed
``entities``/``entity_info`` included, D-05) exits 1 with a named ``UnknownOpError``.

**Configuration check (exit 3, D-12).** Before any op but ``health`` runs, ``main`` checks the
environment v1 sees (the adapter's overlay plus ``v1/.env``). Every op needs ``EMBEDDING_DIM``,
``EMBEDDING_MODEL``, ``EMBEDDING_BINDING_HOST``, ``EMBEDDING_BINDING_API_KEY`` and the four
``LIGHTRAG_*_STORAGE`` keys; ``ingest`` and ``delete`` also need ``LLM_MODEL``,
``LLM_BINDING_API_KEY`` and ``LLM_BINDING_HOST``. A blank value counts as missing. The storage keys
must name ``JsonKVStorage``, ``CozoGraphStorage``, ``FaissVectorDBStorage`` and
``JsonDocStatusStorage``, the backends the ``lightrag/v1-index-sync`` mirror reads (D-01). On any
problem it writes ``{"error": "v1_not_configured", "missing_keys": [...], "unsupported_keys":
[...]}`` and exits 3 — key names only, never values.

``op == "ingest"``'s job carries ``{"documents": [{"id": str, "text": str}, ...], "track_id": str |
None, "file_paths": [str, ...] | None, "docs_format": str | None, "input_dir": str | None,
"retry_doc_ids": [str, ...] | None}``. Builds v1's ``LightRAG`` facade against ``working_dir`` using
the same env-var-driven configuration ``databasise/parity/v1_driver_script.py`` uses, runs the
ingest via ``apipeline_enqueue_documents`` + ``apipeline_process_enqueue_documents`` — never
``ainsert`` — because the two-call form accepts the explicit ``track_id`` the seam hands back as
its job id, and writes ``{"track_id": str, "enqueued": int, "usage": {"llm": {...}, "embedding":
{...}}}`` to stdout (11-03-PLAN.md, D-06):

- ``docs_format == "pending_parse"`` (a staged upload, D-09) sets ``INPUT_DIR`` to ``input_dir`` and
  enqueues the file path with no ``ids=`` (``ids=`` forces RAW mode, which indexed empty text), so
  v1's own parser reads the file's bytes. v1 stores the basename as ``file_path``, mints
  ``doc-<md5(basename)>`` as its id and moves the source to ``<INPUT_DIR>/__parsed__/``. The id stem
  rule maps that row back to our id: the staged name is ``<document_id><suffix>``, so
  ``Path(file_path).stem`` is our document id. A text ingest keeps ``ids=`` (RAW) and v1's id is ours.
- Processing is restricted to this run's targets (D-08): v1's
  ``apipeline_process_enqueue_documents()`` otherwise reprocesses every PENDING, PROCESSING,
  PARSING, ANALYZING and FAILED document, billing for old failures. The driver wraps
  ``rag.doc_status.get_docs_by_statuses`` on this instance only. The targets are this track's rows
  that v1 did not mark ``metadata.is_duplicate``; with ``retry_doc_ids`` they are those ids resolved
  by the stem rule, and the returned ``track_id`` is the first target's own track id.
- ``enqueued`` is the requested count minus the duplicate rows v1 recorded under the caller's track
  id, read after processing (a content-hash duplicate on the file path appears only after parse);
  ``track_id`` is the caller's even when v1 returned ``None`` for a dropped duplicate (D-10).
- ``usage`` holds ``lightrag.utils.TokenTracker.get_usage()`` for the LLM and for embeddings, two
  trackers handed to the model functions with ``token_tracker=`` (D-13). They are never summed:
  the two figures come from different tokenizers.

``op == "delete"``'s job carries ``{"doc_id": str, "delete_llm_cache": bool}``. ``doc_id`` is our
document id, resolved to v1's id by the stem rule. Calls v1's own
``rag.adelete_by_doc_id(v1_id, delete_llm_cache=...)`` — never reimplementing or wrapping its
reference-counting logic, which already subtracts the deleted document's chunk ids from each
affected entity's/relation's ``source_id`` set and deletes the entity/edge only when the remaining
set is empty, rebuilding it from surviving sources otherwise (a helper in ``v1/lightrag/utils.py``,
called only on the v1 side, never copied onto the machine side). Writes one JSON object built from
the returned ``DeletionResult``:
``{"status": str, "doc_id": str, "message": str, "status_code": int, "file_path": str | None,
"usage": {"llm": {...}, "embedding": {...}}}`` — ``usage`` from the same two trackers as ingest,
because a partial-rebuild delete can reach the LLM (D-13). A v1-side status of ``"not_found"`` or
``"not_allowed"`` is a *successful* driver run reporting that status — exit 0, letting the machine
map it; only an exception exits 1.

``op == "status"``'s job carries ``{"track_id": str | None, "limit": int, "offset": int}``
(05-04-PLAN.md Task 1). Counts are always whole-corpus, read via ``rag.get_processing_status()``
(never filtered by ``track_id`` — v1 exposes no track-scoped counts). The document list is read
via ``rag.aget_docs_by_track_id(track_id)`` when a ``track_id`` is given, and otherwise via v1's
own doc-status store, listing every status via ``rag.doc_status.get_docs_by_statuses(list(DocStatus))``
— sorted by document id for a deterministic page, then sliced by ``offset``/``limit`` on this
(the v1) side, so an unbounded list never crosses the pipe. Writes
``{"counts": {<status>: <int>}, "documents": [{"document_id", "status", "updated_at",
"error_message"}, ...], "total": int}`` — ``total`` is the full (unsliced) match count for the
given ``track_id`` filter (or the whole corpus when ``track_id`` is ``None``), and
``error_message`` is only ever a real value for a document whose status is ``"failed"``, ``None``
otherwise.

``op == "health"`` reads no job key and builds no facade, so it creates no working dir (D-14). It
writes ``{"configured": bool, "missing_keys": [...], "unsupported_keys": [...]}`` from the same
configuration check (with the model keys included) and never exits 3; the engine checks the
working dir's existence itself.

A malformed job, a v1-side failure, or any other exception prints a traceback to stderr and exits
1 — the caller (``v1_corpus_adapter.py``) treats any non-zero exit as a refusal carrying that
stderr, never as an empty success.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from functools import partial
from pathlib import Path
from typing import Any

from lightrag import LightRAG
from lightrag.base import DocStatus
from lightrag.constants import FULL_DOCS_FORMAT_PENDING_PARSE, FULL_DOCS_FORMAT_RAW
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc, TokenTracker

_KNOWN_OPS = ("ingest", "delete", "status", "health")

# D-12/D-14: the keys v1 needs, checked by name before any op but health runs. The model keys
# matter only to ops that can call the model; health reports the full set.
_STORE_KEYS = (
    "EMBEDDING_DIM",
    "EMBEDDING_MODEL",
    "EMBEDDING_BINDING_HOST",
    "EMBEDDING_BINDING_API_KEY",
    "LIGHTRAG_KV_STORAGE",
    "LIGHTRAG_GRAPH_STORAGE",
    "LIGHTRAG_VECTOR_STORAGE",
    "LIGHTRAG_DOC_STATUS_STORAGE",
)
_MODEL_KEYS = ("LLM_MODEL", "LLM_BINDING_API_KEY", "LLM_BINDING_HOST")
_MODEL_OPS = ("ingest", "delete", "health")
# D-01: the lightrag/v1-index-sync mirror reads only these backends, so any other is refused.
_SUPPORTED_BACKENDS = {
    "LIGHTRAG_KV_STORAGE": "JsonKVStorage",
    "LIGHTRAG_GRAPH_STORAGE": "CozoGraphStorage",
    "LIGHTRAG_VECTOR_STORAGE": "FaissVectorDBStorage",
    "LIGHTRAG_DOC_STATUS_STORAGE": "JsonDocStatusStorage",
}


class UnknownOpError(ValueError):
    """A job named an ``op`` this driver does not implement — refused by name, never a silent
    no-op."""

    def __init__(self, op: str):
        self.op = op
        super().__init__(f"unknown op {op!r}; this driver implements {_KNOWN_OPS!r}")


def _config_problems(op: str) -> tuple[list[str], list[str]]:
    """``(missing_keys, unsupported_keys)`` for ``op``: key names only, never values (D-12). A
    blank value counts as missing, so an empty overlay value refuses whatever ``v1/.env`` holds."""
    required = _STORE_KEYS + (_MODEL_KEYS if op in _MODEL_OPS else ())
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    unsupported = [
        key
        for key, backend in _SUPPORTED_BACKENDS.items()
        if key not in missing and os.environ[key].strip() != backend
    ]
    return missing, unsupported


class MissingInputDirError(ValueError):
    """A ``pending_parse`` ingest named no ``input_dir``: v1 resolves the staged file's basename
    under ``INPUT_DIR``, so without it v1 would look in ``<cwd>/inputs`` and fail the document."""

    def __init__(self) -> None:
        super().__init__("a pending_parse ingest needs input_dir (the directory holding the staged files)")


def _extra_body(env_var: str) -> dict[str, Any]:
    raw = os.getenv(env_var)
    return json.loads(raw) if raw else {}


async def _llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    keyword_extraction: bool = False,
    token_tracker: TokenTracker | None = None,
    **kwargs: Any,
) -> str:
    del keyword_extraction  # unused — this script never lets v1 extract its own keywords
    return await openai_complete_if_cache(
        os.environ["LLM_MODEL"],
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        api_key=os.environ["LLM_BINDING_API_KEY"],
        base_url=os.environ["LLM_BINDING_HOST"],
        extra_body=_extra_body("OPENAI_LLM_EXTRA_BODY"),
        token_tracker=token_tracker,
        **kwargs,
    )


async def _build_rag(
    working_dir: str,
    *,
    llm_tracker: TokenTracker | None = None,
    embed_tracker: TokenTracker | None = None,
) -> LightRAG:
    """Mirrors ``databasise/parity/v1_driver_script.py``'s own ``_build_rag`` — the same
    env-var-driven pinned configuration, against the corpus's own persistent ``working_dir``
    (accumulating across ingest calls) rather than a fresh one per call. The trackers, when given,
    count every model call this process makes (D-13).
    """
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=partial(_llm_model_func, token_tracker=llm_tracker),
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.environ["EMBEDDING_DIM"]),
            max_token_size=8192,
            func=partial(
                openai_embed.func,  # unwrap: avoid double EmbeddingFunc wrapping
                model=os.environ["EMBEDDING_MODEL"],
                base_url=os.environ["EMBEDDING_BINDING_HOST"],
                api_key=os.environ["EMBEDDING_BINDING_API_KEY"],
                token_tracker=embed_tracker,
            ),
        ),
        kv_storage=os.environ["LIGHTRAG_KV_STORAGE"],
        graph_storage=os.environ["LIGHTRAG_GRAPH_STORAGE"],
        vector_storage=os.environ["LIGHTRAG_VECTOR_STORAGE"],
        doc_status_storage=os.environ["LIGHTRAG_DOC_STATUS_STORAGE"],
        enable_llm_cache=os.environ.get("ENABLE_LLM_CACHE", "false").lower() == "true",
    )
    await rag.initialize_storages()
    return rag


def _is_duplicate(row: Any) -> bool:
    return bool((getattr(row, "metadata", None) or {}).get("is_duplicate"))


def _our_id_matches(v1_id: str, file_path: str | None, our_id: str) -> bool:
    """The id stem rule: a text-ingested row keeps our id; a file-ingested ``doc-<md5>`` row maps
    back through its staged basename ``<document_id><suffix>``."""
    return v1_id == our_id or (v1_id.startswith("doc-") and Path(file_path or "").stem == our_id)


async def _resolve_v1_ids(rag: LightRAG, ids: list[str]) -> dict[str, Any]:
    """Our document ids -> ``{v1_id: row}`` for every v1 row the stem rule matches."""
    rows = await rag.doc_status.get_docs_by_statuses(list(DocStatus))
    wanted = [str(our_id) for our_id in ids]
    return {
        v1_id: row
        for v1_id, row in rows.items()
        if any(_our_id_matches(v1_id, row.file_path, our_id) for our_id in wanted)
    }


def _restrict_processing(rag: LightRAG, targets: set[str]) -> None:
    """Make this instance's pipeline see only ``targets`` (D-08): v1 reprocesses every in-flight
    or failed document on each ``apipeline_process_enqueue_documents()`` call otherwise."""
    original = rag.doc_status.get_docs_by_statuses

    async def only_targets(statuses: list[DocStatus]) -> dict[str, Any]:
        return {k: v for k, v in (await original(statuses)).items() if k in targets}

    rag.doc_status.get_docs_by_statuses = only_targets


async def _run_ingest(job: dict[str, Any]) -> dict[str, Any]:
    documents = job.get("documents") or []
    track_id = job.get("track_id")
    working_dir = str(job["working_dir"])
    file_paths = job.get("file_paths")
    docs_format = job.get("docs_format") or FULL_DOCS_FORMAT_RAW
    input_dir = job.get("input_dir")
    retry_doc_ids = job.get("retry_doc_ids") or []

    if docs_format == FULL_DOCS_FORMAT_PENDING_PARSE and not input_dir:
        raise MissingInputDirError()
    if input_dir:
        os.environ["INPUT_DIR"] = str(input_dir)  # v1 resolves staged basenames under this dir

    llm_tracker, embed_tracker = TokenTracker(), TokenTracker()
    rag = await _build_rag(working_dir, llm_tracker=llm_tracker, embed_tracker=embed_tracker)
    try:
        if retry_doc_ids:
            retry_rows = await _resolve_v1_ids(rag, retry_doc_ids)
            targets = set(retry_rows)
            requested = len(targets)
            track_id = next((row.track_id for row in retry_rows.values() if row.track_id), track_id)
        else:
            if docs_format == FULL_DOCS_FORMAT_PENDING_PARSE:
                requested = len(file_paths or [])
                result_track_id = await rag.apipeline_enqueue_documents(
                    input=[""] * requested,
                    file_paths=file_paths,
                    track_id=track_id,
                    docs_format=FULL_DOCS_FORMAT_PENDING_PARSE,
                )
            else:
                requested = len(documents)
                result_track_id = await rag.apipeline_enqueue_documents(
                    input=[str(doc.get("text") or "") for doc in documents],
                    ids=[str(doc["id"]) for doc in documents],
                    file_paths=file_paths,
                    track_id=track_id,
                    docs_format=docs_format,
                )
            track_id = track_id or result_track_id
            rows = await rag.aget_docs_by_track_id(track_id) if track_id else {}
            targets = {k for k, row in rows.items() if not _is_duplicate(row)}

        _restrict_processing(rag, targets)
        await rag.apipeline_process_enqueue_documents()

        dropped = 0
        if not retry_doc_ids and track_id:
            rows = await rag.aget_docs_by_track_id(track_id)
            dropped = sum(1 for row in rows.values() if _is_duplicate(row))
    finally:
        await rag.finalize_storages()

    return {
        "track_id": track_id,
        "enqueued": max(requested - dropped, 0),
        "usage": {"llm": llm_tracker.get_usage(), "embedding": embed_tracker.get_usage()},
    }


async def _run_delete(job: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(job["doc_id"])
    delete_llm_cache = bool(job.get("delete_llm_cache", False))
    working_dir = str(job["working_dir"])

    llm_tracker, embed_tracker = TokenTracker(), TokenTracker()
    rag = await _build_rag(working_dir, llm_tracker=llm_tracker, embed_tracker=embed_tracker)
    try:
        # The stem rule: our id names a file-ingested doc-<md5> row by its staged basename.
        v1_doc_id = next(iter(await _resolve_v1_ids(rag, [doc_id])), doc_id)
        result = await rag.adelete_by_doc_id(v1_doc_id, delete_llm_cache=delete_llm_cache)
    finally:
        await rag.finalize_storages()

    return {
        "status": result.status,
        "doc_id": result.doc_id,
        "message": result.message,
        "status_code": result.status_code,
        "file_path": result.file_path,
        "usage": {"llm": llm_tracker.get_usage(), "embedding": embed_tracker.get_usage()},
    }


async def _run_status(job: dict[str, Any]) -> dict[str, Any]:
    """A bounded, read-only status probe (05-04-PLAN.md Task 1). Calls only
    ``rag.get_processing_status``/``rag.aget_docs_by_track_id``/``rag.doc_status.get_docs_by_statuses``
    — v1's own public read accessors. This branch calls no mutating v1 API — never the write
    entry points ``_run_ingest``/``_run_delete`` above call — a later edit that adds one here is
    visibly wrong against this docstring's own stated scope: read-only, always.
    """
    track_id = job.get("track_id")
    limit = int(job.get("limit", 50))
    offset = int(job.get("offset", 0))
    working_dir = str(job["working_dir"])

    rag = await _build_rag(working_dir)
    try:
        counts = await rag.get_processing_status()
        if track_id:
            docs_by_id = await rag.aget_docs_by_track_id(track_id)
        else:
            docs_by_id = await rag.doc_status.get_docs_by_statuses(list(DocStatus))
    finally:
        await rag.finalize_storages()

    document_ids = sorted(docs_by_id.keys())
    total = len(document_ids)
    page_ids = document_ids[offset : offset + limit]

    documents: list[dict[str, Any]] = []
    for document_id in page_ids:
        doc_status = docs_by_id[document_id]
        status_value = getattr(doc_status.status, "value", str(doc_status.status))
        documents.append(
            {
                "document_id": document_id,
                "status": status_value,
                "updated_at": doc_status.updated_at,
                "error_message": doc_status.error_msg if status_value == DocStatus.FAILED.value else None,
            }
        )

    return {"counts": counts, "documents": documents, "total": total}


async def _run_health(job: dict[str, Any]) -> dict[str, Any]:
    """Facade-free (D-14): builds no ``LightRAG``, so it creates no working dir and opens no
    store. It reports only whether v1's configuration is usable; the engine checks the dir."""
    del job  # reads no job key
    missing, unsupported = _config_problems("health")
    return {"configured": not (missing or unsupported), "missing_keys": missing, "unsupported_keys": unsupported}


async def _run(job: dict[str, Any]) -> dict[str, Any]:
    op = job["op"]
    if op == "ingest":
        return await _run_ingest(job)
    if op == "delete":
        return await _run_delete(job)
    if op == "status":
        return await _run_status(job)
    if op == "health":
        return await _run_health(job)
    raise UnknownOpError(op)


def main() -> int:
    try:
        job = json.loads(sys.stdin.read())
        if job.get("op") != "health":
            missing, unsupported = _config_problems(str(job.get("op")))
            if missing or unsupported:
                # D-12: key names only, never values; exit 3 is the configuration channel.
                sys.stdout.write(
                    json.dumps({"error": "v1_not_configured", "missing_keys": missing, "unsupported_keys": unsupported})
                )
                return 3
        result = asyncio.run(_run(job))
    except Exception:
        traceback.print_exc()
        return 1
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
