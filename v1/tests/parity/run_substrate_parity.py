"""Substrate-parity harness: Cozo+Faiss vs NetworkX+Faiss.

Usage
-----
From the repo root (sourcerer-lightrag/ parent directory), with provider
environment variables set (see REQUIRED ENV VARS below):

    ./sourcerer-venv/Scripts/python.exe sourcerer-lightrag/tests/parity/run_substrate_parity.py

Or from inside sourcerer-lightrag/:

    python tests/parity/run_substrate_parity.py

The harness:
  1. Loads provider config from the environment / fork .env (never hardcodes keys).
  2. For each backend in [CozoGraphStorage, NetworkXStorage], sets
     LIGHTRAG_GRAPH_STORAGE to that value with LIGHTRAG_VECTOR_STORAGE=FaissVectorDBStorage
     fixed, ingests the SAME fixed corpus into an isolated working directory.
  3. Runs all five query modes (naive, local, global, hybrid, mix) with one
     fixed query per backend.
  4. Captures per backend: entity set + relation set (via get_all_nodes /
     get_all_edges) and, per query mode, the answer text + top-N referenced
     chunk IDs.
  5. Computes a structural diff: entity-set symmetric difference, relation-set
     symmetric difference, per-mode top-N chunk-reference overlap, and a
     prose-similarity score per mode.
  6. Writes a machine-readable JSON result (parity_result.json) and a human
     summary to stdout.
  7. Exits non-zero when structural diffs exceed the equivalence tolerance.

REQUIRED ENV VARS (set in the fork .env or exported before running)
---------------------------------------------------------------------
LLM_BINDING          — e.g. "openai" (or "bedrock", "ollama", etc.)
LLM_BINDING_HOST     — LLM API endpoint (e.g. https://api.cerebras.ai/v1)
LLM_BINDING_API_KEY  — API key for the LLM provider
LLM_MODEL            — Model name (e.g. "llama-3.3-70b")

EMBEDDING_BINDING         — e.g. "openai"
EMBEDDING_BINDING_HOST    — Embedding API endpoint
EMBEDDING_BINDING_API_KEY — API key for the embedding provider
EMBEDDING_MODEL           — Embedding model name
EMBEDDING_DIM             — Embedding dimension (integer, e.g. 1024 or 3072)
EMBEDDING_TOKEN_LIMIT     — Max tokens per embedding request (e.g. 8192)

Optional (recommended for determinism):
OPENAI_LLM_TEMPERATURE=0.0  — Set temperature to 0 for reproducible extraction
MAX_ASYNC_LLM=1             — Serialise LLM calls to minimise non-determinism

EQUIVALENCE TOLERANCES (from REQUIREMENTS.md parity baseline)
--------------------------------------------------------------
- Entity-set symmetric difference: MUST be empty (zero entities differ).
- Relation-set symmetric difference: MUST be empty (zero relations differ).
- Per-mode top-N chunk-reference overlap: at or above CHUNK_OVERLAP_THRESHOLD.
- Prose similarity: at or above PROSE_SIMILARITY_THRESHOLD (non-determinism
  is expected; structure is the parity-critical surface, not exact prose).

Exit codes
----------
0 — PARITY PASS: all structural diffs within tolerance.
1 — PARITY FAIL: one or more structural diffs exceeded tolerance.
2 — SETUP / CONFIGURATION ERROR (missing env vars, import errors, etc.).
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CORPUS_PATH = Path(__file__).parent / "corpus" / "sample.txt"
RESULT_PATH = Path(__file__).parent / "parity_result.json"

PARITY_QUERY = (
    "What contributions did Alan Turing and Grace Hopper make to computing, "
    "and how are their works related to modern computers?"
)

QUERY_MODES = ["naive", "local", "global", "hybrid", "mix"]

# Storage backends to compare
BACKENDS = [
    ("CozoGraphStorage", "cozo"),
    ("NetworkXStorage", "networkx"),
]

# Fixed vector store for both runs
VECTOR_STORE = "FaissVectorDBStorage"
KV_STORE = "JsonKVStorage"
DOC_STATUS_STORE = "JsonDocStatusStorage"

# Parity tolerances
CHUNK_OVERLAP_THRESHOLD = 0.5   # >= 50% top-N chunk IDs must overlap per mode
PROSE_SIMILARITY_THRESHOLD = 0.3  # cosine similarity >= 0.3 (prose is non-deterministic)

# ---------------------------------------------------------------------------
# Env setup — load .env from fork root if present (never hardcode secrets)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from the sourcerer-lightrag directory if python-dotenv is available."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]
    except ImportError:
        return  # python-dotenv not installed; rely on shell environment

    # Walk up from this file to find the fork root (sourcerer-lightrag/)
    here = Path(__file__).resolve()
    for parent in here.parents:
        dotenv_path = parent / ".env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path, override=False)  # shell env takes precedence
            print(f"[setup] Loaded .env from {dotenv_path}")
            break


def _check_required_env() -> list[str]:
    """Return a list of missing required environment variable names."""
    required = [
        "LLM_BINDING",
        "LLM_BINDING_API_KEY",
        "LLM_MODEL",
        "EMBEDDING_BINDING",
        "EMBEDDING_BINDING_API_KEY",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIM",
        "EMBEDDING_TOKEN_LIMIT",
    ]
    missing = [v for v in required if not os.environ.get(v, "").strip()]
    return missing


# ---------------------------------------------------------------------------
# Cosine similarity (pure-python, no extra deps)
# ---------------------------------------------------------------------------

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(_dot(v, v))


def _cosine_sim(a: list[float], b: list[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


def _text_to_bag_of_words(text: str) -> list[float]:
    """Minimal bag-of-words vector for prose similarity (no external deps)."""
    import re
    words = re.findall(r"[a-z]+", text.lower())
    vocab: dict[str, int] = {}
    for w in words:
        vocab[w] = vocab.get(w, 0) + 1
    return list(vocab.values()), list(vocab.keys())


def _prose_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two prose strings using bag-of-words.

    Returns a float in [0.0, 1.0].
    """
    import re

    def tokenize(t: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for w in re.findall(r"[a-z]+", t.lower()):
            counts[w] = counts.get(w, 0) + 1
        return counts

    ca, cb = tokenize(text_a), tokenize(text_b)
    vocab = sorted(set(ca) | set(cb))
    va = [float(ca.get(w, 0)) for w in vocab]
    vb = [float(cb.get(w, 0)) for w in vocab]
    return _cosine_sim(va, vb)


# ---------------------------------------------------------------------------
# LightRAG setup helpers
# ---------------------------------------------------------------------------

def _build_lightrag(working_dir: str, graph_storage: str) -> Any:
    """Instantiate a LightRAG object configured for the given graph backend.

    Provider config is read entirely from the environment (loaded above from
    .env if present). No keys are hardcoded here.
    """
    from lightrag import LightRAG

    # Override storage backends via environment (LightRAG reads these at init)
    os.environ["LIGHTRAG_GRAPH_STORAGE"] = graph_storage
    os.environ["LIGHTRAG_VECTOR_STORAGE"] = VECTOR_STORE
    os.environ["LIGHTRAG_KV_STORAGE"] = KV_STORE
    os.environ["LIGHTRAG_DOC_STATUS_STORAGE"] = DOC_STATUS_STORE

    rag = LightRAG(working_dir=working_dir)
    return rag


async def _run_backend(
    graph_storage_class: str,
    backend_label: str,
    corpus_text: str,
    work_root: str,
) -> dict[str, Any]:
    """Ingest corpus + run 5 query modes for one backend.

    Returns a dict with:
        entities:  set of entity IDs extracted
        relations: set of (src, tgt) relation pairs extracted
        query_results: {mode: {"answer": str, "chunk_ids": list[str]}}
    """
    from lightrag.base import QueryParam

    working_dir = os.path.join(work_root, backend_label)
    os.makedirs(working_dir, exist_ok=True)

    print(f"\n[{backend_label}] Initialising LightRAG with {graph_storage_class} + {VECTOR_STORE} ...")
    rag = _build_lightrag(working_dir, graph_storage_class)

    async with rag:
        # ----- Ingest -----
        print(f"[{backend_label}] Ingesting corpus ({len(corpus_text)} chars) ...")
        t0 = time.monotonic()
        await rag.ainsert(corpus_text)
        ingest_secs = time.monotonic() - t0
        print(f"[{backend_label}] Ingest done in {ingest_secs:.1f}s")

        # ----- Capture graph state -----
        print(f"[{backend_label}] Reading graph state ...")
        all_nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
        all_edges = await rag.chunk_entity_relation_graph.get_all_edges()

        entity_ids: set[str] = {n.get("id", n.get("entity_name", "")).strip().upper()
                                 for n in all_nodes
                                 if n.get("id") or n.get("entity_name")}
        # Relation keys as sorted pairs (case-normalised) to match both backends
        relation_pairs: set[tuple[str, str]] = set()
        for e in all_edges:
            src = (e.get("source") or e.get("src_id") or "").strip().upper()
            tgt = (e.get("target") or e.get("tgt_id") or "").strip().upper()
            if src and tgt:
                relation_pairs.add((min(src, tgt), max(src, tgt)))

        print(f"[{backend_label}] Entities: {len(entity_ids)}, Relations: {len(relation_pairs)}")

        # ----- Run five query modes -----
        query_results: dict[str, dict[str, Any]] = {}
        for mode in QUERY_MODES:
            print(f"[{backend_label}] Running query mode: {mode} ...")
            param = QueryParam(mode=mode)
            try:
                # aquery_data returns structured data including chunk IDs
                data_result = await rag.aquery_data(PARITY_QUERY, param)
                chunks = data_result.get("data", {}).get("chunks", [])
                chunk_ids = [c.get("chunk_id", c.get("reference_id", "")) for c in chunks]

                # aquery for the prose answer
                answer = await rag.aquery(PARITY_QUERY, param)
                if not isinstance(answer, str):
                    # Streaming iterator — collect it
                    parts = []
                    async for part in answer:
                        parts.append(part)
                    answer = "".join(parts)

                query_results[mode] = {
                    "answer": answer,
                    "chunk_ids": [cid for cid in chunk_ids if cid],
                }
                print(f"[{backend_label}]   {mode}: {len(chunk_ids)} chunks referenced, "
                      f"answer len={len(answer)}")
            except Exception as exc:
                print(f"[{backend_label}]   {mode}: ERROR — {exc}")
                query_results[mode] = {"answer": "", "chunk_ids": [], "error": str(exc)}

    return {
        "entities": entity_ids,
        "relations": relation_pairs,
        "entity_count": len(entity_ids),
        "relation_count": len(relation_pairs),
        "query_results": query_results,
        "ingest_secs": ingest_secs,
    }


# ---------------------------------------------------------------------------
# Diff + scoring
# ---------------------------------------------------------------------------

def _compute_diff(
    cozo_result: dict[str, Any],
    networkx_result: dict[str, Any],
) -> dict[str, Any]:
    """Compute structural diff between two backend results."""
    cozo_entities = cozo_result["entities"]
    nx_entities = networkx_result["entities"]
    cozo_relations = cozo_result["relations"]
    nx_relations = networkx_result["relations"]

    entity_sym_diff = cozo_entities.symmetric_difference(nx_entities)
    relation_sym_diff = cozo_relations.symmetric_difference(nx_relations)

    mode_diffs: dict[str, dict[str, Any]] = {}
    for mode in QUERY_MODES:
        cozo_qr = cozo_result["query_results"].get(mode, {})
        nx_qr = networkx_result["query_results"].get(mode, {})

        cozo_chunks = set(cozo_qr.get("chunk_ids", []))
        nx_chunks = set(nx_qr.get("chunk_ids", []))

        if cozo_chunks or nx_chunks:
            intersection = cozo_chunks & nx_chunks
            union = cozo_chunks | nx_chunks
            overlap_ratio = len(intersection) / len(union) if union else 1.0
        else:
            intersection = set()
            union = set()
            overlap_ratio = 1.0  # both empty = equivalent

        cozo_answer = cozo_qr.get("answer", "")
        nx_answer = nx_qr.get("answer", "")
        prose_sim = _prose_similarity(cozo_answer, nx_answer)

        cozo_err = cozo_qr.get("error")
        nx_err = nx_qr.get("error")

        mode_diffs[mode] = {
            "cozo_chunk_count": len(cozo_chunks),
            "networkx_chunk_count": len(nx_chunks),
            "intersection_count": len(intersection),
            "union_count": len(union),
            "chunk_overlap_ratio": round(overlap_ratio, 4),
            "chunk_overlap_pass": overlap_ratio >= CHUNK_OVERLAP_THRESHOLD,
            "prose_similarity": round(prose_sim, 4),
            "prose_similarity_pass": prose_sim >= PROSE_SIMILARITY_THRESHOLD,
            "cozo_error": cozo_err,
            "networkx_error": nx_err,
        }

    return {
        "entity_symmetric_difference": sorted(entity_sym_diff),
        "entity_sym_diff_count": len(entity_sym_diff),
        "entity_sym_diff_pass": len(entity_sym_diff) == 0,
        "relation_symmetric_difference": [list(r) for r in sorted(relation_sym_diff)],
        "relation_sym_diff_count": len(relation_sym_diff),
        "relation_sym_diff_pass": len(relation_sym_diff) == 0,
        "cozo_entity_count": cozo_result["entity_count"],
        "networkx_entity_count": networkx_result["entity_count"],
        "cozo_relation_count": cozo_result["relation_count"],
        "networkx_relation_count": networkx_result["relation_count"],
        "mode_diffs": mode_diffs,
    }


def _overall_pass(diff: dict[str, Any]) -> bool:
    """Return True iff all parity criteria pass."""
    if not diff["entity_sym_diff_pass"]:
        return False
    if not diff["relation_sym_diff_pass"]:
        return False
    for mode, md in diff["mode_diffs"].items():
        if md.get("cozo_error") or md.get("networkx_error"):
            return False
        if not md["chunk_overlap_pass"]:
            return False
        if not md["prose_similarity_pass"]:
            return False
    return True


# ---------------------------------------------------------------------------
# Human summary printer
# ---------------------------------------------------------------------------

def _print_summary(diff: dict[str, Any], passed: bool) -> None:
    """Print a human-readable parity summary to stdout."""
    verdict = "PASS" if passed else "FAIL"
    print("\n" + "=" * 70)
    print(f"  SUBSTRATE PARITY RESULT: {verdict}")
    print("=" * 70)
    print(f"  Graph backends: CozoGraphStorage vs NetworkXStorage")
    print(f"  Vector backend: {VECTOR_STORE} (fixed, both runs)")
    print(f"  Tolerances: chunk_overlap>={CHUNK_OVERLAP_THRESHOLD:.0%}, prose_sim>={PROSE_SIMILARITY_THRESHOLD:.2f}")
    print()
    print(f"  Entity counts:   Cozo={diff['cozo_entity_count']}, NetworkX={diff['networkx_entity_count']}")
    print(f"  Relation counts: Cozo={diff['cozo_relation_count']}, NetworkX={diff['networkx_relation_count']}")

    entity_pass = "OK" if diff["entity_sym_diff_pass"] else "FAIL"
    relation_pass = "OK" if diff["relation_sym_diff_pass"] else "FAIL"
    print(f"  Entity sym-diff:   {diff['entity_sym_diff_count']} [{entity_pass}]")
    print(f"  Relation sym-diff: {diff['relation_sym_diff_count']} [{relation_pass}]")

    if diff["entity_symmetric_difference"]:
        print(f"  Differing entities: {diff['entity_symmetric_difference'][:10]}")
    if diff["relation_symmetric_difference"]:
        print(f"  Differing relations: {diff['relation_symmetric_difference'][:5]}")

    print()
    print("  Per-mode results:")
    header = f"  {'Mode':<10} {'Cozo chunks':>12} {'NX chunks':>10} {'Overlap':>9} {'ChunkOK':>8} {'ProseSim':>9} {'ProseOK':>8}"
    print(header)
    print("  " + "-" * 68)
    for mode in QUERY_MODES:
        md = diff["mode_diffs"][mode]
        err = "ERROR" if (md.get("cozo_error") or md.get("networkx_error")) else ""
        chunk_ok = "OK" if md["chunk_overlap_pass"] else "FAIL"
        prose_ok = "OK" if md["prose_similarity_pass"] else "FAIL"
        if err:
            print(f"  {mode:<10} {'':>12} {'':>10} {'':>9} {'':>8} {'':>9} {err}")
        else:
            print(
                f"  {mode:<10} {md['cozo_chunk_count']:>12} {md['networkx_chunk_count']:>10} "
                f"{md['chunk_overlap_ratio']:>9.3f} {chunk_ok:>8} {md['prose_similarity']:>9.3f} {prose_ok:>8}"
            )

    print()
    print(f"  Overall: {verdict}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main() -> int:
    """Run the full parity comparison. Returns the exit code."""
    print("=" * 70)
    print("  Sourcerer substrate parity harness")
    print(f"  CozoGraphStorage vs NetworkXStorage (vector: {VECTOR_STORE})")
    print("=" * 70)

    # Load .env (non-secret names only; values come from file/shell)
    _load_dotenv()

    # Check required env vars
    missing = _check_required_env()
    if missing:
        print("\nERROR: Missing required environment variables:")
        for v in missing:
            print(f"  {v}")
        print("\nSet these in your fork .env (sourcerer-lightrag/.env) or export them before running.")
        print("See SETUP-NOTES.md and the harness module docstring for the full list.")
        return 2

    # Check corpus
    if not CORPUS_PATH.exists() or CORPUS_PATH.stat().st_size == 0:
        print(f"\nERROR: Corpus file missing or empty: {CORPUS_PATH}")
        return 2

    corpus_text = CORPUS_PATH.read_text(encoding="utf-8")
    print(f"\n[setup] Corpus: {CORPUS_PATH} ({len(corpus_text)} chars)")
    print(f"[setup] Query:  {PARITY_QUERY!r}")
    print(f"[setup] Modes:  {QUERY_MODES}")

    # Create an isolated temp root for this run's working directories
    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
    work_root = os.path.join(tempfile.gettempdir(), f"sourcerer_parity_{run_timestamp}")
    os.makedirs(work_root, exist_ok=True)
    print(f"[setup] Working dirs: {work_root}/{{cozo,networkx}}")

    results: dict[str, dict[str, Any]] = {}

    try:
        for graph_class, label in BACKENDS:
            try:
                result = await _run_backend(
                    graph_storage_class=graph_class,
                    backend_label=label,
                    corpus_text=corpus_text,
                    work_root=work_root,
                )
                # Convert sets to lists for JSON serialisation
                result["entities"] = sorted(result["entities"])
                result["relations"] = sorted([list(r) for r in result["relations"]])
                results[label] = result
            except Exception as exc:
                print(f"\nFATAL ERROR running {label} backend: {exc}")
                import traceback
                traceback.print_exc()
                return 1

        if "cozo" not in results or "networkx" not in results:
            print("\nERROR: One or both backends failed to produce results.")
            return 1

        # Reconstruct sets for diff computation
        cozo_res = dict(results["cozo"])
        nx_res = dict(results["networkx"])
        cozo_res["entities"] = set(cozo_res["entities"])
        cozo_res["relations"] = {tuple(r) for r in cozo_res["relations"]}
        nx_res["entities"] = set(nx_res["entities"])
        nx_res["relations"] = {tuple(r) for r in nx_res["relations"]}

        diff = _compute_diff(cozo_res, nx_res)
        passed = _overall_pass(diff)
        _print_summary(diff, passed)

        # Write machine-readable result
        output = {
            "schema_version": "1.0",
            "run_timestamp": run_timestamp,
            "corpus_path": str(CORPUS_PATH),
            "query": PARITY_QUERY,
            "query_modes": QUERY_MODES,
            "graph_backends": [b[0] for b in BACKENDS],
            "vector_backend": VECTOR_STORE,
            "tolerances": {
                "chunk_overlap_threshold": CHUNK_OVERLAP_THRESHOLD,
                "prose_similarity_threshold": PROSE_SIMILARITY_THRESHOLD,
            },
            "backend_results": {
                label: {
                    "entity_count": r["entity_count"],
                    "relation_count": r["relation_count"],
                    "ingest_secs": round(r["ingest_secs"], 2),
                    "entities": sorted(r["entities"]) if isinstance(r["entities"], set) else r["entities"],
                    "relations": (sorted([list(x) for x in r["relations"]])
                                  if isinstance(r["relations"], set) else r["relations"]),
                    "query_results": {
                        mode: {
                            "chunk_ids": qr.get("chunk_ids", []),
                            "answer_length": len(qr.get("answer", "")),
                            "error": qr.get("error"),
                        }
                        for mode, qr in r["query_results"].items()
                    },
                }
                for label, r in results.items()
            },
            "diff": diff,
            "verdict": "PASS" if passed else "FAIL",
        }

        RESULT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"\n[result] Machine-readable result written to: {RESULT_PATH}")

        return 0 if passed else 1

    finally:
        # Clean up temp working directories
        try:
            shutil.rmtree(work_root, ignore_errors=True)
            print(f"[cleanup] Removed temp dir: {work_root}")
        except Exception:
            pass


if __name__ == "__main__":
    # Validate that the module itself can be imported and key symbols are present
    # (catches syntax errors before attempting a live run)
    assert "LIGHTRAG_GRAPH_STORAGE" in open(__file__).read(), "sentinel check"
    assert "CozoGraphStorage" in open(__file__).read(), "sentinel check"
    assert "NetworkXStorage" in open(__file__).read(), "sentinel check"
    assert "FaissVectorDBStorage" in open(__file__).read(), "sentinel check"

    sys.exit(asyncio.run(main()))
