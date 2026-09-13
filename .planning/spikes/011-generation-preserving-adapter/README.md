---
spike: 011
idea: melodyscribe
name: generation-preserving-adapter
type: comparison
validates: "Given the shared query set and spike 003's teacher ops, when MiniCPM5-2B is trained with adapter recipes designed to keep op emission alive (lower capacity, a KL anchor to the base, a joint contrastive plus op-emission loss, and a per-pass adapter toggle), then test MRR against the 0.6B embedder and op emission retained or improved, per recipe, on identical inputs"
verdict: PARTIAL
related: [003, 004, 006, 008]
tags: [embeddings, adapter, training, generation-retained, MelodyScribe-2B]
---

# Spike 011: generation-preserving-adapter

## What This Validates

Spike 006 showed a contrastive LoRA (rank 16, lr 1e-4, 6 epochs) takes the 2B's `⟦EMB⟧` state from test MRR 0.316 to 0.748 against the 0.6B embedder at 0.801, and that the same adapter collapses op emission to zero parses. The one-pass design needs one set of weights that embeds near parity and still emits ops. This spike tests the recipes that could give that, and it is the first attempt at `MelodyScribe-2B-v0.1`. Read `.claude/skills/spike-findings-melodyscribe/SKILL.md`, then `references/embedding-training-and-hybrids.md` and `references/graph-prompt-design.md`, before building. Reuse spike 006's `data.py`, `train_b.py`, `embed_lora.py`, `eval_recall.py`, `gen_eval.py` and spike 003's `student.py`, `evaluate.py`, `teacher.json`, `ops.v0.2.schema.json`, `v02_grammar.py`, `resolve.py` read-only through `sys.path` (copy what you must change into this folder; never edit an earlier spike).

Read also `reference/micro-harnesses/deep-research-3/REPORT.md` section 5, the sourced recipe written to map onto this spike's arms, and adopt from it: alpha = 2r or rsLoRA scaling (alpha over the square root of r) whenever rank varies between arms; the KL anchor as a soft-distribution loss against the base model's next-token distribution, not text replay; the toggle arm (T) as the baseline shape and the single-adapter joint loss (J) as the experiment; a KILT-style gated joint metric where an op counts only if its quote is verbatim and it parses; and report a syntax-versus-grounding split of Proof failures. Deviations from the recipe are recorded as such in the README.

## Plan

Data. Retrieval: `.planning/spikes/shared/queries-v1.json`, train split for training, test split (30 queries over 5 held-out documents) for scoring, the 2 HotpotQA gold queries reported separately. Op emission: spike 003's `teacher.json` ops for the 15 train documents only, formatted with spike 008's recommended one-shot prompt (`008-graph-prompt-design/results/best-prompt.md`, example document `shirley_temple` is a test document, so pick the example from a train document by the same median-op rule and record it); the 5 test documents are never trained on. Negatives as in 006 (in-batch plus other documents).

Training-free controls first (all arms score these before any training, per the research recipe): mean-centering, whitening on the 20 document states plus the train queries, and marker template-bias subtraction on the untrained `⟦EMB⟧` state. If a control alone reaches within 0.05 MRR of the embedder, say so and stop the training arms early.

Arms, all on MiniCPM5-2B in `.venv-train`, identical test inputs, identical evaluation:

- R: spike 006's recipe reproduced (rank 16, lr 1e-4, 6 epochs, InfoNCE, temperature 0.03). Expected test MRR about 0.75 and generation collapse; the reference point.
- L: lower capacity: rank 4, lr 2e-5, 2 epochs, attention projections only. Measures how much retrieval survives when the update is small enough to leave generation alone.
- K: R's objective plus a KL anchor: KL(base logits, adapted logits) on the next-token distribution over spike 003's op-emission prompts (train documents), weight swept over two values (0.1, 1.0). Keeps the language model's predictions near the base while the marker state moves.
- J: joint loss: InfoNCE on the marker state plus causal language-model loss on the one-shot op-emission prompt with the teacher ops as the target (supervised fine-tuning on the train documents). This arm is the `MelodyScribe-2B-v0.1` candidate: it should improve op emission over the base, not merely retain it.
- T: toggle: R's adapter enabled for the embedding pass and disabled for the op pass (peft `disable_adapter`), two decodes. Measures what the one-pass property costs if the build falls back to two passes with one set of weights.

