"""06-04-PLAN.md Task 2's <behavior> block: EvalBundle mints both §EV.2 target families over three
disjoint splits, and every one of §EV.1's five invalidating changes mints a new version while
leaving the prior version's bytes byte-identical on disk (never edited in place).

Also covers 06-04-PLAN.md Task 3: the committed `bundle@v1` at
`databasise/evidence/eval-bundles/` loads and hash-verifies, its recorded determinism/concurrency
settings equal the engine's own live constants, and `EVAL-BUNDLE-V1.md`'s findings table carries
one row per §EV.1 required member — parsed structurally, never by whole-file grep (mirrors
`tests/evidence/test_f14_record.py`'s own discipline).
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import pytest

from databasise.eval.bundle import (
    ANSWER_LEVEL_FAMILY,
    ANSWER_LEVEL_TIER,
    GOLD_PASSAGE_FAMILY,
    GOLD_PASSAGE_TIER,
    BundleDriftError,
    HoldoutUsageRequiredError,
    MissingSealedEventError,
    MissingTargetFamilyError,
    load_bundle,
    mint_bundle,
    open_sealed,
    read_holdout,
    record_holdout_use,
)

_JUDGE_INSTANCE = "stub-judge@v1"
_JUDGE_PROMPT_HASH = "a" * 64
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"


def _mint(bundle_root: Path, snapshot, **overrides):
    kwargs = {
        "judge_instance": _JUDGE_INSTANCE,
        "judge_prompt_hash": _JUDGE_PROMPT_HASH,
        "determinism_setting": _DETERMINISM_SETTING,
        "concurrency_setting": _CONCURRENCY_SETTING,
    }
    kwargs.update(overrides)
    return mint_bundle(snapshot, bundle_root, **kwargs)


# --------------------------------------------------------------------------------------------- #
# Test 1
# --------------------------------------------------------------------------------------------- #


def test_mint_bundle_produces_bundle_v1_with_six_content_members_and_disjoint_splits(
    bundle_root, eval_snapshot
):
    bundle = _mint(bundle_root, eval_snapshot)

    assert bundle.version == "bundle@v1"
    # §EV.1's six content members, by their own names.
    assert {q.id for q in bundle.questions} == {q.id for q in eval_snapshot.queries}
    assert set(bundle.gold_answers) == {q.id for q in eval_snapshot.queries}
    assert bundle.judge_instance == _JUDGE_INSTANCE
    assert bundle.judge_prompt_hash == _JUDGE_PROMPT_HASH
    assert bundle.corpus_snapshot_hash == eval_snapshot.corpus_hash
    assert bundle.determinism_setting == _DETERMINISM_SETTING
    assert bundle.concurrency_setting == _CONCURRENCY_SETTING

    dev = set(bundle.splits["dev"].question_ids)
    holdout = set(bundle.splits["holdout"].question_ids)
    sealed = set(bundle.splits["sealed"].question_ids)
    full = {q.id for q in eval_snapshot.queries}

    assert dev & holdout == set()
    assert dev & sealed == set()
    assert holdout & sealed == set()
    assert dev | holdout | sealed == full


# --------------------------------------------------------------------------------------------- #
# Test 2
# --------------------------------------------------------------------------------------------- #


def test_both_target_families_present_for_every_question(bundle_root, eval_snapshot):
    bundle = _mint(bundle_root, eval_snapshot)

    names = {tf.name for tf in bundle.target_families}
    assert names == {GOLD_PASSAGE_FAMILY, ANSWER_LEVEL_FAMILY}

    by_name = {tf.name: tf for tf in bundle.target_families}
    assert by_name[GOLD_PASSAGE_FAMILY].tier == GOLD_PASSAGE_TIER
    assert by_name[ANSWER_LEVEL_FAMILY].tier == ANSWER_LEVEL_TIER

    full_ids = {q.id for q in eval_snapshot.queries}
    assert set(by_name[GOLD_PASSAGE_FAMILY].targets) == full_ids
    assert set(by_name[ANSWER_LEVEL_FAMILY].targets) == full_ids
    assert all(by_name[GOLD_PASSAGE_FAMILY].targets[qid] for qid in full_ids)


def test_missing_gold_document_ids_raises_missing_target_family_error(bundle_root, eval_snapshot):
    stripped_queries = tuple(
        dataclasses.replace(q, gold_document_ids=()) if i == 0 else q
        for i, q in enumerate(eval_snapshot.queries)
    )
    stripped_snapshot = dataclasses.replace(eval_snapshot, queries=stripped_queries)

    with pytest.raises(MissingTargetFamilyError):
        _mint(bundle_root, stripped_snapshot)


# --------------------------------------------------------------------------------------------- #
# Test 3
# --------------------------------------------------------------------------------------------- #

_INVALIDATING_CHANGES = ("question_removed", "gold_answer_corrected", "judge_instance",
                         "corpus_snapshot_hash", "determinism_setting")


@pytest.mark.parametrize("change", _INVALIDATING_CHANGES)
def test_each_invalidating_change_mints_v2_and_leaves_v1_bytes_unchanged(
    bundle_root, eval_snapshot, change
):
    v1 = _mint(bundle_root, eval_snapshot)
    assert v1.version == "bundle@v1"
    v1_bundle_path = bundle_root / "bundle@v1" / "bundle.json"
    v1_bytes_before = v1_bundle_path.read_bytes()

    if change == "question_removed":
        v2 = _mint(bundle_root, dataclasses.replace(eval_snapshot, queries=eval_snapshot.queries[:-1]))
    elif change == "gold_answer_corrected":
        corrected = tuple(
            dataclasses.replace(q, answer=q.answer + " (corrected)") if i == 0 else q
            for i, q in enumerate(eval_snapshot.queries)
        )
        v2 = _mint(bundle_root, dataclasses.replace(eval_snapshot, queries=corrected))
    elif change == "judge_instance":
        v2 = _mint(bundle_root, eval_snapshot, judge_instance="a-different-judge@v1")
    elif change == "corpus_snapshot_hash":
        v2 = _mint(bundle_root, dataclasses.replace(eval_snapshot, corpus_hash="f" * 64))
    elif change == "determinism_setting":
        v2 = _mint(bundle_root, eval_snapshot, determinism_setting="cache-permitted")
    else:  # pragma: no cover - exhaustive over _INVALIDATING_CHANGES
        raise AssertionError(change)

    assert v2.version == "bundle@v2"
    assert v2.content_hash != v1.content_hash
    assert v1_bundle_path.read_bytes() == v1_bytes_before


# --------------------------------------------------------------------------------------------- #
# Test 4
# --------------------------------------------------------------------------------------------- #


def test_mutating_a_minted_bundle_on_disk_is_detected_and_refused_on_next_load(
    bundle_root, eval_snapshot
):
    v1 = _mint(bundle_root, eval_snapshot)
    bundle_path = bundle_root / v1.version / "bundle.json"
    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    data["judge_instance"] = "tampered-judge"
    bundle_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(BundleDriftError) as excinfo:
        load_bundle(bundle_root, v1.version)
    assert v1.version in str(excinfo.value)


# --------------------------------------------------------------------------------------------- #
# Test 5
# --------------------------------------------------------------------------------------------- #


def test_open_sealed_mints_new_version_logs_event_and_requires_one(bundle_root, eval_snapshot):
    v1 = _mint(bundle_root, eval_snapshot)
    sealed_ids_before = v1.splits["sealed"].question_ids

    with pytest.raises(MissingSealedEventError):
        open_sealed(bundle_root, v1.version, event="")

    opening = open_sealed(bundle_root, v1.version, event="promotion-decision-2026-09-09")

    assert opening.bundle.version == "bundle@v2"
    assert opening.sealed_question_ids == sealed_ids_before

    usage_path = bundle_root / "bundle@v2" / "usage.jsonl"
    entries = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines()]
    assert any(
        e["kind"] == "sealed_open" and e["event"] == "promotion-decision-2026-09-09"
        for e in entries
    )


# --------------------------------------------------------------------------------------------- #
# Test 6
# --------------------------------------------------------------------------------------------- #


def test_record_holdout_use_appends_entry_and_gates_holdout_reads(bundle_root, eval_snapshot):
    v1 = _mint(bundle_root, eval_snapshot)

    with pytest.raises(HoldoutUsageRequiredError):
        read_holdout(bundle_root, v1.version)

    record_holdout_use(bundle_root, v1.version, reader="06-06-calibration", reason="A/A dev-set check")

    holdout_ids = read_holdout(bundle_root, v1.version)
    assert holdout_ids == v1.splits["holdout"].question_ids

    usage_path = bundle_root / v1.version / "usage.jsonl"
    entries = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines()]
    assert any(
        e["kind"] == "holdout_read" and e["reader"] == "06-06-calibration"
        for e in entries
    )


# --------------------------------------------------------------------------------------------- #
# Test 7 — negative control
# --------------------------------------------------------------------------------------------- #


def test_negative_control_identical_content_hashes_equal_differing_content_hashes_differ(
    bundle_root, eval_snapshot
):
    first = _mint(bundle_root, eval_snapshot)
    second = _mint(bundle_root, eval_snapshot)  # identical inputs — no new version minted

    assert second.version == first.version == "bundle@v1"
    assert second.content_hash == first.content_hash

    third = _mint(bundle_root, eval_snapshot, judge_instance="a-different-judge@v1")
    assert third.version == "bundle@v2"
    assert third.content_hash != first.content_hash


# --------------------------------------------------------------------------------------------- #
# 06-04-PLAN.md Task 3: the committed bundle@v1 and its evidence document
# --------------------------------------------------------------------------------------------- #

_REPO_EVAL_DIR = Path(__file__).resolve().parent.parent.parent
_COMMITTED_BUNDLE_ROOT = _REPO_EVAL_DIR / "evidence" / "eval-bundles"

# §EV.1's six required content members, by the evidence document's own findings-table naming —
# not derivable from a single Python collection, since EvalBundle splits the sixth ("the
# determinism/concurrency setting") into two dataclass fields (RIG.md ## §EV.1's own prose names
# it as one combined member: "the determinism/concurrency setting it was calibrated under").
_EV1_REQUIRED_MEMBERS = (
    "questions",
    "gold_answers",
    "judge_instance",
    "judge_prompt_hash",
    "corpus_snapshot_hash",
    "determinism_concurrency_setting",
)


def _evidence_text(name: str) -> str:
    return (_REPO_EVAL_DIR / "evidence" / name).read_text(encoding="utf-8")


def _section(text: str, heading_pattern: str) -> str:
    """Return the body of the first ``##``-level section whose heading matches
    ``heading_pattern``, up to (not including) the next ``## `` heading or EOF. Mirrors
    ``tests/evidence/test_f14_record.py``'s own helper of the same name.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and re.search(heading_pattern, line, re.IGNORECASE):
            start = i
            break
    assert start is not None, f"no section heading matching {heading_pattern!r} found"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _parse_markdown_table(section_text: str) -> list[list[str]]:
    table_lines = [line for line in section_text.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3, f"expected a header + separator + rows, found {table_lines!r}"

    def _is_separator(line: str) -> bool:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return all(re.fullmatch(r"-+", c) for c in cells)

    header, *rest = table_lines
    assert _is_separator(rest[0]), f"second table line is not a separator row: {rest[0]!r}"
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in rest[1:]]


