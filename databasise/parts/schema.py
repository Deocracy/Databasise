"""NodeKind tagged sum, the Effect vocabulary, the Depth ladder, and the Part/WiringNode shapes,
per CONTRACT.md §2.

``Effect`` is the frozen 17-member vocabulary, enumerated exactly per CONTRACT.md §2 — a node's
declared effects MUST be drawn only from this list (deny-by-default: "The machine MUST refuse at
wire time any behaviour a part did not declare in its effects[]").

``NodeKind`` is a pydantic v2 discriminated union keyed on a single ``kind`` field, per CONTRACT
§2's own wording ("serde external tagging or a pydantic discriminated union"). Its members here
are the five *structural* kinds CONTRACT §2 names explicitly: ``fanout``, ``join``, ``fixpoint``,
``subgraph``, ``opaque``. CONTRACT §2 states the tagged sum's full membership is "the primitive
part types plus five structural kinds" without ever freezing an authoritative list of the
primitive part types — this module does not invent one. ``WiringNode.kind`` is typed as a plain
``str`` rather than joined to this union: this tracer's two reference parts (``passthrough``,
``kv-writer``) are primitive kinds, not structural ones, and a later plan is where the
fanout/join/fixpoint/subgraph/opaque structural-kind dispatch actually gets built and where
``NodeKind`` starts being consumed as more than a declared skeleton.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Effect = Literal[
    "reads_kv",
    "reads_vector",
    "reads_graph",
    "reads_lexical",
    "reads_blob",
    "writes_artifact",
    "calls_llm",
    "calls_rerank",
    "calls_embedding",
    "net",
    "fs",
    "self_storage",
    "mutates_store",
    "writes_kv",
    "writes_vector",
    "writes_graph",
    "writes_lexical",
]

Depth = Literal["opaque", "evidence", "stage"]

ArtifactScope = Literal["shared", "quarantined", "self_storage"]
"""The three artifact scopes CONTRACT.md §3 defines — MUST NOT be flattened into two categories
with a caveat, since the shareability difference between ``quarantined`` and ``self_storage`` is
the entire point of the distinction. An opaque node MAY write ``quarantined`` and MUST NOT write
``shared``.
"""


class _FanoutKind(BaseModel):
    kind: Literal["fanout"] = "fanout"


class _JoinKind(BaseModel):
    kind: Literal["join"] = "join"


class _FixpointKind(BaseModel):
    kind: Literal["fixpoint"] = "fixpoint"


class _SubgraphKind(BaseModel):
    kind: Literal["subgraph"] = "subgraph"


class _OpaqueKind(BaseModel):
    kind: Literal["opaque"] = "opaque"


NodeKind = Annotated[
    _FanoutKind | _JoinKind | _FixpointKind | _SubgraphKind | _OpaqueKind,
    Field(discriminator="kind"),
]


@dataclass
class NodeContext:
    """The calling convention every ``Part.body`` receives: its own node id, the wiring-declared
    config (possibly ``None``), the already-computed outputs of its direct dependencies, the
    stores dict the runner assembled for this run, and the clients dict the runner assembled for
    this run (D-06) — scoped the same deny-by-default way ``stores`` is. Defaults to an empty
    dict so every existing construction site and every existing test that builds a
    ``NodeContext`` by keyword keeps working unchanged.
    """

    node_id: str
    config: dict[str, Any] | None
    inputs: dict[str, Any]
    stores: dict[str, Any]
    clients: dict[str, Any] = field(default_factory=dict)


@dataclass
class Part:
    """A registered component: its name@version identity, its structural depth and declared
    effects (the registry's own capability row — CONTRACT §2's wire-time declaration), an
    optional upstream_ref lineage pointer (CONTRACT §7, D-14), and an optional executable body.
    ``body is None`` marks a declaration-only entry (D-04): schema plus effects[] only, with no
    executable behaviour yet — a later plan's job is to dispatch such an entry as an explicit
    refusal, never a silent no-op.

    ``artifact_scope`` is set only for a part that declares ``writes_artifact`` — CONTRACT §3's
    three-scope table (``shared``/``quarantined``/``self_storage``) — and stays ``None`` for a
    part that writes no artifact at all.
    """

    name_at_version: str
    kind: str
    structural_depth: Depth
    effects: list[Effect]
    upstream_ref: str | None
    body: Callable[[NodeContext], Any] | None = None
    artifact_scope: ArtifactScope | None = None


class WiringNode(BaseModel):
    """One node in a wiring document. ``config`` defaults to ``None`` (absent), never to an
    empty dict — silently defaulting it here would mean two nodes that both omit ``config``
    hash identically to a node that explicitly declares ``config: {}``, which is not the same
    author-supplied input (see identity/canon.py's own never-normalise rule).
    """

    # Full wire-time strictness (Falsifier 2, Phase 2): a wiring is untrusted author input, and
    # CONTRACT §3's depth and execution_mode are computed, never declared. An unknown node key is
    # therefore refused rather than silently discarded, so an author who writes one never believes
    # it took effect. See validator/parse.py's derived-field check for the finer-grained refusal
    # this enables (self-declared-derivation vs. an ordinary schema typo).
    model_config = ConfigDict(extra="forbid")

    component: str
    kind: str
    effects: list[Effect] = Field(default_factory=list)
    config: dict[str, Any] | None = None
    deps: list[str] = Field(default_factory=list)
