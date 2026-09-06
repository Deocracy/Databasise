"""Renders ``databasise/evidence/PARITY-EVIDENCE.md`` and
``databasise/evidence/DECLARED-DEVIATIONS.md`` from the committed result files under
``databasise/evidence/parity_results/`` (03-09-PLAN.md Task 2).

Follows ``databasise/evidence/falsifier2.py``'s own house style: load committed inputs, render
Markdown a second author can read without opening a test file, never recompute a number the
harness (``databasise.parity.run_comparison``, ``databasise.parity.storage_audit``) already
recorded. ``render_markdown()`` and ``render_deviations_markdown()`` are pure functions of the
committed inputs under ``parity_results/`` — no timestamp, no host path beyond what a result file
itself already recorded, no run-varying value of any kind — so two calls in one process (and two
runs of ``main()`` over unchanged inputs) return byte-identical text.

**Provenance check (``--check-results``).** :func:`check_results` validates that every committed
result file under ``parity_results/`` carries the fields Task 1's own acceptance criteria name,
and enforces the plan's own stated prohibition: a result whose ``status`` is ``"inconclusive"``
must carry no comparison number (``chunk_diff``/``entity_diff``/``relation_diff``/
``keyword_variance_band`` all null) and must name a reason. This is the one implementation of
"what a complete result looks like" that both Task 1's own ``<verify>`` command and this module's
rendering share, so the two can never silently disagree about what "complete" means.

**The declared-deviation refusal (CONTRACT §5).** :func:`render_deviations_markdown` raises
:class:`UnreasonedDeviationError` for any :class:`DeclaredDeviation` whose ``cause`` is empty or
falls in a small set of generic/blanket phrases (``"expected variance"``, ``"noise"``, ...) — an
absorber category that lets any excursion through unnamed is exactly the failure mode the
parity-not-gain rule exists to prevent. Zero deviations is a result (rendered as an explicit
"zero, and here is why" statement); an absent file is not.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).resolve().parent / "parity_results"
EVIDENCE_PATH = Path(__file__).resolve().parent / "PARITY-EVIDENCE.md"
DEVIATIONS_PATH = Path(__file__).resolve().parent / "DECLARED-DEVIATIONS.md"

# The one committed, human-authored input this module reads (03-10-PLAN.md Task 1). Lives at the
# evidence root, not inside the machine-written `parity_results/` directory, because it is never
# written by the harness or this renderer — see `load_human_findings()`.
HUMAN_FINDINGS_PATH = Path(__file__).resolve().parent / "human_findings.json"

ARMS: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")

# Matches databasise.parity.run_comparison._DEFAULT_KEYWORD_VARIANCE_RUNS. The choice and its
# reasoning are recorded in 03-09-SUMMARY.md's "Decisions Made" section (03-09-PLAN.md Task 1's
# own instruction: "record the choice and its reason in the plan summary").
KEYWORD_VARIANCE_N = 5

# databasise.parity.run_arm._DETERMINISM_SETTING / _CONCURRENCY_SETTING — restated here rather
# than imported, so this evidence module never needs to import a live-endpoint-touching module
# just to render text about settings that are plain string constants.
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"

_GATE_AMENDMENT_REF = ".planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md"
_GATE_WAIVER_REF = ".planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md"
_VALIDATION_REF = ".planning/phases/03-lightrag-query-side/03-VALIDATION.md"

# The corpus snapshot carries exactly 2 queries (03-VALIDATION.md's own note); Task 3's human
# spot-check section is rendered per query, never inferred from whatever the record set happens
# to name.
QUERY_IDS: tuple[str, ...] = ("q1", "q2")


# --------------------------------------------------------------------------------------------- #
# Loading committed inputs
# --------------------------------------------------------------------------------------------- #


def load_comparison(arm: str) -> list[dict[str, Any]]:
    """Load the committed per-query comparison records for one arm."""
    path = RESULTS_DIR / f"{arm}-comparison.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_storage_audit(arm: str) -> dict[str, Any]:
    """Load the committed storage-audit result for one arm. Today every committed file records
    an environment-precondition refusal (see module docstring and 03-09-SUMMARY.md); once a real
    run lands, this same loader reads whatever shape ``databasise.parity.storage_audit`` writes.
    """
    path = RESULTS_DIR / f"{arm}-storage-audit.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_human_findings() -> dict[str, Any]:
    """Load the one committed, human-authored input this module reads: ``declared_causes``
    (per-excursion causes) and ``answer_spotchecks`` (Task 3's human judgment landing place).
    Returns ``{}`` when the file is absent — an absent file is not a silent pass; every excursion
    it would have named a cause for still falls through to :func:`_collect_deviations`'s
    no-matching-entry refusal, which names this file's own path.
    """
    if not HUMAN_FINDINGS_PATH.exists():
        return {}
    return json.loads(HUMAN_FINDINGS_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------- #
# Run-state derivation (03-10-PLAN.md Task 2) — every prose section routes through this; no
# section may assert a run state it did not read.
# --------------------------------------------------------------------------------------------- #


def _run_state() -> str:
    """Derive one of ``"completed"``, ``"inconclusive"``, or ``"mixed"`` from the ``status``
    field of every committed comparison record and every committed storage audit. Reads via
    :func:`load_comparison`/:func:`load_storage_audit`, both of which resolve the module-level
    :data:`RESULTS_DIR` global at call time — so ``monkeypatch.setattr(parity_report,
    "RESULTS_DIR", tmp_path)`` in a test retargets this function too, with no separate
    ``results_dir`` parameter needed.
    """
    statuses = {
        record.get("status", "inconclusive")
        for arm in ARMS
        for record in load_comparison(arm)
    }
    statuses |= {load_storage_audit(arm).get("status", "inconclusive") for arm in ARMS}
    if statuses == {"completed"}:
        return "completed"
    if statuses == {"inconclusive"}:
        return "inconclusive"
    return "mixed"


def _arm_degraded(arm: str) -> tuple[bool, str]:
    """Whether any completed comparison record for ``arm`` reports
    ``decomposed_run_record.degraded`` — read fresh from the committed records on every call, per
    this module's own no-hardcoded-run-state rule (03-10-PLAN.md Task 2; 03-10 fix cycle, finding
    2). Returns the first degradation reason found, or ``""`` when none of the arm's completed
    records degraded. A clean re-run of a currently-degraded arm flips this to ``(False, "")``
    with no code change — every prose section that reads it follows automatically.
    """
    for record in load_comparison(arm):
        if record.get("status") != "completed":
            continue
        drr = record.get("decomposed_run_record", {})
        if drr.get("degraded"):
            return True, drr.get("degradation_reason") or drr.get("stop_reason") or ""
    return False, ""


def _never_executed_nodes(arm: str) -> list[str]:
    """Node ids ``arm``'s storage audit reports (its full wiring node set) that never appear in
    any of the arm's completed comparison records' ``decomposed_run_record.nodes`` list — i.e.
    nodes the comparison run's scheduler never dispatched at all before halting on a
    ``NodeExecutionError`` (``databasise/runner/scheduler.py`` breaks the whole scheduling loop on
    the first batch failure, so every node downstream of the failure is never dispatched).

    The storage-audit result file itself carries no dispatch/degraded information of its own (a
    known, separately-tracked gap — the audit's ``rows`` record only which handles were touched,
    not whether the node ran at all before the batch it belonged to failed); this cross-references
    the comparison run's own per-node dispatch list instead, read fresh on every call so a repair
    of the underlying crash is reflected with no code change here.
    """
    audit_nodes = {row["node_id"] for row in load_storage_audit(arm).get("rows", [])}
    executed_nodes = {
        node["node_id"]
        for record in load_comparison(arm)
        if record.get("status") == "completed"
        for node in record.get("decomposed_run_record", {}).get("nodes", [])
    }
    return sorted(audit_nodes - executed_nodes)


# --------------------------------------------------------------------------------------------- #
# Provenance check (Task 1's own <verify> command; also exposed via --check-results)
# --------------------------------------------------------------------------------------------- #

_REQUIRED_COMPARISON_KEYS: tuple[str, ...] = (
    "status",
    "arm",
    "query_id",
    "query",
    "corpus_hash",
    "determinism_setting",
    "concurrency_setting",
    "run_count",
    "resolved_model_identities",
    "inconclusive_reason",
)

_COMPARISON_NUMBER_KEYS: tuple[str, ...] = (
    "chunk_diff",
    "entity_diff",
    "relation_diff",
    "keyword_variance_band",
)

_REQUIRED_AUDIT_KEYS: tuple[str, ...] = ("arm", "command", "exit_code", "status", "outcome", "reason")


@dataclass(frozen=True)
class ProvenanceViolation:
    """One committed result file's departure from "what a complete result looks like"."""

    file: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.file}: {self.detail}"


