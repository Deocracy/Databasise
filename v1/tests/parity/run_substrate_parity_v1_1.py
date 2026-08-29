"""Substrate-parity exit gate — v1.1: Cozo (graph) vs NetworkX (graph), Faiss fixed.

WHAT THIS PROVES
----------------
Swapping the embedded graph store NetworkX -> Cozo (with FaissVectorDBStorage
FIXED as the vector store for BOTH runs) does not change LightRAG's observable
behavior. We ingest ONE fixed corpus through both substrates and diff:
  * the extracted entity set (graph nodes) — symmetric difference must be empty
  * the extracted relation set (graph edges) — symmetric difference must be empty
  * per query mode, the referenced-chunk overlap (top-N, ranked) — at/above threshold
  * per query mode, the prose answer similarity — compared by similarity ONLY
    (LLM non-determinism is tolerated; prose never gates the result)

The GATE is STRUCTURAL: empty entity/relation symmetric difference + per-mode
top-N chunk overlap at/above CHUNK_OVERLAP_THRESHOLD. Prose is reported but is
NOT a gating criterion in v1.1 (it was a weak, gameable signal in v1.0).

This is v1.1 of tests/parity/run_substrate_parity.py. It is a NEW, SEPARATE,
STANDALONE entry point — the v1.0 file is left untouched. v1.1 differs from v1.0:
  - REUSES the fork's own binding helpers (api.config.parse_args +
    api.lightrag_server.create_embedding_function_from_args + the
    openai_complete_if_cache primitive) so it wires providers exactly like the
    real server pipeline, and explicitly sets llm_model_func / embedding_func
    (the fork RAISES ValueError if embedding_func is None — v1.0's bare
    LightRAG(working_dir=...) would never have ingested).
  - Uses the MANDATORY lifecycle: initialize_storages() / finalize_storages().
  - Has clearly LABELED START (preflight + setup) and STOP (teardown + report)
    sections; teardown runs in a finally block (cleanup even on exception).
  - FAILS CLOSED: writes the JSON result and KEEPS the temp dir on FAILURE so
    the diverging graph/vector artifacts survive for diagnosis; prints the
    NAMED diverging entities / relations / modes; uses distinct exit codes.
  - Fixes v1.0's silent-pass holes: empty-vs-empty chunk overlap is NO LONGER a
    free pass, edges are canonicalised (sorted pair) before diffing because the
    two backends emit different source/target orientation, and per-mode query
    exceptions surface as a distinct exit code (3), not an ambiguous "1".
  - Closes the DEGENERATE-EQUALITY holes a false-pass audit found in this v1.1:
      * NON-ZERO STRUCTURAL FLOOR — both backends MUST extract >= MIN_ENTITIES
        entities AND >= MIN_RELATIONS relations. Empty-equals-empty is a FAIL,
        because the fork's ingest pipeline fails closed-but-silent (marks docs
        FAILED, does not re-raise), so a corpus that extracted NOTHING would
        otherwise pass the symmetric-difference gate trivially.
      * POST-INGEST DOC-STATUS CHECK — after ainsert returns (a track_id is NOT
        proof of extraction success) we read doc-status and FAIL if ANY document
        is DocStatus.FAILED, or if no document reached PROCESSED, on either
        backend.
      * aquery_data status:"failure" is a HARD per-mode EXCEPTION (exit 3), not
        silently flattened to chunk_ids=[]. A broken retrieval subsystem can no
        longer masquerade as "this mode legitimately returned no chunks."
      * RANK-AWARE chunk comparison — set Jaccard PLUS a rank-correlation check
        of the shared ordering, with the top-N cap raised so it never truncates
        this corpus's pool. A ranking divergence on graph modes can no longer
        hide behind a small pool or a set-only metric.
      * GRAPH-DEPENDENT-MODE ASSERTION — local/global MUST return graph-derived
        chunks on both backends, so an empty-graph run cannot pass on Faiss
        vector fallback alone.
  - Applies determinism aids (OPENAI_LLM_TEMPERATURE=0.0, MAX_ASYNC_LLM=1) when
    the user has not already set them, so extraction is as stable as the
    provider allows; structural equivalence remains the gate regardless.

USAGE
-----
From the repo root:

    ./sourcerer-venv/Scripts/python.exe sourcerer-lightrag/tests/parity/run_substrate_parity_v1_1.py

Or from inside sourcerer-lightrag/:

    python tests/parity/run_substrate_parity_v1_1.py

PROVIDER CONFIG comes ONLY from sourcerer-lightrag/.env (or the shell env).
No keys are ever hardcoded, printed, logged, or written. The JSON report
records the provider/model FAMILY only.

REQUIRED ENV VARS (present in the fork .env)
--------------------------------------------
LLM_BINDING, LLM_BINDING_HOST, LLM_BINDING_API_KEY, LLM_MODEL,
EMBEDDING_BINDING, EMBEDDING_BINDING_HOST, EMBEDDING_BINDING_API_KEY,
EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_TOKEN_LIMIT.

EXIT CODES
----------
0 — PARITY PASS: structural equivalence within tolerance (entity + relation
    symmetric difference empty AND every mode's chunk overlap at/above threshold).
1 — PARITY FAIL: a structural divergence exceeded tolerance.
2 — SETUP / CONFIGURATION ERROR (missing env vars, missing/empty corpus,
    import failure, provider wiring failure).
3 — BACKEND / QUERY EXCEPTION: a backend crashed during ingest, ingest left a
    document in DocStatus.FAILED or produced zero PROCESSED documents, a query
    mode raised, or aquery_data returned status="failure" — all distinguished
    from a genuine structural divergence (which is exit 1).
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The fork .env lives at sourcerer-lightrag/.env. This file is at
# sourcerer-lightrag/tests/parity/, so the fork root is parents[2].
FORK_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = FORK_ROOT / ".env"

# REUSE the existing corpus — do NOT create a new one.
CORPUS_PATH = Path(__file__).parent / "corpus" / "sample.txt"

# Machine-readable result, written next to this script (NOT v1.0's file).
RESULT_PATH = Path(__file__).parent / "parity_result_v1_1.json"

PARITY_QUERY = (
    "What contributions did Alan Turing and Grace Hopper make to computing, "
    "and how are their works related to modern computers?"
)

# All five query modes, fixed query for each (bypass is intentionally excluded:
# it skips retrieval and returns no chunks, so it carries nothing to compare).
QUERY_MODES = ["naive", "local", "global", "hybrid", "mix"]

# Graph backends to compare. LIGHTRAG_VECTOR_STORAGE is FIXED to Faiss for BOTH.
BACKENDS = [
    ("CozoGraphStorage", "cozo"),
    ("NetworkXStorage", "networkx"),
]

# Fixed substrate for both runs (only the graph store varies).
VECTOR_STORE = "FaissVectorDBStorage"
KV_STORE = "JsonKVStorage"
DOC_STATUS_STORE = "JsonDocStatusStorage"

# Parity tolerances.
# STRUCTURAL gate: entity/relation symmetric difference MUST be exactly empty,
# and per-mode top-N referenced-chunk overlap MUST be at/above this threshold.
CHUNK_OVERLAP_THRESHOLD = 0.8     # Jaccard overlap of referenced chunk IDs per mode
# Compare ALL referenced chunks per mode, not a truncated prefix. With a small
# corpus the candidate pool is tiny; truncating to a fixed N can make two
# differently-RANKED lists look set-identical (Jaccard 1.0) and hide a real
# graph-traversal ranking divergence. Setting the cap large enough that it never
# truncates this corpus's pool, AND scoring rank order separately (see
# _rank_agreement / RANK_AGREEMENT_THRESHOLD), closes that hole.
TOP_N_CHUNKS = 1000               # effectively "all" for this corpus; never truncates the pool
# Rank order must also agree: a set-only Jaccard cannot see that the two
# substrates ordered the same chunks differently. Graph modes (local/global/
# hybrid/mix) derive ordering from graph traversal, so a Cozo-vs-NetworkX
# ranking divergence is exactly what this gate exists to catch.
RANK_AGREEMENT_THRESHOLD = 0.8    # min rank-correlation of the shared chunk ordering per mode

# Non-zero STRUCTURAL FLOORS — empty-equals-empty MUST be a FAIL. The fork's
# ingest pipeline fails CLOSED-BUT-SILENT (marks docs FAILED, does not re-raise),
# so an empty graph on BOTH backends would otherwise pass the sym-diff gate
# trivially. Require both backends to have extracted at least this many entities
# and relations from the corpus before parity can even be evaluated.
MIN_ENTITIES = 1                  # corpus-calibrated floor; > 0 is the minimum defensible value
MIN_RELATIONS = 1                 # corpus-calibrated floor; > 0 is the minimum defensible value

# Modes whose retrieval is graph-DERIVED (not pure vector). On a healthy corpus
# these MUST return chunks on both backends; an empty-graph run that only passes
# via Faiss vector fallback (e.g. naive/mix) cannot be allowed to PASS on the
# strength of vector results alone. naive is pure vector and is intentionally
# excluded from this assertion.
GRAPH_DEPENDENT_MODES = ["local", "global"]

# Prose is reported ONLY (never gates) — LLM non-determinism is tolerated.
PROSE_SIMILARITY_REPORT_FLOOR = 0.3  # informational annotation, not a pass/fail gate

REQUIRED_ENV = [
    "LLM_BINDING",
    "LLM_BINDING_HOST",
    "LLM_BINDING_API_KEY",
    "LLM_MODEL",
    "EMBEDDING_BINDING",
    "EMBEDDING_BINDING_HOST",
    "EMBEDDING_BINDING_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "EMBEDDING_TOKEN_LIMIT",
]

# Names treated as secrets — NEVER printed/logged/serialised by this harness.
_SECRET_SUFFIXES = ("API_KEY", "SECRET", "TOKEN", "PASSWORD")


def _is_secret_name(name: str) -> bool:
    up = name.upper()
    return any(up.endswith(suf) for suf in _SECRET_SUFFIXES)


# ---------------------------------------------------------------------------
# Pure-python prose similarity (reported only; not a gate)
# ---------------------------------------------------------------------------

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(_dot(v, v))


def _prose_similarity(text_a: str, text_b: str) -> float:
    """Bag-of-words cosine similarity in [0,1]. Informational only in v1.1."""
    import re

    def tokenize(t: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for w in re.findall(r"[a-z]+", t.lower()):
            counts[w] = counts.get(w, 0) + 1
        return counts

    ca, cb = tokenize(text_a), tokenize(text_b)
    vocab = sorted(set(ca) | set(cb))
    if not vocab:
        return 0.0
    va = [float(ca.get(w, 0)) for w in vocab]
    vb = [float(cb.get(w, 0)) for w in vocab]
    na, nb = _norm(va), _norm(vb)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(va, vb) / (na * nb)


# ===========================================================================
# ===== START: preflight + setup ============================================
# ===========================================================================
#
# preflight() loads provider config from sourcerer-lightrag/.env (via
# python-dotenv, the same loader the fork uses), VALIDATES that every required
# provider env var is present (fail fast otherwise), applies determinism aids,
# builds the fork's real LLM + embedding funcs by REUSING the server helpers,
# and prepares two ISOLATED temp working dirs (one per backend).

def _load_dotenv() -> bool:
    """Load the fork .env explicitly (CWD-relative auto-load misses it).

    The fork modules call load_dotenv(".env") relative to CWD at import time;
    a script run from the repo root would miss sourcerer-lightrag/.env. We load
    it explicitly with override=True BEFORE importing lightrag/config so the
    binding vars are present when those modules read the environment.
    Returns True if a .env was loaded.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]
    except ImportError:
        print("[preflight] python-dotenv not installed; relying on shell env.")
        return False
    if DOTENV_PATH.exists():
        load_dotenv(DOTENV_PATH, override=True)
        print(f"[preflight] Loaded provider config from {DOTENV_PATH}")
        return True
    print(f"[preflight] No .env at {DOTENV_PATH}; relying on shell env.")
    return False


