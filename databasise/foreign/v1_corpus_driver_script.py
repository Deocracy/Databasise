"""Subprocess entry point for LightRAG's corpus-side operations — ingest (05-01-PLAN.md Task 1),
delete and status (05-03/05-04, added by name in later plans' driver-script extensions).

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
implements ``op == "ingest"`` (05-01-PLAN.md Task 1), ``op == "delete"`` and ``op == "entities"``
(05-03-PLAN.md Task 1), and ``op == "entity_info"`` (05-03-PLAN.md Task 3) — any other ``op``
value exits 1 with a named message rather than a silent no-op (05-04 adds the status branch).

``op == "ingest"``'s job carries ``{"documents": [{"id": str, "text": str}, ...], "track_id": str |
None, "file_paths": [str, ...] | None, "docs_format": str | None}`` (``file_paths``/``docs_format``
are the raw-upload extension, 05-01-PLAN.md Task 3). Builds v1's ``LightRAG`` facade against
``working_dir`` using the same env-var-driven configuration
``v1/scripts/run_parity_ingest.py``/``databasise/parity/v1_driver_script.py`` already use, runs the
ingest via ``apipeline_enqueue_documents`` + ``apipeline_process_enqueue_documents`` — never
``ainsert`` — because the two-call form is the path that accepts an explicit ``track_id`` the seam
hands back to the caller as its job id, and writes one JSON object to stdout:
``{"track_id": str, "enqueued": int, "usage": {...} | None}``. ``usage`` carries whatever token
accounting v1 exposes for the run, or ``None`` when v1 reports none (which is every call today —
``apipeline_process_enqueue_documents`` returns no per-run token count) — never a fabricated zero.

``op == "delete"``'s job carries ``{"doc_id": str, "delete_llm_cache": bool}``. Calls v1's own
``rag.adelete_by_doc_id(doc_id, delete_llm_cache=...)`` — never reimplementing or wrapping its
reference-counting logic, which already subtracts the deleted document's chunk ids from each
affected entity's/relation's ``source_id`` set and deletes the entity/edge only when the remaining
set is empty, rebuilding it from surviving sources otherwise (a helper in ``v1/lightrag/utils.py``,
called only on the v1 side, never copied onto the machine side). Writes one JSON object built from
the returned ``DeletionResult``:
``{"status": str, "doc_id": str, "message": str, "status_code": int, "file_path": str | None}``. A
v1-side status of ``"not_found"`` or ``"not_allowed"`` is a *successful* driver run reporting that
status — exit 0, letting the machine map it; only an exception exits 1.

``op == "entities"``'s job carries ``{"doc_id": str}`` — used only by 05-03-PLAN.md Task 3's real
graph-aware-cleanup proof. Reads the named document's own chunk ids from v1's doc-status store
(the same ``chunks_list`` field ``adelete_by_doc_id`` itself reads), then walks every entity label
in the graph (``chunk_entity_relation_graph.get_all_labels()``) via v1's own public
``rag.get_entity_info()`` accessor — never reaching into a storage implementation directly — and
returns ``{"chunk_ids": [...], "entities": {<entity_name>: [<source_id>, ...]}}`` for exactly the
entity names whose own ``source_id`` set names at least one of the document's chunk ids.
``chunk_ids`` is the same document's own chunk id list, returned alongside the entity map so the
caller can partition it into "shared" (an entity's ``source_id`` set names a chunk outside
``chunk_ids``) versus "orphan-only" (every chunk id in the set is one of ``chunk_ids``) without a
second round trip. An absent document (no doc-status record) returns
``{"chunk_ids": None, "entities": {}}`` rather than raising.

``op == "entity_info"``'s job carries ``{"entity_names": [str, ...]}`` — used only by
05-03-PLAN.md Task 3's real graph-aware-cleanup proof, for its post-deletion re-check: a completed
deletion removes the document's own doc-status record, so ``op == "entities"`` can no longer look
entities up by ``doc_id`` for that document. This op instead looks each named entity up directly
via v1's own ``get_entity_info`` accessor and returns
``{"entities": {<entity_name>: [<source_id>, ...] | None}}`` — ``None`` for a name whose graph
node no longer exists, never omitted from the map.

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
from typing import Any

from lightrag import LightRAG
from lightrag.constants import FULL_DOCS_FORMAT_RAW, GRAPH_FIELD_SEP
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

_KNOWN_OPS = ("ingest", "delete", "entities", "entity_info")


class UnknownOpError(ValueError):
    """A job named an ``op`` this driver does not implement — refused by name, never a silent
    no-op (plans 05-03/05-04 add the missing branches)."""

    def __init__(self, op: str):
        self.op = op
        super().__init__(f"unknown op {op!r}; this driver implements {_KNOWN_OPS!r}")


def _extra_body(env_var: str) -> dict[str, Any]:
    raw = os.getenv(env_var)
    return json.loads(raw) if raw else {}


async def _llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    keyword_extraction: bool = False,
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
        **kwargs,
    )


async def _build_rag(working_dir: str) -> LightRAG:
    """Mirrors ``databasise/parity/v1_driver_script.py``'s own ``_build_rag`` exactly — the same
    env-var-driven pinned configuration, against the corpus's own persistent ``working_dir``
    (accumulating across ingest calls) rather than a fresh one per call.
    """
    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=_llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.environ["EMBEDDING_DIM"]),
            max_token_size=8192,
            func=partial(
                openai_embed.func,  # unwrap: avoid double EmbeddingFunc wrapping
                model=os.environ["EMBEDDING_MODEL"],
                base_url=os.environ["EMBEDDING_BINDING_HOST"],
                api_key=os.environ["EMBEDDING_BINDING_API_KEY"],
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


async def _run_ingest(job: dict[str, Any]) -> dict[str, Any]:
    documents = job.get("documents") or []
    track_id = job.get("track_id")
    working_dir = str(job["working_dir"])
    file_paths = job.get("file_paths")
    docs_format = job.get("docs_format") or FULL_DOCS_FORMAT_RAW

    ids = [str(doc["id"]) for doc in documents]
    texts = [str(doc.get("text") or "") for doc in documents]

    rag = await _build_rag(working_dir)
    try:
        result_track_id = await rag.apipeline_enqueue_documents(
            input=texts,
            ids=ids,
            file_paths=file_paths,
            track_id=track_id,
            docs_format=docs_format,
        )
        await rag.apipeline_process_enqueue_documents()
    finally:
        await rag.finalize_storages()

    # v1's apipeline_process_enqueue_documents() exposes no per-run token count — usage is always
    # None here, never a fabricated zero (see module docstring).
    return {"track_id": result_track_id, "enqueued": len(documents), "usage": None}


async def _run_delete(job: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(job["doc_id"])
    delete_llm_cache = bool(job.get("delete_llm_cache", False))
    working_dir = str(job["working_dir"])

    rag = await _build_rag(working_dir)
    try:
        result = await rag.adelete_by_doc_id(doc_id, delete_llm_cache=delete_llm_cache)
    finally:
        await rag.finalize_storages()

    return {
        "status": result.status,
        "doc_id": result.doc_id,
        "message": result.message,
        "status_code": result.status_code,
        "file_path": result.file_path,
    }


async def _run_entities(job: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(job["doc_id"])
    working_dir = str(job["working_dir"])

    rag = await _build_rag(working_dir)
    try:
        doc_status_data = await rag.doc_status.get_by_id(doc_id)
        if not doc_status_data:
            return {"chunk_ids": None, "entities": {}}
        doc_chunk_ids = list(doc_status_data.get("chunks_list") or [])
        chunk_ids_set = set(doc_chunk_ids)

        labels = await rag.chunk_entity_relation_graph.get_all_labels()
        entities: dict[str, list[str]] = {}
        for label in labels:
            info = await rag.get_entity_info(label)
            source_id = info.get("source_id")
            if not source_id:
                continue
            source_ids = [chunk for chunk in source_id.split(GRAPH_FIELD_SEP) if chunk]
            if chunk_ids_set & set(source_ids):
                entities[label] = source_ids
    finally:
        await rag.finalize_storages()

    return {"chunk_ids": doc_chunk_ids, "entities": entities}


async def _run_entity_info(job: dict[str, Any]) -> dict[str, Any]:
    """05-03-PLAN.md Task 3's "after" leg: ``op == "entities"`` keys off a document's own
    doc-status record, which a completed deletion has already removed — there is no longer a
    ``doc_id`` to look entities up by. This op instead looks up a caller-supplied list of entity
    *names* (captured from an earlier ``entities`` call, before deletion) directly via v1's own
    ``get_entity_info`` accessor, so post-deletion state can be re-checked by name regardless of
    whether the originating document's doc-status record still exists. Returns
    ``{"entities": {<entity_name>: [<source_id>, ...] | None}}`` — ``None`` for a name whose graph
    node no longer exists (or carries no ``source_id``), never omitted from the map.
    """
    entity_names = job.get("entity_names") or []
    working_dir = str(job["working_dir"])

    rag = await _build_rag(working_dir)
    try:
        entities: dict[str, list[str] | None] = {}
        for name in entity_names:
            info = await rag.get_entity_info(name)
            source_id = info.get("source_id")
            entities[name] = (
                [chunk for chunk in source_id.split(GRAPH_FIELD_SEP) if chunk] if source_id else None
            )
    finally:
        await rag.finalize_storages()

    return {"entities": entities}


async def _run(job: dict[str, Any]) -> dict[str, Any]:
    op = job["op"]
    if op == "ingest":
        return await _run_ingest(job)
    if op == "delete":
        return await _run_delete(job)
    if op == "entities":
        return await _run_entities(job)
    if op == "entity_info":
        return await _run_entity_info(job)
    raise UnknownOpError(op)


def main() -> int:
    try:
        job = json.loads(sys.stdin.read())
        result = asyncio.run(_run(job))
    except Exception:
        traceback.print_exc()
        return 1
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
