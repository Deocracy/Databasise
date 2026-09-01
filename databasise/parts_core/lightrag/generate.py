"""``lightrag/generator-llm`` (naive arm position 6 of 7) — the final answer-generation LLM call.
Ported by search from ``v1/lightrag/operate.py``'s ``naive_query``, which formats
``PROMPTS["naive_rag_response"]`` with the assembled ``context_content`` and calls
``global_config["role_llm_funcs"]["query"]``.

The original query text is not one of this node's dependency outputs (the base wiring's own
``deps: ["assemble"]`` does not include ``embedder-query``) — it is threaded through this node's
own ``config["query"]`` instead, the same way ``databasise/parity/run_arm.py`` threads it onto
``embedder-query``'s config. No LLM response cache (03-04-PLAN.md's own instruction): a cache-served
re-run would make a parity comparison match trivially, and the published base declares no KV
effect for this node.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/generator-llm@0.1.0"


async def _generate_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))
    assemble_output = ctx.inputs.get("assemble")
    context = str(assemble_output.get("context", "")) if assemble_output is not None else ""

    if context:
        prompt = f"Context:\n{context}\n\nQuestion: {query}"
    else:
        prompt = query

    client = ctx.clients["llm"]
    result = await client.chat([{"role": "user", "content": prompt}])
    return {
        "completion": result.text,
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
    }


LIGHTRAG_GENERATOR_LLM_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="generator",
    structural_depth="stage",
    effects=["calls_llm"],
    upstream_ref="v1/lightrag/operate.py",
    body=_generate_body,
)