def _check_required_env() -> list[str]:
    """Return the names of any missing/blank required env vars."""
    return [v for v in REQUIRED_ENV if not os.environ.get(v, "").strip()]


def _apply_determinism_aids() -> dict[str, str]:
    """Set low-temperature / serial-LLM env vars IF the user has not set them.

    These make extraction as stable as the provider allows. We never override a
    value the user explicitly chose. Structural equivalence remains the gate
    regardless of provider determinism. Returns the values now in effect
    (non-secret) for the report.
    """
    aids = {
        "OPENAI_LLM_TEMPERATURE": "0.0",
        "MAX_ASYNC_LLM": "1",
    }
    applied: dict[str, str] = {}
    for k, default in aids.items():
        if not os.environ.get(k, "").strip():
            os.environ[k] = default
        applied[k] = os.environ[k]
    return applied


def _build_provider_funcs() -> tuple[Any, Any, dict[str, str]]:
    """Build (llm_model_func, embedding_func, provider_family) via fork helpers.

    REUSES the fork's own machinery so wiring matches the real server:
      * api.config.parse_args() -> args populated from env (binding/host/model/
        key/storage selectors/timeouts/cosine threshold).
      * api.lightrag_server.create_embedding_function_from_args(args) -> the
        fully-configured EmbeddingFunc (same vector space as the server).
      * the LLM func is built over openai_complete_if_cache for openai-compatible
        bindings (the fork's create_llm_model_func is NOT importable — it is
        nested inside the app factory and closes over args/config_cache).

    Returns the two funcs plus a SECRET-FREE provider_family dict (binding +
    model family + host) for the report. Never returns or logs any key.
    """
    # parse_args() reads sys.argv with no list, so neutralise our own argv first.
    saved_argv = sys.argv[:]
    sys.argv = [saved_argv[0]]
    try:
        from lightrag.api.config import parse_args

        args = parse_args()
    finally:
        sys.argv = saved_argv

    from lightrag.api.lightrag_server import create_embedding_function_from_args

    embedding_func = create_embedding_function_from_args(args)

    binding = (getattr(args, "llm_binding", "") or "").lower()

    if binding in ("openai", "openai-ollama", "azure_openai", "gemini", "bedrock",
                   "ollama", "lollms"):
        # For OpenAI-compatible endpoints (this fork's .env: Cerebras LLM +
        # Voyage embeddings, both via the openai binding) wrap the lower-level
        # primitive exactly as create_optimized_openai_llm_func does internally.
        from lightrag.llm.openai import openai_complete_if_cache

        llm_host = getattr(args, "llm_binding_host", None)
        llm_key = getattr(args, "llm_binding_api_key", None)
        llm_model = getattr(args, "llm_model", None)
        llm_timeout = getattr(args, "llm_timeout", None)

        # Pull an optional deterministic temperature from the env (non-secret).
        temp_raw = os.environ.get("OPENAI_LLM_TEMPERATURE", "").strip()
        try:
            temperature = float(temp_raw) if temp_raw else None
        except ValueError:
            temperature = None

        async def llm_model_func(prompt, system_prompt=None, history_messages=None,
                                 **kwargs):
            if history_messages is None:
                history_messages = []
            if llm_timeout is not None:
                kwargs.setdefault("timeout", llm_timeout)
            if temperature is not None:
                kwargs.setdefault("temperature", temperature)
            return await openai_complete_if_cache(
                llm_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                base_url=llm_host,
                api_key=llm_key,
                **kwargs,
            )
    else:
        raise RuntimeError(
            f"Unsupported LLM_BINDING for this parity harness: {binding!r}. "
            "Use an openai-compatible binding."
        )

    provider_family = {
        "llm_binding": binding,
        "llm_model_family": (getattr(args, "llm_model", "") or "").split(":")[0],
        "llm_host": getattr(args, "llm_binding_host", "") or "",
        "embedding_binding": (getattr(args, "embedding_binding", "") or "").lower(),
        "embedding_model_family": (getattr(args, "embedding_model", "") or "").split(":")[0],
        "embedding_host": getattr(args, "embedding_binding_host", "") or "",
    }
    # Carry through the cosine threshold the server would use.
    provider_family["_cosine_threshold"] = getattr(args, "cosine_threshold", None)
    return llm_model_func, embedding_func, provider_family


