"""06-04-PLAN.md Task 2's <behavior> block: EvalBundle mints both §EV.2 target families over three
disjoint splits, and every one of §EV.1's five invalidating changes mints a new version while
leaving the prior version's bytes byte-identical on disk (never edited in place).
"""

from __future__ import annotations

import dataclasses
import json
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
