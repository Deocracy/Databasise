"""D-04's fake LLM caller: declares ``calls_llm``, returns a canned completion, and populates a
real ``TokenAccounting`` object with the five §TR.2 members recorded separately. Routes its
result through ``cache_partition_key`` (identity/instance.py) against the run's own KV store, so
a second identical call is a genuine cache hit the runner can stamp — not a simulated one.
"""

from __future__ import annotations

from typing import Any

from databasise.identity.canon import config_hash
from databasise.identity.instance import cache_partition_key
from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import TokenAccounting

_NAME_AT_VERSION = "parts-core/fake-llm-caller@1.0.0"
_CANNED_COMPLETION = "This is a deterministic canned completion from the fake LLM caller."
_TOKENIZER_ID = "fixture-tokenizer@1"


def _prompt_cache_key(prompt: str) -> str:
    """The cache-partition key this part's calls are keyed by: its own name@version, a static
    (empty) config_hash — this part takes no config of its own — no dependencies, and the
    prompt as the declared input value.
    """
    return cache_partition_key(_NAME_AT_VERSION, config_hash({}), [], {"prompt": prompt})


async def _fake_llm_caller_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    prompt = str(config.get("prompt", ""))
    cache_store = ctx.stores["kv"]
    partition_key = _prompt_cache_key(prompt)

    cached = await cache_store.get_by_id(partition_key)
    cache_hit = cached is not None
    call_count = (cached["call_count"] if cache_hit else 0) + 1

    prompt_tokens = len(prompt.split())
    completion_tokens = len(_CANNED_COMPLETION.split())
    accounting = TokenAccounting(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_read_tokens=prompt_tokens if cache_hit else 0,
        call_count=call_count,
        counted_by=_TOKENIZER_ID,
    )
    await cache_store.upsert(
        {partition_key: {"completion": _CANNED_COMPLETION, "call_count": call_count}}
    )
    return {"completion": _CANNED_COMPLETION, "cache_hit": cache_hit, "tokens": accounting}


FAKE_LLM_CALLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="llm-caller",
    structural_depth="stage",
    effects=["calls_llm"],
    upstream_ref=None,
    body=_fake_llm_caller_body,
)