Budget: at most 30 minutes GPU per training run; bf16, gradient checkpointing, sequence length at most 768 for J (one-shot prompt plus ops), 512 elsewhere; every GPU process under `flock /tmp/melodyscribe-gpu.lock`; one model per process.

Metrics, every arm: recall@1, @3, @10 and MRR on the test split and on the gold queries; mean pairwise document cosine; generation retained by spike 006's `gen_eval.py` path (greedy HF decode of the 003 prompt bytes, Proof, grammar-free) with the adapter on versus off: parse rate, routing_exact, Proof-pass, tokens per paragraph; for J also op emission on the 5 test documents with the one-shot prompt, scored against the teacher (routing_exact, subject/value recall, Proof-pass and failure categories). Stretch, only if it fits in 30 minutes of trying: merge J's adapter into the base, convert to GGUF with llama.cpp's converter (a clone may exist under `reference/micro-harnesses/sources/*/code/`; otherwise `pip install` nothing new, record the failure), and score it with spike 003's grammar-constrained `student.py` and `evaluate.py` as arm `minicpm2b-v0.1` next to 003's `minicpm2b` row. Record adapter SHA-256 hashes and training wall time and peak VRAM per arm.

Pass conditions, stated before the run: an arm passes if test MRR is at least 0.75 (006's contrastive level) and generation retained is within 0.05 routing and Proof-pass of the base with the adapter on; J passes if it also improves routing or Proof-pass on the test documents over the base. If no arm passes, PARTIAL with the trade-off curve (MRR against generation retained) and the best arm named; if a control passes without training, VALIDATED with the control as the recommendation.

Environment: `source .planning/spikes/env.sh`; `export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib HF_HUB_OFFLINE=1`; training under `.planning/spikes/.venv-train/bin/python`; weights `.models/hf/openbmb__MiniCPM5-2B`; adapters under this folder in `adapters/` (git-ignored) with hashes in the README. The GPU may be shared with other spike processes; every number reported comes from a lock-held run.

## Research

Read first, in order: `.planning/spikes/MANIFEST.md` (idea + requirements),
`001-score-io-model/SCORE-IO-SPEC.md` + `ops.schema.json` (contract),
`reference/micro-harnesses/README.md` (orientation), this spike's README,
then `.claude/skills/spike-findings-melodyscribe/SKILL.md` +
`references/embedding-training-and-hybrids.md` (settled: contrastive LoRA
reaches test MRR 0.748 vs embedder 0.801 and collapses op emission to 0/20;
distillation INVALIDATED; linear merge 0.82x) +
`references/graph-prompt-design.md` (settled: D1 one-shot is the
recommended single-decode prompt; 008's example doc `shirley_temple` is a
TEST doc in queries-v1, so training must use a train-doc example), then
`reference/micro-harnesses/deep-research-3/REPORT.md` section 5 (the sourced
recipe this spike's arms map onto).

Decisions taken from the recipe:
- alpha = 2r in every arm (R/K/J: r16/alpha32; L: r4/alpha8), so the
  alpha/r ratio is constant while rank varies; rsLoRA scaling then differs
  by construction (8 vs 4) and is reported, not hidden.
- KL anchor as a soft-distribution loss: mean-position KL(base || adapted)
  over the next-token distribution on 003's zero-shot op prompt (train
  docs), base logits from the same weights with the adapter disabled --
  no replay text anywhere.
- Toggle (T) as the baseline shape: R's adapter on for the embedding pass,
  disabled for the op pass; byte-recovery verified, not assumed.
- Single-adapter joint loss (J) as the experiment: InfoNCE + 0.5 x causal
  LM on the one-shot prompt with teacher ops as target (labels -100 on the
  prompt so only op tokens supervise).
- KILT-style gating is inherited from 003's metrics (only Proof-PASSING ops
  enter routing/recall/F1 -- an op counts iff its quote is verbatim AND it
  parses); syntax-vs-grounding split reported on every failure set.

