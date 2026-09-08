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
implements only ``op == "ingest"``, whose job carries
``{"documents": [{"id": str, "text": str}, ...], "track_id": str | None, "file_paths": [str, ...] |
None, "docs_format": str | None}`` (``file_paths``/``docs_format`` are the raw-upload extension,
05-01-PLAN.md Task 3) — any other ``op`` value exits 1 with a named message rather than a silent
no-op (plans 05-03 and 05-04 add the delete and status branches). Builds v1's ``LightRAG`` facade
against ``working_dir`` using the same env-var-driven configuration
``v1/scripts/run_parity_ingest.py``/``databasise/parity/v1_driver_script.py`` already use, runs the
ingest via ``apipeline_enqueue_documents`` + ``apipeline_process_enqueue_documents`` — never
``ainsert`` — because the two-call form is the path that accepts an explicit ``track_id`` the seam
hands back to the caller as its job id, and writes one JSON object to stdout:
``{"track_id": str, "enqueued": int, "usage": {...} | None}``. ``usage`` carries whatever token
accounting v1 exposes for the run, or ``None`` when v1 reports none (which is every call today —
``apipeline_process_enqueue_documents`` returns no per-run token count) — never a fabricated zero.

A malformed job, a v1-side ingest failure, or any other exception prints a traceback to stderr and
exits 1 — the caller (``v1_corpus_adapter.py``) treats any non-zero exit as a refusal carrying that
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
from lightrag.constants import FULL_DOCS_FORMAT_RAW
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

_KNOWN_OPS = ("ingest",)


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


async def _run(job: dict[str, Any]) -> dict[str, Any]:
    op = job["op"]
    if op == "ingest":
        return await _run_ingest(job)
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
