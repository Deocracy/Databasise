"""Runs stock v1 LightRAG's ingest over the Phase 3 parity corpus snapshot exactly once
(03-02-PLAN.md Task 2, D-01).

This script lives under ``v1/`` rather than ``databasise/`` because it necessarily imports v1's
own ``lightrag`` package to drive the ingest — ``databasise/tools/check_import_boundary.py``
forbids that import anywhere under ``databasise/`` (D-14). It reads the corpus fixture's on-disk
files directly (``MANIFEST.json`` + one ``.txt`` per document under
``databasise/tests/fixtures/corpus/``) rather than importing ``databasise.parity.corpus`` — v1
never imports from ``databasise/`` either, keeping the boundary a two-way wall, not a one-way one.

Usage (see v1/README-PARITY.md):

    cd v1 && set -a && . .env.parity && set +a && uv run python scripts/run_parity_ingest.py

Writes v1's native Cozo graph, Faiss index + ``.index.meta.json`` sidecar, and JSON KV state into
``v1/.parity_working_dir/`` (gitignored — a build artifact; see Task 3's
``databasise/parity/import_index.py`` for the verified import into the v2 namespace layout).

**Run exactly once.** Every parity number recorded in plans 03-07 and 03-09 is keyed to this one
build (D-01, rated costly) — re-running this script means re-running the whole comparison.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from functools import partial
from pathlib import Path

from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

_V1_ROOT = Path(__file__).resolve().parent.parent
_CORPUS_DIR = _V1_ROOT.parent / "databasise" / "tests" / "fixtures" / "corpus"
_WORKING_DIR = _V1_ROOT / ".parity_working_dir"


def _load_corpus_documents() -> list[tuple[str, str]]:
    """Read the corpus fixture's manifest + on-disk document text directly (no
    ``databasise.parity.corpus`` import — see module docstring). Returns ``(doc_id, text)`` pairs,
    sorted by id for a deterministic ingest order.
    """
    manifest_path = _CORPUS_DIR / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = []
    for doc_id in sorted(manifest["documents"]):
        text = (_CORPUS_DIR / "documents" / f"{doc_id}.txt").read_text(encoding="utf-8")
        documents.append((doc_id, text))
    return documents


def _extra_body(env_var: str) -> dict:
    raw = os.getenv(env_var)
    return json.loads(raw) if raw else {}


async def llm_model_func(
    prompt, system_prompt=None, history_messages=None, keyword_extraction=False, **kwargs
) -> str:
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


async def initialize_rag() -> LightRAG:
    rag = LightRAG(
        working_dir=str(_WORKING_DIR),
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.environ["EMBEDDING_DIM"]),
            max_token_size=8192,
            func=partial(
                openai_embed.func,  # unwrap: avoid double EmbeddingFunc wrapping (matches
                # v1/examples/lightrag_openai_compatible_demo.py's documented pattern)
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


async def main() -> None:
    required = [
        "LLM_MODEL",
        "LLM_BINDING_API_KEY",
        "LLM_BINDING_HOST",
        "EMBEDDING_MODEL",
        "EMBEDDING_BINDING_HOST",
        "EMBEDDING_BINDING_API_KEY",
        "EMBEDDING_DIM",
        "LIGHTRAG_KV_STORAGE",
        "LIGHTRAG_GRAPH_STORAGE",
        "LIGHTRAG_VECTOR_STORAGE",
        "LIGHTRAG_DOC_STATUS_STORAGE",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(
            f"missing required env vars: {missing} — source v1/.env.parity first "
            "(see v1/README-PARITY.md)",
            file=sys.stderr,
        )
        raise SystemExit(1)

    documents = _load_corpus_documents()
    print(f"loaded {len(documents)} corpus documents from {_CORPUS_DIR}")

    _WORKING_DIR.mkdir(parents=True, exist_ok=True)
    rag = await initialize_rag()
    try:
        for doc_id, text in documents:
            print(f"ingesting {doc_id}...")
            await rag.ainsert(text, ids=doc_id, file_paths=f"{doc_id}.txt")
        print(f"ingest complete. index written under {_WORKING_DIR}")
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