def test_bundle_v1_loads_and_matches_the_engines_own_settings():
    from databasise.parity.corpus import load_snapshot
    from databasise.seam.engine import _CONCURRENCY_SETTING, _DETERMINISM_SETTING

    bundle = load_bundle(_COMMITTED_BUNDLE_ROOT, "bundle@v1")  # raises BundleDriftError if drifted

    assert bundle.determinism_setting == _DETERMINISM_SETTING
    assert bundle.concurrency_setting == _CONCURRENCY_SETTING

    snapshot = load_snapshot(_REPO_EVAL_DIR / "tests" / "fixtures" / "eval-corpus")
    assert bundle.corpus_snapshot_hash == snapshot.corpus_hash


def test_eval_bundle_v1_evidence_doc_findings_table_has_one_row_per_ev1_member():
    text = _evidence_text("EVAL-BUNDLE-V1.md")
    findings = _section(text, r"^## Findings")  # the §EV.1-members table is the first "## Findings"
    rows = _parse_markdown_table(findings)

    member_cells = [row[0].strip("`") for row in rows]
    assert set(member_cells) == set(_EV1_REQUIRED_MEMBERS), (
        f"findings table member set {set(member_cells)} does not match "
        f"the §EV.1 required members {set(_EV1_REQUIRED_MEMBERS)}"
    )
    assert len(member_cells) == len(_EV1_REQUIRED_MEMBERS), "a member appears more than once"

    for row in rows:
        assert any("[code-verified]" in cell for cell in row), (
            f"row for {row[0]!r} carries no [code-verified] tag: {row}"
        )


def test_eval_bundle_v1_evidence_doc_carries_a_dated_header_and_verdict():
    text = _evidence_text("EVAL-BUNDLE-V1.md")
    header = "\n".join(text.splitlines()[:6])
    assert re.search(r"\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}", header)

    verdict = _section(text, r"^## Verdict")
    assert "MACH-02" in verdict
    assert "met in full" in verdict.lower() or "not met" in verdict.lower()


def test_eval_bundle_v1_evidence_doc_limits_name_the_absent_corpus_and_absent_aa_null():
    text = _evidence_text("EVAL-BUNDLE-V1.md")
    limits = _section(text, r"^## Method and limits")
    assert "owner" in limits.lower() and "corpus" in limits.lower()
    assert "A/A" in limits