## How to Run

```
cd .planning/spikes/011-generation-preserving-adapter
./run.sh [RUN]     # RUN defaults to run1; reproduces everything (~90-120 min)
```

`run.sh` sources `../env.sh`, exports `TRITON_LIBCUDA_PATH` and
`HF_HUB_OFFLINE=1`. Every GPU step runs under
`flock /tmp/melodyscribe-gpu.lock`, one model per process; scoring and
controls are CPU-only without the lock. Scripts: `embed_a.py` (A),
`embed_untrained.py` (E), `bias_probe.py` + `controls.py` (training-free
controls), `train_r.py` (R, verbatim 006 recipe), `train_l.py` (L),
`train_k.py` (K, `--kl=`), `train_j.py` (J), `embed_lora.py` (per-arm
vectors), `eval_recall.py` (head-to-head, CPU), `gen_eval.py` (zero-shot
generation retained), `verify_toggle.py` (T justification),
`gen_oneshot.py` (one-shot op emission on the 5 test docs).
`opdata.py` holds the train-doc example rule and one-shot builder.
Logs: `logs/*.jsonl` (ISO timestamps) + `logs/*-<utc>.jsonl` per gen run.
Copies from 006 (`data.py`, `common_eval.py`, `embed_*.py`,
`eval_recall.py`, `gen_eval.py`, `train_r.py`) are byte-identical except
`embed_lora.py`'s import (`train_r`, this folder has no `train_b`).
003/001 artefacts are imported read-only through `sys.path`; no earlier
spike was edited. Adapters are git-ignored (`adapters/`); vec dumps are
git-ignored (regenerable); recall/gen/oneshot/toggle JSON and logs are
committed.

Deviations from the spike plan (all recorded here, none silent):
- J's LM forward is capped at 2048 tokens, not 768. The 768 cap cannot
  hold even the target JSON alone for 5/15 train docs (charles_craft
  target = 858 tokens, doctor_strange 897), and truncating targets would
  train on invalid JSON. With 2048 only one train doc (charles_craft,
  2070 total) loses 22 prompt-head tokens to left truncation; every
  target is intact. Contrastive side stays at 512. Peak 10.0 GB, still
  inside 16 GB; train time 231 s, inside the 30-min budget.
- Generation-retained runs without the llama-cpp grammar (same disclosed
  deviation as 006: adapters are HF-native, no GGUF path). Change-on vs
  change-off share one unconstrained greedy decoder; Proof scores the
  difference. Absolute routing is below 003/008 grammar levels.
- The GGUF-merge stretch (J into base + 003 grammar scoring) was not run:
  its premise (J retains generation) failed, so conversion would only
  reproduce collapse at conversion cost. Recorded, not silently dropped.

## What to Expect

~90-120 min wall (five LoRA trainings ~15 min total; ~35 min zero-shot
greedy generation scoring over 6 configs; embeds ~15 min; the rest is
model load). Head-to-head tables: no training-free control near the
embedder; no trained arm clears MRR 0.75 with generation intact; the KL
arms retain (and K01 improves) zero-shot emission at a retrieval cost;
the joint arm matches R on retrieval and collapses generation harder
than the base; the toggle is byte-exact so T = R retrieval + base
generation in two passes. `run.sh` asserts the corpus hash and the
train/test split at every load.

## Investigation Trail