def check_results(results_dir: Path | None = None) -> list[ProvenanceViolation]:
    """Validate every committed result file under ``parity_results/`` (or ``results_dir``, for
    tests) carries its required provenance fields, and that no result carries a comparison number
    alongside an ``"inconclusive"`` status — the plan's own stated prohibition. Returns an empty
    list when clean; never raises for a validation failure (the CLI decides the exit code).
    """
    results_dir = results_dir or RESULTS_DIR
    violations: list[ProvenanceViolation] = []

    for arm in ARMS:
        comparison_path = results_dir / f"{arm}-comparison.json"
        if not comparison_path.exists():
            violations.append(ProvenanceViolation(str(comparison_path), "file does not exist"))
        else:
            records = json.loads(comparison_path.read_text(encoding="utf-8"))
            if not records:
                violations.append(
                    ProvenanceViolation(str(comparison_path), "no query records recorded")
                )
            for record in records:
                missing = [k for k in _REQUIRED_COMPARISON_KEYS if k not in record]
                if missing:
                    violations.append(
                        ProvenanceViolation(
                            str(comparison_path),
                            f"query {record.get('query_id', '?')!r} missing required key(s) {missing}",
                        )
                    )
                if record.get("status") == "inconclusive":
                    if not record.get("inconclusive_reason"):
                        violations.append(
                            ProvenanceViolation(
                                str(comparison_path),
                                f"query {record.get('query_id', '?')!r} is inconclusive but names "
                                "no reason",
                            )
                        )
                    carries_number = any(
                        record.get(k) is not None for k in _COMPARISON_NUMBER_KEYS
                    )
                    if carries_number:
                        violations.append(
                            ProvenanceViolation(
                                str(comparison_path),
                                f"query {record.get('query_id', '?')!r} is status=inconclusive but "
                                "carries a comparison number — the plan's own stated prohibition",
                            )
                        )

        audit_path = results_dir / f"{arm}-storage-audit.json"
        if not audit_path.exists():
            violations.append(ProvenanceViolation(str(audit_path), "file does not exist"))
        else:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            missing = [k for k in _REQUIRED_AUDIT_KEYS if k not in audit]
            if missing:
                violations.append(
                    ProvenanceViolation(str(audit_path), f"missing required key(s) {missing}")
                )

    return violations


def _degraded_but_vacuous_arms(results_dir: Path | None = None) -> list[str]:
    """Arm names whose committed comparison file has at least one ``status="completed"`` record
    with ``decomposed_run_record.degraded=true`` and every comparison-number diff empty — such a
    record satisfies every rule :func:`check_results` checks (required keys present, no number
    alongside ``inconclusive``) but its zero diffs reflect a crashed run that never completed a
    real retrieval, not a validated retrieval-level agreement (WR-03, ``03-REVIEW.md``). Used only
    to qualify the CLI's "clean" success line — it is not itself a :class:`ProvenanceViolation`,
    since the ``degraded``/``degradation_reason`` fields are already honestly disclosed on the
    record; the gap is that a reader of the CLI's bare "clean" line would not otherwise know.
    """
    results_dir = results_dir or RESULTS_DIR
    degraded_arms: list[str] = []
    for arm in ARMS:
        comparison_path = results_dir / f"{arm}-comparison.json"
        if not comparison_path.exists():
            continue
        records = json.loads(comparison_path.read_text(encoding="utf-8"))
        for record in records:
            if record.get("status") != "completed":
                continue
            if not record.get("decomposed_run_record", {}).get("degraded"):
                continue
            all_empty = all(
                not (record.get(key) or {}).get("symmetric_difference")
                for key in ("chunk_diff", "entity_diff", "relation_diff")
            )
            if all_empty:
                degraded_arms.append(arm)
                break
    return degraded_arms


# --------------------------------------------------------------------------------------------- #
# The declared-deviation record (CONTRACT §5) — Task 2's own refusal behavior
# --------------------------------------------------------------------------------------------- #

# A deviation "cause" matching one of these (case/whitespace-insensitive) is an absorber category,
# not a named cause — CONTRACT §5's parity-not-gain rule exists precisely to forbid this.
_GENERIC_CAUSES: frozenset[str] = frozenset(
    {
        "",
        "expected variance",
        "expected",
        "variance",
        "noise",
        "n/a",
        "na",
        "unknown",
        "unclear",
        "tbd",
        "misc",
        "other",
    }
)


class UnreasonedDeviationError(ValueError):
    """A :class:`DeclaredDeviation` whose ``cause`` is empty or a generic/blanket category — see
    module docstring.
    """


class StaleDeviationCauseError(UnreasonedDeviationError):
    """A ``human_findings.json`` ``declared_causes`` entry names a ``symmetric_difference`` that no
    longer matches the currently measured one (03-10-PLAN.md Task 1). A cause names one specific
    excursion; a re-run that changes the measurement invalidates it rather than silently
    inheriting it onto whatever the new measurement happens to be. Subclasses
    :class:`UnreasonedDeviationError` so every existing caller/test that catches the parent keeps
    working unchanged.
    """


class OrphanDeviationCauseError(UnreasonedDeviationError):
    """A ``human_findings.json`` ``declared_causes`` entry's ``(arm, query_id, field)`` triple
    matches no measured excursion in the committed comparison records (03-10 fix cycle, finding
    7). A cause filed under a mistyped key, or one whose excursion disappeared on a re-run, must
    not sit silently in the human-authored record describing nothing — this is the same
    record-never-silent discipline as :class:`StaleDeviationCauseError`, just for the opposite
    direction (a cause with no matching measurement, rather than a measurement whose cause is
    stale).
    """


