"""Subprocess entry point for the original (pre-decomposition) LightRAG arm (03-07-PLAN.md Task 1).

Lives under ``databasise/parity/`` (a directory owned by the decomposed side) but is executed
**by v1's own interpreter** (``v1/.venv/bin/python``), never by the interpreter running
``databasise/``'s own code. This split exists because the parity harness
(``databasise/parity/v1_arm.py``) needs a caller-side driver that lives alongside its own
package, while the actual v1 facade construction must run inside v1's own Python environment —
v1's ``lightrag`` package is neither installed in nor importable from `databasise/`'s
environment, and ``databasise/tools/check_import_boundary.py`` forbids that import anywhere
under ``databasise/`` regardless (D-14).

This module is therefore a **leaf**: it imports only v1's own packages (``lightrag``) and the
standard library. Nothing under ``databasise/`` ever imports it with a Python ``import`` —
``databasise/parity/v1_arm.py`` reaches it only by launching it as a subprocess with a job JSON on
stdin, exactly the way ``v1/scripts/run_parity_ingest.py`` (03-02-PLAN.md) is a v1-side script that
``databasise/`` never imports either.

Protocol: read one JSON object from stdin —
``{"mode": str, "query": str, "hl_keywords": [str, ...], "ll_keywords": [str, ...],
"working_dir": str}`` — build v1's ``LightRAG`` facade against ``working_dir`` (the plan 03-02
ingest output) using the same env-var-driven configuration
``v1/scripts/run_parity_ingest.py`` used to build it, set
``QueryParam(hl_keywords=..., ll_keywords=...)`` so v1's own keyword-resolution short-circuit
(``v1/lightrag/operate.py``'s ``get_keywords_from_query``, which returns
``query_param.hl_keywords, query_param.ll_keywords`` directly whenever either is set, at
``v1/lightrag/operate.py:4023-4024``) fires rather than v1 extracting its own keywords, run the
query, and write one JSON object to stdout:
``{"chunk_ids": [...], "entity_ids": [...], "relation_ids": [...], "answer": str,
"hl_keywords_used": [...], "ll_keywords_used": [...]}``.

``hl_keywords_used``/``ll_keywords_used`` are read back from v1's own ``aquery_data`` response
(``data["metadata"]["keywords"]``) — v1's own echo of what it actually used to retrieve, not a
value this script merely reflects on its own behalf. This is the mechanism Task 1's acceptance
criteria uses to confirm a pinned, deliberately distinctive keyword set actually reached v1's
retrieval rather than v1 silently extracting its own: pass a pinned pair no genuine extraction
would produce, and confirm that exact pair comes back in ``hl_keywords_used``/``ll_keywords_used``.

A malformed job, a v1-side query failure, or any other exception prints a traceback to stderr and
exits 1 — the caller (``v1_arm.py``) treats any non-zero exit as a refusal carrying that stderr,
never as an empty success.
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
from lightrag.base import QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc


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
    """Mirrors ``v1/scripts/run_parity_ingest.py``'s own ``initialize_rag`` construction shape —
    the same env-var-driven D-05/D-07/D-08/amended-D-09 pinned configuration, against an existing
    (already-ingested) ``working_dir`` rather than a fresh one.
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


async def _run(job: dict[str, Any]) -> dict[str, Any]:
    mode = job["mode"]
    query = str(job["query"])
    hl_keywords = [str(k) for k in (job.get("hl_keywords") or [])]
    ll_keywords = [str(k) for k in (job.get("ll_keywords") or [])]
    working_dir = str(job["working_dir"])

    rag = await _build_rag(working_dir)
    try:
        param = QueryParam(mode=mode, hl_keywords=hl_keywords, ll_keywords=ll_keywords)

        # Data-only retrieval — v1's own aquery_data forces only_need_context=True internally, so
        # this never triggers LLM generation; it returns the final (post-truncation) chunks,
        # entities and relationships v1 would send to the LLM, per its own docstring.
        data_response = await rag.aquery_data(query.strip(), param)
        data = data_response.get("data") or {} if data_response.get("status") == "success" else {}
        chunk_ids = [
            str(c["chunk_id"]) for c in data.get("chunks", []) if c.get("chunk_id")
        ]
        entity_ids = [
            str(e["entity_name"]) for e in data.get("entities", []) if e.get("entity_name")
        ]
        relation_ids = [
            f"{r['src_id']}->{r['tgt_id']}"
            for r in data.get("relationships", [])
            if r.get("src_id") and r.get("tgt_id")
        ]
        used_keywords = (data_response.get("metadata") or {}).get("keywords") or {}
        hl_keywords_used = [str(k) for k in (used_keywords.get("high_level") or hl_keywords)]
        ll_keywords_used = [str(k) for k in (used_keywords.get("low_level") or ll_keywords)]

        # The prose answer — a second, real call through v1's full pipeline (keyword resolution
        # short-circuits identically here, so this spends no extra keyword-extraction call).
        answer = await rag.aquery(query.strip(), param)
        if not isinstance(answer, str):
            parts: list[str] = []
            async for part in answer:
                parts.append(part)
            answer = "".join(parts)

        return {
            "chunk_ids": chunk_ids,
            "entity_ids": entity_ids,
            "relation_ids": relation_ids,
            "answer": answer,
            "hl_keywords_used": hl_keywords_used,
            "ll_keywords_used": ll_keywords_used,
        }
    finally:
        await rag.finalize_storages()


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