class _Preflight(SimpleNamespace):
    """Container for everything the backend runs and teardown need."""
    corpus_text: str
    work_root: str
    llm_model_func: Any
    embedding_func: Any
    provider_family: dict[str, str]
    determinism: dict[str, str]
    run_timestamp: str


def preflight() -> _Preflight:
    """Validate config, wire providers, and prepare isolated working dirs.

    Raises SystemExit(2) on any setup/config error (fail fast, clear message).
    """
    print("=" * 72)
    print("  Sourcerer substrate-parity exit gate — v1.1")
    print(f"  Graph: CozoGraphStorage vs NetworkXStorage  |  Vector (fixed): {VECTOR_STORE}")
    print("=" * 72)

    _load_dotenv()

    missing = _check_required_env()
    if missing:
        print("\n[preflight] ERROR — missing required environment variables:")
        for v in missing:
            print(f"    {v}")
        print(f"\n[preflight] Set these in {DOTENV_PATH} (provider creds only) "
              "or export them before running.")
        raise SystemExit(2)

    if not CORPUS_PATH.exists() or CORPUS_PATH.stat().st_size == 0:
        print(f"\n[preflight] ERROR — corpus missing or empty: {CORPUS_PATH}")
        raise SystemExit(2)
    corpus_text = CORPUS_PATH.read_text(encoding="utf-8")

    determinism = _apply_determinism_aids()

    try:
        llm_model_func, embedding_func, provider_family = _build_provider_funcs()
    except SystemExit:
        raise
    except Exception as exc:  # provider wiring failure is a SETUP error
        print(f"\n[preflight] ERROR — failed to wire provider funcs: {exc}")
        traceback.print_exc()
        raise SystemExit(2)

    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
    # Isolated temp root so the two backends never share state on disk.
    import tempfile

    work_root = os.path.join(tempfile.gettempdir(), f"sourcerer_parity_v1_1_{run_timestamp}")
    os.makedirs(work_root, exist_ok=True)

    # SECRET-SAFE summary: family + host only, never keys.
    print(f"\n[preflight] Corpus: {CORPUS_PATH} ({len(corpus_text)} chars)")
    print(f"[preflight] Query:  {PARITY_QUERY!r}")
    print(f"[preflight] Modes:  {QUERY_MODES}")
    print(f"[preflight] LLM binding/model: {provider_family['llm_binding']} / "
          f"{provider_family['llm_model_family']} @ {provider_family['llm_host']}")
    print(f"[preflight] Embedding binding/model: {provider_family['embedding_binding']} / "
          f"{provider_family['embedding_model_family']} @ {provider_family['embedding_host']}")
    print(f"[preflight] Determinism aids in effect: {determinism}")
    print(f"[preflight] Working dirs: {work_root}/{{cozo,networkx}}")

    return _Preflight(
        corpus_text=corpus_text,
        work_root=work_root,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        provider_family=provider_family,
        determinism=determinism,
        run_timestamp=run_timestamp,
    )


def _build_lightrag(working_dir: str, graph_storage: str, pf: _Preflight) -> Any:
    """Construct LightRAG on the Faiss-fixed substrate with the given graph store.

    Mirrors the server's LightRAG wiring: explicit llm_model_func +
    embedding_func (the fork RAISES if embedding_func is None), Faiss vector
    store fixed for BOTH runs, only the graph store varies.
    """
    from lightrag import LightRAG

    # Belt-and-suspenders: also export the storage selectors so any module that
    # reads them at import time sees the same choice the kwargs make.
    os.environ["LIGHTRAG_GRAPH_STORAGE"] = graph_storage
    os.environ["LIGHTRAG_VECTOR_STORAGE"] = VECTOR_STORE
    os.environ["LIGHTRAG_KV_STORAGE"] = KV_STORE
    os.environ["LIGHTRAG_DOC_STATUS_STORAGE"] = DOC_STATUS_STORE

    cosine = pf.provider_family.get("_cosine_threshold")
    vdb_kwargs = {}
    if cosine is not None:
        vdb_kwargs["cosine_better_than_threshold"] = cosine

    # Per-backend workspace isolation. LightRAG's shared_storage keeps doc-status /
    # full-docs / pipeline_status in PROCESS-GLOBAL, per-workspace dicts that survive
    # across LightRAG instances in the same process (initialize_share_data() is a
    # no-op once initialized). Without a distinct workspace, the SECOND backend's
    # identical corpus is detected as a duplicate of the first backend's already-
    # registered doc and skipped (left in DocStatus.FAILED), starving the parity
    # comparison. A distinct workspace per backend partitions that shared state
    # (AGENTS.md: "workspace = data isolation"). Workspace is only a storage
    # partition label — it does not change the extracted graph, so parity stays valid.
    workspace = os.path.basename(os.path.normpath(working_dir))

    rag = LightRAG(
        working_dir=working_dir,
        workspace=workspace,
        llm_model_func=pf.llm_model_func,
        embedding_func=pf.embedding_func,
        kv_storage=KV_STORE,
        vector_storage=VECTOR_STORE,
        graph_storage=graph_storage,
        doc_status_storage=DOC_STATUS_STORE,
        vector_db_storage_cls_kwargs=vdb_kwargs,
    )
    return rag


