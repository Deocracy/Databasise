"""Phase 13 code-review fixes (13-REVIEW.md): regression tests for the Warning findings.

Kept in a new file because the tests that cover the neighbouring behaviour are ledger-protected.
No network, no v1 artifacts, no live client.
"""

from __future__ import annotations

from databasise.seam.refusals import MutableStoreComparisonExcludedError, refusal_body


def test_the_mutable_store_refusal_names_the_capability_not_the_part():
    """A-WR-01 (D-15, §18.3): the public body carries ``mutates_store``; the part name stays private."""
    part = "codebase-memory-mcp/indexer@1.2.3"
    body = refusal_body(MutableStoreComparisonExcludedError(component=part))
    assert body["component"] == "mutates_store"
    assert "codebase-memory-mcp" not in repr(body)
