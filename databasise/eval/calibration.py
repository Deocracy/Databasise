"""The A/A calibration procedure (MACH-03, Falsifier 5): bootstrap-resample n paired per-question
differences from one arm run against itself, take the resampled distribution's p95 as the
calibrated promotion floor, keyed to `(bundle@v, tier, metric)` — RIG.md `### §AA.1`.

Follows `databasise/parity/run_comparison.py`'s harness shape: pure functions over inputs, a
machine-readable result object (:class:`CalibrationResult`), and a pre-flight verification gate
before any number is trusted — the same D-02 pattern that module establishes for index-identity,
applied here to `### §AA.2`'s cache-bypass precondition.

**Two preconditions, both enforced as refusals, not warnings.**

1. **The cache-bypass precondition (`### §AA.2`).** A cache-served re-run returns a stored value
   and short-circuits the underlying call entirely, so a cache-hit-heavy calibration run measures
   a near-zero variance — not merely a small one, since a cached response cannot differ from
   itself. A promotion floor derived from that near-zero null is too permissive: real noise, on a
   genuine cache-bypassed run, would exceed a floor calibrated this thin, and the gate would
   promote it as if it were signal. This is a **correctness risk specific to calibration, not a
   cost-efficiency concern** — the failure mode is a floor that looks fine (tight, well-behaved,
   cheap to have calibrated) and is not. `calibrate_aa_floor` therefore refuses
   (:class:`UnusableFloorError`) when any node in either run reports a cache hit, and equally when
   the bypass status cannot be established at all (`cache_hit` absent or explicitly unknown) — "a
   null whose bypass status is unknown is not usable as a floor" is a refusal to calibrate, not a
   caveat attached to a published number.

2. **The staleness precondition (`### §AA.1`, `CONTRACT.md §5`'s fourth refusal condition).** One
   A/A null exists per `(bundle@v, tier, metric)` triple, and that triple is inseparable from the
   run's own declared determinism and concurrency setting — a null calibrated under one setting
   cannot be read as a floor for a comparison run under a different one. Four events invalidate a
   null: a `bundle@v` change, a tier change, a metric change, and a determinism-or-concurrency
   setting change (named as one combined event, per `### §AA.1`'s own "the concurrency/determinism
   setting is part of the null's own identity" reading). :meth:`CalibrationResult.floor_for` is the
   concrete implementation of `§5`'s fourth refusal condition: it raises :class:`StaleNullError`
   naming exactly which invalidating event applies, rather than a bare mismatch.

**The boundary rule.** A measured delta landing exactly on the calibrated p95 floor does not clear
it — the floor is a one-tailed critical value at the null's own 95th percentile, and a delta
sitting exactly at that mark is a value the null already produces 5% of the time by chance.
:meth:`CalibrationResult.clears_floor` returns true only for a delta strictly above the floor.

**The bootstrap itself.** `scipy.stats.bootstrap(..., paired=True, method="percentile")` — never a
hand-rolled resampling loop. `### §AA.1` explicitly reuses "the paired-bootstrap machinery `§5`
already specifies" and mints no new statistical apparatus; `scipy`'s implementation already
handles the tie and degenerate-resample edge cases a hand-rolled version gets wrong. Default
`n_resamples` is 2000 (06-RESEARCH.md assumption A3: `RIG.md` never states a replicate count), and
the value actually used is recorded on every :class:`CalibrationResult` rather than assumed by a
later reader.

**The batch-width correction (`### §AA.3`), nested with, and distinct from, `§5`'s epoch-level
correction.** `correct_for_batch_width` implements `### §AA.3`'s two-tier design: Benjamini-Hochberg
FDR (`scipy.stats.false_discovery_control`, never hand-rolled) at the bulk-screening tier —
controls the expected proportion of false discoveries among rejections, the right trade at a cheap
screening stage since a false positive there costs only an escalation, not a promotion — and Holm
step-down at the escalated-survivor tier. `### §AA.3` names Dunnett-style as preferred where a
resampling implementation is practical and Holm step-down as the stated fallback; Holm is
implemented here as that named fallback, not as a substitute for a correction the record did not
consider — no ready-made library implementation of either Dunnett-style or Holm exists in this
project's approved dependency set, so Holm's own well-defined, non-resampling step-down algorithm
(sort ascending, adjust by `(N - rank) * p`, enforce monotonicity by running maximum) is
implemented directly; RIG.md's "don't hand-roll" prohibition names only the bootstrap resampling
loop, not this correction. This narrows N arms-within-a-batch down to at most one decision per
batch; `§5`'s own epoch-level correction then runs across the resulting per-batch decisions
separately — the two operate on distinct populations (arms-within-a-batch vs.
decisions-within-an-epoch) and this module never stacks one tier's output as the other's input.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats as _scipy_stats

_DEFAULT_N_RESAMPLES = 2000
_FLOOR_CONFIDENCE_LEVEL = 0.90  # two-sided 90% CI's upper bound == the one-sided p95 floor

BULK_SCREENING_TIER = "bulk_screening"
ESCALATED_SURVIVOR_TIER = "escalated_survivor"
_BATCH_WIDTH_TIERS = (BULK_SCREENING_TIER, ESCALATED_SURVIVOR_TIER)


class UnusableFloorError(RuntimeError):
    """§AA.2's cache-bypass precondition failed: a node in one of the two A/A runs reports a cache
    hit, or its cache-bypass status cannot be established at all. A refusal to calibrate, not a
    warning attached to a published floor — see module docstring precondition 1.
    """


class StaleNullError(RuntimeError):
    """A stored :class:`CalibrationResult` was read under a `NullIdentity` differing from the one
    it was calibrated against — CONTRACT.md §5's fourth refusal condition, concretely
    implemented. ``event`` names exactly which of §AA.1's four invalidating events applies:
    ``"bundle@v change"``, ``"tier change"``, ``"metric change"``, or ``"concurrency or
    determinism setting change"``.
    """

    def __init__(self, event: str, detail: str) -> None:
        self.event = event
        super().__init__(
            f"stale A/A null ({event}): {detail} — §AA.1's four invalidating events "
            "(bundle@v, tier, metric, concurrency/determinism setting) make the setting part of "
            "the null's own identity; a comparison under a differing setting cannot borrow this floor"
        )


@dataclass(frozen=True)
class NullIdentity:
    """The frozen key a calibrated null is stored and read under — §AA.1: "the concurrency/
    determinism setting is part of the null's own identity... exactly as (bundle@v, tier, metric)
    already is." All five fields are members of the key, not metadata beside it.
    """

    bundle_at_v: str
    tier: str
    metric: str
    determinism_setting: str
    concurrency_setting: str

    def stale_reason(self, candidate: "NullIdentity") -> str | None:
        """Return the name of the §AA.1 invalidating event that makes ``candidate`` unable to read
        this identity's own null, or ``None`` if the two identities match exactly.
        """
        if self.bundle_at_v != candidate.bundle_at_v:
            return "bundle@v change"
        if self.tier != candidate.tier:
            return "tier change"
        if self.metric != candidate.metric:
            return "metric change"
        if (
            self.determinism_setting != candidate.determinism_setting
            or self.concurrency_setting != candidate.concurrency_setting
        ):
            return "concurrency or determinism setting change"
        return None


@dataclass(frozen=True)
class CalibrationResult:
    """One calibrated A/A null: the bootstrap-resampled p95 floor at ``identity``, and every value
    a later reader needs to judge how it was produced rather than assuming it.
    """

    identity: NullIdentity
    floor: float
    n_questions: int
    n_resamples: int
    seed: int | None

    def clears_floor(self, delta: float) -> bool:
        """True only for a delta strictly above the floor — a delta landing exactly on the p95
        mark does not clear it (§AA.1's boundary rule; see module docstring).
        """
        return delta > self.floor

    def floor_for(self, candidate: NullIdentity) -> float:
        """Read this null's floor for ``candidate``'s own identity. Raises :class:`StaleNullError`
        naming the invalidating event when ``candidate`` differs from the identity this null was
        actually calibrated under (CONTRACT.md §5's fourth refusal condition).
        """
        reason = self.identity.stale_reason(candidate)
        if reason is not None:
            raise StaleNullError(
                reason, f"stored null identity {self.identity!r} vs. candidate {candidate!r}"
            )
        return self.floor


# --------------------------------------------------------------------------------------------- #
# paired_differences — n per-question differences from two runs of the same arm
# --------------------------------------------------------------------------------------------- #


def paired_differences(
    run_a: Mapping[str, float], run_b: Mapping[str, float], metric: str
) -> tuple[float, ...]:
    """The n per-question differences (``run_b[qid] - run_a[qid]``) between two runs of the same
    arm — the arm run against itself, twice, at one fixed metric. ``run_a``/``run_b`` map each
    question id to that run's already-computed score for ``metric``. Refuses (``ValueError``) when
    the two runs do not cover the same question set: a paired statistic over unequal sets is not
    paired. Order is deterministic (sorted by question id), so a fixed-seed bootstrap over the
    result is reproducible independent of the caller's own dict ordering.
    """
    ids_a, ids_b = set(run_a), set(run_b)
    if ids_a != ids_b:
        only_a = sorted(ids_a - ids_b)
        only_b = sorted(ids_b - ids_a)
        raise ValueError(
            f"paired_differences({metric!r}): run_a and run_b do not cover the same question "
            f"set — only in run_a: {only_a}, only in run_b: {only_b}. A paired statistic over "
            "unequal sets is not paired."
        )
    return tuple(run_b[qid] - run_a[qid] for qid in sorted(ids_a))


# --------------------------------------------------------------------------------------------- #
# The cache-bypass precondition (§AA.2) — read from either NodeTrace instances or plain dicts
# --------------------------------------------------------------------------------------------- #


def _node_cache_hit(node: Any) -> bool | None:
    """``None`` means "unknown" — either the field is genuinely absent (a dict with no
    ``cache_hit`` key) or was explicitly recorded as unresolvable (``cache_hit=None``ish on a
    looser record). Only an explicit ``False`` counts as a verified bypass.
    """
    if isinstance(node, Mapping):
        return node.get("cache_hit")
    return getattr(node, "cache_hit", None)


def _node_id(node: Any) -> str:
    if isinstance(node, Mapping):
        return str(node.get("node_id", "<unknown>"))
    return str(getattr(node, "node_id", "<unknown>"))


def _verify_cache_bypassed(run_a_nodes: Iterable[Any], run_b_nodes: Iterable[Any]) -> None:
    """§AA.2's hard precondition: every node in both runs must report ``cache_hit is False``.
    Raises :class:`UnusableFloorError` on the first node reporting a hit, or an unknown/absent
    status — never a warning, per the module docstring's precondition 1.
    """
    for label, nodes in (("run_a", run_a_nodes), ("run_b", run_b_nodes)):
        for node in nodes:
            hit = _node_cache_hit(node)
            if hit is False:
                continue
            reason = "reports a cache hit" if hit is True else "has an unknown cache-bypass status"
            raise UnusableFloorError(
                f"{label} node {_node_id(node)!r} {reason} — §AA.2 makes cache-bypass a hard "
                "precondition for calibration: a null whose bypass status is unknown, or which "
                "was calibrated from a cache-served run, is not usable as a floor. A cache-served "
                "re-run cannot differ from itself, so the resulting null is near-zero-width and "
                "the floor derived from it is too permissive — it looks tight, well-behaved and "
                "cheap while being wrong."
            )


# --------------------------------------------------------------------------------------------- #
# calibrate_aa_floor — the bootstrap itself
# --------------------------------------------------------------------------------------------- #


def calibrate_aa_floor(
    paired_diffs: Sequence[float],
    *,
    identity: NullIdentity,
    run_a_nodes: Iterable[Any],
    run_b_nodes: Iterable[Any],
    n_resamples: int = _DEFAULT_N_RESAMPLES,
    seed: int | None = None,
) -> CalibrationResult:
    """§AA.1's procedure: verify the §AA.2 cache-bypass precondition first (pre-flight, before any
    number is trusted — D-02's pattern), then bootstrap-resample ``paired_diffs`` with replacement
    via ``scipy.stats.bootstrap(paired=True, method="percentile")`` and take the resampled
    distribution's p95 as the calibrated floor.
    """
    _verify_cache_bypassed(run_a_nodes, run_b_nodes)

    diffs = np.asarray(paired_diffs, dtype=float)
    if diffs.size == 0:
        raise ValueError("calibrate_aa_floor: paired_diffs must be non-empty")

    result = _scipy_stats.bootstrap(
        (diffs,),
        statistic=np.mean,
        n_resamples=n_resamples,
        method="percentile",
        paired=True,
        confidence_level=_FLOOR_CONFIDENCE_LEVEL,
        random_state=seed,
    )
    floor = float(result.confidence_interval.high)

    return CalibrationResult(
        identity=identity,
        floor=floor,
        n_questions=diffs.size,
        n_resamples=n_resamples,
        seed=seed,
    )


# --------------------------------------------------------------------------------------------- #
# correct_for_batch_width — §AA.3's two-tier correction
# --------------------------------------------------------------------------------------------- #


def _holm_step_down(p_values: Sequence[float]) -> list[float]:
    """Holm-Bonferroni step-down adjusted p-values — §AA.3's named fallback where a Dunnett-style
    resampling correction is impractical. Standard algorithm, not the resampling loop RIG.md's
    "don't hand-roll" prohibition names: sort ascending, adjust rank ``i`` (0-based) by
    ``(N - i) * p``, enforce monotonicity via a running maximum, cap at 1.0.
    """
    n = len(p_values)
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    running_max = 0.0
    for rank, idx in enumerate(order):
        candidate = (n - rank) * p_values[idx]
        running_max = max(running_max, candidate)
        adjusted[idx] = min(running_max, 1.0)
    return adjusted


def correct_for_batch_width(
    p_values: Sequence[float], *, tier: str
) -> list[float]:
    """§AA.3's two-tier batch-width correction, applied on a population distinct from §5's own
    epoch-level correction (see module docstring). ``tier`` selects the scheme:
    :data:`BULK_SCREENING_TIER` (Benjamini-Hochberg FDR, ``scipy.stats.false_discovery_control``)
    or :data:`ESCALATED_SURVIVOR_TIER` (Holm step-down). Each call is independent and stateless —
    never stacks one tier's output as the other's input.
    """
    if tier == BULK_SCREENING_TIER:
        adjusted = _scipy_stats.false_discovery_control(np.asarray(p_values, dtype=float), method="bh")
        return [float(v) for v in adjusted]
    if tier == ESCALATED_SURVIVOR_TIER:
        return _holm_step_down(list(p_values))
    raise ValueError(
        f"correct_for_batch_width: unknown tier {tier!r} — must be one of {_BATCH_WIDTH_TIERS}"
    )


__all__ = [
    "BULK_SCREENING_TIER",
    "ESCALATED_SURVIVOR_TIER",
    "CalibrationResult",
    "NullIdentity",
    "StaleNullError",
    "UnusableFloorError",
    "calibrate_aa_floor",
    "correct_for_batch_width",
    "paired_differences",
]