# ===========================================================================
# Backend run — ingest one corpus + run all five query modes
# ===========================================================================

def _canonical_entity(node: dict) -> str:
    """Normalised entity key. Both backends expose the name under "id"."""
    raw = node.get("id", node.get("entity_name", ""))
    return (raw or "").strip().upper()


def _canonical_relation(edge: dict) -> tuple[str, str] | None:
    """Direction-agnostic relation key.

    The graph is UNDIRECTED in both backends, but Cozo emits edges in canonical
    lexicographic (src<tgt) order while NetworkX emits them in insertion order.
    A naive (source, target) tuple would report spurious diffs, so canonicalise
    to a sorted pair before diffing.
    """
    src = (edge.get("source") or edge.get("src_id") or "").strip().upper()
    tgt = (edge.get("target") or edge.get("tgt_id") or "").strip().upper()
    if not src or not tgt:
        return None
    return (min(src, tgt), max(src, tgt))


async def _read_doc_status(rag: Any, label: str) -> dict[str, Any]:
    """Read post-ingest doc-status and surface FAILED / non-PROCESSED documents.

    The fork's ingest pipeline catches per-document extraction failures, marks
    the doc DocStatus.FAILED, persists, and CONTINUES without re-raising, so
    ainsert returning a track_id is NOT proof of successful extraction. We read
    the doc-status store directly and report:
      * failed_doc_ids:   documents left in DocStatus.FAILED
      * processed_count:  documents that reached DocStatus.PROCESSED
      * status_counts:    full status histogram (secret-free)
    Returns a plain dict (no DocProcessingStatus objects) so it is JSON-safe.
    """
    from lightrag.base import DocStatus

    failed_doc_ids: list[str] = []
    processed_count = 0
    status_counts: dict[str, int] = {}

    try:
        status_counts = dict(await rag.doc_status.get_status_counts())
    except Exception as exc:  # noqa: BLE001 — diagnostic only; the hard checks below still run
        print(f"[{label}]   doc-status: WARN — get_status_counts failed: {exc}")

    try:
        failed_docs = await rag.doc_status.get_docs_by_status(DocStatus.FAILED)
        failed_doc_ids = sorted(failed_docs.keys())
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}]   doc-status: WARN — get_docs_by_status(FAILED) failed: {exc}")

    try:
        processed_docs = await rag.doc_status.get_docs_by_status(DocStatus.PROCESSED)
        processed_count = len(processed_docs)
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}]   doc-status: WARN — get_docs_by_status(PROCESSED) failed: {exc}")

    print(
        f"[{label}]   doc-status: processed={processed_count}, "
        f"failed={len(failed_doc_ids)}, counts={status_counts}"
    )
    return {
        "failed_doc_ids": failed_doc_ids,
        "processed_count": processed_count,
        "status_counts": status_counts,
    }


def _llm_cache_path(working_dir: str) -> str:
    """On-disk path of LightRAG's LLM response cache for this working dir.

    The KV store nests under the workspace subdir (workspace == basename(working_dir),
    set in _build_lightrag); ``kv_store_llm_response_cache.json`` is LightRAG's fixed
    JsonKVStorage filename. Used to SEED the second backend's cache from the first.
    """
    ws = os.path.basename(os.path.normpath(working_dir))
    return os.path.join(working_dir, ws, "kv_store_llm_response_cache.json")