@dataclass(frozen=True)
class DeclaredDeviation:
    """One CONTRACT §5 declared-deviation entry: an excursion outside the stated retrieval-level
    tolerance, named individually with its own cause. The retrieval-level tolerance itself starts
    at zero (03-09-PLAN.md's own flagged planner assumption: with keywords pinned and one shared
    index, exact agreement is the expectation), so any non-empty ``symmetric_difference`` on a
    pinned-keyword run is, by default, an excursion requiring an entry here.

    ``field`` (default ``""`` for backward compatibility with hand-built test fixtures) names
    which of ``chunk_diff``/``entity_diff``/``relation_diff`` the excursion was measured on — the
    third element of the ``(arm, query_id, field)`` triple ``human_findings.json``'s
    ``declared_causes`` entries key against.

    ``recorded_by``/``recorded_at`` (both default ``""``) mirror ``AnswerSpotCheck``'s own
    provenance fields (03-10 fix cycle, finding 8) — ``declared_causes`` is documented as
    "human-authored" and its sibling ``answer_spotchecks`` schema already required both; a cause
    with no recorded provenance is the same class of defect as an unverified cause.
    """

    arm: str
    query_id: str
    description: str
    cause: str
    field: str = ""
    recorded_by: str = ""
    recorded_at: str = ""


def render_deviations_markdown(deviations: list[DeclaredDeviation]) -> str:
    """Render ``DECLARED-DEVIATIONS.md``. Raises :class:`UnreasonedDeviationError` before
    rendering anything if any entry's cause is empty or generic — the whole render fails rather
    than emitting a document with one bad row, so a bad cause can never slip into a committed
    document silently.
    """
    for deviation in deviations:
        cause_norm = deviation.cause.strip().lower()
        if cause_norm in _GENERIC_CAUSES:
            raise UnreasonedDeviationError(
                f"{deviation.arm}/{deviation.query_id}/{deviation.field or '?'}: cause "
                f"{deviation.cause!r} is empty or a generic/blanket category — CONTRACT §5 "
                "requires each excursion named individually with its own specific cause, not an "
                f"absorber category. Add a `declared_causes` entry to {HUMAN_FINDINGS_PATH} for "
                f"(arm={deviation.arm!r}, query_id={deviation.query_id!r}, "
                f"field={deviation.field!r}) naming the measured {deviation.description}."
            )

    sections = [
        "# Declared Deviations\n",
        (
            "CONTRACT §5's parity-not-gain record: every excursion outside the stated "
            "retrieval-level tolerance (zero, per 03-09-PLAN.md's own flagged planner "
            "assumption — see `PARITY-EVIDENCE.md`), named individually with its own cause. "
            "A blanket or catch-all cause makes this document's own renderer refuse to render "
            "rather than silently absorbing the excursion into an unnamed category.\n"
        ),
    ]

    if not deviations:
        state = _run_state()
        if state == "inconclusive":
            sections.append(
                "## Zero declared deviations\n\n"
                "No excursion is recorded in this document. This is a stated zero, not an absent "
                "file — and, as of this render, it reflects that **no completed comparison run has "
                "occurred**: every arm's committed result under `parity_results/` carries "
                "`status=\"inconclusive\"` (the index-identity precondition and/or the "
                "`v1/.env.parity` precondition failed on this machine — see `PARITY-EVIDENCE.md`'s "
                "\"What was compared\" section). A stated zero here should therefore be read as "
                "\"nothing has been measured yet,\" not as \"the comparison ran and found no "
                "excursions.\" Re-running `parity_report.py` after a real comparison lands will "
                "populate this section with either named entries or an updated zero statement that "
                "reflects an actual completed comparison.\n"
            )
        else:
            sections.append(
                "## Zero declared deviations\n\n"
                "No excursion is recorded in this document. This is a stated zero, and, as of "
                "this render, it reflects a **completed comparison that found no excursion**: "
                "every completed comparison record's `chunk_diff`/`entity_diff`/`relation_diff` "
                "carried an empty `symmetric_difference`. This is a different statement from "
                "\"nothing has been measured yet\" — the comparison ran and found agreement.\n"
            )
    else:
        header = (
            "| arm | query | measured difference | cause | recorded by | recorded at |\n"
            "|---|---|---|---|---|---|\n"
        )
        rows = [
            f"| {d.arm} | {d.query_id} | {d.description} | {d.cause} | "
            f"{d.recorded_by or 'unrecorded'} | {d.recorded_at or 'unrecorded'} |"
            for d in deviations
        ]
        sections.append("## Named deviations\n\n" + header + "\n".join(rows) + "\n")

    # CR-01 (03-REVIEW.md): a structural v2-vs-v1 difference known from reading the code, not
    # from a measured run. Emitted by the renderer itself so a re-render cannot drop it — a hand
    # edit to DECLARED-DEVIATIONS.md is overwritten by main() on the next render.
    sections.append(_render_known_design_deviation())

    return "\n".join(sections)


def _render_known_design_deviation() -> str:
    """CR-01's known structural v2-vs-v1 difference (one shared query-vector embed vs v1's two
    separate keyword-derived vectors) — originally recorded as a standing prediction ahead of any
    measurement. Now testable against the committed records (03-10-PLAN.md Task 2): state the
    measured outcome rather than leaving the prediction standing.
    """
    header = (
        "## Known design deviation (pending measurement)\n\n"
        "Not a measured excursion (`_collect_deviations()` only picks up a `symmetric_difference` "
        "on a `status=\"completed\"` comparison record); recorded here ahead of the automatic "
        "mechanism because it is already known from reading the code, per CR-01's `03-REVIEW.md` "
        "finding.\n\n"
    )
    graph_diffs = [
        (arm, record.get("entity_diff"), record.get("relation_diff"))
        for arm in ("hybrid", "local", "global")
        for record in load_comparison(arm)
        if record.get("status") == "completed"
    ]
    zero_entity_relation = graph_diffs and all(
        entity_diff is not None
        and relation_diff is not None
        and not entity_diff.get("symmetric_difference")
        and not relation_diff.get("symmetric_difference")
        for _arm, entity_diff, relation_diff in graph_diffs
    )
    any_degraded = any(_arm_degraded(arm)[0] for arm in ("hybrid", "local", "global"))
    if zero_entity_relation:
        status_sentence = (
            "**Status, from the completed run**: `hybrid`/`local`/`global` all measured "
            "`entity_diff`/`relation_diff` `symmetric_difference=[]` on both corpus queries — "
            "the predicted excursion did not surface as a non-empty diff. "
            + (
                "That measurement is not dispositive, though: the same three arms' decomposed "
                "runs degraded before completing a real retrieval on both sides (see the "
                "per-arm degradation note in \"Per-arm retrieval-level comparison\" and the "
                "Verdict section) — the zero reflects both the decomposed and original arm "
                "retrieving nothing on this run, not a validated agreement over non-trivial "
                "entity/relation sets. The structural difference below is unrefuted, not "
                "confirmed absent; a clean run is needed to actually test it.\n\n"
                if any_degraded
                else "Read this alongside the storage audit, whose `matched`/`no-touch`/"
                "`over-declared` counts are independent evidence the ported nodes touched what "
                "they declared.\n\n"
            )
        )
    else:
        status_sentence = (
            "**Status, from the completed run**: not yet re-derivable from a completed "
            "`entity_diff`/`relation_diff` on all three graph arms — see the per-arm table "
            "above for what is actually recorded.\n\n"
        )
    table = (
        "| arm | query | measured difference | cause |\n"
        "|---|---|---|---|\n"
        "| hybrid, local, global | n/a — design-level, not a measured excursion | v2's "
        "`entity-lookup`/`relation-lookup` embed one raw-query vector (`embedder-query`'s output "
        "for `ctx.inputs[\"keywords\"][\"query\"]`) | v1 embeds two separate keyword-derived "
        "vectors instead: `\", \".join(ll_keywords)` for entity lookup (`_get_node_data`) and "
        "`\", \".join(hl_keywords)` for relation lookup (`_get_edge_data`), per "
        "`v1/lightrag/operate.py`. The v2 wiring (`databasise/wirings/lightrag/base.json`, frozen "
        "input) feeds one shared `embedder-query` node into `entity-lookup`, `relation-lookup`, "
        "and `chunk-vector`, so this is a structural difference, not a bug — CR-01's fix makes "
        "`embedder-query` embed the real query text (closing the \"empty string\" bug) but does "
        "not restructure the wiring into v1's two-keyword-vector shape. |\n"
    )
    return header + status_sentence + table


