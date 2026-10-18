"""LRAG-02 / LRAG-01 (11-01-PLAN.md, D-01): a document ingested through the seam's LightRAG path is
what the query arms retrieve.

Real v1 driver, real v1 pipeline, loopback stub model server (``tests/fixtures/v1_stub_server``).
The v1 index lands in ``<store_root>/<workspace>/lightrag-v1`` and the ``lightrag/v1-index-sync``
node mirrors it into the v2 stores the naive arm reads. Skips only when the v1 venv is absent.
"""

from __future__ import annotations

from pathlib import Path

from databasise.clients.builder import build_clients
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_WS = "lrag-path"
_TEXT = "UNIQalpha Corp builds bridges in UNIQalpha City."
_OPERATOR_CORPUS = Path(__file__).resolve().parents[3] / "v1" / ".corpus_working_dir"


def _listing(root: Path) -> dict[str, int]:
    if not root.exists():
        return {}
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in root.rglob("*")}


def _engine(real_v1) -> Databasise:  # noqa: F811
    return Databasise(store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env))


@requires_v1
async def test_an_ingested_document_is_what_the_naive_arm_retrieves_and_resolves(real_v1):  # noqa: F811
    operator_before = _listing(_OPERATOR_CORPUS)
    engine = _engine(real_v1)

    job = await engine.ingest(IngestDocument(document_id="lragdoc1", text=_TEXT))

    assert job.enqueued == 1
    assert (real_v1.store_root / _WS / "lightrag-v1" / "kv_store_doc_status.json").is_file()
    assert _listing(_OPERATOR_CORPUS) == operator_before

    envelope = await engine.query(QueryObject(text="UNIQalpha bridges"))
    assert envelope.evidence, "the naive arm returned no evidence for an ingested document"
    record = await engine.resolve_evidence(envelope.evidence[0])
    assert record["full_doc_id"] == "lragdoc1"
    assert "UNIQalpha" in record["content"]