async def _run_backend(
    graph_class: str,
    label: str,
    pf: _Preflight,
    seed_cache_path: str | None = None,
) -> dict[str, Any]:
    """Ingest the corpus and run all five query modes for one graph backend.

    Returns entity set, relation set, and per-mode {answer, chunk_ids (ordered)}.
    Raises on a hard ingest/init failure (mapped to exit 3 by the caller); a
    per-mode query exception is recorded as {"error": ...} and surfaced later.

    ``seed_cache_path`` (when given) is the prior backend's LLM response cache; it is
    copied in BEFORE ingest so extraction is byte-identical across backends.
    """
    from lightrag.base import QueryParam

    working_dir = os.path.join(pf.work_root, label)
    os.makedirs(working_dir, exist_ok=True)

    # Seed the LLM extraction cache from the prior backend so BOTH backends ingest
    # byte-identical extracted entities/relations. LightRAG's entity extraction is
    # path-dependent (the gleaning loop feeds earlier results into later prompts), so
    # two independent ingests of the same corpus yield slightly different entity SETS
    # purely from LLM non-determinism — which would forge or mask a graph-store parity
    # verdict. With the cache pre-seeded, every extraction call is a cache hit returning
    # the first backend's exact responses, so any remaining entity/relation difference
    # is attributable to the GRAPH STORE alone (the actual thing under test).
    if seed_cache_path and os.path.isfile(seed_cache_path):
        dest = _llm_cache_path(working_dir)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(seed_cache_path, dest)
        print(f"[{label}] Seeded LLM cache from prior backend ({os.path.getsize(dest)} bytes)")

    print(f"\n[{label}] Initialising LightRAG ({graph_class} + {VECTOR_STORE}) ...")
    rag = _build_lightrag(working_dir, graph_class, pf)

    await rag.initialize_storages()
    try:
        print(f"[{label}] Ingesting corpus ({len(pf.corpus_text)} chars) ...")
        t0 = time.monotonic()
        await rag.ainsert(pf.corpus_text, file_paths=str(CORPUS_PATH))
        ingest_secs = time.monotonic() - t0
        print(f"[{label}] Ingest done in {ingest_secs:.1f}s")

        # ainsert returning a track_id is NOT proof of successful extraction: the
        # fork's pipeline CATCHES per-document extraction failures, marks the doc
        # DocStatus.FAILED, persists, and CONTINUES without re-raising. A failed
        # doc leaves an EMPTY graph and ainsert still returns normally. So we
        # inspect doc-status here and FAIL CLOSED if anything went wrong.
        doc_status_report = await _read_doc_status(rag, label)
        if doc_status_report.get("failed_doc_ids"):
            raise RuntimeError(
                f"[{label}] ingest left {len(doc_status_report['failed_doc_ids'])} "
                f"document(s) in DocStatus.FAILED "
                f"(ids={doc_status_report['failed_doc_ids']}); "
                "extraction did not complete — refusing to evaluate parity on an "
                "unvalidated corpus."
            )
        if doc_status_report.get("processed_count", 0) < 1:
            raise RuntimeError(
                f"[{label}] ingest produced ZERO documents in DocStatus.PROCESSED "
                f"(status_counts={doc_status_report.get('status_counts')}); the "
                "corpus did not extract — refusing to evaluate parity on an empty "
                "graph."
            )

        # Read graph state AFTER ingest has flushed (read-your-writes is fine here;
        # both backends are post-commit at this point).
        all_nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
        all_edges = await rag.chunk_entity_relation_graph.get_all_edges()

        entity_ids: set[str] = {
            _canonical_entity(n) for n in all_nodes if _canonical_entity(n)
        }
        relation_pairs: set[tuple[str, str]] = set()
        for e in all_edges:
            key = _canonical_relation(e)
            if key is not None:
                relation_pairs.add(key)

        print(f"[{label}] Entities: {len(entity_ids)}, Relations: {len(relation_pairs)}")

        query_results: dict[str, dict[str, Any]] = {}
        for mode in QUERY_MODES:
            print(f"[{label}] Query mode: {mode} ...")
            param = QueryParam(mode=mode)
            try:
                # aquery_data: structured retrieval, no LLM generation needed for
                # the chunk-overlap dimension. Ordered list = relevance ranking.
                data_result = await rag.aquery_data(PARITY_QUERY, param)

                # aquery_data RETURNS (does not raise) on failure: the documented
                # Failure Response is {"status": "failure", "message": ...,
                # "data": {}}. Treat that as a HARD per-mode exception (exit 3) so
                # a broken retrieval subsystem cannot masquerade as "this mode
                # legitimately returned no chunks." Do NOT silently flatten it to
                # chunk_ids=[].
                status = (data_result or {}).get("status")
                if status == "failure":
                    raise RuntimeError(
                        "aquery_data returned status='failure': "
                        f"{(data_result or {}).get('message', 'no message')}"
                    )

                data = data_result.get("data", {}) or {}
                chunks = data.get("chunks", []) or []
                ordered_chunk_ids = [
                    c.get("chunk_id", c.get("reference_id", "")) for c in chunks
                ]
                ordered_chunk_ids = [cid for cid in ordered_chunk_ids if cid]

                # aquery: prose answer (reported only).
                answer = await rag.aquery(PARITY_QUERY, param)
                if not isinstance(answer, str):
                    parts: list[str] = []
                    async for part in answer:
                        parts.append(part)
                    answer = "".join(parts)

                query_results[mode] = {
                    "answer": answer,
                    "chunk_ids": ordered_chunk_ids,
                }
                print(f"[{label}]   {mode}: {len(ordered_chunk_ids)} chunks, "
                      f"answer len={len(answer)}")
            except Exception as exc:
                print(f"[{label}]   {mode}: QUERY ERROR — {exc}")
                query_results[mode] = {"answer": "", "chunk_ids": [], "error": str(exc)}
    finally:
        await rag.finalize_storages()

    return {
        "entities": entity_ids,
        "relations": relation_pairs,
        "entity_count": len(entity_ids),
        "relation_count": len(relation_pairs),
        "query_results": query_results,
        "ingest_secs": ingest_secs,
        "doc_status": doc_status_report,
    }


# ===========================================================================
# Diff + scoring (STRUCTURAL gate; prose reported only)
# ===========================================================================

def _rank_agreement(cozo_ordered: list[str], nx_ordered: list[str]) -> float | None:
    """Rank-correlation of the SHARED chunks' ordering, in [-1, 1] (None if N<2).

    Set Jaccard cannot see that the two substrates ordered the SAME chunks
    differently — but graph modes derive ordering from graph traversal, so a
    Cozo-vs-NetworkX ranking divergence is exactly what must not hide. We
    restrict to chunks present in BOTH lists (ranking is only comparable over
    shared items), then compute Spearman's rank correlation over those ranks.
    Returns None when fewer than two shared chunks exist (rank order undefined).
    """
    shared = [cid for cid in cozo_ordered if cid in set(nx_ordered)]
    n = len(shared)
    if n < 2:
        return None
    cozo_rank = {cid: i for i, cid in enumerate(cozo_ordered)}
    nx_rank = {cid: i for i, cid in enumerate(nx_ordered)}
    # Spearman = 1 - 6*sum(d^2) / (n*(n^2-1)), d = rank difference over shared set.
    d2 = sum((cozo_rank[cid] - nx_rank[cid]) ** 2 for cid in shared)
    denom = n * (n * n - 1)
    if denom == 0:
        return None
    return 1.0 - (6.0 * d2) / denom


def _topn_overlap(cozo_ordered: list[str], nx_ordered: list[str]) -> dict[str, Any]:
    """Top-N referenced-chunk overlap (set + RANK) with NO silent empty pass.

    Compares the first TOP_N_CHUNKS of each ranked list two ways:
      1. as SETS (Jaccard) — must be >= CHUNK_OVERLAP_THRESHOLD; and
      2. by RANK order of the shared chunks (Spearman) — must be
         >= RANK_AGREEMENT_THRESHOLD when >= 2 chunks are shared.
    TOP_N_CHUNKS is set large enough that it never truncates this corpus's pool,
    so a ranking divergence cannot be masked by a small/truncated candidate set.
    Unlike v1.0, empty-vs-empty does NOT score 1.0 — if BOTH modes returned no
    chunks we mark retrieval as empty and FAIL the dimension, so a globally
    broken retrieval path cannot silently PASS.
    """
    cozo_top = cozo_ordered[:TOP_N_CHUNKS]
    nx_top = nx_ordered[:TOP_N_CHUNKS]
    cset, nset = set(cozo_top), set(nx_top)

    both_empty = not cset and not nset
    if both_empty:
        return {
            "cozo_chunk_count": 0,
            "networkx_chunk_count": 0,
            "intersection_count": 0,
            "union_count": 0,
            "overlap_ratio": 0.0,
            "rank_agreement": None,
            "rank_pass": False,
            "both_empty": True,
            "overlap_pass": False,  # no silent pass on broken retrieval
        }
    inter = cset & nset
    union = cset | nset
    ratio = len(inter) / len(union) if union else 0.0

    rank_corr = _rank_agreement(cozo_top, nx_top)
    # When <2 chunks are shared, rank order is undefined; do not invent a pass.
    # The set-overlap gate already governs that case. When rank IS defined, it
    # must meet the threshold.
    rank_pass = True if rank_corr is None else (rank_corr >= RANK_AGREEMENT_THRESHOLD)

    return {
        "cozo_chunk_count": len(cset),
        "networkx_chunk_count": len(nset),
        "intersection_count": len(inter),
        "union_count": len(union),
        "overlap_ratio": round(ratio, 4),
        "rank_agreement": (round(rank_corr, 4) if rank_corr is not None else None),
        "rank_pass": rank_pass,
        "both_empty": False,
        "overlap_pass": ratio >= CHUNK_OVERLAP_THRESHOLD,
    }