def _collect_deviations() -> list[DeclaredDeviation]:
    """Scan every committed comparison record for a completed excursion (a non-empty
    ``symmetric_difference`` on a completed run's ``chunk_diff``/``entity_diff``/``relation_diff``)
    and look up its cause in ``human_findings.json``'s ``declared_causes`` (Task 1). Three
    outcomes per excursion, all of which abort the whole render:

    - no matching ``(arm, query_id, field)`` entry: ``cause=""`` is left on the returned
      :class:`DeclaredDeviation`, so :func:`render_deviations_markdown`'s existing
      absorber-category refusal fires — its message names :data:`HUMAN_FINDINGS_PATH`, the exact
      triple, and the measured ``symmetric_difference``.
    - a matching entry whose recorded ``symmetric_difference`` no longer equals the one just
      measured: raises :class:`StaleDeviationCauseError` immediately — a re-run changed the
      measurement, so the recorded cause no longer applies to it.
    - a matching entry with a blanket/empty cause text: unchanged behavior —
      :func:`render_deviations_markdown`'s ``_GENERIC_CAUSES`` check still refuses it.

    A fourth outcome applies to the ``declared_causes`` list as a whole, after every measured
    excursion has been scanned: any entry whose ``(arm, query_id, field)`` triple matched no
    measured excursion is an orphan — raises :class:`OrphanDeviationCauseError` (03-10 fix cycle,
    finding 7) rather than exiting clean with a dead cause left on file.
    """
    declared_causes = load_human_findings().get("declared_causes", [])
    causes_by_key: dict[tuple[str, str, str], dict[str, Any]] = {
        (entry["arm"], entry["query_id"], entry["field"]): entry for entry in declared_causes
    }
    used_keys: set[tuple[str, str, str]] = set()

    deviations: list[DeclaredDeviation] = []
    for arm in ARMS:
        for record in load_comparison(arm):
            if record.get("status") != "completed":
                continue
            for field_name in ("chunk_diff", "entity_diff", "relation_diff"):
                diff = record.get(field_name)
                if not diff or not diff.get("symmetric_difference"):
                    continue

                measured = diff["symmetric_difference"]
                query_id = record.get("query_id", "?")
                description = f"{field_name}: symmetric_difference={measured}"
                key = (arm, query_id, field_name)
                entry = causes_by_key.get(key)

                if entry is None:
                    # No cause recorded yet — leave cause="" so the existing absorber-category
                    # refusal fires (the point of the refusal: force a human to name it first).
                    cause = ""
                    recorded_by = recorded_at = ""
                elif entry.get("symmetric_difference") != measured:
                    raise StaleDeviationCauseError(
                        f"{arm}/{query_id}/{field_name}: the declared_causes entry in "
                        f"{HUMAN_FINDINGS_PATH} was written against "
                        f"symmetric_difference={entry.get('symmetric_difference')!r}, but the "
                        f"currently measured symmetric_difference is {measured!r} — a re-run "
                        "changed the measurement, so the recorded cause no longer applies to "
                        "it. Update the matching entry before this document can render again."
                    )
                else:
                    used_keys.add(key)
                    cause = entry.get("cause", "")
                    recorded_by = entry.get("recorded_by", "")
                    recorded_at = entry.get("recorded_at", "")

                deviations.append(
                    DeclaredDeviation(
                        arm=arm,
                        query_id=query_id,
                        description=description,
                        cause=cause,
                        field=field_name,
                        recorded_by=recorded_by,
                        recorded_at=recorded_at,
                    )
                )

    orphans = sorted(set(causes_by_key) - used_keys)
    if orphans:
        orphan_list = ", ".join(f"(arm={a!r}, query_id={q!r}, field={f!r})" for a, q, f in orphans)
        raise OrphanDeviationCauseError(
            f"{HUMAN_FINDINGS_PATH} has {len(orphans)} declared_causes entry(ies) matching no "
            f"measured excursion in the committed comparison records: {orphan_list}. Each cause "
            "names one specific excursion; a triple that matches nothing currently measured is "
            "either a mistyped key or a cause whose excursion disappeared on a re-run. Remove "
            "the stale entry or correct its (arm, query_id, field) to match the excursion it was "
            "written for."
        )

    return deviations


# --------------------------------------------------------------------------------------------- #
# The human answer-substance spot-check (03-10-PLAN.md Task 3)
# --------------------------------------------------------------------------------------------- #

_VALID_JUDGMENTS: frozenset[str] = frozenset({"match", "no-match", "partial"})


class InvalidJudgmentError(ValueError):
    """An ``answer_spotchecks`` entry's ``judgment`` is not one of
    :data:`_VALID_JUDGMENTS`. A judgment must be a judgment, not free text that quietly
    renders (03-10-PLAN.md Task 3) — never derived from a diff number, never defaulted.
    """


@dataclass(frozen=True)
class AnswerSpotCheck:
    """One human-recorded answer-substance judgment for one corpus query, read from
    ``human_findings.json``'s ``answer_spotchecks`` list (Task 1 created the key empty; this
    task is the first to read and render it). Never fabricated, defaulted, or inferred from a
    diff number — an unrecorded judgment renders as unrecorded, not as a guess.
    """

    query_id: str
    arm: str
    judgment: str
    notes: str
    recorded_by: str
    recorded_at: str

    def __post_init__(self) -> None:
        if self.judgment not in _VALID_JUDGMENTS:
            raise InvalidJudgmentError(
                f"answer_spotchecks entry for query_id={self.query_id!r}: judgment "
                f"{self.judgment!r} is not one of {sorted(_VALID_JUDGMENTS)} — a judgment must "
                "be a judgment, not free text that quietly renders."
            )


