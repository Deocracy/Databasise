# API Coverage — Phase 4: The Seam

## No external API integration: this phase exposes a surface, it does not consume one

Phase 4 integrates no third-party API. It builds the machine's own consumer-facing §18 seam — the
query object in, the closed response envelope out, the four selectors, the refusal vocabulary, the
trace reference, and an optional REST transport over the same call path.

The one external API this system does integrate is the OpenAI-compatible model endpoint (OpenRouter
and a local Ollama endpoint). That integration is **Phase 3's** and is unchanged by this phase: the
same `databasise/clients/openai_compat.py` client, the same pinned provider routing, the same
role-scoped calls from the `keywords`, `embedder-query`, `embedder-index` and `generate` positions.
Its coverage record is `.planning/phases/03-lightrag-query-side/COVERAGE.md` and remains the
authoritative one. No row is restated here, and no row is fabricated for a provider capability this
phase does not touch.

Two provider-side rows in Phase 3's matrix are worth naming because this phase changes their status
in the *product*, not in the integration:

- `chat.completions` streaming is marked `OPT-OUT` in Phase 3's matrix with the reason "the
  streaming transport is Phase 4's §18 seam concern." That reason is now discharged — but at the
  seam, not at the provider. This phase streams the **envelope** over server-sent events (API-04,
  D-16); it does not begin consuming the provider's own token stream. Phase 3's row stands as
  written.
- `rerank` remains `OPT-OUT` for the same reason Phase 3 gives (D-09 configures the `rerank` node as
  a pass-through). Nothing in this phase changes it.

## The seam's own exposed operations (§18.5 record)

CONTRACT §18.5 governs how this surface may grow: *"The tool surface MAY grow per part and MUST NOT
grow per modality."* Its selector-versus-tool test is only applicable against a written record of
what the surface currently is. That record is this table.

Every operation is reachable through both transports — in-process (`import databasise`) and the
optional REST layer (`databasise[rest]`) — because ROADMAP criterion 5 requires the two to be
equivalent, not merely both present.

| operation | transports | plan | why an operation and not a selector |
|---|---|---|---|
| query (non-streaming) | in-process, REST | 04-01, 04-05 | The seam's one answering operation. Every modality answers it; §18.5's growth rule means a second modality adds no second operation — it is reached by selector over this one. |
| query (streaming, SSE) | in-process (async generator), REST (`EventSourceResponse`) | 04-05 | A different delivery shape for the same operation, not a different operation. It exists because incremental delivery cannot be expressed as a selector over a call that has already returned. |
| evidence dereference | in-process, REST | 04-02, 04-05 | §4 requires evidence references be machine-resolvable and deref-raising. Resolution is a distinct part kind's operation (evidence), not a variant of answering, and no selector can express "resolve this reference." |
| trace resolution | in-process, REST | 04-04, 04-05 | §18.2 keeps trace content behind the reference rather than in the envelope. Following the reference is therefore its own operation; debug-gated, so the node-by-node content is returned only when asked for. |

### Operations deliberately absent

An absent operation without a stated reason is the undecided hole this section exists to close.

| operation | decision | reason |
|---|---|---|
| MCP transport (API-07) | OPT-OUT | A CONTEXT.md Deferred Idea. The ROADMAP scopes this phase to REST plus in-process; §18.5 additionally requires the MCP surface to add no tool a selector could express, which is a design constraint better applied once the selector set is proven. |
| ingest | OPT-OUT | Phase 5's opaque-side admission (MODAL-02). The seam is locked before ingest ships precisely so the ingest endpoints land against a frozen envelope. |
| delete / document status | OPT-OUT | Phase 5, alongside ingest. |
| promote / rollback | OPT-OUT | Phase 7. `databasise/ledger/ledger.py`'s own scope fence names the atomic alias repoint as Phase 7's deliverable; this phase reads the alias registry and never writes it. |
| comparison-rig operations | OPT-OUT | The rig is a peer client of this seam (§18.3), not an operation on it. It reaches the machine through the same surface every other consumer does. |
| a per-modality tool of any kind | FORBIDDEN | §18.5: a consumer calling a modality-named tool has, by construction, named the modality, which §18.3's invariance rule forbids. This is not an opt-out that a later phase may revisit — it is a contract prohibition, recorded here so the growth rule is enforced against a written surface rather than from memory. |

### Authentication and transport hardening

Not covered by this phase and not silently omitted: the REST layer ships with no authentication,
authorization, TLS termination or rate limiting. No requirement in this phase's set (API-03, API-04,
API-05, API-10, API-11, EMBED-02, MACH-11) asks for any of them, and a partial auth story would be
worse than none. The transport is an optional, locally-bound embedded surface; binding, TLS and
access control are the operator's boundary. This position is recorded as threats T-04-25 and T-04-26
in `04-05-PLAN.md`'s threat register with disposition `transfer`, and must be stated in
`databasise/seam/rest.py`'s module docstring so a reader of the code inherits the decision rather
than discovering the absence.
