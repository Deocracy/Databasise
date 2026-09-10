"""A cost-bounded ingest path for the 291-document eval-corpus (06-12-PLAN.md Task 1) — closes
`databasise/evidence/FALSIFIER-5-EVIDENCE.md`'s precondition 2.

**Exact invocation (module docstring convention, mirroring
``databasise/parity/build_hipporag_index.py``'s own):**

    uv run python -m databasise.eval.corpus_ingest --limit N [--arm lightrag|hipporag] [--spend]

**The contract: estimate first, spend only on explicit opt-in.** The blocker
``FALSIFIER-5-EVIDENCE.md`` records is not that ingesting the eval-corpus is expensive — it is that
it is *unbudgetable*: v1's own `full-ingest` reports `counted_by="unbudgetable"`
(``databasise.parts_core.lightrag.full_ingest._UNBUDGETABLE_TOKENS_SENTINEL``), so no bound can be
enforced from inside the run. The bound that *is* available is the one outside the run —
document count — plus an a-priori projection the owner can price before committing to it. Without
`--spend`, :func:`main` prints :func:`estimate`'s real, computed projection and returns, having
constructed no client and touched no store. With `--spend`, it ingests exactly `--limit` documents,
one :meth:`~databasise.seam.engine.Databasise.ingest` call per document, through the public §18
seam (06-10-PLAN.md's per-modality write dispatch) — so a stopped run has consumed a known prefix,
never a partially-consumed batch.

**`CHARS_PER_TOKEN` is a declared assumption, not a measurement.** No tokenizer is invoked by
:func:`estimate`; the divisor is a module constant, carried on every :class:`IngestEstimate` so the
printed number is labelled as a projection, never presented as a bill.

**`--limit` above the corpus size is refused, never clamped** (:class:`LimitExceedsCorpusError`) —
this codebase's refusals-over-silent-narrowing house style, the same discipline
``databasise.seam.corpus.Page``'s own ``PageSizeExceededError`` already applies to an oversized
page request.

**Nothing here makes a live call by default.** `--spend` reaches real clients built from
``v1/.env.parity`` through ``databasise.parity.run_arm``'s own ``_build_clients``/`_load_env_file`
— the identical construction path `run_arm.py`/`build_hipporag_index.py` already use. This module
is genuine, runnable code, gated behind `06-13`'s own blocking spend checkpoint; it is not invoked
for real by this plan.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise.parity.corpus import CorpusSnapshot, load_snapshot
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    _build_clients,
    _load_env_file,
)
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument, IngestJob
from databasise.seam.refusals import ForeignEngineRefusalError, NoWritePathForModalityError
from databasise.seam.selectors import Selector

# The same directory bundle@v1's own corpus_snapshot_hash was minted from
# (databasise/evidence/EVAL-BUNDLE-V1.md's findings table).
CORPUS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "eval-corpus"

# A declared assumption, not a measurement — see module docstring.
CHARS_PER_TOKEN = 4

# The v1 corpus this module's own `--spend` path ingests into, kept separate from the Phase 3
# parity store (`databasise.parity.run_arm.DEFAULT_STORE_ROOT`) and the Phase 6 build harness's
# own store (`databasise.parity.import_index.DEFAULT_STORE_ROOT`) so a real eval-corpus ingest run
# never lands documents in either of those two stores' own directories.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVAL_INGEST_STORE_ROOT = _REPO_ROOT / "v1" / ".eval_corpus_store"
_EVAL_INGEST_WORKSPACE = "eval-corpus-ingest"

# The exact two Selector values databasise/tests/seam/test_compare.py already uses to reach each
# arm — copied verbatim per this plan's own read_first instruction, never a new selector value.
_ARM_SELECTORS: dict[str, Selector] = {
    "lightrag": Selector(capability=["reads_vector"]),
    "hipporag": Selector(capability=["reads_graph", "reads_kv"]),
}

_ARM_CHOICES: tuple[str, ...] = ("lightrag", "hipporag")


class LimitExceedsCorpusError(ValueError):
    """Raised by :func:`estimate` when ``limit`` exceeds the snapshot's own document count —
    refused, never silently clamped down to the corpus size, per this codebase's
    refusals-over-silent-narrowing house style (``databasise.seam.corpus.Page``'s own
    ``PageSizeExceededError`` is the same discipline applied to an oversized page request).
    """

    def __init__(self, *, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(
            f"LimitExceedsCorpusError: requested limit {requested} exceeds the "
            f"{available}-document eval-corpus — refusing to silently clamp to {available}"
        )


@dataclass(frozen=True)
class IngestEstimate:
    """A real, computed projection for the first ``limit`` eval-corpus documents — never an
    estimate presented as a bill (see module docstring). ``bound`` names what actually bounds the
    spend for ``arm``; ``note`` carries the arm-specific caveat that labels this figure as a
    floor, not a bill.
    """

    documents: int
    bytes: int
    input_tokens_floor: int
    chars_per_token: int
    arm: str
    bound: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents": self.documents,
            "bytes": self.bytes,
            "input_tokens_floor": self.input_tokens_floor,
            "chars_per_token": self.chars_per_token,
            "arm": self.arm,
            "bound": self.bound,
            "note": self.note,
        }


def estimate(snapshot: CorpusSnapshot, *, limit: int, arm: str) -> IngestEstimate:
    """Sum the UTF-8 byte length of the first ``limit`` documents in ``snapshot``'s own order,
    divide by :data:`CHARS_PER_TOKEN` for ``input_tokens_floor``, and label the result with the
    real bound that applies to ``arm``. Raises :class:`LimitExceedsCorpusError` when ``limit``
    exceeds ``snapshot``'s own document count — before any byte is summed.
    """
    available = len(snapshot.documents)
    # RED-DRAFT DEFECT (06-12-PLAN.md Task 1, TDD RED phase): the over-limit refusal is disabled
    # here on purpose, so test_limit_exceeding_corpus_size_is_refused_by_name fails on a real
    # assertion (pytest.raises does not fire) rather than an import/collection error. Restored in
    # the GREEN commit.
    # if limit > available:
    #     raise LimitExceedsCorpusError(requested=limit, available=available)

    documents = snapshot.documents[:limit]
    total_bytes = sum(len(doc.text.encode("utf-8")) for doc in documents)
    input_tokens_floor = total_bytes // CHARS_PER_TOKEN

    # RED-DRAFT DEFECT: bound/note left empty regardless of arm, so
    # test_estimate_labels_its_own_bound_and_note_per_arm fails on a real assertion. Restored in
    # the GREEN commit.
    bound = ""
    note = ""

    return IngestEstimate(
        documents=len(documents),
        bytes=total_bytes,
        input_tokens_floor=input_tokens_floor,
        chars_per_token=CHARS_PER_TOKEN,
        arm=arm,
        bound=bound,
        note=note,
    )


async def ingest_documents(
    engine: Databasise, snapshot: CorpusSnapshot, *, limit: int, arm: str
) -> list[IngestJob]:
    """One :meth:`Databasise.ingest` call per document, in ``snapshot``'s own order, for the first
    ``limit`` documents — the bound this module exists to provide: a stopped run has ingested a
    known prefix, never a partially-consumed batch. Raises :class:`LimitExceedsCorpusError` before
    any document is ingested when ``limit`` exceeds the snapshot's own document count.
    """
    est = estimate(snapshot, limit=limit, arm=arm)  # raises before any spend on an over-large limit
    selector = _ARM_SELECTORS[arm]

    # RED-DRAFT DEFECT: off-by-one, ignores est.documents — makes
    # test_estimate_then_ingest_lands_in_hipporags_own_namespaces and
    # test_spend_flag_ingests_exactly_the_limit_never_the_whole_corpus fail on a real assertion
    # (one extra document ingested). Restored in the GREEN commit.
    jobs: list[IngestJob] = []
    for document in snapshot.documents[: limit + 1]:
        job = await engine.ingest(
            IngestDocument(document_id=document.id, text=document.text), selector=selector
        )
        jobs.append(job)
    return jobs


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.eval.corpus_ingest --limit N`` — the exact invocation this
    module's own docstring names. Without ``--spend``: prints the projection and returns 0,
    constructing no client and touching no store. With ``--spend``: prints the identical
    projection first, then ingests, then prints one JSON summary of the resulting jobs. Exit codes:
    0 on success (estimate-only or a completed ingest), 1 on any refusal — mirrors
    ``build_hipporag_index.main``'s own convention.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--arm", choices=list(_ARM_CHOICES), default="lightrag")
    parser.add_argument("--spend", action="store_true", default=False)
    args = parser.parse_args(argv)

    snapshot = load_snapshot(CORPUS_DIR)
    try:
        result = estimate(snapshot, limit=args.limit, arm=args.arm)
    except LimitExceedsCorpusError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))

    if not args.spend:
        # RED-DRAFT DEFECT: wrong mode label — makes test_default_path_spends_nothing fail on a
        # real assertion (the exact "mode: estimate-only" string is absent from stdout). Restored
        # in the GREEN commit.
        print("mode: not-yet-implemented")
        return 0

    try:
        env = _load_env_file(DEFAULT_V1_ENV_PARITY)
        clients = _build_clients(env)
    except (MissingParityEnvError, MissingParityEnvKeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    engine = Databasise(
        store_root=_EVAL_INGEST_STORE_ROOT,
        workspace=_EVAL_INGEST_WORKSPACE,
        clients=clients,
    )
    try:
        jobs = asyncio.run(ingest_documents(engine, snapshot, limit=args.limit, arm=args.arm))
    except (
        LimitExceedsCorpusError,
        ForeignEngineRefusalError,
        NoWritePathForModalityError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps([job.model_dump() for job in jobs], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "CHARS_PER_TOKEN",
    "CORPUS_DIR",
    "IngestEstimate",
    "LimitExceedsCorpusError",
    "estimate",
    "ingest_documents",
    "main",
]
