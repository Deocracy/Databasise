# API Coverage — Phase 1 (Machine Core)

No external API integration: Phase 1 builds an in-process Python engine over embedded stores only
(4 runtime deps — `pycozo`, `faiss-cpu`, `rfc8785`, `pydantic` — none a service client), and the
architecture constraint is explicitly "local NixOS, embeddable in-process, no external DB servers,
no Docker"; the one "LLM caller" in scope (`databasise/parts_core/fake_llm_caller.py`) is a
deterministic in-process fake with no network call.

## Detector disposition

`api-coverage.cjs` returned `detected: true` on a single signal:

> `(surface)` + `api` — "Registry API: `PartRegistry.get(name_at_version)` raising
> `UnknownPartError` listing the …"

That match is `databasise.parts.registry.PartRegistry` — an **internal Python class API**, not an
external service, SDK, REST/GraphQL/gRPC endpoint, or webhook. Re-reading the phase scope confirms
no external API is integrated anywhere in Phase 1 or in this gap-closure plan (`01-10-PLAN.md`),
whose entire surface is `databasise/runner/scheduler.py`, `databasise/__init__.py`, and tests.

Per the API-coverage checkpoint's own rule, a capability matrix is NOT fabricated for a capability
surface that does not exist; this reasoned declaration stands in its place.