def _render_spotcheck_arm_guidance() -> str:
    """Which arm the live re-run this section names can actually be performed against (03-10 fix
    cycle, finding 5). `hybrid`/`local`/`global`'s decomposed runs degrade before reaching
    `generate` (see the per-arm degradation notes above and the Verdict section), so they never
    produce a decomposed-side answer to read side by side with v1's — instructing a spot-check
    against one of those three arms would mean judging two non-answers. `naive` completed its
    full pipeline end to end and has a real generated answer on both sides, so it is the arm
    where this read is actually possible today. Derived per-arm on every render, not a fixed
    recommendation, so a repair of the crash flips this automatically.
    """
    if _run_state() != "completed":
        return (
            "No comparison run recorded in this document reached completion (see \"What was "
            "compared\"), so no arm has an answer to read yet either side of this spot-check.\n"
        )
    graph_arms = ("hybrid", "local", "global")
    blocked_arms = [arm for arm in graph_arms if _arm_degraded(arm)[0]]
    if blocked_arms:
        return (
            f"`{'`, `'.join(blocked_arms)}` cannot host this read today: each one's decomposed "
            "run degrades before reaching `generate` (see the per-arm degradation notes above), "
            "so there is no decomposed-side answer to compare — v1's own answer for those "
            "query/arm pairs is also `\"…[no-context]\"` (see `original_arm_result.answer` in "
            "the raw `parity_results/` files). Run this spot-check against `naive` instead, "
            "whose pipeline completed end to end on both sides; the graph arms become available "
            "for this read once their crash is repaired (out of this plan's scope).\n"
        )
    return (
        "All five arms completed without a decomposed-run degradation, so this read is "
        "available against any of them.\n"
    )


def _render_answer_spotcheck() -> str:
    """The landing place 03-VERIFICATION.md's second ``behavior_unverified_items`` entry asks
    for: a committed input a human record survives re-render through, because both evidence
    documents are renderer-owned and a hand edit to either is overwritten on the next render
    (03-REVIEW-FIX.md CR-01).
    """
    by_query: dict[str, AnswerSpotCheck] = {}
    for raw in load_human_findings().get("answer_spotchecks", []):
        spotcheck = AnswerSpotCheck(
            query_id=raw["query_id"],
            arm=raw["arm"],
            judgment=raw["judgment"],
            notes=raw.get("notes", ""),
            recorded_by=raw.get("recorded_by", ""),
            recorded_at=raw.get("recorded_at", ""),
        )
        by_query[spotcheck.query_id] = spotcheck

    sections = [
        "## Human spot-check of answer substance\n",
        (
            "Criterion 6's substitute-gate half this document's retrieval-level comparison "
            "does not cover: an LLM-generated answer's *substance* is not mechanically "
            "checkable — `generate` is stochastic and no A/A floor is calibrated yet "
            f"(MACH-02/MACH-03 deferred to Phase 6, `{_GATE_AMENDMENT_REF}`) — so only a human "
            "judgment call substitutes for it. Recorded per query in `human_findings.json`'s "
            f"`answer_spotchecks` list; run instructions are `{_VALIDATION_REF}`'s Manual-Only "
            "Verifications row for this behavior.\n"
        ),
        (
            "Each completed comparison record already carries the original (v1) arm's answer "
            "text under `original_arm_result.answer` (see the raw `parity_results/` files); the "
            "decomposed arm's answer text is not recorded in the run record, so the side-by-side "
            "read this section names is a live re-run, not a document comparison.\n"
        ),
        _render_spotcheck_arm_guidance(),
    ]
    for query_id in QUERY_IDS:
        entry = by_query.get(query_id)
        if entry is None:
            sections.append(
                f"### `{query_id}`\n\n"
                "**Not yet recorded.** A human is required — answer substance is not "
                "mechanically checkable and no A/A floor is calibrated (MACH-02/MACH-03 "
                "deferred to Phase 6). To record it, add an entry to `human_findings.json`'s "
                f"`answer_spotchecks` list naming `query_id={query_id!r}`, the `arm` compared, "
                "a `judgment` (one of the three values this module's own "
                "`InvalidJudgmentError` enforces), `notes`, `recorded_by`, and `recorded_at`. "
                f"Run instructions: `{_VALIDATION_REF}`'s Manual-Only Verifications table, "
                "\"Human spot-check of answer substance\" row.\n"
            )
        else:
            recorded_by = entry.recorded_by or "unrecorded"
            recorded_at = entry.recorded_at or "unrecorded"
            sections.append(
                f"### `{query_id}`\n\n"
                f"**Judgment: `{entry.judgment}`** (arm `{entry.arm}`, recorded by "
                f"{recorded_by} at {recorded_at}).\n\n"
                f"{_escape_cell(entry.notes)}\n"
            )
    return "\n".join(sections)


# --------------------------------------------------------------------------------------------- #
# PARITY-EVIDENCE.md rendering
# --------------------------------------------------------------------------------------------- #


def _escape_cell(value: str) -> str:
    """Escape a markdown table cell so an author-supplied `|` or newline can't silently split a
    rendered row into extra columns (mirrors ``falsifier2.py``'s own ``_escape_cell``, WR-01).
    """
    return value.replace("|", "\\|").replace("\n", " ")


