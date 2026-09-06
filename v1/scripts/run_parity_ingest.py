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


class UnparseableExtraBodyError(RuntimeError):
    """Raised when an ``OPENAI_LLM_EXTRA_BODY``-shaped env var is set but not valid JSON — the
    exact defect reproduced during 03-11-PLAN.md's planning: bash's quote-removal on an unquoted
    ``.env.parity`` assignment strips the inner double quotes before the process ever sees the
    value. Named so the refusal happens once at startup rather than once per chunk inside an
    extraction call whose failure was previously visible only in per-document ``error_msg``.
    """

    def __init__(self, env_var: str, raw_value: str):
        self.env_var = env_var
        self.raw_value = raw_value
        super().__init__(
            f"{env_var} is set but is not valid JSON: {raw_value!r}. If this value is set in "
            "v1/.env.parity (or v1/parity-env.txt), wrap it in single quotes so bash's "
            "`set -a && . .env.parity` sourcing does not strip the inner double quotes — see "
            "v1/README-PARITY.md."
        )


def _extra_body(env_var: str) -> dict:
    raw = os.getenv(env_var)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UnparseableExtraBodyError(env_var, raw) from exc


def _validate_extra_body_env() -> None:
    """Call every ``_extra_body``-consumed env var once at startup, before ``initialize_rag()``,
    so an unparseable value refuses immediately instead of raising once per chunk inside an
    extraction call.
    """
    _extra_body("OPENAI_LLM_EXTRA_BODY")


def _all_documents_processed(working_dir: Path) -> tuple[bool, list[tuple[str, str]]]:
    """Read back document statuses from ``kv_store_doc_status.json`` after ``finalize_storages()``.
    Returns ``(all_processed, failures)`` where ``failures`` is a list of
    ``(doc_id, error_msg)`` for every document not at status ``processed``.
    """
    status_path = working_dir / "kv_store_doc_status.json"
    if not status_path.exists():
        return False, [("<all>", f"doc status file not found at {status_path}")]
    statuses = json.loads(status_path.read_text(encoding="utf-8"))
    failures = [
        (doc_id, record.get("error_msg", "<no error_msg recorded>"))
        for doc_id, record in statuses.items()
        if record.get("status") != "processed"
    ]
    return not failures, failures


def _entity_and_relation_sidecars_both_empty(working_dir: Path) -> bool:
    """The exact signature of the OPENAI_LLM_EXTRA_BODY defect: chunks present (naive/bypass
    embed fine, never touching ``_extra_body``) while both extraction-derived sidecars are empty.
    """

    def _is_empty(name: str) -> bool:
        path = working_dir / name
        if not path.exists():
            return True
        try:
            return not json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return True

    return _is_empty("faiss_index_entities.index.meta.json") and _is_empty(
        "faiss_index_relationships.index.meta.json"
    )


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

    try:
        _validate_extra_body_env()
    except UnparseableExtraBodyError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    documents = _load_corpus_documents()
    print(f"loaded {len(documents)} corpus documents from {_CORPUS_DIR}")

    _WORKING_DIR.mkdir(parents=True, exist_ok=True)
    rag = await initialize_rag()
    try:
        for doc_id, text in documents:
            print(f"ingesting {doc_id}...")
            await rag.ainsert(text, ids=doc_id, file_paths=f"{doc_id}.txt")
    finally:
        await rag.finalize_storages()

    all_processed, failures = _all_documents_processed(_WORKING_DIR)
    if not all_processed:
        print(
            f"ingest FAILED: {len(failures)} document(s) did not reach status 'processed':",
            file=sys.stderr,
        )
        for doc_id, error_msg in failures:
            print(f"  - {doc_id}: {error_msg}", file=sys.stderr)
        raise SystemExit(1)

    if _entity_and_relation_sidecars_both_empty(_WORKING_DIR):
        print(
            "ingest FAILED: every document reports status 'processed', but both "
            "faiss_index_entities.index.meta.json and faiss_index_relationships.index.meta.json "
            "are empty while chunks are present — this is the exact signature of the "
            "OPENAI_LLM_EXTRA_BODY defect (extraction silently produced no entities/relations). "
            "Refusing to report this as a completed ingest.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"ingest complete. index written under {_WORKING_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
