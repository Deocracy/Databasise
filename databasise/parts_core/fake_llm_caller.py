"""D-04's fake LLM caller: declares ``calls_llm``, returns a canned completion, and populates a
real ``TokenAccounting`` object with the five §TR.2 members recorded separately. Routes its
result through ``cache_partition_key`` (identity/instance.py) against the run's own KV store, so
a second identical call is a genuine cache hit the runner can stamp — not a simulated one.

**Effects (01-10-PLAN.md Task 1 residual fix).** Also declares ``writes_kv``: the cache round trip
below reads AND writes ``ctx.stores["kv"]``, which only resolves under the runner's
``_ScopedStoresView`` (``runner/scheduler.py``, CR-01) when this Part's own declared ``effects``
carries a member whose suffix is ``kv`` (``reads_kv``/``writes_kv``). This Part was previously
declared with ``effects=["calls_llm"]`` alone and had never been dispatched through the live
scheduler path (only invoked as a bare body against a raw, unscoped ``stores`` dict in
``tests/parts/test_reference_parts.py`` and ``tests/runner/test_run_record.py``) — the missing
declaration surfaced only when 01-10-PLAN.md's Task 1 first ran it end to end through
``databasise.run_wiring``, where ``ctx.stores["kv"]`` raised ``UndeclaredEffectError`` before the
body could reach its own cache check. ``writes_kv`` (rather than ``reads_kv``) because the body
also unconditionally ``upsert``s the cache entry.
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
    effects=["calls_llm", "writes_kv"],
    upstream_ref=None,
    body=_fake_llm_caller_body,
)
