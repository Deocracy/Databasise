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
appends its own usage entry to both the opened version and the new one before returning the sealed
content. A loaded :class:`EvalBundle` reports ``sealed_opened`` from that log, so :func:`mint_bundle`
never hands back an opened version as if unopened; :func:`open_sealed` refuses an opened version
and ``eval.remint`` refuses a mint that resolves to one (:class:`SealedPartitionOpenedError`).
Opening also mints a new highest version, so every floor persisted against the previous highest
version is stale at the promotion gate.

**Versions before and after 15-05 (TOOL-13, D-14).** ``bundle@v1`` keeps its old-scheme
``content_hash`` (question ids and gold answers only) and records no ``split_counts``; its realised
counts, dev 17 / holdout 9 / sealed 4, are stated in ``databasise/evidence/EVAL-BUNDLE-V1.md``. Newly
minted versions hash the question text and gold document ids too and record ``split_counts``. Dedup
recomputes each stored version's hash from its own content, so v1 still matches unchanged input.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
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


class CorruptUsageLogError(RuntimeError):
    """A line of a version's ``usage.jsonl`` is not JSON (for example an append cut short by a crash
    or a full disk). The log is outside ``bundle.sha256``, so this is refused by name rather than
    read past: a skipped line could be the ``sealed_open`` entry (B-WR-06)."""

    def __init__(self, version: str, path: Path, line_number: int) -> None:
        self.version = version
        self.path = path
        self.line_number = line_number
        super().__init__(
            f"bundle {version!r}: line {line_number} of {path} is not JSON; repair or remove that line "
            "before the version is loaded again"
        )


