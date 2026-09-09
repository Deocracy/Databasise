# Eval Bundle v1 — Minted and Recorded

**Date:** 2026-09-09

`RIG.md ## §EV.1`'s content requirement, quoted verbatim:

> A bundle at `bundle@v` carries questions, gold answers, a judge instance, a judge prompt hash, a
> corpus snapshot hash, and the determinism/concurrency setting it was calibrated under, split into
> `dev` / `holdout` / `sealed` partitions.

This document records `bundle@v1` — the project's first real eval bundle, minted from
`databasise/tests/fixtures/eval-corpus/` (06-04-PLAN.md Task 1) by `databasise.eval.bundle.mint_bundle`
(06-04-PLAN.md Task 2), committed at `databasise/evidence/eval-bundles/bundle@v1/`.

## Findings — one row per §EV.1 required member, real minted values

| Member | Value / value shape | Tag |
|---|---|---|
| `questions` | 30 questions, ids `q3`-`q32` (`databasise.eval.bundle.EvalBundle.questions`, one `BundleQuestion(id, text)` per question) | `[code-verified]` |
| `gold_answers` | 30 entries, keyed by question id (`EvalBundle.gold_answers`, `dict[str, str]`) | `[code-verified]` |
| `judge_instance` | `"unresolved"` — see Limits below; not a fabricated plausible string | `[code-verified]` |
| `judge_prompt_hash` | `a826736e1e2bb7884b233123aad1cedd0c59fac702ed8d9de0406de4f1fa57ea` — SHA-256 of the checked-in prompt text at `databasise/evidence/eval-bundles/judge-prompt-v1.txt` | `[code-verified]` |
| `corpus_snapshot_hash` | `405ee4b9deb1bf5b8e82839b61b26213eb5b379a01d8c4a5bf9180afe9eb0f63` — equals `load_snapshot(Path("tests/fixtures/eval-corpus")).corpus_hash` | `[code-verified]` |
| `determinism_concurrency_setting` | `determinism_setting="cache-bypassed"`, `concurrency_setting="sequential"` — read from `databasise.seam.engine._DETERMINISM_SETTING`/`_CONCURRENCY_SETTING` at mint time, not restated as literals | `[code-verified]` |

**Partitions**, real minted values: `dev` 17 questions, `holdout` 9 questions, `sealed` 4 questions
— pairwise disjoint, union equal to the full 30-question set (`EvalBundle.splits`, asserted at
mint time in `mint_bundle`). Assignment is deterministic from a SHA-256 hash of each question's own
id (`databasise.eval.bundle._assign_split`), so a remint from the same snapshot and settings
reproduces the identical assignment — proven by `tests/eval/test_bundle_versioning.py`'s negative
control (Test 7).

## Findings — both §EV.2 target families, real minted values

| Target family | `§4` evidence tier | Cost band, by reference to `## §CM` | Real content this bundle carries |
|---|---|---|---|
| `gold_passage` | `T1` and above | ~1-5% of the full per-decision bill (`RIG.md ## §EV.2`'s own table; invokes neither generator nor judge) | 30 entries, one non-empty `gold_document_ids` list per question (`EvalBundle.target_families[0].targets`) — `[code-verified]` |
| `answer_level` | `T0` | The full `## §CM.2` query-side figure (~5.1-5.2M tokens/decision) plus judging | 30 entries, one gold answer string per question (`EvalBundle.target_families[1].targets`) — `[code-verified]` |

Both families are present for every one of the 30 questions — `mint_bundle` refuses
(`MissingTargetFamilyError`) rather than minting a bundle where either family is a configuration
choice, proven by `tests/eval/test_bundle_versioning.py`'s `test_missing_gold_document_ids_raises_missing_target_family_error`.

## Verdict

**MACH-02's content requirement is met in full for `bundle@v1`.** All six `§EV.1` members are
present with real, minted values; both `§EV.2` target families are present for every question, not
a configuration choice; the three partitions are pairwise disjoint and their union is the full
question set; `bundle@v1` hash-verifies (`load_bundle` re-checks `bundle.sha256` against
`bundle.json`'s on-disk bytes on every load) — proven in
`tests/eval/test_bundle_versioning.py::test_bundle_v1_loads_and_matches_the_engines_own_settings`.

One member's *value*, not its presence, is qualified: `judge_instance` is recorded as the explicit
sentinel `"unresolved"`, not a fabricated model identity — see Limits.

## Method and limits

**Method.** `bundle@v1` was minted for real, this session, via `databasise.eval.bundle.mint_bundle`
against the real 30-question corpus snapshot Task 1 built
(`databasise.parity.corpus.load_snapshot(Path("tests/fixtures/eval-corpus"))`), with
`determinism_setting`/`concurrency_setting` read live from `databasise.seam.engine`'s own module
constants rather than restated as literals. The judge prompt text is checked in at
`databasise/evidence/eval-bundles/judge-prompt-v1.txt`; `judge_prompt_hash` is its real SHA-256,
computed this session, not a placeholder.

**Limits, stated plainly:**

- **The split sizes at 30 questions.** Per `RIG.md ## §EV.3`'s own paired-continuous formula
  (`n = (2.8016/d)²`, solved for `d`), the *bundle's own* n=30 detects `d ≈ 2.8016/√30 ≈ 0.512 SD`
  for a continuous-metric (gold-passage) target — coarser than `§EV.3`'s own n=40 anchor
  (`d ≈ 0.443 SD`), since fewer questions detect only a larger true effect at the same 80%/α=0.05
  power. This is arithmetic on `§EV.3`'s own formula, not a new derivation; it is not corrected for
  the binary/McNemar case `§EV.3` also derives (gold-passage hit/miss, binary judge verdict), which
  needs a larger n for the same power at the discordance rates `§EV.3` anchors on.
- **No A/A null exists yet.** This bundle is the *instrument*; plan 06-06 calibrates the first A/A
  null keyed to `(bundle@v1, tier, metric)` per `RIG.md ## §AA.1`. No promotion or parity claim can
  ride on `bundle@v1` alone — `RIG.md ## §EV.1`'s own sequencing rule (the eval instrument precedes
  every claim; benchmarks never settle decisions) is unchanged by this document.
- **This bundle does not yet carry the owner's own corpus.** `tests/fixtures/eval-corpus/` is a
  public-benchmark corpus (HotpotQA distractor validation split) — exactly what MACH-02's own text
  asks the bundle to be bootstrapped from, and exactly what `RIG.md ## §EV.1`'s sequencing clause
  bounds: a benchmark supplies the instrument, never the decision. Phase 7's HARD-04 is where the
  owner's own corpus layers in; nothing in this document changes that disposition.
- **`judge_instance` is recorded as `"unresolved"`, not a resolved model identity.** This project's
  own convention (Phase 1 D-12 / Phase 2 D-08: "hash what is installed, never what is declared";
  the `unbudgetable`-over-a-fabricated-zero discipline `databasise/parts_core/lightrag/full_ingest.py`
  and `full_delete.py` already establish for token accounting) resolves a model identity only from a
  real provider response, never from a requested/declared id. No such live call was made in this
  environment for this plan — inventing a plausible-looking judge model string here would be exactly
  the kind of substitution that convention forbids. When a real judge call is first made (plan 06-06
  or later), the resolved identity becomes part of the bundle's own next-minted version, per `§EV.1`'s
  own "judge instance ... changing" invalidating-change rule — this document is not re-edited in
  place to carry it retroactively.