def _compute_diff(cozo_result: dict[str, Any], nx_result: dict[str, Any]) -> dict[str, Any]:
    cozo_entities: set[str] = cozo_result["entities"]
    nx_entities: set[str] = nx_result["entities"]
    cozo_relations: set[tuple[str, str]] = cozo_result["relations"]
    nx_relations: set[tuple[str, str]] = nx_result["relations"]

    entity_sym_diff = cozo_entities.symmetric_difference(nx_entities)
    relation_sym_diff = cozo_relations.symmetric_difference(nx_relations)

    mode_diffs: dict[str, dict[str, Any]] = {}
    for mode in QUERY_MODES:
        cqr = cozo_result["query_results"].get(mode, {})
        nqr = nx_result["query_results"].get(mode, {})

        cozo_err = cqr.get("error")
        nx_err = nqr.get("error")

        ov = _topn_overlap(cqr.get("chunk_ids", []), nqr.get("chunk_ids", []))
        prose_sim = _prose_similarity(cqr.get("answer", ""), nqr.get("answer", ""))

        mode_diffs[mode] = {
            **ov,
            "prose_similarity": round(prose_sim, 4),
            "prose_above_report_floor": prose_sim >= PROSE_SIMILARITY_REPORT_FLOOR,
            "cozo_error": cozo_err,
            "networkx_error": nx_err,
        }

    cozo_entity_count = cozo_result["entity_count"]
    nx_entity_count = nx_result["entity_count"]
    cozo_relation_count = cozo_result["relation_count"]
    nx_relation_count = nx_result["relation_count"]

    # NON-ZERO STRUCTURAL FLOOR (closes the empty-equals-empty hole): BOTH
    # backends must have extracted at least MIN_ENTITIES entities AND
    # MIN_RELATIONS relations. An empty graph on both sides trivially satisfies
    # the symmetric-difference gate, so without this floor a corpus that
    # extracted NOTHING would PASS. min(...) over the two backends means either
    # backend falling below the floor fails the gate.
    entity_floor_pass = min(cozo_entity_count, nx_entity_count) >= MIN_ENTITIES
    relation_floor_pass = min(cozo_relation_count, nx_relation_count) >= MIN_RELATIONS

    # GRAPH-DEPENDENT-MODE ASSERTION: local/global derive their chunks from graph
    # traversal. On a healthy corpus they MUST return chunks on BOTH backends; an
    # empty-graph run that only passes via Faiss vector fallback (naive/mix) must
    # not be allowed to PASS on that strength alone.
    graph_mode_pass = True
    graph_mode_failures: list[str] = []
    for mode in GRAPH_DEPENDENT_MODES:
        md = mode_diffs.get(mode, {})
        # If this mode raised, the exception path already handles it; only assert
        # for modes that completed without error.
        if md.get("cozo_error") or md.get("networkx_error"):
            continue
        c_count = md.get("cozo_chunk_count", 0)
        n_count = md.get("networkx_chunk_count", 0)
        if c_count < 1 or n_count < 1:
            graph_mode_pass = False
            graph_mode_failures.append(
                f"{mode} (cozo={c_count}, networkx={n_count})"
            )

    return {
        # entity-set divergence
        "entity_symmetric_difference": sorted(entity_sym_diff),
        "entity_sym_diff_count": len(entity_sym_diff),
        "entity_sym_diff_pass": len(entity_sym_diff) == 0,
        "cozo_only_entities": sorted(cozo_entities - nx_entities),
        "networkx_only_entities": sorted(nx_entities - cozo_entities),
        # relation-set divergence
        "relation_symmetric_difference": [list(r) for r in sorted(relation_sym_diff)],
        "relation_sym_diff_count": len(relation_sym_diff),
        "relation_sym_diff_pass": len(relation_sym_diff) == 0,
        "cozo_only_relations": [list(r) for r in sorted(cozo_relations - nx_relations)],
        "networkx_only_relations": [list(r) for r in sorted(nx_relations - cozo_relations)],
        # counts
        "cozo_entity_count": cozo_entity_count,
        "networkx_entity_count": nx_entity_count,
        "cozo_relation_count": cozo_relation_count,
        "networkx_relation_count": nx_relation_count,
        # non-zero structural floors (empty-equals-empty is a FAIL)
        "min_entities_required": MIN_ENTITIES,
        "min_relations_required": MIN_RELATIONS,
        "entity_floor_pass": entity_floor_pass,
        "relation_floor_pass": relation_floor_pass,
        # graph-dependent modes must return graph-derived chunks on both sides
        "graph_dependent_modes": list(GRAPH_DEPENDENT_MODES),
        "graph_mode_pass": graph_mode_pass,
        "graph_mode_failures": graph_mode_failures,
        # per-mode
        "mode_diffs": mode_diffs,
    }


