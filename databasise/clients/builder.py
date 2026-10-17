"""The one shipped client builder: env-file parsing plus ``OpenAICompatibleClient`` construction.

Moved out of ``databasise.parity.run_arm`` (08-01-PLAN.md, RUN-05) so the parity CLIs and the
``databasise-rest`` / ``databasise-mcp`` launchers share one builder. ``run_arm`` re-exports these
names under their old underscore spellings, so every existing importer and monkeypatch seam keeps
working.

Privacy (RUN-05): no error message here contains an env-file value. Refusals name keys only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from databasise.clients.openai_compat import OpenAICompatibleClient
from databasise.clients.rerank import (
    RERANK_BINDINGS,
    HttpRerankClient,
    UnsupportedRerankBindingError,
)

__all__ = [
    "PROVIDER_ROUTING_ENV_KEY",
    "REQUIRED_ENV_KEYS",
    "RERANK_BINDING_ENV_KEY",
    "RERANK_ENV_KEYS",
    "MissingParityEnvError",
    "MissingParityEnvKeyError",
    "UnparseableProviderRoutingError",
    "build_clients",
    "load_env_file",
    "parse_provider_routing_body",
]


class MissingParityEnvError(RuntimeError):
    """Raised when the env file does not exist — named rather than a bare ``FileNotFoundError``,
    per this codebase's refusals-over-silent-fallbacks house style.
    """

    def __init__(self, path: Path):
        self.path = path
        super().__init__(
            f"the env file was not found at {path} — see v1/README-PARITY.md to recreate it, or "
            "pass an explicit clients= mapping to run_arm() to bypass real-client construction"
        )


class MissingParityEnvKeyError(RuntimeError):
    """Raised when the env file exists but is missing (or misspells) one of the keys
    ``build_clients`` requires — named rather than a bare ``KeyError``, per this module's own
    "refusals over silent fallbacks" house style (WR-01).
    """

    def __init__(self, missing_keys: list[str]):
        self.missing_keys = missing_keys
        super().__init__(
            f"the env file is missing required key(s): {', '.join(missing_keys)} — "
            "see v1/README-PARITY.md to recreate it, or pass an explicit clients= mapping to "
            "run_arm() to bypass real-client construction"
        )


def load_env_file(path: Path) -> dict[str, str]:
    """A minimal ``KEY=VALUE`` parser for the flat, already-established ``.env.parity`` shape
    (blank lines and ``#``-prefixed comments skipped, optional matching quote pair stripped) —
    intentionally not ``python-dotenv``: that package is not one of
    ``databasise/pyproject.toml``'s approved runtime dependencies, and this format needs nothing
    more than stdlib string splitting.

    IN-01: deliberately duplicated in ``databasise/parity/v1_arm.py``'s own ``_load_env_file``
    rather than imported — see that copy's docstring for why — but this copy raises on an absent
    file while the sibling copy returns ``{}``; that asymmetry is deliberate (this copy is always
    called first in the normal ``compare_arm_on_query`` flow, so it is the one whose refusal a
    caller actually sees).
    """
    if not path.exists():
        raise MissingParityEnvError(path)
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key.strip()] = value
    return env


REQUIRED_ENV_KEYS = (
    "LLM_BINDING_HOST",
    "LLM_MODEL",
    "LLM_BINDING_API_KEY",
    "EMBEDDING_BINDING_HOST",
    "EMBEDDING_MODEL",
    "EMBEDDING_BINDING_API_KEY",
)

# Optional by design (D-07 pin has no meaning for a local Ollama configuration with no provider to
# route) — deliberately NOT added to REQUIRED_ENV_KEYS, which would break the existing WR-01
# missing-key tests that assert exactly which keys are required.
PROVIDER_ROUTING_ENV_KEY = "OPENAI_LLM_EXTRA_BODY"

# Optional rerank wiring (D-08), key names from v1/env.example. RERANK_BINDING picks the request
# shape (cohere, jina, aliyun); "null" or an empty value means absent, as in v1.
RERANK_BINDING_ENV_KEY = "RERANK_BINDING"
RERANK_ENV_KEYS = ("RERANK_BINDING_HOST", "RERANK_MODEL", "RERANK_BINDING_API_KEY")


class UnparseableProviderRoutingError(RuntimeError):
    """Raised when ``OPENAI_LLM_EXTRA_BODY`` is present in the env file but is not valid JSON —
    a named refusal, matching ``MissingParityEnvKeyError``'s "refusals over silent fallbacks"
    house style, rather than silently dropping the pin and running the decomposed arm with
    unpinned provider routing while the original arm's ``v1/scripts/run_parity_ingest.py`` refuses
    the same malformed value outright.

    The value is kept only as the ``raw_value`` attribute; the message withholds it (RUN-05).
    """

    def __init__(self, env_var: str, raw_value: str, problem: str = "not valid JSON"):
        self.env_var = env_var
        self.raw_value = raw_value
        self.problem = problem
        super().__init__(f"{env_var} is set in the env file but {problem}; value withheld")


def parse_provider_routing_body(env: dict[str, str]) -> dict[str, Any] | None:
    """Source D-07's pinned provider-routing body from the same env mapping the six required keys
    come from. Absent -> ``None`` (no pin — correct for a local Ollama configuration that has no
    provider to route). Present-but-unparseable -> a named refusal, never a silently dropped pin.
    """
    raw = env.get(PROVIDER_ROUTING_ENV_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # exc.msg is the decoder's fixed text and never contains document text.
        raise UnparseableProviderRoutingError(
            PROVIDER_ROUTING_ENV_KEY,
            raw,
            problem=f"is not valid JSON ({exc.msg} at line {exc.lineno} column {exc.colno})",
        ) from exc


def build_clients(env: dict[str, str]) -> dict[str, Any]:
    """One ``OpenAICompatibleClient`` construction shape (D-07) reaches both the LLM and the
    embedding endpoint the pinned config names — real network calls, never a cache, never a stub.

    Rerank is optional (D-08), in three cases over ``RERANK_BINDING`` plus ``RERANK_ENV_KEYS``
    (an empty value for the other three counts as absent): none present, or the binding present as
    empty or ``null`` (v1's "rerank off") -> ``{llm, embedding}``, rerank not wired; all present ->
    a ``rerank`` entry is added; some present -> a named ``MissingParityEnvKeyError`` listing the
    absent rerank keys, ``RERANK_BINDING`` included when the key is absent.

    WR-01: refuses with a named ``MissingParityEnvKeyError`` naming every absent key (required and
    rerank together), rather than a bare ``KeyError`` on whichever key happens to be read first.
    """
    missing = [key for key in REQUIRED_ENV_KEYS if key not in env]
    binding = env.get(RERANK_BINDING_ENV_KEY)
    # As in v1: a binding that is present and empty or "null" (any case) switches rerank off, whatever
    # the other RERANK_* keys hold. Only an ABSENT binding key makes the other keys a partial set.
    rerank_off = binding is not None and binding.strip().lower() in ("", "null")
    if rerank_off:
        binding = None
    rerank_values = {key: env.get(key) for key in RERANK_ENV_KEYS}
    if not rerank_off and (binding or any(rerank_values.values())):
        if not binding:
            missing.append(RERANK_BINDING_ENV_KEY)
        missing.extend(key for key, value in rerank_values.items() if not value)
    if missing:
        raise MissingParityEnvKeyError(missing)
    if binding:
        binding = binding.strip().lower()  # v1 values are lowercase; match as the "null"/"off" check does
    if binding and binding not in RERANK_BINDINGS:
        raise UnsupportedRerankBindingError(RERANK_BINDING_ENV_KEY)
    provider_routing_body = parse_provider_routing_body(env)
    clients: dict[str, Any] = {
        "llm": OpenAICompatibleClient(
            base_url=env["LLM_BINDING_HOST"],
            model=env["LLM_MODEL"],
            api_key=env["LLM_BINDING_API_KEY"],
            provider_routing_body=provider_routing_body,
        ),
        "embedding": OpenAICompatibleClient(
            base_url=env["EMBEDDING_BINDING_HOST"],
            model=env["EMBEDDING_MODEL"],
            api_key=env["EMBEDDING_BINDING_API_KEY"],
        ),
    }
    if binding:
        clients["rerank"] = HttpRerankClient(
            url=env["RERANK_BINDING_HOST"],
            model=env["RERANK_MODEL"],
            binding=binding,
            api_key=env["RERANK_BINDING_API_KEY"],
        )
    return clients
