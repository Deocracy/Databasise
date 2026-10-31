"""LIVE-01 (D-01, D-02): the launcher serves the built console same-origin at GET /console.

The row test is the page fetch: a POST /query from the console page returns 200 with no CORS or
Access-Control console message. The server-side checks (headers, flag absent, OpenAPI unchanged,
host and port refusals, the wheel) are added in 18-02 task 2. Uses the in-process harness in
``conftest.py``; no test here uses the live marker.
"""

from __future__ import annotations

QUERY_WORD = "Wood"  # a word of the seeded HippoRAG document text

_FETCH_QUERY = """async (body) => {
  const res = await fetch("/query", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  return res.status;
}"""


def test_page_fetch_post_query_returns_200_without_cors_errors(seeded, live_ui):
    body = {"query": {"text": QUERY_WORD}, "selector": {"capability": ["reads_graph", "reads_kv"]}}
    status = live_ui.page.evaluate(_FETCH_QUERY, body)
    assert status == 200
    assert live_ui.cors_messages() == []