def _classify(diff: dict[str, Any]) -> tuple[str, list[str]]:
    """Return (verdict, reasons). verdict in {PASS, FAIL, EXCEPTION}.

    EXCEPTION (exit 3): any per-mode query raised — a config/impl bug, not a
    genuine structural divergence. FAIL (exit 1): a structural criterion was
    exceeded. PASS (exit 0): structural equivalence within tolerance.
    Prose similarity NEVER gates; it is informational only.
    """
    reasons: list[str] = []

    # 1. Query exceptions take precedence — they are not parity divergences.
    has_exception = False
    for mode, md in diff["mode_diffs"].items():
        if md.get("cozo_error"):
            has_exception = True
            reasons.append(f"[EXCEPTION] cozo {mode}: {md['cozo_error']}")
        if md.get("networkx_error"):
            has_exception = True
            reasons.append(f"[EXCEPTION] networkx {mode}: {md['networkx_error']}")
    if has_exception:
        return "EXCEPTION", reasons

    structural_fail = False

    # 2. NON-ZERO STRUCTURAL FLOOR — empty-equals-empty MUST be a FAIL. This is
    #    the primary fix for the P0 silent-ingest hole: two empty graphs trivially
    #    have an empty symmetric difference, so the floor is checked FIRST and
    #    independently of the sym-diff gate.
    if not diff.get("entity_floor_pass", False):
        structural_fail = True
        reasons.append(
            f"[FAIL] entity floor not met: cozo={diff['cozo_entity_count']}, "
            f"networkx={diff['networkx_entity_count']} "
            f"(require >= {diff.get('min_entities_required', MIN_ENTITIES)} on BOTH); "
            "empty-equals-empty is NOT parity — ingest likely extracted nothing."
        )
    if not diff.get("relation_floor_pass", False):
        structural_fail = True
        reasons.append(
            f"[FAIL] relation floor not met: cozo={diff['cozo_relation_count']}, "
            f"networkx={diff['networkx_relation_count']} "
            f"(require >= {diff.get('min_relations_required', MIN_RELATIONS)} on BOTH); "
            "empty-equals-empty is NOT parity — ingest likely extracted nothing."
        )

    if not diff["entity_sym_diff_pass"]:
        structural_fail = True
        reasons.append(
            f"[FAIL] entity symmetric difference = {diff['entity_sym_diff_count']}; "
            f"cozo-only={diff['cozo_only_entities']}; "
            f"networkx-only={diff['networkx_only_entities']}"
        )
    if not diff["relation_sym_diff_pass"]:
        structural_fail = True
        reasons.append(
            f"[FAIL] relation symmetric difference = {diff['relation_sym_diff_count']}; "
            f"cozo-only={diff['cozo_only_relations']}; "
            f"networkx-only={diff['networkx_only_relations']}"
        )

    # 3. GRAPH-DEPENDENT-MODE ASSERTION — local/global must return graph-derived
    #    chunks on both backends; otherwise an empty-graph run could pass on
    #    Faiss vector fallback (naive/mix) alone.
    if not diff.get("graph_mode_pass", True):
        structural_fail = True
        reasons.append(
            "[FAIL] graph-dependent mode(s) returned zero chunks on a backend "
            f"(empty-graph / vector-fallback suspected): "
            f"{diff.get('graph_mode_failures', [])}"
        )

    for mode, md in diff["mode_diffs"].items():
        if md.get("both_empty"):
            structural_fail = True
            reasons.append(
                f"[FAIL] mode '{mode}': BOTH backends returned zero referenced chunks "
                "(retrieval path appears broken — no silent pass)"
            )
        elif not md["overlap_pass"]:
            structural_fail = True
            reasons.append(
                f"[FAIL] mode '{mode}': top-{TOP_N_CHUNKS} chunk overlap "
                f"{md['overlap_ratio']:.3f} < {CHUNK_OVERLAP_THRESHOLD} "
                f"(cozo={md['cozo_chunk_count']}, nx={md['networkx_chunk_count']}, "
                f"intersection={md['intersection_count']})"
            )
        # RANK divergence is a FAIL even when the SET overlap passes — graph
        # modes that order the same chunks differently are a real divergence.
        if not md.get("both_empty") and not md.get("rank_pass", True):
            structural_fail = True
            reasons.append(
                f"[FAIL] mode '{mode}': chunk RANK agreement "
                f"{md.get('rank_agreement')} < {RANK_AGREEMENT_THRESHOLD} "
                "(same chunks, divergent ordering — graph traversal differs)"
            )

    if structural_fail:
        return "FAIL", reasons
    return "PASS", reasons


# ===========================================================================
# ===== STOP: teardown + report =============================================
# ===========================================================================
#
# teardown() ALWAYS runs (finally block). It finalises/closes both stores
# (already done per-backend), removes the temp working dirs ON SUCCESS, KEEPS
# them on FAILURE/EXCEPTION for diagnosis, and writes the machine-readable JSON
# result next to this script PLUS a human summary to stdout — in EVERY case.

def _verdict_to_exit(verdict: str) -> int:
    return {"PASS": 0, "FAIL": 1, "EXCEPTION": 3}.get(verdict, 1)


def _print_summary(verdict: str, reasons: list[str], diff: dict[str, Any] | None,
                   pf: _Preflight | None) -> None:
    print("\n" + "=" * 72)
    print(f"  SUBSTRATE PARITY (v1.1) RESULT: {verdict}")
    print("=" * 72)
    print("  Graph backends: CozoGraphStorage vs NetworkXStorage")
    print(f"  Vector backend: {VECTOR_STORE} (fixed for both runs)")
    print(f"  Gate: entity+relation sym-diff == 0 AND floors met (>= {MIN_ENTITIES} "
          f"entities, >= {MIN_RELATIONS} relations on BOTH) AND graph modes "
          f"{GRAPH_DEPENDENT_MODES} non-empty AND per-mode top-{TOP_N_CHUNKS} "
          f"chunk overlap >= {CHUNK_OVERLAP_THRESHOLD:.0%} AND rank agreement "
          f">= {RANK_AGREEMENT_THRESHOLD:.0%}")
    print("  Prose similarity is reported ONLY (LLM non-determinism tolerated).")

    if diff is not None:
        print()
        ef_ok = "OK" if diff.get("entity_floor_pass") else "FAIL"
        rf_ok = "OK" if diff.get("relation_floor_pass") else "FAIL"
        print(f"  Entity counts:   Cozo={diff['cozo_entity_count']}, "
              f"NetworkX={diff['networkx_entity_count']}  "
              f"(floor >= {diff.get('min_entities_required', MIN_ENTITIES)} [{ef_ok}])")
        print(f"  Relation counts: Cozo={diff['cozo_relation_count']}, "
              f"NetworkX={diff['networkx_relation_count']}  "
              f"(floor >= {diff.get('min_relations_required', MIN_RELATIONS)} [{rf_ok}])")
        e_ok = "OK" if diff["entity_sym_diff_pass"] else "FAIL"
        r_ok = "OK" if diff["relation_sym_diff_pass"] else "FAIL"
        print(f"  Entity sym-diff:   {diff['entity_sym_diff_count']} [{e_ok}]")
        print(f"  Relation sym-diff: {diff['relation_sym_diff_count']} [{r_ok}]")
        gm_ok = "OK" if diff.get("graph_mode_pass", True) else "FAIL"
        print(f"  Graph modes {GRAPH_DEPENDENT_MODES} non-empty on both: [{gm_ok}]"
              + (f"  failures={diff.get('graph_mode_failures')}"
                 if not diff.get("graph_mode_pass", True) else ""))

        print()
        print("  Per-mode results:")
        hdr = (f"  {'Mode':<8} {'Cozo':>6} {'NX':>6} {'Inter':>6} {'Overlap':>8} "
               f"{'ChunkOK':>8} {'Rank':>7} {'RankOK':>7} {'ProseSim':>9}")
        print(hdr)
        print("  " + "-" * 72)
        for mode in QUERY_MODES:
            md = diff["mode_diffs"][mode]
            if md.get("cozo_error") or md.get("networkx_error"):
                print(f"  {mode:<8} {'':>6} {'':>6} {'':>6} {'':>8} {'EXCEPTION':>8}")
                continue
            chunk_ok = "OK" if md["overlap_pass"] else ("EMPTY" if md.get("both_empty") else "FAIL")
            rank_corr = md.get("rank_agreement")
            rank_str = f"{rank_corr:>7.3f}" if isinstance(rank_corr, (int, float)) else f"{'n/a':>7}"
            rank_ok = "OK" if md.get("rank_pass", True) else "FAIL"
            print(f"  {mode:<8} {md['cozo_chunk_count']:>6} {md['networkx_chunk_count']:>6} "
                  f"{md['intersection_count']:>6} {md['overlap_ratio']:>8.3f} "
                  f"{chunk_ok:>8} {rank_str} {rank_ok:>7} {md['prose_similarity']:>9.3f}")

    if reasons:
        print()
        print("  Diverging items / errors (NAMED):")
        for r in reasons:
            print(f"    {r}")

    print()
    print(f"  OVERALL: {verdict}  (exit {_verdict_to_exit(verdict)})")
    if verdict != "PASS" and pf is not None:
        print(f"  Temp artifacts KEPT for diagnosis: {pf.work_root}")
    print("=" * 72)


