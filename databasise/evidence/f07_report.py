"""``databasise.evidence.f07_report`` — 06-09-PLAN.md Task 1: MACH-10/F-07's disposition record,
rendered from the registry itself (never hand-transcribed), following
``databasise/evidence/parity_report.py``'s own render-from-committed-inputs convention:
:func:`render_f07_record` is a pure function of ``default_registry()`` plus this module's own two
catalogued-not-built roster entries (`MC-1`, `CA-7`) — re-rendering on unchanged inputs reproduces
the committed document byte-identically (this plan's own acceptance criterion: "a second run of
the discharge is not a second finding").

`databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md` is this function's own committed output,
written verbatim so ``test_f07_record.py``'s byte-identical re-render assertion holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from databasise.parts.registry import PartRegistry

# §14.4 point 3's two admissible dispositions (docs/system-model/CONTRACT.md, the mutable-store
# definition's own third numbered point) -- the only two legitimate outcomes for a mutates_store-
# declaring component. No third value is admissible for any row this record carries.
DISPOSITION_PERMANENT_EXCLUSION = "permanent-exclusion"
DISPOSITION_SNAPSHOT_RESET_DEFINED = "snapshot-reset-defined"

_ADMISSIBLE_DISPOSITIONS = (DISPOSITION_PERMANENT_EXCLUSION, DISPOSITION_SNAPSHOT_RESET_DEFINED)


@dataclass(frozen=True)
class _DispositionRow:
    component: str
    disposition: str
    reason: str
    tag: str


_CODEBASE_MEMORY_MCP_REASON = (
    "CA-2 in MODEL-RED-TEAM.md's own F-07 roster; the only mutable-store component this "
    "project has actually admitted and registered. Admitted whole-engine opaque (PARTS.md "
    "## §X); its provides node resolves opaque effective depth, so it is already excluded "
    "from the *default* selector under §8 condition 7. It is also not currently resolvable "
    "through any of §18.4's four production selectors at all: databasise/wirings/resolve.py's "
    'WIRING_NAMES names only ("lightrag", "hipporag"), so the capability/default/harness '
    "selectors' shared candidate pool (all_wirings()) never includes "
    "databasise/wirings/codebase-memory-mcp.json today. No requirement in this milestone asks "
    "for manage_adr/delete_project's own behaviour to be A/B-testable. Reversal condition: a "
    "future requirement asking for that A/B-testability, at which point the snapshot/reset "
    "protocol is a file-copy-and-restore of the engine's own SQLite database plus its WAL and "
    "SHM siblings, in databasise/foreign/codebase_memory_mcp_adapter.py -- the same file-unlink "
    "shape that adapter already owns for delete_project."
)

_LIGHTRAG_FULL_DELETE_REASON = (
    "Not named in MODEL-RED-TEAM.md's own three-entry F-07 roster -- a fourth, real, "
    "registered mutable-store component this record's own registry-derived enumeration finds "
    "that a hand list would have missed, which is exactly why this record computes its "
    "population from default_registry() rather than transcribing the frozen roster. Dispatched "
    "directly by Databasise.delete_document() through a single-node wiring built inline, never "
    "routed through resolve_selector()'s candidate pool (all_wirings()) that query()/compare() "
    "draw from -- structurally unreachable through any comparison today, by construction rather "
    "than by this record's own choice. No requirement in this milestone asks for corpus-delete "
    "behaviour to be A/B-testable. Recorded for completeness, not because a comparison call can "
    "reach it."
)

_KNOWN_REASONS: dict[str, str] = {
    "codebase-memory-mcp@0.1.0": _CODEBASE_MEMORY_MCP_REASON,
    "lightrag/full-delete@0.1.0": _LIGHTRAG_FULL_DELETE_REASON,
}

# The two roster entries MODEL-RED-TEAM.md's F-07 finding names that are catalogued in
# CATALOG.md ## §T but never registered in default_registry() today. Their disposition is not a
# fresh decision of its own — it is the projection of this record's own default
# (permanent-exclusion) onto a component that does not yet exist, stated explicitly rather than
# left unanswered until the day one is actually built.
_CATALOGUED_NOT_BUILT: tuple[_DispositionRow, ...] = (
    _DispositionRow(
        component="MC-1 (postgres-mcp's execute_sql, Unrestricted Mode)",
        disposition=DISPOSITION_PERMANENT_EXCLUSION,
        reason=(
            "Catalogued in CATALOG.md ## §T as a roster entry declaring mutable-store; no "
            "postgres-mcp Part is registered in default_registry() today. Catalogued, not "
            "registered -- inherits this record's default disposition (permanent-exclusion) if "
            "and when it is built, unless a future requirement asks for its own A/B "
            "testability, per this record's own reversal condition."
        ),
        tag="[docs-verified]",
    ),
    _DispositionRow(
        component="CA-7 (a hypothetical memory-agent system's own memory-edit node)",
        disposition=DISPOSITION_PERMANENT_EXCLUSION,
        reason=(
            "Catalogued in CATALOG.md ## §T as a roster entry declaring mutable-store; "
            "hypothetical -- no such system is built in this project. Catalogued, not "
            "registered -- inherits this record's default disposition (permanent-exclusion) if "
            "and when it is built, unless a future requirement asks for its own A/B "
            "testability, per this record's own reversal condition."
        ),
        tag="[docs-verified]",
    ),
)


def _live_mutates_store_rows(registry: PartRegistry) -> list[_DispositionRow]:
    """Every ``Part`` in ``registry`` whose ``effects`` contain ``mutates_store`` — computed from
    the registry itself, never a hand list. Raises rather than silently omitting a row for a
    component this module has not been given a named disposition reason for: an enumeration that
    could silently miss a future component is not a discharge.
    """
    rows: list[_DispositionRow] = []
    for name in sorted(registry.keys()):
        part = registry.get(name)
        if "mutates_store" not in part.effects:
            continue
        reason = _KNOWN_REASONS.get(part.name_at_version)
        if reason is None:
            raise ValueError(
                f"{part.name_at_version!r} declares mutates_store but has no named disposition "
                "reason in databasise/evidence/f07_report.py -- extend _KNOWN_REASONS before "
                "regenerating F-07-MUTABLE-STORE-DISPOSITION.md; a component discovered by the "
                "registry and then silently dropped is exactly the incomplete discharge §14.4 "
                "point 3 forbids"
            )
        rows.append(
            _DispositionRow(
                component=part.name_at_version,
                disposition=DISPOSITION_PERMANENT_EXCLUSION,
                reason=reason,
                tag="[code-verified]",
            )
        )
    return rows


def _table_markdown(rows: list[_DispositionRow]) -> str:
    lines = ["| Component | Disposition | Reason | Tag |", "|---|---|---|---|"]
    for row in rows:
        reason_cell = " ".join(row.reason.split())
        lines.append(f"| `{row.component}` | `{row.disposition}` | {reason_cell} | {row.tag} |")
    return "\n".join(lines)


def render_f07_record(registry: PartRegistry) -> str:
    """Pure function of ``registry`` (plus this module's own two catalogued-not-built rows) —
    calling this twice against the same registry state reproduces the identical document, byte
    for byte (``parity_report.py``'s own convention, applied here). Raises if the resulting
    enumeration would be empty: an F-07 record naming nothing is refused as incomplete rather
    than rendered as an empty-table document that reads as a discharge.
    """
    live_rows = _live_mutates_store_rows(registry)
    all_rows = [*live_rows, *_CATALOGUED_NOT_BUILT]
    if not all_rows:
        raise ValueError(
            "F-07 record would enumerate zero mutable-store components -- refused as an "
            "incomplete discharge rather than rendered as an empty-table document"
        )
    table = _table_markdown(all_rows)

    return f"""# F-07 Mutable-Store Disposition — MACH-10

Dated 2026-09-10 (06-09-PLAN.md). Discharges MACH-10 / F-07: every component declaring
`mutates_store` in this project's own registry, plus every roster entry
`docs/system-model/MODEL-RED-TEAM.md`'s F-07 finding names but this project has not built, is
named below in exactly one of §14.4 point 3's two admissible dispositions. Rendered from
`databasise.parts.registry.default_registry()` through `render_f07_record()`
(`databasise/evidence/f07_report.py`) — re-rendering on unchanged inputs reproduces this document
byte-identically; a second run of this discharge is not a second finding.

## The clause under discharge (`CONTRACT.md §14.4` point 3, quoted verbatim)

> The determinism and parity decision. `§5`'s "determinism is verified, never declared" clause
> requires re-running a node on identical input to confirm it, and the parity gate compares a
> decomposition's output to the pre-decomposition original under an A/A band. A node that
> mutates its own backing store on each call is not safely re-runnable for this purpose without
> an explicit snapshot/reset protocol this contract does not define. **Decision:** a
> `mutates_store`-declaring node MUST be excluded from `§5`'s parity and determinism comparisons
> by an explicit refusal, mirroring `§4`'s `unbudgetable`-node exclusion from token comparisons
> — never by substituting an estimated or pre-mutation number in its place — unless and until a
> snapshot/reset protocol is defined and the node is re-verified against it.

## The finding under discharge (`MODEL-RED-TEAM.md` F-07, quoted verbatim)

> `CONTRACT.md §14.4`'s `mutable-store` capability definition states, in its own third numbered
> point: "a `mutates_store`-declaring node MUST be excluded from `§5`'s parity and determinism
> comparisons by an explicit refusal, mirroring `§4`'s `unbudgetable`-node exclusion from token
> comparisons — never by substituting an estimated or pre-mutation number in its place — unless
> and until a snapshot/reset protocol is defined and the node is re-verified against it." No
> snapshot/reset protocol is defined anywhere in `CONTRACT.md`, `ANATOMY.md`, `PARTS.md`,
> `CATALOG.md`, or `RIG.md` — the clause names the escape condition and leaves it unmet. This is
> not a hypothetical class: `CATALOG.md ## §T` catalogues `CA-2` (codebase-memory-mcp,
> `manage_adr`/`delete_project`), `MC-1` (postgres-mcp's `execute_sql` in Unrestricted Mode), and
> `CA-7` (memory-agent systems' own memory-edit node) as three roster entries declaring exactly
> this capability. For each, goal 8's own requirement — vary, budget, A/B-run against the
> original — is structurally unreachable through `§5`'s gate, the machine's only specified
> comparison mechanism, with no repair path scoped anywhere in the record.

**Fix, as recorded by `MODEL-RED-TEAM.md`:** "Define the snapshot/reset protocol `§14.4`'s own
point 3 names as the condition for lifting the exclusion, or state explicitly that
`mutable-store` components are permanently excluded from goal 8's A/B mechanism and must instead
rely on `## §PR`'s operator-asserted promotion path alone — the contract currently names neither
outcome as settled." This record takes the second branch, per component, below.

## Population and disposition

Enumerated from `default_registry()` itself at render time — never a hand list — plus the two
roster entries named above that this project has not registered as a `Part`:

{table}

Every real, registered component above is given the **`{DISPOSITION_PERMANENT_EXCLUSION}`**
disposition, on `06-RESEARCH.md`'s own recommended grounds: the only real instance
(`codebase-memory-mcp@0.1.0`) is admitted whole-engine opaque and already excluded from the
default selector, and no requirement in this milestone asks for either real component's mutation
behaviour to be A/B-testable. The alternative not taken, for either component, is
**`{DISPOSITION_SNAPSHOT_RESET_DEFINED}`** — building an explicit snapshot/reset protocol and
re-verifying the node against it, per §14.4 point 3's own escape clause.

## Verdict

F-07 is discharged for both real, registered mutable-store components this project has built:
`codebase-memory-mcp@0.1.0` and `lightrag/full-delete@0.1.0` each carry exactly one recorded
disposition (`{DISPOSITION_PERMANENT_EXCLUSION}`), enforced as an explicit refusal in the
comparison path for the component actually reachable there
(`databasise.seam.refusals.MutableStoreComparisonExcludedError`, 06-09-PLAN.md Task 2). The two
catalogued-not-built roster entries (`MC-1`, `CA-7`) carry the same disposition, scoped
explicitly to what they are — inherited, not a fresh decision, since neither is built.

**A qualification stated plainly, not left implicit.** `lightrag/full-delete@0.1.0`'s exclusion
is a *structural* fact of how it is dispatched (directly, by `Databasise.delete_document()`,
never through `resolve_selector()`'s candidate pool) rather than an *enforced* refusal the way
`codebase-memory-mcp@0.1.0`'s is — no selector-based comparison call can resolve to it in the
first place, so there is no live code path for `MutableStoreComparisonExcludedError` to guard for
this component today. This record still names it, because this record's own population is
computed from the registry rather than from what happens to be reachable.

**How this stands against MODAL-05.** The comparison path's own explicit refusal
(`MutableStoreComparisonExcludedError`) governs exactly one live candidate pool today: the
capability/default/harness selectors' shared `all_wirings()` set, which names only LightRAG's
five arms and HippoRAG's base wiring — neither `codebase-memory-mcp@0.1.0` nor
`lightrag/full-delete@0.1.0` is a member of that set, so this exclusion does not narrow
`Databasise.compare()`'s own reachable A/B surface for the LightRAG-vs-HippoRAG comparison
`MODAL-05` names. `MODAL-05` itself stays unproven for the separate, unrelated reason recorded in
`databasise/evidence/CROSS-MODALITY-EVIDENCE.md` (the owner-deferred real cross-modality run) —
this record's own F-07 disposition neither advances nor blocks that separate open requirement.

## Method and limits

**Method.** `_live_mutates_store_rows()` (`databasise/evidence/f07_report.py`) walks
`default_registry().keys()`, filters to every `Part` whose `effects` contain `mutates_store`, and
raises rather than silently omitting a row if it finds a component this module has not been told
a disposition reason for. The two catalogued-not-built rows are a fixed, hand-maintained
addition, since neither is discoverable from the registry by construction.

**The write-quiesce caveat (06-RESEARCH.md's own assumption A5), recorded as unestablished.** Had
either component taken the `{DISPOSITION_SNAPSHOT_RESET_DEFINED}` disposition instead, a
file-level snapshot/reset of `codebase-memory-mcp`'s own SQLite database (plus its WAL and SHM
siblings) would assume no other process holds an open write handle across the snapshot window — a
brief write-quiesce this project has **not established** against
`databasise/foreign/codebase_memory_mcp_adapter.py`'s actual concurrency model. This record states
that limit as not established, rather than assuming it away, since it is exactly the concurrency
question a reader would otherwise have to ask unanswered.

**What is guaranteed under an interrupted or concurrent snapshot/reset.** Neither real component
took the `{DISPOSITION_SNAPSHOT_RESET_DEFINED}` disposition, so no snapshot or reset ever runs
against either one — the explicit refusal fires before any arm executes (06-09-PLAN.md Task 2's
own tested acceptance criterion), which makes an interrupted-mid-snapshot state and a
two-comparisons-touching-the-same-store race both structurally impossible under the disposition
this record actually adopts. Neither guarantee is established by an actual snapshot/reset
mechanism, because none is built; both are guaranteed instead by the mutation never being
attempted concurrently with a comparison in the first place. Had either component instead taken
`{DISPOSITION_SNAPSHOT_RESET_DEFINED}`, both questions would need a real answer this record does
not attempt to pre-supply for a protocol that was never built.

**Reversal.** Either component's disposition flips to `{DISPOSITION_SNAPSHOT_RESET_DEFINED}` only
when a future requirement specifically asks for that component's own mutation behaviour to be
A/B-testable — not by this record being re-rendered on an unchanged registry, which reproduces it
byte-identically by design.
"""


__all__ = [
    "DISPOSITION_PERMANENT_EXCLUSION",
    "DISPOSITION_SNAPSHOT_RESET_DEFINED",
    "render_f07_record",
]