def _render_what_was_compared() -> str:
    state = _run_state()
    completed = state == "completed"

    if completed:
        one_index_trailing = (
            "and gated on every comparison run by plan 03-02's index-identity verifier "
            "(`databasise.parity.import_index.verify_import`) — the same precondition this "
            "run passed.\n"
        )
    else:
        one_index_trailing = (
            "and gated on every comparison run by plan 03-02's index-identity verifier "
            "(`databasise.parity.import_index.verify_import`) — the same precondition this "
            "document's own recorded runs failed against (see below).\n"
        )

    if completed:
        naive_record = load_comparison("naive")[0]
        ids = naive_record["resolved_model_identities"]
        pinned_models_clause = (
            "The completed run resolved these identities live from each provider's response, "
            "never the requested id (Phase 1 D-12) — recorded per-comparison in each committed "
            f"record's own `resolved_model_identities` field: `decomposed_generate={ids['decomposed_generate']!r}`, "
            f"`original_arm_llm_model={ids['original_arm_llm_model']!r}`, "
            f"`original_arm_embedding_model={ids['original_arm_embedding_model']!r}` (naive/bypass, "
            "the two arms whose `generate` node ran). `hybrid`/`local`/`global` recorded "
            "`decomposed_generate=\"\"` because their `generate` node never ran — see the "
            "per-arm degradation note in \"Per-arm retrieval-level comparison\" below.\n"
        )
    else:
        pinned_models_clause = (
            "No comparison run recorded in this document reached the point of resolving these "
            "identities live (see \"What is not measured\" and the precondition state below); "
            "the pins themselves are config, not a claim about what ran.\n"
        )

    if completed:
        hashes = sorted(
            {
                record.get("corpus_hash", "")
                for arm in ARMS
                for record in load_comparison(arm)
                if record.get("status") == "completed"
            }
        )
        run_state_bullet = (
            "- **Run state (this render)**: all five arms' comparison runs and storage audits "
            f"completed, against corpus hash `{hashes[0] if len(hashes) == 1 else hashes}`. "
            "`v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` "
            "were all present for this run — this is a completed comparison, not D-02's failed-"
            "precondition refusal (`inconclusive`) path. That refusal path is proven "
            "separately, against a monkeypatched fixture, in "
            "`tests/parity/test_parity_evidence.py`, so it stays covered even though the real "
            "committed data no longer exercises it.\n"
        )
    else:
        run_state_bullet = (
            "- **Environment precondition state on this machine (this render)**: `v1/.venv`, "
            "`v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are all "
            "absent — gitignored, worktree-local build artifacts from a different execution "
            "session (03-02's own real ingest run) that do not carry over to a freshly spawned "
            "worktree. Every arm's comparison run below therefore stopped at the index-identity "
            "precondition gate before either arm was touched, and every arm's storage-audit run "
            "stopped at client construction before the scheduler ran a single node. Both are the "
            "harness's own designed refusal behavior (D-02, this document's own governing "
            "prohibition against emitting a pass/fail verdict on a failed precondition), not a "
            "code defect. Rebuild steps and the exact re-run commands are listed in "
            "03-09-SUMMARY.md's \"Next Phase Readiness\" section.\n"
        )

    lines = [
        "## What was compared\n",
        (
            "- **Corpus**: `databasise/tests/fixtures/corpus/` — 20 documents, 2 queries "
            "(HotpotQA distractor setting, D-06). Corpus hash and per-arm query set are recorded "
            "per-arm below from each committed comparison result's own `corpus_hash` field.\n"
        ),
        (
            "- **One index**: built exactly once by a real v1 OpenRouter ingest run over the "
            "pinned corpus (plan 03-02, `v1/scripts/run_parity_ingest.py`), imported into the v2 "
            "namespace layout by a verified read-and-reinsert import "
            "(`databasise/parity/import_index.py`), " + one_index_trailing
        ),
        (
            f"- **Determinism / concurrency**: `{_DETERMINISM_SETTING}` / "
            f"`{_CONCURRENCY_SETTING}` (`databasise.parity.run_arm`'s own pinned settings).\n"
        ),
        (
            "- **Rerank**: disabled (`RERANK_BINDING=null`, D-09's unchanged half; "
            "`v1/README-PARITY.md`). A number recorded with rerank off does not transfer to a "
            "run with it on — this evidence never claims otherwise.\n"
        ),
        (
            "- **Pinned model identities**: `qwen/qwen3.7-flash` (generator + keyword "
            "extraction, provider-pinned to Alibaba, D-07/D-08) and `qwen/qwen3-embedding-8b` "
            "(embedder, amended D-09) — see `v1/README-PARITY.md`. " + pinned_models_clause
        ),
        run_state_bullet,
    ]
    return "\n".join(lines)


def _render_trace_asymmetry() -> str:
    return (
        "## The trace asymmetry\n\n"
        "Stated before the numbers, not after them. The decomposed arm's run comes back as a "
        "full RIG §TR.1 run record (`databasise.runner.trace.RunRecord`) — one entry per node, "
        "its own token accounting, its own effects. The original (pre-decomposition) arm comes "
        "back as `databasise.parity.v1_arm.V1ArmResult`, instrumented from the outside only "
        "(wall clock, exit status, captured stderr) — its `instrumentation` field is always "
        "`\"harness-external\"`. This is not a defect to fix; v1 was never built to emit a RIG "
        "§TR.1 record and never will be. Wherever a number below appears next to the original "
        "arm, it is read against this asymmetry, not against a claim of matching instrumentation "
        f"(D-05, `{_GATE_AMENDMENT_REF}`).\n"
    )