def _write_report(verdict: str, reasons: list[str], diff: dict[str, Any] | None,
                  results: dict[str, dict[str, Any]], pf: _Preflight | None) -> None:
    """Write the machine-readable JSON result next to this script. SECRET-FREE."""
    backend_results: dict[str, Any] = {}
    for label, r in results.items():
        backend_results[label] = {
            "entity_count": r.get("entity_count", 0),
            "relation_count": r.get("relation_count", 0),
            "ingest_secs": round(r.get("ingest_secs", 0.0), 2),
            # Post-ingest doc-status (ainsert returning a track_id is NOT proof
            # of extraction success; this surfaces FAILED / non-PROCESSED docs).
            "doc_status": r.get("doc_status", {}),
            "entities": sorted(r["entities"]) if isinstance(r.get("entities"), set)
                        else r.get("entities", []),
            "relations": sorted([list(x) for x in r["relations"]])
                         if isinstance(r.get("relations"), set)
                         else r.get("relations", []),
            "query_results": {
                mode: {
                    "chunk_ids": qr.get("chunk_ids", []),
                    "answer_length": len(qr.get("answer", "")),
                    "error": qr.get("error"),
                }
                for mode, qr in r.get("query_results", {}).items()
            },
        }

    output = {
        "schema_version": "1.1",
        "harness": "run_substrate_parity_v1_1.py",
        "run_timestamp": getattr(pf, "run_timestamp", time.strftime("%Y%m%d_%H%M%S")),
        "corpus_path": str(CORPUS_PATH),
        "query": PARITY_QUERY,
        "query_modes": QUERY_MODES,
        "graph_backends": [b[0] for b in BACKENDS],
        "vector_backend": VECTOR_STORE,
        "kv_backend": KV_STORE,
        "doc_status_backend": DOC_STATUS_STORE,
        "tolerances": {
            "chunk_overlap_threshold": CHUNK_OVERLAP_THRESHOLD,
            "top_n_chunks": TOP_N_CHUNKS,
            "rank_agreement_threshold": RANK_AGREEMENT_THRESHOLD,
            "min_entities": MIN_ENTITIES,
            "min_relations": MIN_RELATIONS,
            "graph_dependent_modes": GRAPH_DEPENDENT_MODES,
            "prose_similarity_report_floor": PROSE_SIMILARITY_REPORT_FLOOR,
            "prose_gates_result": False,
        },
        # SECRET-FREE provenance: family + host only, never any key.
        "provider_family": {
            k: v for k, v in (getattr(pf, "provider_family", {}) or {}).items()
            if not _is_secret_name(k) and not k.startswith("_")
        },
        "determinism_aids": getattr(pf, "determinism", {}),
        "backend_results": backend_results,
        "diff": diff,
        "reasons": reasons,
        "verdict": verdict,
        "exit_code": _verdict_to_exit(verdict),
    }
    try:
        RESULT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"[report] Machine-readable result written to: {RESULT_PATH}")
    except Exception as exc:
        print(f"[report] WARNING — could not write result JSON: {exc}")


def teardown(verdict: str, reasons: list[str], diff: dict[str, Any] | None,
             results: dict[str, dict[str, Any]], pf: _Preflight | None) -> None:
    """Report + cleanup. ALWAYS invoked from the finally block.

    Writes the JSON report and human summary in EVERY case (including failures),
    then removes the temp working dirs ONLY on PASS — on FAIL/EXCEPTION the
    on-disk graph/vector artifacts are KEPT so the divergence can be debugged.
    """
    _print_summary(verdict, reasons, diff, pf)
    _write_report(verdict, reasons, diff, results, pf)

    if pf is None:
        return
    if verdict == "PASS":
        try:
            shutil.rmtree(pf.work_root, ignore_errors=True)
            print(f"[teardown] Removed temp dir (PASS): {pf.work_root}")
        except Exception:
            pass
    else:
        print(f"[teardown] Temp dir KEPT for diagnosis ({verdict}): {pf.work_root}")


# ===========================================================================
# Orchestrator
# ===========================================================================

async def _run() -> int:
    pf: _Preflight | None = None
    diff: dict[str, Any] | None = None
    results: dict[str, dict[str, Any]] = {}
    verdict = "FAIL"
    reasons: list[str] = []

    try:
        # ----- START: preflight + setup -----
        pf = preflight()

        # ----- Run both backends on the Faiss-fixed substrate -----
        # Seed each subsequent backend's LLM cache from the previous one so extraction
        # is identical and ONLY the graph store varies (see _run_backend seeding note).
        prev_cache_path: str | None = None
        for graph_class, label in BACKENDS:
            try:
                results[label] = await _run_backend(
                    graph_class, label, pf, seed_cache_path=prev_cache_path
                )
                prev_cache_path = _llm_cache_path(os.path.join(pf.work_root, label))
            except Exception as exc:
                print(f"\n[{label}] FATAL backend error: {exc}")
                traceback.print_exc()
                verdict = "EXCEPTION"
                reasons = [f"[EXCEPTION] backend '{label}' crashed: {exc}"]
                return _verdict_to_exit(verdict)

        if "cozo" not in results or "networkx" not in results:
            verdict = "EXCEPTION"
            reasons = ["[EXCEPTION] one or both backends produced no result"]
            return _verdict_to_exit(verdict)

        # ----- Diff + classify -----
        diff = _compute_diff(results["cozo"], results["networkx"])
        verdict, reasons = _classify(diff)
        return _verdict_to_exit(verdict)

    except SystemExit as se:
        # preflight() raised a setup/config error (exit 2). Report what we can.
        code = se.code if isinstance(se.code, int) else 2
        verdict = "SETUP_ERROR"
        reasons = [f"[SETUP] configuration/setup error (exit {code})"]
        # Still emit a report so failures leave a machine-readable artifact.
        teardown(verdict, reasons, diff, results, pf)
        return code
    finally:
        # ----- STOP: teardown + report (always, even on exception) -----
        if verdict != "SETUP_ERROR":
            teardown(verdict, reasons, diff, results, pf)


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