class SealedPartitionOpenedError(RuntimeError):
    """A version whose sealed partition was already opened (its ``usage.jsonl`` records
    ``sealed_open``) was about to be used as if sealed: by :func:`open_sealed` a second time, or by
    ``eval.remint`` as the result of a mint. RIG §EV.1: a touched partition is no longer sealed, and
    a fresh mint of the same questions would only re-label them sealed, so a sealed bundle needs a
    changed question set (B-WR-07)."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(
            f"{version!r}'s sealed partition has already been opened (usage.jsonl records sealed_open), "
            "so it is not sealed; change the question set to mint a sealed bundle"
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
    # Derived from the version's usage log on load, never serialised: True once a sealed_open entry exists.
    sealed_opened: bool = False
    # Realised size of each split; None for bundle@v1, which predates the field (15-05, D-14).
    split_counts: dict[str, int] | None = None


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
    question_texts: dict[str, str],
    gold_answers: dict[str, str],
    gold_document_ids: dict[str, list[str]],
    judge_instance: str,
    judge_prompt_hash: str,
    corpus_snapshot_hash: str,
    determinism_setting: str,
    concurrency_setting: str,
) -> str:
    """SHA-256 over the JCS canonicalisation of §EV.1's five invalidating inputs: the question set
    (ids and text), the gold answers and gold document ids, the judge instance/prompt hash, the
    corpus snapshot hash, and the determinism/concurrency setting pair. Two calls with identical
    inputs MUST return the identical hash; two calls differing in any one input MUST return
    different hashes (Test 7's negative control) — a comparator that ignores one of these inputs
    would pass the "differ" half of that control by accident but never the "identical" half
    consistently, so both directions are exercised.

    The text and the gold ids joined the payload in 15-05 (TOOL-13, D-14); ``bundle@v1``'s stored
    ``content_hash`` predates that, which is why dedup recomputes (:func:`_recomputed_content_hash`).
    """
    payload = {
        "question_ids": sorted(question_ids),
        "question_texts": dict(sorted(question_texts.items())),
        "gold_answers": dict(sorted(gold_answers.items())),
        "gold_document_ids": {k: sorted(v) for k, v in sorted(gold_document_ids.items())},
        "judge_instance": judge_instance,
        "judge_prompt_hash": judge_prompt_hash,
        "corpus_snapshot_hash": corpus_snapshot_hash,
        "determinism_setting": determinism_setting,
        "concurrency_setting": concurrency_setting,
    }
    return hashlib.sha256(canonicalise(payload)).hexdigest()


def _recomputed_content_hash(bundle: EvalBundle) -> str:
    """The current-scheme hash of ``bundle``'s own stored content. Dedup compares against this, never
    against the stored ``content_hash`` field: ``bundle@v1`` stores an old-scheme hash, but its
    stored text and gold ids recompute to the new-scheme value, so unchanged input still dedups to it.
    """
    gold_passage = next(tf for tf in bundle.target_families if tf.name == GOLD_PASSAGE_FAMILY)
    return _compute_content_hash(
        question_ids=[q.id for q in bundle.questions],
        question_texts={q.id: q.text for q in bundle.questions},
        gold_answers=bundle.gold_answers,
        gold_document_ids={k: list(v) for k, v in gold_passage.targets.items()},
        judge_instance=bundle.judge_instance,
        judge_prompt_hash=bundle.judge_prompt_hash,
        corpus_snapshot_hash=bundle.corpus_snapshot_hash,
        determinism_setting=bundle.determinism_setting,
        concurrency_setting=bundle.concurrency_setting,
    )


def _find_version_by_content_hash(bundle_root: Path, content_hash: str) -> str | None:
    for number in _list_version_numbers(bundle_root):
        version = f"bundle@v{number}"
        bundle = load_bundle(bundle_root, version)
        if _recomputed_content_hash(bundle) == content_hash:
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
    data: dict[str, Any] = {
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
    if bundle.split_counts is not None:  # absent for bundle@v1; a copy of it must not gain the key
        data["split_counts"] = dict(bundle.split_counts)
    return data


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
        split_counts=dict(data["split_counts"]) if data.get("split_counts") is not None else None,
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
    missing = [q.id for q in snapshot.queries if not q.gold_document_ids]
    if missing:
        raise MissingTargetFamilyError(
            f"cannot mint a bundle: question id(s) {missing} carry no gold_document_ids — a bundle "
            "must carry both §EV.2 target families (gold-passage and answer-level) for every "
            "question, never one alone as a configuration choice"
        )

    questions = [BundleQuestion(id=q.id, text=q.question) for q in snapshot.queries]
    gold_answers = {q.id: q.answer for q in snapshot.queries}
    question_ids = [q.id for q in questions]

    content_hash = _compute_content_hash(
        question_ids=question_ids,
        question_texts={q.id: q.text for q in questions},
        gold_answers=gold_answers,
        gold_document_ids={q.id: list(q.gold_document_ids) for q in snapshot.queries},
        judge_instance=judge_instance,
        judge_prompt_hash=judge_prompt_hash,
        corpus_snapshot_hash=snapshot.corpus_hash,
        determinism_setting=determinism_setting,
        concurrency_setting=concurrency_setting,
    )

    existing_version = _find_version_by_content_hash(bundle_root, content_hash)
    if existing_version is not None:
        return load_bundle(bundle_root, existing_version)

    splits: dict[str, list[str]] = {name: [] for name in _SPLIT_NAMES}
    for question_id in question_ids:
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
        "split_counts": {name: len(ids) for name, ids in splits.items()},
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
    actual_checksum = hashlib.sha256(body).hexdigest()
    expected_checksum = checksum_path.read_text(encoding="utf-8").strip()
    if actual_checksum != expected_checksum:
        raise BundleDriftError(version, expected_checksum, actual_checksum)

    data = json.loads(body.decode("utf-8"))
    opened = any(e.get("kind") == "sealed_open" for e in _load_usage_entries(bundle_root, version))
    return replace(_bundle_from_json_dict(data), sealed_opened=opened)


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
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CorruptUsageLogError(version, path, number) from exc
    return entries


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
    usage = [e for e in _load_usage_entries(bundle_root, version) if e.get("kind") == "holdout_read"]
    if not usage:
        raise HoldoutUsageRequiredError(
            f"{version}'s holdout partition has no recorded usage entry — call record_holdout_use "
            "before reading holdout content (RIG §EV.1's partition discipline)"
        )
    return bundle.splits["holdout"].question_ids


def open_sealed(bundle_root: Path, version: str, *, event: str) -> SealedOpening:
    """Open ``version``'s sealed partition: requires a stated ``event`` (raises
    :class:`MissingSealedEventError` if empty), unconditionally mints a new bundle version carrying
    the identical six content members (bypassing :func:`mint_bundle`'s content-hash dedup — sealing
    is a property of whether the partition has been touched, not of the content itself), and
    appends a usage entry naming ``event`` to that new version before returning the sealed content.
    """
    if not event:
        raise MissingSealedEventError(
            "open_sealed requires a stated opening event naming what opened the sealed partition — "
            "a sealed read that quietly succeeds is the one outcome sealing exists to prevent"
        )
    old_bundle = load_bundle(bundle_root, version)
    if old_bundle.sealed_opened:  # a second opening would hand out seen questions as sealed (B-WR-07)
        raise SealedPartitionOpenedError(version)
    sealed_ids = old_bundle.splits["sealed"].question_ids

    bundle_content = _bundle_to_json_dict(old_bundle)
    bundle_content.pop("version", None)
    new_version = f"bundle@v{_next_version_number(bundle_root)}"
    _write_version(bundle_root, new_version, bundle_content)
    # Both versions: a remint dedups to the source, which must not look unopened afterwards.
    for opened_version in (version, new_version):
        _append_usage_entry(bundle_root, opened_version, {"kind": "sealed_open", "event": event})

    return SealedOpening(bundle=load_bundle(bundle_root, new_version), sealed_question_ids=sealed_ids)


__all__ = [
    "ANSWER_LEVEL_FAMILY",
    "ANSWER_LEVEL_TIER",
    "GOLD_PASSAGE_FAMILY",
    "GOLD_PASSAGE_TIER",
    "BundleDriftError",
    "BundleEditInPlaceError",
    "BundleQuestion",
    "BundleSplit",
    "CorruptUsageLogError",
    "EvalBundle",
    "HoldoutUsageRequiredError",
    "MissingSealedEventError",
    "MissingTargetFamilyError",
    "SealedOpening",
    "SealedPartitionOpenedError",
    "TargetFamily",
    "load_bundle",
    "mint_bundle",
    "open_sealed",
    "read_holdout",
    "record_holdout_use",
]