1. **Recon + prompt measurement.** `⟦EMB⟧` tokenises to 5 MiniCPM ids
   with `add_special_tokens=False` (006 reported 6 -- the 6th is the BOS
   prepended under the HF default `True`; the encode paths are
   nevertheless identical to 006's, and E reproduces 0.316 exactly).
   One-shot prompt (INSTRUCTION + adam_collis example + section) is
   ~1000 tokens; prompt + target runs 1111-2070, which forced the J
   2048-cap deviation above. Median-op rule restricted to the 15 train
   docs picks `adam_collis` (sorted train op counts
   2,3,3,4,6,7,8,**10**,10,10,15,16,16,18,18 -- index 7).
   Log: ad-hoc measure (no log file; lengths re-verifiable from
   `teacher.json` + tokenizer).
2. **Baselines reproduce 006 exactly** (`logs/run1.jsonl` model_loaded,
   `results/recall_run1controls.json`): A test MRR 0.801 / gold 1.00 /
   aniso 0.279; E test MRR 0.316 / gold 0.125 / aniso 0.903.
3. **Controls (CPU, `controls.py`, same recall table).** Cmean 0.356
   (+0.04 over E, aniso -0.049); Cwhiten 0.587 (+0.27, aniso -0.001,
   gold 1.00); Cbias 0.407 (+0.09, aniso 0.843). No control within 0.05
   of A (best gap 0.214), so training arms proceeded -- the
   pre-registered early-stop did not trigger. Note against interest:
   whitening removes anisotropy ENTIRELY yet MRR stalls at 0.587, so
   anisotropy is not the whole untrained-state deficit.
4. **R trained** (143 s, peak 7.1 GB, loss 0.9 -> 0.02): test MRR 0.708
   vs 006's 0.748 (run-to-run LoRA variance; 006's own repro was 0.724,
   so the R-class band is ~0.71-0.75). Generation collapses 0/20 parses
   again. R is a successful reproduction of the reference point.
5. **L trained** (22 steps, 36 s, peak 6.7 GB, 2.15M trainable params):
   loss barely moves (2.6 -> 2.1 against chance ln(15) = 2.71).
   Retrieval 0.326 (untrained level) but generation fully retained
   (route 0.05, parse 0.15, proof 9/9 -- identical parse/pass counts to
   base). Capacity dial confirmed: this little learning leaves
   generation alone because it learns nothing at all.
6. **K01/K10 trained** (170 s each, peak 7.7 GB). KL term runs 2-6 nats
   and grows as NCE falls (K01): the contrastive objective drags the
   whole next-token distribution, which is exactly what the anchor
   prices. At kl=1.0 the NCE stalls near ~2 (anchor wins); at 0.1 the
   NCE falls normally. Retrieval: K01 0.569 (train 0.932, memorised),
   K10 0.621 (train 0.703) -- the stronger anchor regularises (smaller
   train/test gap) and generalises better. Against the naive
   expectation, the heavier anchor retrieves BETTER here.
7. **J trained** (231 s, peak 10.0 GB, lam 0.5): LM loss 0.4 -> 0.01
   (teacher-forced memorisation of 14 train docs), NCE falls with R's
   shape. Retrieval 0.738 -- inside the R-class band (neither helps nor
   hurts vs R). Generation collapses on BOTH prompts (see 9).
