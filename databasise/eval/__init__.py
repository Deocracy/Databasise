"""The eval bundle (MACH-02): dev/holdout/sealed splits carrying questions, gold answers, a judge
instance, a judge prompt hash, a corpus snapshot hash, and the determinism/concurrency setting it
was calibrated under — minted, never edited in place. See :mod:`databasise.eval.bundle`.

The A/A calibration procedure (MACH-03, Falsifier 5): bootstrap-resample n paired per-question
differences from one arm run against itself, take the resampled distribution's p95 as the
calibrated promotion floor keyed to `(bundle@v, tier, metric)`. See
:mod:`databasise.eval.calibration`.
"""

from __future__ import annotations
