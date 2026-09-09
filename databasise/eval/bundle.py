"""The eval bundle (MACH-02): a versioned, content-addressed artifact carrying §EV.1's six content
members — questions, gold answers, a judge instance, a judge prompt hash, a corpus snapshot hash,
and the determinism/concurrency setting it was calibrated under — split into `dev`/`holdout`/
`sealed` partitions, and both §EV.2 target families (gold-passage, answer-level).

Follows ``databasise/evidence/parity_report.py``'s own shape: pure functions over on-disk state,
explicit empty-state handling, no hidden mutation. Follows ``databasise/parity/corpus.py``'s and
``databasise/stores/vector.py``'s shared refuse-rather-than-trust convention: a version whose
on-disk bytes no longer match its own recorded checksum is refused (:class:`BundleDriftError`),
never silently loaded.

**Minted, never edited in place (RIG.md §EV.1).** ``mint_bundle`` writes a new numbered directory
under the bundle root and never touches an existing one — re-minting from unchanged input (the
same five invalidating inputs §EV.1 names) is idempotent and returns the already-minted version
rather than writing a duplicate; re-minting after any one of the five inputs changed always writes
a new, sequentially-numbered version, leaving every prior version's bytes untouched.
``BundleEditInPlaceError`` is the defensive backstop should a version directory the mint logic
computed as "next" ever already exist on disk — it should never fire in ordinary use, since minting
always computes the next number fresh.

**Version identity vs. file integrity — two different hashes, both ``hashlib.sha256`` (no second
hashing library is imported here).** ``content_hash`` is a SHA-256 over the RFC 8785 (JCS)
canonicalisation (``databasise.identity.canon.canonicalise``) of exactly the five invalidating
inputs §EV.1 names — it is what a version *means*, and is what a remint compares against to decide
whether a new version is needed at all. The on-disk ``bundle.sha256`` sidecar is a plain SHA-256 of
``bundle.json``'s own raw bytes — it is what proves the file was not modified after minting,
independent of what the file's content means.

**Partition discipline (§EV.1).** ``dev`` is freely readable directly off the returned
:class:`EvalBundle`'s own ``splits["dev"]``. ``holdout`` is readable only via :func:`read_holdout`,
which refuses (``HoldoutUsageRequiredError``) until :func:`record_holdout_use` has appended a usage
entry naming the reader and the reason. ``sealed`` is not readable at all except through
:func:`open_sealed`, which requires a stated opening event, unconditionally mints a new bundle
version (bypassing :func:`mint_bundle`'s own content-hash dedup — the partition it drew from is no
longer sealed once touched, regardless of whether the six content members themselves changed), and
appends its own usage entry to that new version before returning the sealed content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from databasise.identity.canon import canonicalise
from databasise.parity.corpus import CorpusSnapshot

GOLD_PASSAGE_FAMILY = "gold_passage"
ANSWER_LEVEL_FAMILY = "answer_level"
GOLD_PASSAGE_TIER = "T1"  # "T1 and above" per §EV.2's table
ANSWER_LEVEL_TIER = "T0"

_SPLIT_NAMES: tuple[str, ...] = ("dev", "holdout", "sealed")
# [flagged assumption, this plan's own decision — 06-04-PLAN.md <flagged_assumptions>]: neither
# §EV.1 nor §10 states a minimum partition size or correct split proportions.
_SPLIT_PROPORTIONS: dict[str, float] = {"dev": 0.6, "holdout": 0.2, "sealed": 0.2}

_BUNDLE_FILE = "bundle.json"
_CHECKSUM_FILE = "bundle.sha256"
_USAGE_FILE = "usage.jsonl"


class BundleDriftError(RuntimeError):
    """A minted version's on-disk ``bundle.json`` no longer matches its own ``bundle.sha256``
    sidecar checksum — refused rather than silently loaded, naming the version.
    """

    def __init__(self, version: str, expected: str, actual: str) -> None:
        self.version = version
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"bundle {version!r} is corrupted: bundle.sha256 recorded {expected!r}, but the "
            f"on-disk bundle.json's actual checksum is {actual!r} — refusing to load a mutated "
            "minted version rather than silently trusting it"
        )


class MissingTargetFamilyError(ValueError):
    """Raised by :func:`mint_bundle` when one or more questions in the source snapshot carry no
    ``gold_document_ids`` — §EV.2's both-target-families rule enforced at mint time rather than
    discovered later by a measurement that quietly covered less than it claimed.
    """


class BundleEditInPlaceError(RuntimeError):
    """Raised if the version directory a mint computed as "next" already exists on disk — the
    defensive backstop for §EV.1's "minted, never edited in place" rule. Should never fire in
    ordinary use.
    """


class MissingSealedEventError(ValueError):
    """:func:`open_sealed` was called with no stated opening event — a sealed read that quietly
    succeeds is the one outcome that destroys the property sealing exists to buy.
    """


class HoldoutUsageRequiredError(RuntimeError):
    """:func:`read_holdout` was called before :func:`record_holdout_use` appended a usage entry
    for this bundle version.
    """


@dataclass(frozen=True)
class BundleQuestion:
    """One question's identity and text — the "questions" member of §EV.1's six."""

    id: str
    text: str


@dataclass(frozen=True)
class BundleSplit:
    """One of the three `dev`/`holdout`/`sealed` partitions: a name and its question id set."""

    name: str
    question_ids: tuple[str, ...]


@dataclass(frozen=True)
class TargetFamily:
    """One §EV.2 target family: its own name (`gold_passage` | `answer_level`), its `§4` evidence
    tier, and its per-question target payload — a list of gold document ids for `gold_passage`, the
    gold answer text for `answer_level`.
    """

    name: str
    tier: str
    targets: dict[str, Any]


@dataclass(frozen=True)
class EvalBundle:
    """A minted, content-addressed bundle version: §EV.1's six content members, three disjoint
    splits, and both §EV.2 target families.
    """

    version: str
    content_hash: str
    questions: tuple[BundleQuestion, ...]
    gold_answers: dict[str, str]
    judge_instance: str
    judge_prompt_hash: str
    corpus_snapshot_hash: str
    determinism_setting: str
    concurrency_setting: str
    splits: dict[str, BundleSplit]
    split_proportions: dict[str, float]
    target_families: tuple[TargetFamily, TargetFamily]


@dataclass(frozen=True)
class SealedOpening:
    """:func:`open_sealed`'s return value: the newly minted version and the sealed content it was
    minted to expose.
    """

    bundle: EvalBundle
    sealed_question_ids: tuple[str, ...]


# --------------------------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------------------------- #


def _version_dir(bundle_root: Path, version: str) -> Path:
    return bundle_root / version


def _list_version_numbers(bundle_root: Path) -> list[int]:
    if not bundle_root.exists():
        return []
    numbers: list[int] = []
    for path in bundle_root.iterdir():
        if path.is_dir() and path.name.startswith("bundle@v"):
            suffix = path.name[len("bundle@v") :]
            if suffix.isdigit():
                numbers.append(int(suffix))
    return sorted(numbers)


def _next_version_number(bundle_root: Path) -> int:
    existing = _list_version_numbers(bundle_root)
    return (max(existing) + 1) if existing else 1


# --------------------------------------------------------------------------------------------- #
# Content hash (version identity) — the version-hash comparator Test 7 checks
# --------------------------------------------------------------------------------------------- #


def _compute_content_hash(
    *,
    question_ids: list[str],
    gold_answers: dict[str, str],
    judge_instance: str,
    judge_prompt_hash: str,
    corpus_snapshot_hash: str,
    determinism_setting: str,
    concurrency_setting: str,
) -> str:
    """SHA-256 over the JCS canonicalisation of exactly §EV.1's five invalidating inputs: the
    question set, the gold answers, the judge instance/prompt hash, the corpus snapshot hash, and
    the determinism/concurrency setting pair. Two calls with identical inputs MUST return the
    identical hash; two calls differing in any one input MUST return different hashes (Test 7's
    negative control) — a comparator that ignores one of these inputs would pass the "differ"
    half of that control by accident but never the "identical" half consistently, so both
    directions are exercised.
    """
    payload = {
        "question_ids": sorted(question_ids),
        "gold_answers": dict(sorted(gold_answers.items())),
        "judge_instance": judge_instance,
        "judge_prompt_hash": judge_prompt_hash,
        "corpus_snapshot_hash": corpus_snapshot_hash,
        "determinism_setting": determinism_setting,
        "concurrency_setting": concurrency_setting,
    }
    return hashlib.sha256(canonicalise(payload)).hexdigest()


def _find_version_by_content_hash(bundle_root: Path, content_hash: str) -> str | None:
    for number in _list_version_numbers(bundle_root):
        version = f"bundle@v{number}"
        bundle = load_bundle(bundle_root, version)
        if bundle.content_hash == content_hash:
            return version
    return None


# --------------------------------------------------------------------------------------------- #
# Split assignment — deterministic from a hash of the question id (RIG §EV.1: "auditable rather
# than implicit")
# --------------------------------------------------------------------------------------------- #


def _assign_split(question_id: str) -> str:
    digest = hashlib.sha256(question_id.encode("utf-8")).hexdigest()
    fraction = (int(digest[:8], 16) % 10_000) / 10_000
    boundary_dev = _SPLIT_PROPORTIONS["dev"]
    boundary_holdout = boundary_dev + _SPLIT_PROPORTIONS["holdout"]
    if fraction < boundary_dev:
        return "dev"
    if fraction < boundary_holdout:
        return "holdout"
    return "sealed"


# --------------------------------------------------------------------------------------------- #
# JSON (de)serialisation
# --------------------------------------------------------------------------------------------- #


def _bundle_to_json_body(bundle_content: dict[str, Any]) -> bytes:
    return json.dumps(bundle_content, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _bundle_to_json_dict(bundle: EvalBundle) -> dict[str, Any]:
    return {
        "version": bundle.version,
        "content_hash": bundle.content_hash,
        "questions": [{"id": q.id, "text": q.text} for q in bundle.questions],
        "gold_answers": bundle.gold_answers,
        "judge_instance": bundle.judge_instance,
        "judge_prompt_hash": bundle.judge_prompt_hash,
        "corpus_snapshot_hash": bundle.corpus_snapshot_hash,
        "determinism_setting": bundle.determinism_setting,
        "concurrency_setting": bundle.concurrency_setting,
        "splits": {name: list(split.question_ids) for name, split in bundle.splits.items()},
        "split_proportions": dict(bundle.split_proportions),
        "target_families": [
            {"name": tf.name, "tier": tf.tier, "targets": tf.targets} for tf in bundle.target_families
        ],
    }


def _bundle_from_json_dict(data: dict[str, Any]) -> EvalBundle:
    families = tuple(
        TargetFamily(name=tf["name"], tier=tf["tier"], targets=dict(tf["targets"]))
        for tf in data["target_families"]
    )
    if len(families) != 2:  # pragma: no cover - defensive, cannot happen via mint_bundle
        raise ValueError(f"bundle {data.get('version')!r} carries {len(families)} target families, not 2")
    return EvalBundle(
        version=data["version"],
        content_hash=data["content_hash"],
        questions=tuple(BundleQuestion(id=q["id"], text=q["text"]) for q in data["questions"]),
        gold_answers=dict(data["gold_answers"]),
        judge_instance=data["judge_instance"],
        judge_prompt_hash=data["judge_prompt_hash"],
        corpus_snapshot_hash=data["corpus_snapshot_hash"],
        determinism_setting=data["determinism_setting"],
        concurrency_setting=data["concurrency_setting"],
        splits={
            name: BundleSplit(name=name, question_ids=tuple(ids))
            for name, ids in data["splits"].items()
        },
        split_proportions=dict(data["split_proportions"]),
        target_families=(families[0], families[1]),
    )


def _write_version(bundle_root: Path, version: str, bundle_content: dict[str, Any]) -> EvalBundle:
    """Write a brand-new version directory. Never overwrites — raises
    :class:`BundleEditInPlaceError` if ``version``'s directory already exists, since every caller
    of this function has already computed ``version`` as the next free number.
    """
    version_dir = _version_dir(bundle_root, version)
    if version_dir.exists():
        raise BundleEditInPlaceError(
            f"refusing to write {version!r}: its directory already exists at {version_dir} — "
            "a bundle version is minted once and never edited in place"
        )
    version_dir.mkdir(parents=True)

    payload = dict(bundle_content)
    payload["version"] = version
    body = _bundle_to_json_body(payload)
    (version_dir / _BUNDLE_FILE).write_bytes(body)
    checksum = hashlib.sha256(body).hexdigest()
    (version_dir / _CHECKSUM_FILE).write_text(checksum + "\n", encoding="utf-8")
    (version_dir / _USAGE_FILE).write_text("", encoding="utf-8")

    return _bundle_from_json_dict(payload)


# --------------------------------------------------------------------------------------------- #
# mint_bundle / load_bundle
# --------------------------------------------------------------------------------------------- #


def mint_bundle(
    snapshot: CorpusSnapshot,
    bundle_root: Path,
    *,
    judge_instance: str,
    judge_prompt_hash: str,
    determinism_setting: str,
    concurrency_setting: str,
) -> EvalBundle:
    """Mint (or, for unchanged input, return the already-minted) bundle version from ``snapshot``.

    Raises :class:`MissingTargetFamilyError` if any question in ``snapshot`` carries no
    ``gold_document_ids`` — §EV.2's both-target-families rule, enforced before anything is written.
    """
    # RED-DRAFT: validation intentionally omitted for the RED run (06-04-PLAN.md Task 2, TDD).
    questions = [BundleQuestion(id=q.id, text=q.question) for q in snapshot.queries]
    gold_answers = {q.id: q.answer for q in snapshot.queries}
    question_ids = [q.id for q in questions]

    content_hash = _compute_content_hash(
        question_ids=question_ids,
        gold_answers=gold_answers,
        judge_instance=judge_instance,
        judge_prompt_hash=judge_prompt_hash,
        corpus_snapshot_hash=snapshot.corpus_hash,
        determinism_setting=determinism_setting,
        concurrency_setting=concurrency_setting,
    )

    # RED-DRAFT: dedup lookup intentionally disabled for the RED run.
    existing_version = None
    if existing_version is not None:
        return load_bundle(bundle_root, existing_version)

    splits: dict[str, list[str]] = {name: [] for name in _SPLIT_NAMES}
    for question_id in question_ids[:-1]:  # RED-DRAFT: drops the last question id
        splits[_assign_split(question_id)].append(question_id)

    all_assigned = splits["dev"] + splits["holdout"] + splits["sealed"]
    assert sorted(all_assigned) == sorted(question_ids), (
        "split assignment must partition the full question set (RIG §EV.1)"
    )
    assert len(set(all_assigned)) == len(all_assigned), "splits must be pairwise disjoint"

    target_families = [
        {
            "name": GOLD_PASSAGE_FAMILY,
            "tier": GOLD_PASSAGE_TIER,
            "targets": {q.id: list(q.gold_document_ids) for q in snapshot.queries},
        },
        {
            "name": ANSWER_LEVEL_FAMILY,
            "tier": ANSWER_LEVEL_TIER,
            "targets": {q.id: q.answer for q in snapshot.queries},
        },
    ]

    bundle_content = {
        "content_hash": content_hash,
        "questions": [{"id": q.id, "text": q.text} for q in questions],
        "gold_answers": gold_answers,
        "judge_instance": judge_instance,
        "judge_prompt_hash": judge_prompt_hash,
        "corpus_snapshot_hash": snapshot.corpus_hash,
        "determinism_setting": determinism_setting,
        "concurrency_setting": concurrency_setting,
        "splits": splits,
        "split_proportions": dict(_SPLIT_PROPORTIONS),
        "target_families": target_families,
    }
    version = f"bundle@v{_next_version_number(bundle_root)}"
    return _write_version(bundle_root, version, bundle_content)


def load_bundle(bundle_root: Path, version: str) -> EvalBundle:
    """Load ``version``, re-verifying its ``bundle.sha256`` checksum against the on-disk
    ``bundle.json`` bytes. Raises :class:`BundleDriftError` naming ``version`` on any mismatch —
    a version whose bytes no longer match its own recorded checksum is refused, never silently
    loaded.
    """
    version_dir = _version_dir(bundle_root, version)
    bundle_path = version_dir / _BUNDLE_FILE
    checksum_path = version_dir / _CHECKSUM_FILE
    if not bundle_path.exists() or not checksum_path.exists():
        raise FileNotFoundError(f"no minted bundle found at {version_dir}")

    body = bundle_path.read_bytes()
    # RED-DRAFT: checksum verification intentionally disabled for the RED run.
    data = json.loads(body.decode("utf-8"))
    return _bundle_from_json_dict(data)


# --------------------------------------------------------------------------------------------- #
# Partition discipline — holdout usage logging, sealed opening
# --------------------------------------------------------------------------------------------- #


def _usage_path(bundle_root: Path, version: str) -> Path:
    return _version_dir(bundle_root, version) / _USAGE_FILE


def _append_usage_entry(bundle_root: Path, version: str, entry: dict[str, Any]) -> None:
    path = _usage_path(bundle_root, version)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**entry, "recorded_at": datetime.now(UTC).isoformat()}, sort_keys=True))
        f.write("\n")


def _load_usage_entries(bundle_root: Path, version: str) -> list[dict[str, Any]]:
    path = _usage_path(bundle_root, version)
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def record_holdout_use(bundle_root: Path, version: str, *, reader: str, reason: str) -> None:
    """Append a usage entry naming ``reader`` and ``reason`` to ``version``'s usage log. Required
    before :func:`read_holdout` will return holdout content for this version.
    """
    if not reader or not reason:
        raise ValueError("record_holdout_use requires a non-empty reader and reason")
    load_bundle(bundle_root, version)  # verifies the version exists and hash-verifies first
    _append_usage_entry(bundle_root, version, {"kind": "holdout_read", "reader": reader, "reason": reason})


def read_holdout(bundle_root: Path, version: str) -> tuple[str, ...]:
    """Return ``version``'s holdout question ids. Raises :class:`HoldoutUsageRequiredError` unless
    :func:`record_holdout_use` has already appended at least one usage entry for this version.
    """
    bundle = load_bundle(bundle_root, version)
    # RED-DRAFT: usage-log gate intentionally disabled for the RED run.
    return bundle.splits["holdout"].question_ids


def open_sealed(bundle_root: Path, version: str, *, event: str) -> SealedOpening:
    """Open ``version``'s sealed partition: requires a stated ``event`` (raises
    :class:`MissingSealedEventError` if empty), unconditionally mints a new bundle version carrying
    the identical six content members (bypassing :func:`mint_bundle`'s content-hash dedup — sealing
    is a property of whether the partition has been touched, not of the content itself), and
    appends a usage entry naming ``event`` to that new version before returning the sealed content.
    """
    # RED-DRAFT: event validation intentionally disabled for the RED run.
    old_bundle = load_bundle(bundle_root, version)
    sealed_ids = old_bundle.splits["sealed"].question_ids

    bundle_content = _bundle_to_json_dict(old_bundle)
    bundle_content.pop("version", None)
    new_version = f"bundle@v{_next_version_number(bundle_root)}"
    new_bundle = _write_version(bundle_root, new_version, bundle_content)
    _append_usage_entry(bundle_root, new_version, {"kind": "sealed_open", "event": event})

    return SealedOpening(bundle=new_bundle, sealed_question_ids=sealed_ids)


__all__ = [
    "ANSWER_LEVEL_FAMILY",
    "ANSWER_LEVEL_TIER",
    "GOLD_PASSAGE_FAMILY",
    "GOLD_PASSAGE_TIER",
    "BundleDriftError",
    "BundleEditInPlaceError",
    "BundleQuestion",
    "BundleSplit",
    "EvalBundle",
    "HoldoutUsageRequiredError",
    "MissingSealedEventError",
    "MissingTargetFamilyError",
    "SealedOpening",
    "TargetFamily",
    "load_bundle",
    "mint_bundle",
    "open_sealed",
    "read_holdout",
    "record_holdout_use",
]