8. **Zero-shot generation** (`results/gen_*_run1.json`, 20 docs each):
   base route 0.10 / parse 0.15 / proof 1.0 (9/9) at 856.6 tok/para --
   byte-level reproduction of 006. R 0/0 (collapse reproduced). L at
   base level (above). K01 route 0.15 / parse 0.30 / proof 0.957
   (22/23): parse rate DOUBLED vs base (6/20 vs 3/20 docs; routing +1
   doc sits inside 008's ~0.06 noise floor). K10 route 0.10 / parse
   0.20 / proof 0.9 (9/10). J 0/0. Collapsed arms show ~44 s/para vs
   ~17-37 for emitting arms (same artifact 006 saw; GPU otherwise idle,
   `nvidia-smi` 1 MiB after the runs -- the comparison, not the timing,
   is the evidence).
9. **Followed the J surprise into the raw text.** J one-shot emits
   `{"{"{"...` brace soup from token 1 (2048 chars, 1025 tokens, never
   a key). Base one-shot emits a REAL op prefix -- valid structure,
   verbatim quotes -- with drifted schema keys (`birth_date`, `year`,
   `context`) and never terminates (cap). So J is strictly worse than
   base: teacher-forced LM loss memorised the targets yet free
   generation dies at the first token. The contrastive pressure moves
   the early-token distribution; the KL anchor (K arms) is what holds
   it -- K01 zero-shot emits clean closed JSON (279 tokens, terminates).
10. **K01 one-shot extra** (unplanned, head-to-head fair, ~4 min):
    0/5 parses like base, failing the same way (structured prefix, no
    termination at the 1024 cap). No adapter fixes one-shot
    non-termination -- a separate failure from zero-shot collapse
    (needs stopping/abstention training or the grammar cap, not a
    smaller adapter). This bounds the KL win to the zero-shot prompt.
11. **Toggle verified** (`results/toggle_run1.json`): R-adapter-disabled
    vs pure-base forward max abs logit diff = 0.0 exactly, greedy
    continuations equal, adapter-enabled differs. T is rigorous: R
    retrieval (0.708) + base generation (0.10/0.15/1.0) in two passes
    with one weight set.

## Results

Verdict: **PARTIAL**. No arm meets the pre-registered pass bar (test MRR
at least 0.75 AND generation within 0.05 routing/Proof-pass of base with
the adapter on). The trade-off curve is now mapped and the best arm per
goal is named.

Retrieval head-to-head (identical inputs, 30 test queries over 5
held-out docs ranked against all 20; `results/recall_run1.json`):

| arm | test r@1 / r@3 / r@10 / MRR | train MRR | gold MRR | aniso |
|---|---|---|---|---|
| A dedicated 0.6B | 0.700 / 0.867 / 1.000 / 0.801 | 0.788 | 1.000 | 0.279 |
| E 2B untrained | 0.233 / 0.267 / 0.633 / 0.316 | 0.315 | 0.125 | 0.903 |
| Cmean (control) | 0.267 / 0.300 / 0.700 / 0.356 | 0.352 | 0.094 | -0.049 |
| Cwhiten (control) | 0.467 / 0.633 / 0.833 / 0.587 | 0.493 | 1.000 | -0.001 |
| Cbias (control) | 0.300 / 0.333 / 0.800 / 0.407 | 0.432 | 0.375 | 0.843 |
| R contrastive (006 recipe) | 0.533 / 0.867 / 1.000 / 0.708 | 0.942 | 0.750 | 0.687 |
| L rank-4, lr 2e-5, 2ep | 0.233 / 0.267 / 0.533 / 0.326 | 0.412 | 0.375 | 0.930 |
| K01 KL anchor 0.1 | 0.300 / 0.767 / 1.000 / 0.569 | 0.932 | 0.750 | 0.723 |
| K10 KL anchor 1.0 | 0.433 / 0.800 / 0.833 / 0.621 | 0.703 | 1.000 | 0.954 |
| J joint NCE + 0.5 LM | 0.600 / 0.833 / 1.000 / 0.738 | 0.942 | 0.750 | 0.719 |
| T toggle (R on / R off) | retrieval = R (0.708); generation = base (below) | -- | -- | -- |

Generation retained, zero-shot 003 prompt, 20 docs
(`results/gen_*_run1.json`):

| arm | routing_exact | parse_rate | Proof-pass | tok/para | s/para |
|---|---|---|---|---|---|
| base (adapter off) | 0.100 | 0.150 | 1.000 (9/9) | 856.6 | 17.14 |
| +R | 0.000 | 0.000 | 1.000 (0/0) | 1019.9 | 44.20 |
| +L | 0.050 | 0.150 | 1.000 (9/9) | 896.4 | 29.84 |
| +K01 | 0.150 | 0.300 | 0.957 (22/23) | 797.5 | 36.54 |
| +K10 | 0.100 | 0.200 | 0.900 (9/10) | 850.6 | 36.55 |
| +J | 0.000 | 0.000 | 1.000 (0/0) | 1025.0 | 44.30 |

One-shot op emission, 5 test docs, KILT-gated 003 metrics
(`results/oneshot-*_run1.json`):

| arm | route | sv_rec | op_F1 | parse | proof | syn / grd |
|---|---|---|---|---|---|---|
| base one-shot | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 (0/0) | 5 / 0 |
| +J one-shot | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 (0/0) | 5 / 0 |
| +K01 one-shot | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 (0/0) | 5 / 0 |

All 15 one-shot failures are syntax (`unparseable-output`), zero are
grounding -- but the three arms fail differently (trail item 9): base
and K01 emit structured op prefixes with verbatim quotes and die by
non-termination at the cap; J dies at token 1 with brace soup.

Sub-claims:

- **PARTIAL (trade-off mapped)**: no single adapter reaches MRR 0.75
  with generation intact. Best retrieval with any emission alive is K10
  (0.621 + retained); best emission with any retrieval gain is K01
  (parse 0.30 + MRR 0.569); best raw retrieval (J 0.738, R 0.708) is
  generation-dead. Nothing is within 0.05 of A (0.801) while emitting.
- **VALIDATED (mechanism)**: the KL anchor preserves zero-shot
  generation where plain contrastive destroys it (K01/K10/L parse
  6/4/3 docs vs R/J 0/20; toggle proves the adapter, not the base, is
  the collapse site). Contrastive pull moves the early-token
  distribution (KL 2-6 nats during K01 training); the anchor prices
  that drift.
- **INVALIDATED (J as v0.1 candidate)**: joint NCE + op-emission LM
  matches R on retrieval (0.738, inside the R-class run band) and
  collapses generation on both prompts, strictly worse than base
  one-shot (brace soup vs structured prefix). Teacher-forced LM loss to
  0.01 does not transfer to free generation. J also fails its own pass
  condition (no routing/Proof improvement on test docs over base: 0/5
  vs 0/5).
- **VALIDATED (T shape)**: adapter-disabled forward is bit-identical to
  pure base (max abs logit diff 0.0, greedy equal). T = 0.708 retrieval
  + base generation with one weight set in two passes -- the pragmatic
  fallback if the build accepts two passes, exactly as REPORT s5
  ordered (toggle first, joint as experiment).
- **INVALIDATED (controls as shortcut)**: best training-free control
  (whitening, 0.587) misses the embedder by 0.214 despite full
  isotropy. No early stop; no control is the recommendation.
- **Not promotion**: K01's parse doubling (6/20 vs 3/20 docs) exceeds
  008's noise floor but rests on 20 short-paragraph docs and a
  grammar-free decoder; the one-pass v0.1 needs K-class retrieval at
  R-class level first (untested: longer K-anchored runs, higher rank
  with anchor, K + few-shot SFT warm start).
- Harness facts: all five trainings inside budget (R 143 s / 7.1 GB,
  L 36 s / 6.7 GB, K 170 s / 7.7 GB each, J 231 s / 10.0 GB of 16 GB);
  trainable params 25.1M (r16) vs 2.15M (r4); adapter SHAs in
  `logs/run1.jsonl` (`train_done`: R `cf8f29b9…`, L `e0fe8340…`, K01
  `ee7a16c0…`, K10 `b08e86c9…`, J `4d932560…`); every GPU step
  lock-held, one model per process; test split n=30 over 5 docs, docs
  are short paragraphs; `TRITON_LIBCUDA_PATH` required on NixOS.

Owner re-run result (2026-09-12, `run.sh repro`): A, E, and the three controls exact; trained arms within 0.05 MRR (R 0.708 to 0.718, L 0.326 to 0.325, K01 0.569 to 0.602, K10 0.621 to 0.568, J 0.738 to 0.736), so the two K arms trade places inside a 0.57 to 0.62 band; generation: R and J again 0/20 parses, K01 parse 0.20 (17/17 Proof), K10 0.15 (9/9), L 0.20 (11/11), base 0.15 (9/9). The retention mechanism reproduces; K01's parse doubling in this run reads as 0.20 versus 0.15 on the re-run, inside the noise floor, so it is not a promotion claim. One-shot: base and J 0/5 both runs.

Owner re-run: `run.sh repro` reproduces everything under a fresh RUN
name (adapters + merges stay on disk per arm). GPU LoRA training is not
bit-exact across runs (006 measured +/-0.025 MRR on retrains; R here
landed 0.708 vs 006's 0.748); the verdict ordering (K retains, R/J
collapse, J ~= R on retrieval, controls short) does not depend on the
exact R value.
