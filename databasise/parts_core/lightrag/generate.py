"""``lightrag/generator-llm`` — the final answer-generation LLM call, shaped as v1 sends it (D-16,
LRAG-17). v1's ``kg_query`` and ``naive_query`` (``v1/lightrag/operate.py``) format
``PROMPTS["rag_response"]`` / ``PROMPTS["naive_rag_response"]`` with the assembled context,
``response_type="Multiple Paragraphs"`` and ``user_prompt="n/a"``, send that as the system prompt
and the query as the user message. ``config["prompt_template"]`` picks the template: absent or
``rag_response`` for the KG arms, ``naive`` for the naive arm, and a value starting with ``none``
(the bypass arm) sends the bare query as one user message. Any other value is refused by name.

With an empty context v1 returns ``PROMPTS["fail_response"]`` without calling the model; so does
this node. ``config["priority_class"]`` is echoed in the result (v1 uses it only as the scheduler
priority of the call).

The query text is not a dependency output: it arrives in this node's own ``config["query"]``
(``consumes_query``). No LLM response cache: a cache-served re-run would make a parity comparison
match trivially, and the published base declares no KV effect for this node.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "lightrag/generator-llm@0.1.0"
# prompt_template value -> (PROMPTS key, the template's context placeholder)
_SYSTEM_TEMPLATES = {
    "rag_response": ("rag_response", "context_data"),
    "naive": ("naive_rag_response", "content_data"),
}


class UnknownPromptTemplateError(ValueError):
    """``config["prompt_template"]`` names no v1 answer template."""

    def __init__(self, prompt_template: Any) -> None:
        self.prompt_template = prompt_template
        super().__init__(
            f"unknown generate prompt_template {prompt_template!r}; expected one of "
            f"{sorted(_SYSTEM_TEMPLATES)} or a value starting with 'none'"
        )


async def _generate_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))
    prompt_template = config.get("prompt_template", "rag_response")
    echoed = {"priority_class": config.get("priority_class")}

    if str(prompt_template).startswith("none"):
        messages = [{"role": "user", "content": query}]
    elif prompt_template in _SYSTEM_TEMPLATES:
        assemble_output = ctx.inputs.get("assemble") or {}
        context = str(assemble_output.get("context", ""))
        if not context:
            return {
                "completion": PROMPTS["fail_response"],
                "tokens": TokenAccounting(counted_by="none"),
                **echoed,
            }
        prompt_key, placeholder = _SYSTEM_TEMPLATES[prompt_template]
        system = PROMPTS[prompt_key].format(
            response_type="Multiple Paragraphs", user_prompt="n/a", **{placeholder: context}
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": query}]
    else:
        raise UnknownPromptTemplateError(prompt_template)

    result = await ctx.clients["llm"].chat(messages)
    return {
        "completion": result.text,
        "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity,
        **echoed,
    }


LIGHTRAG_GENERATOR_LLM_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="generator",
    structural_depth="stage",
    effects=["calls_llm"],
    upstream_ref="v1/lightrag/operate.py",
    body=_generate_body,
)
