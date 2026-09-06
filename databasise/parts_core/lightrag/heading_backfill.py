"""``lightrag/chunk-heading-backfiller`` (naive arm position 3 of 7; also base-wiring position,
reached by ``hybrid``/``local``/``global`` via ``join-chunks``) — attaches each retrieved chunk's
authoritative KV-stored content and, when present, its heading breadcrumb. Ported by search from
``v1/lightrag/operate.py``'s ``_attach_content_headings``, which looks each chunk up by
``chunk_id`` in ``text_chunks`` KV storage and joins its parent-heading chain
(``v1/lightrag/chunk_schema.py``'s ``format_parent_headings``/``normalize_chunk_heading``) into a
single breadcrumb string, omitted when empty rather than sent as an empty field.

This node's own sole predecessor's *name* differs by arm — the base wiring (``wirings/lightrag/
base.json``, used by ``hybrid``/``local``/``global``) declares ``deps: ["join-chunks"]``, while
``arm-naive.json-patch.json`` overrides that to ``deps: ["chunk-vector"]`` (naive has no
``join-chunks`` node at all — ``chunk-vector`` feeds this position directly). The scheduler keys
``ctx.inputs`` by each dependency's own node id (``runner/scheduler.py``'s ``_run_node``), so this
body reads its single upstream value positionally (``next(iter(ctx.inputs.values()))``) rather
than by a hardcoded dependency name — reading a hardcoded ``"chunk-vector"`` key here silently
raised ``NodeExecutionError: 'chunk-vector'`` on every ``hybrid``/``local``/``global`` run, a defect
invisible until 03-12-PLAN.md's namespace fix let retrieval reach this node for the first time.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/chunk-heading-backfiller@0.1.0"
_BREADCRUMB_SEP = " > "


def _content_headings(chunk_record: dict[str, Any]) -> str:
    """Join a chunk's parent-heading chain plus its own section heading into one breadcrumb
    string, mirroring v1's ``format_parent_headings``/``normalize_chunk_heading`` shape without
    reproducing their token-budgeting/char-capping (not needed at this tracer's scale — see
    03-04-PLAN.md's own instruction to locate the logic by search, not by line citation, and this
    port's job is the metadata attachment, not byte-identical string formatting).
    """
    parts: list[str] = []
    parent_headings = chunk_record.get("parent_headings")
    if isinstance(parent_headings, (list, tuple)):
        parts.extend(str(h) for h in parent_headings if h)
    elif isinstance(parent_headings, dict):
        parts.extend(str(v) for v in parent_headings.values() if v)

    heading = chunk_record.get("heading")
    heading_text = heading.get("heading") if isinstance(heading, dict) else heading
    if heading_text:
        parts.append(str(heading_text))

    return _BREADCRUMB_SEP.join(p for p in parts if p)


async def _heading_backfill_body(ctx: NodeContext) -> dict[str, Any]:
    # Read the sole predecessor positionally, not by name — see module docstring: the name is
    # "chunk-vector" for naive and "join-chunks" for hybrid/local/global, and this node has
    # exactly one dependency in every arm that includes it at all.
    (upstream_output,) = ctx.inputs.values()
    items = list(upstream_output["items"])
    if not items:
        return {"items": []}

    # ``store.get_by_ids`` (databasise/stores/kv.py) silently drops missing ids rather than
    # returning a same-length list with ``None`` placeholders, so zipping its result against
    # ``chunk_ids`` positionally would misalign records the moment any one chunk id is missing.
    # ``get_by_id`` per item keeps this backfill's id-to-record mapping correct regardless.
    kv_store = ctx.stores["kv"]
    records_by_id = {item["id"]: await kv_store.get_by_id(item["id"]) for item in items}

    backfilled: list[dict[str, Any]] = []
    for item in items:
        record = records_by_id.get(item["id"])
        new_item = dict(item)
        if record is not None:
            if "content" in record:
                new_item["content"] = record["content"]
            new_item["file_path"] = record.get("file_path", new_item.get("file_path", "unknown_source"))
            headings = _content_headings(record)
            if headings:
                new_item["content_headings"] = headings
        backfilled.append(new_item)

    return {"items": backfilled}


LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="grader-filter",
    structural_depth="stage",
    effects=["reads_kv"],
    upstream_ref="v1/lightrag/operate.py",
    body=_heading_backfill_body,
)