def _render_per_arm_comparison() -> str:
    sections = ["## Per-arm retrieval-level comparison\n"]
    for arm in ARMS:
        records = load_comparison(arm)
        sections.append(f"### `{arm}`\n")
        header = (
            "| query_id | status | chunk sym_diff | ranking agreement | first disagreement | "
            "entity sym_diff | relation sym_diff | reason |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
        rows = []
        for record in records:
            chunk_diff = record.get("chunk_diff")
            entity_diff = record.get("entity_diff")
            relation_diff = record.get("relation_diff")
            retrieval_note = record.get("retrieval_note")
            if chunk_diff is not None:
                chunk_cell = str(len(chunk_diff["symmetric_difference"]))
                agreement_cell = f"{chunk_diff['ranking_agreement']:.3f}"
                first_dis_cell = str(chunk_diff["first_disagreement_position"])
            elif retrieval_note is not None:
                chunk_cell = agreement_cell = first_dis_cell = "no retrieval to compare"
            else:
                chunk_cell = agreement_cell = first_dis_cell = "—"
            entity_cell = (
                str(len(entity_diff["symmetric_difference"])) if entity_diff is not None else "—"
            )
            relation_cell = (
                str(len(relation_diff["symmetric_difference"]))
                if relation_diff is not None
                else "—"
            )
            reason_cell = _escape_cell(record.get("inconclusive_reason") or "")
            rows.append(
                f"| {record['query_id']} | {record['status']} | {chunk_cell} | "
                f"{agreement_cell} | {first_dis_cell} | {entity_cell} | {relation_cell} | "
                f"{reason_cell} |"
            )
        sections.append(header + "\n".join(rows) + "\n")
        if arm == "bypass":
            sections.append(
                "`bypass` resolves to a single `generate` node with no retrieval at all "
                "(`databasise.wirings.resolve.resolve_arm(\"bypass\")` has no chunk-source "
                "node). Its chunk/entity/relation columns above read `\"no retrieval to "
                "compare\"` once a run completes, distinct from a computed zero symmetric "
                "difference — see `databasise/parity/run_comparison.py`'s own "
                "`_no_retrieval_to_compare_note`.\n"
            )
        elif arm == "naive":
            sections.append(
                "`naive` resolves to `embedder-index`/`embedder-query`/`chunk-vector`/"
                "`heading-backfill`/`rerank`/`assemble`/`generate` — no entity or relation "
                "lookup node at all. Its entity/relation columns above read `\"—\"` because "
                "the arm's wiring has no entity/relation lookup to measure, not because a "
                "measurement was skipped.\n"
            )
        degraded_records = [
            record
            for record in records
            if record.get("status") == "completed"
            and record.get("decomposed_run_record", {}).get("degraded")
        ]
        if degraded_records:
            reasons = sorted(
                {
                    record["decomposed_run_record"].get("degradation_reason") or ""
                    for record in degraded_records
                }
            )
            queries = ", ".join(record["query_id"] for record in degraded_records)
            sections.append(
                f"**Degraded run — read the zero diffs above with this in mind.** "
                f"`{arm}`'s decomposed run halted before completing retrieval on {queries} "
                f"(MACH-09's `degraded`/`degradation_reason` labelling, RIG §TR): "
                f"{'; '.join(reasons)}. The original arm's own answer for the same query/arm "
                "pairs also carries zero chunk/entity/relation ids (`original_arm_result` — see "
                "the raw `parity_results/` record). The `0` symmetric_difference reported above "
                "is therefore both sides retrieving nothing, not a validated matched retrieval — "
                "a live defect this comparison surfaced, out of this plan's scope to repair. See "
                "the Verdict section for how this bounds what the comparison actually shows.\n"
            )
    return "\n".join(sections)


def _render_keyword_variance_band() -> str:
    sections = [
        "## The `keywords` variance band\n",
        (
            f"**N = {KEYWORD_VARIANCE_N} runs** (`databasise.parity.run_comparison."
            "_DEFAULT_KEYWORD_VARIANCE_RUNS`). Chosen (reasoning recorded in full in "
            "03-09-SUMMARY.md's Decisions Made section): large enough to show repeats in the "
            "per-keyword frequency table for a typical HotpotQA question (2-4 keywords per "
            "level), small enough that 5 extra live `keywords` calls per query stays well "
            "within a rung-2 comparison's affordability, and `compute_keyword_variance_band` "
            "itself accepts any N ≥ 2 — raising N on a future real run needs no code change, "
            "only a different `keyword_variance_runs=` argument.\n"
        ),
    ]
    header = (
        "| arm | query_id | run count (N) | hl size mean | hl size stdev | ll size mean | "
        "ll size stdev | any cache served |\n|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for arm in ARMS:
        for record in load_comparison(arm):
            band = record.get("keyword_variance_band")
            if band is None:
                if record.get("status") == "completed":
                    cell = f"not applicable — {arm}'s wiring has no `keywords` node"
                else:
                    cell = (
                        f"not run — "
                        f"{_escape_cell(record.get('inconclusive_reason') or record['status'])}"
                    )
                rows.append(f"| {arm} | {record['query_id']} | {cell} | — | — | — | — | — |")
                continue
            rows.append(
                f"| {arm} | {record['query_id']} | {band['run_count']} | "
                f"{band['high_level_size_mean']:.2f} | {band['high_level_size_stdev']:.2f} | "
                f"{band['low_level_size_mean']:.2f} | {band['low_level_size_stdev']:.2f} | "
                f"{band['any_cache_served']} |"
            )
    sections.append(header + "\n".join(rows) + "\n")
    return "\n".join(sections)


def _render_storage_audit() -> str:
    sections = [
        "## The per-node storage-ownership audit\n",
        (
            "Criterion 3 requires this to ship as part of the parity evidence, which is why it "
            "is a section here and not a separate file. `matched`/`no-touch`/`over-declared` "
            "are `databasise.parity.storage_audit`'s own three legitimate per-node states — "
            "never a pass/fail bit — counted separately below, per arm.\n"
        ),
    ]
    header = "| arm | matched | no-touch | over-declared | outcome |\n|---|---|---|---|---|\n"
    rows = []
    for arm in ARMS:
        audit = load_storage_audit(arm)
        matched = audit.get("matched_count", 0)
        no_touch = audit.get("no_touch_count", 0)
        over_declared = audit.get("over_declared_count", 0)
        outcome = audit.get("status", "unknown")
        rows.append(f"| {arm} | {matched} | {no_touch} | {over_declared} | {outcome} |")
    sections.append(header + "\n".join(rows) + "\n")
    if _run_state() == "completed":
        counts = {arm: load_storage_audit(arm) for arm in ARMS}
        arm_degraded = {arm: _arm_degraded(arm) for arm in ARMS}
        clean_arms = [arm for arm in ARMS if not arm_degraded[arm][0]]
        degraded_arms = [arm for arm in ARMS if arm_degraded[arm][0]]

        if clean_arms:
            clean_detail = "; ".join(
                f"`{arm}`: matched={counts[arm].get('matched_count', 0)} "
                f"no-touch={counts[arm].get('no_touch_count', 0)} "
                f"over-declared={counts[arm].get('over_declared_count', 0)}"
                for arm in clean_arms
            )
            sections.append(
                f"`{'`, `'.join(clean_arms)}` ran to completion clean — the comparison run "
                "reports no `decomposed_run_record.degraded=true` for these arms, so every "
                f"dispatched node had the chance to touch what it declared: {clean_detail}. "
                "`matched`/`no-touch`/`over-declared` remain three distinct states throughout, "
                "and an `over-declared` count of `0` on these arms is a real measured zero, not "
                "an assumed one (D-15).\n"
            )

        for arm in degraded_arms:
            _, reason = arm_degraded[arm]
            never_executed = _never_executed_nodes(arm)
            never_executed_cell = (
                ", ".join(f"`{n}`" for n in never_executed) if never_executed else "none"
            )
            sections.append(
                f"**`{arm}`'s audit is crash-truncated, not clean.** The comparison run's own "
                f"`decomposed_run_record` reports `degraded=true` ({reason}), and "
                "`databasise/runner/scheduler.py` halts the whole scheduling loop on that "
                "`NodeExecutionError` without dispatching any node downstream of it — a node "
                "that never executed is a fundamentally different state from a node that ran "
                "and legitimately touched nothing. Cross-referencing this audit's own rows "
                "against the node ids the comparison run's `decomposed_run_record` actually "
                f"dispatched: {never_executed_cell} never executed in the run this audit "
                "reflects. Some report `no-touch` above (a node that never touched its own "
                "declared handle); some report `matched` vacuously (a node with no declared "
                "effect at all — a join or budget node — counted `matched` regardless of "
                "whether it was ever dispatched, per `storage_audit.py`'s own "
                "no-declared-effects rule). A node that never ran cannot be shown not to have "
                f"over-declared — `{arm}`'s audit counts (matched="
                f"{counts[arm].get('matched_count', 0)} no-touch="
                f"{counts[arm].get('no_touch_count', 0)} over-declared="
                f"{counts[arm].get('over_declared_count', 0)}) are coverage of a halted run, "
                "not proof every node touches only what it declares.\n"
            )
    else:
        sections.append(
            "Every arm above reports `matched=0 no-touch=0 over-declared=0` in this render — "
            "none of the five audits reached the scheduler: "
            "`databasise.parity.storage_audit.run_audit` builds clients from `v1/.env.parity` "
            "before dispatching a single node, and that file is absent on this machine (see "
            "\"What was compared\"). This is the audit's own `MissingParityEnvError` refusal, "
            "captured verbatim in each arm's committed `{arm}-storage-audit.json` under "
            "`parity_results/` — not a claim that every node correctly touched nothing.\n"
        )
    return "\n".join(sections)


def _render_not_measured() -> str:
    first_paragraph = (
        "## What is not measured\n\n"
        "The A/A floor (MACH-02's eval bundle, MACH-03's bootstrap-resampled p95 calibration) is "
        f"deferred to Phase 6's side-by-side run, per `{_GATE_AMENDMENT_REF}` — this is the "
        "**second** deferral of the same pair of requirements (first Phase 2 to Phase 3, "
        f"recorded in `{_GATE_WAIVER_REF}`; now Phase 3 to Phase 6). Residual risk, in D-11's own "
        "words, not softened: **answer-level drift originating in `keywords` and `generate` "
        "stays unmeasured until a floor exists.** GATE-01's standing condition continues to "
        "hold regardless of this document's own findings: no promotion decision and no parity "
        "claim rides on an unmeasured comparison.\n\n"
    )
    if _run_state() == "completed":
        graph_arms = ("hybrid", "local", "global")
        degraded_arms = [arm for arm in graph_arms if _arm_degraded(arm)[0]]
        if degraded_arms:
            degradation_clause = (
                f"and `{'`/`'.join(degraded_arms)}`'s decomposed run degraded before completing "
                "a real retrieval (see the per-arm degradation notes above), so its measured "
                "zero diff is not a validated agreement over non-trivial content"
                if len(degraded_arms) == 1
                else (
                    f"and `{'`/`'.join(degraded_arms)}`'s decomposed runs degraded before "
                    "completing a real retrieval (see the per-arm degradation notes above), so "
                    "their measured zero diffs are not a validated agreement over non-trivial "
                    "content"
                )
            )
        else:
            degradation_clause = (
                f"and `{'`/`'.join(graph_arms)}` completed without a decomposed-run "
                "degradation, so their measured retrieval-level agreement is not an artifact of "
                "a halted run"
            )
        second_paragraph = (
            "Separately, and specific to this render: the retrieval-level comparison **has** "
            "run — all five arms are `completed` (see \"What was compared\" and \"Per-arm "
            "retrieval-level comparison\") — but the human answer-substance spot-check for q1/q2 "
            "has not yet been recorded (see \"Human spot-check of answer substance\" above), "
            f"{degradation_clause}. Neither gap is measured by this document; both are named "
            "here rather than left implicit.\n"
        )
    else:
        second_paragraph = (
            "Separately, and specific to this render: **no comparison in this document has "
            "actually run.** Every arm's retrieval-level diff, `keywords` variance band, and "
            "storage-ownership audit are all `inconclusive` on this machine (see \"What was "
            "compared\"). This document is correct and complete for that inconclusive outcome, "
            "and is re-runnable to produce the real verdict once the owner rebuilds the v1 "
            "environment — see 03-09-SUMMARY.md's \"Next Phase Readiness\" for the exact rebuild "
            "and re-run commands.\n"
        )
    return first_paragraph + second_paragraph


def _render_verdict() -> str:
    if _run_state() != "completed":
        return (
            "## Verdict\n\n"
            "**No parity verdict is recorded by this document.** Every one of the five arms' "
            "comparison runs and storage-ownership audits reports an environment-precondition "
            "refusal — never a pass, never a fail, exactly as this document's own stated prohibition "
            "requires (\"the parity harness must not emit a pass or fail verdict when the "
            "index-identity preconditions failed; it must emit `inconclusive`\"). The harness code "
            "itself, its provenance-checking (`--check-results`), and this rendering are proven "
            "correct against the real refusal path in this session; the clean-pass path — an actual "
            "retrieval-level comparison against the real imported index and live model endpoints — "
            "awaits the owner rebuilding the v1 environment (`v1/README-PARITY.md`) and re-running "
            "the exact commands 03-09-SUMMARY.md names.\n"
        )

    graph_arms = ("hybrid", "local", "global")
    arm_status = {arm: _arm_degraded(arm) for arm in graph_arms}
    degraded_arms = [arm for arm in graph_arms if arm_status[arm][0]]

    lines = [
        "## Verdict\n",
        (
            "**All five arms completed.** `naive` and `bypass` ran their full pipelines end to "
            "end and their retrieval-level comparisons are informative: `bypass` has no "
            "retrieval to compare; `naive` measured exact chunk-set agreement past "
            "`ranking_agreement=1.000` with two named tail-length excursions per query, both "
            "carried as declared deviations in `DECLARED-DEVIATIONS.md` with a grounded cause "
            "(top_k cutoff vs v1's token-budget truncation) rather than folded into a silent "
            "pass.\n"
        ),
    ]
    for arm in graph_arms:
        degraded, reason = arm_status[arm]
        if degraded:
            lines.append(
                f"`{arm}` also completed and measured `chunk_diff`/`entity_diff`/"
                "`relation_diff` `symmetric_difference=[]` on both corpus queries — but **this "
                f"is not read as exact retrieval-level agreement.** `{arm}`'s decomposed run "
                f"degraded before completing a real retrieval ({reason} — see the per-arm "
                "degradation note in \"Per-arm retrieval-level comparison\"), and the original "
                "(v1) arm's own answer for the same query/arm pairs also carries zero "
                "chunk/entity/relation ids. The measured zero is both sides retrieving nothing, "
                "not a validated match over non-trivial content — a live defect this comparison "
                "surfaced, not evidence of parity. Fixing that defect is out of this plan's "
                "scope; recorded here so the verdict does not overstate what this arm actually "
                "showed.\n"
            )
        else:
            lines.append(
                f"`{arm}` also completed and measured `chunk_diff`/`entity_diff`/"
                "`relation_diff` `symmetric_difference=[]` on both corpus queries, with no "
                "decomposed-run degradation — a validated exact retrieval-level agreement.\n"
            )

    coverage_gap = (
        f", and the {'/'.join(degraded_arms)} degradation above means the retrieval-level "
        "comparison itself is not yet clean for "
        + ("that arm" if len(degraded_arms) == 1 else "those arms")
        + " either"
        if degraded_arms
        else ""
    )
    lines.append(
        "**What this verdict does not cover.** D-10's gate is the deterministic retrieval "
        "level only — this document makes no answer-level parity claim. The human "
        "answer-substance spot-check for q1/q2 is not yet recorded (see \"Human spot-check of "
        "answer substance\" above). GATE-01's standing condition continues to hold: no "
        f"promotion decision and no parity claim rides on an unmeasured comparison{coverage_gap}.\n"
    )
    return "\n".join(lines)


def render_markdown() -> str:
    """Render ``PARITY-EVIDENCE.md``. A pure function of the committed files under
    ``parity_results/`` — see module docstring.
    """
    sections = [
        "# Parity Evidence\n",
        (
            "Rendered from the committed result files under `databasise/evidence/"
            "parity_results/` by `databasise/evidence/parity_report.py`, following "
            "`FALSIFIER-2-EVIDENCE.md`'s committed, re-runnable, human-readable precedent.\n"
        ),
        _render_what_was_compared(),
        _render_trace_asymmetry(),
        _render_per_arm_comparison(),
        _render_answer_spotcheck(),
        _render_keyword_variance_band(),
        _render_storage_audit(),
        _render_not_measured(),
        _render_verdict(),
    ]
    return "\n".join(sections)


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.evidence.parity_report`` renders and writes both documents.
    ``--check-results`` instead runs :func:`check_results` and prints/returns without writing.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-results", action="store_true")
    args = parser.parse_args(argv)

    if args.check_results:
        violations = check_results()
        if violations:
            for v in violations:
                print(f"VIOLATION: {v}", file=sys.stderr)
            return 1
        degraded_arms = _degraded_but_vacuous_arms()
        if degraded_arms:
            degraded_list = ", ".join(f"`{arm}`" for arm in degraded_arms)
            print(
                f"parity_results/ provenance check: clean ({len(ARMS)} arms, "
                f"{len(degraded_arms)} degraded — {degraded_list} measured a zero diff only "
                "because the decomposed run crashed before completing a real retrieval; see "
                "PARITY-EVIDENCE.md for disclosure)"
            )
        else:
            print(f"parity_results/ provenance check: clean ({len(ARMS)} arms)")
        return 0

    deviations = _collect_deviations()
    deviations_text = render_deviations_markdown(deviations)
    DEVIATIONS_PATH.write_text(deviations_text, encoding="utf-8")

    evidence_text = render_markdown()
    EVIDENCE_PATH.write_text(evidence_text, encoding="utf-8")

    print(evidence_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
