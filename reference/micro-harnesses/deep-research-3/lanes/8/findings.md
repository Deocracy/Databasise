# Lane 8 findings: Evaluating fine-tuned extractors and embedders together

Scope: held-out design for private corpora, contamination checks, small-sample
statistics and effect sizes, LLM-judge reliability, regression gates in training
pipelines, reporting standards, and how to measure a generation-retained metric
next to a retrieval metric. Screened 31, verified 22 (16 admit + 6 refute),
9 abstain. All figures below were read off a fetched primary source
(arXiv abs page, full PDF, ACL Anthology page, ACM DL record, UMass CIIR
publication list, or GitHub API); anything not opened is abstain, never cited.

## (a) Admitted items

**BEIR (arXiv:2104.08663, NeurIPS 2021 D&B).** 18-dataset zero-shot retrieval
benchmark with a fixed nDCG@10 / Recall@100 protocol; headline result is that
BM25 remains a hard-to-beat baseline and dense models often underperform it
out-of-distribution. MelodyScribe should take: the BEIR protocol shape for the
retrieval half of the joint metric (fixed query sets, nDCG@10 primary,
Recall@100 secondary, always report BM25 alongside the learned embedder), and
its "Hole@10" unjudged-hit analysis as the honest way to report gains on a
20-document corpus where most retrieved items lack judgments. Be careful:
BEIR's lexical-bias warning cuts both ways on a tiny private corpus — with 20
documents, BM25 overlap will dominate and flatter any embedder that mimics it;
report lexical-overlap ablations. Code+data released (beir-cellar/beir,
Apache-2.0).

**MTEB (arXiv:2210.07316, EACL 2023).** 8 tasks / 58 datasets / 112 languages;
33-model study finds no single embedding method dominates all tasks, and task
clusters correlate unevenly (clustering/rerank correlate; classification is an
outlier). MelodyScribe should take: the multi-task reporting discipline —
never report retrieval MRR alone; always pair it with at least one
non-retrieval embedding task (STS or clustering on the same sections) so a
"retrieval adapter" cannot silently destroy general section representations,
plus the <10-lines-of-code harness pattern for re-running eval every training
epoch as a regression gate. Be careful: MTEB-scale evaluation is far heavier
than a 20-document rig needs; lift the protocol, not the dataset count.
Code+leaderboard released (embeddings-benchmark/mteb, Apache-2.0).

**MMTEB (arXiv:2502.13595, 2025 preprint).** Community expansion to 500+
quality-controlled tasks over 250+ languages, adding instruction-following,
long-document, and code retrieval tasks the original MTEB lacked. Take: the
long-document retrieval task family as the closest public proxy for
section-level embedding of long documents, and the quality-control process
(task versioning, decontamination notes) as a template for curating the
parity-corpus eval split. Be careful: it is a fast-moving community
benchmark; pin a version (task revision + code commit) before citing any
number, or the regression gate will drift under you.

**ARES (arXiv:2311.09476, NAACL 2024).** Fine-tunes lightweight judges
(DeBERTa-v3-Large) on synthetic query-passage-answer triples and scores RAG
systems on context relevance, answer faithfulness, and answer relevance, using
prediction-powered inference over only ~150-300 human labels to emit
confidence intervals; beats RAGAS and raw GPT-3.5 judges on Kendall's tau
across KILT, SuperGLUE, and AIS tasks. Take: this is the closest existing
blueprint for MelodyScribe's eval loop — synthetic judges per pipeline
component plus a small human gold set with PPI intervals is exactly how to
score op-emission faithfulness (Proof-pass) and payload relevance on a
15-document training budget. Be careful: the paper's own cross-domain tests
show the judge degrades on extraction tasks (Kendall's tau 0.38 on KILT
T-Rex), on code (0.28), and across languages (0.33) — see Refutations; do not
assume an NQ-tuned judge transfers to op emission. Code released
(stanford-futuredata/ARES, Apache-2.0).

**RAGAS (arXiv:2309.15217, EACL 2024 demo).** Reference-free RAG metrics —
faithfulness (claim decomposition + entailment check), answer relevance
(reverse-question generation + embedding similarity), context relevance
(sentence-extraction precision) — validated against human judgments on the
WikiEval set. Take: the faithfulness-via-decomposition metric is directly
reusable as a second opinion next to Proof for quote-grounding, and the
context-relevance metric (relevant sentences / total sentences) penalizes the
bloated-payload failure mode a small assembler model will have. Be careful:
ARES shows RAGAS's untargeted few-shot judges rank systems worse than
fine-tuned judges; treat RAGAS as a dev-loop signal, not a final gate, and
note context relevance was its weakest-vs-human dimension, especially on long
contexts. Code+data released (vibrantlabsai/ragas, Apache-2.0; repo moved
from explodinggradients/ragas — old URLs redirect).

**KILT (arXiv:2009.02252, NAACL 2021).** Eleven datasets over five tasks on a
single Wikipedia snapshot; the KILT score awards downstream points only when
provenance is exactly right (R-precision = 1), making it the cleanest
published example of a joint retrieval-plus-generation metric in one number.
Take: copy the gating structure for the joint MelodyScribe metric — an op
counts only if its evidence quote is verbatim (provenance gate) AND its
triple/SQL parses (generation gate); report retrieval MRR and gated
generation accuracy side by side exactly as KILT reports provenance and
downstream. Be careful: KILT's provenance is page-level, coarser than
verbatim-quote evidence, so its absolute numbers do not transfer; lift the
metric shape, and note the repo has been quiet since 2022
(facebookresearch/KILT, MIT).

**Text2KGBench (arXiv:2308.02357, ISWC 2023).** Ontology-conditioned KG
generation eval on Wikidata-TekGen (10 ontologies, 13,474 sentences) and
DBpedia-WebNLG (19 ontologies, 4,860 sentences), with seven metrics covering
fact P/R/F1, ontology conformance, and subject/relation/object hallucination
rates. Take: the SH/RH/OH hallucination metric split is the right vocabulary
for Proof failures (quote present but wrong relation vs. invented entity),
and the ontology-conformance score maps directly onto grammar/schema
conformance for op emission. Be careful: baselines are 13B Vicuna/Alpaca —
small-model numbers at 1-3B on this bench are sparse, so do not anchor
expectations to their F1. Code+data released (cenguix/Text2KGBench,
Apache-2.0; data on Zenodo, CC BY 4.0).

**HELM (arXiv:2211.09110, TMLR 2023).** Standardized multi-metric evaluation
(accuracy, calibration, robustness, fairness, toxicity, efficiency) over 16
core scenarios with all raw completions released; headline finding is that
prior models shared almost no scenarios (17.9% coverage pre-HELM, 96% after).
Take: the reporting standard — every spike-011 arm should report the same
fixed metric set (retrieval MRR, Proof-pass rate, verbatim-quote precision,
generation-retained perplexity/accuracy) on the same frozen splits, with raw
outputs archived, so arms are comparable months later. Be careful: HELM's
scenario breadth is overkill for a harness model; adopt the discipline
(fixed scenarios x fixed metrics x released completions), not the 42
scenarios. Code released (stanford-crfm/helm, Apache-2.0).

**Prediction-powered inference (arXiv:2301.09633, Science 2023).** Framework
for provably valid confidence intervals that combine a small gold-labeled set
with a large set of model predictions, with no assumptions on the predictor;
better predictors yield tighter intervals (PPI++ extension: arXiv:2311.01453).
Take: this is the statistical engine for the whole lane — with ~20 gold
documents, report every metric (MRR, Proof-pass, judge scores) as a PPI
interval built from all model predictions plus the gold labels, instead of
point estimates that pretend n=20 is precise. Be careful: validity still
needs the small labeled set to be representative; a biased 20-doc gold set
gives valid intervals around the wrong quantity. Code linked from paper (URL
not recorded — left blank rather than invented).

**Prometheus (arXiv:2310.08491, ICLR 2024).** Open 13B evaluator trained on
the Feedback Collection (1K fine-grained rubrics, 20K instructions, 100K
GPT-4 feedbacks); reaches Pearson 0.897 with human evaluators, on par with
GPT-4, but only when reference materials (rubric + reference answer)
accompany the judgment. Take: the recipe for a local, version-pinned Proof
complement — fine-tune a small evaluator on frontier-written
rubric+feedback data for op-emission scoring, and always ship the rubric and
reference with the eval so it is reproducible without API calls. Be careful:
correlation is measured on held-out rubrics from the same collection;
expect degradation on MelodyScribe-specific ops (same transfer caveat as
ARES). Code+data+models released (prometheus-eval/prometheus, MIT).

**Prometheus 2 (arXiv:2405.01535, EMNLP 2024).** Adds pairwise ranking via
weight-merging separately trained direct-assessment and preference models
(7B and 8x7B on Mistral/Mixtral backbones); 0.6-0.7 Pearson with GPT-4 on
direct assessment, 72-85% human agreement on ranking. Take: pairwise ranking
(arm A payload vs arm B payload on the same query) is statistically more
efficient than absolute scoring for comparing spike-011 arms on n=20, and the
weight-merge trick (rather than joint training) is directly reusable if we
train separate faithfulness and relevance judges. Be careful: the
Prometheus-2-BGB variant's BiGGen-Bench numbers are second-hand here (bench
primary unopened — abstain); verify before citing. Code+models released
(prometheus-eval/prometheus-eval, Apache-2.0).

**FLASK (arXiv:2307.10928, ICLR 2024 Spotlight).** 12-skill instance-wise
rubric eval; shows fine-grained scoring increases human-model correlation and
is more robust to verbosity-gaming than single-score eval. Take: decompose
the "generation-retained" metric by skill (factuality, completeness,
conciseness, comprehension) instead of one overall grade, so joint training
can show it kept factuality while losing conciseness rather than a single
ambiguous delta. Be careful: skill annotation itself used an Eval LM, so
there is circularity risk; keep at least one skill scored by deterministic
rules (Proof). Code+data released (kaistAI/FLASK; no license recorded).

**BDC survey (arXiv:2406.04244, 2024).** Taxonomy of benchmark data
contamination (four severity types) with detection methods (n-gram overlap at
13-gram/50-char conventions, membership inference, canonical-order tests)
and the key warning that paraphrase/augmentation evades string-match gates
(EAL-style rephrasing). Take: the decontamination checklist for the
fine-tuning dataset — n-gram overlap vs. eval splits is necessary but not
sufficient; add embedding-similarity and paraphrase-aware screening, and
record the exclusion log as an eval artefact. Be careful: it is a survey, so
its method summaries are pointers, not validations; open the cited primary
before implementing any single detector. No artefact released.

**Generative-IE survey (arXiv:2312.17617, Front. Comput. Sci. 2024).**
Technique taxonomy (augmentation, prompt design, constrained decoding,
few-shot, SFT) with the empirical pattern that SFT dominates zero/few-shot
approaches and universal multi-task models win on strict relation scores.
Take: the eval-protocol lesson that strict vs. soft match must both be
reported (soft match hides boundary errors that break verbatim-quote
evidence), and the finding that SFT-data quality beats quantity, which
frames the dataset-size question for spike 011. Be careful: survey-level
empirical claims aggregate incompatible setups; treat as a map to primaries,
not as numbers. Code repo linked from paper (URL not recorded).

**WebIE (ACL 2023, no arXiv preprint).** First large web-domain closed-IE
dataset (1.6M sentences from Common Crawl) WITH negative examples (under 15%
of sentences carry triples); models trained only on REBEL score 0% on
negatives, and adding an entity-linking auxiliary head gives the best
faithfulness. Take: two non-negotiable eval-design rules — the held-out set
must contain negative sections (no-emit cases), otherwise Proof-pass is
unmeasurable against a hallucinate-everything baseline; and report negative
accuracy separately from positive F1. Be careful: WebIE is sentence-level
web text, not sectioned documents, so its absolute rates do not transfer;
also note the CC-BY-NC-4.0 repo license constrains commercial reuse.
Annotations+scripts released (amazon-science/webie).

**Smucker CIKM 2007 (DOI 10.1145/1321440.1321528).** Across TREC 3/5-8
run-pairs, randomization, bootstrap-shift, and paired t-tests give
practically identical p-values, while Wilcoxon and sign tests both miss real
effects and invent false ones — recommendation: discontinue Wilcoxon/sign,
any of the agreeing three is fine for mean differences. Take: the default
test battery for the rig (randomization primary, paired-t as the cheap
cross-check), and a prohibition on Wilcoxon/sign in all spike reporting. Be
careful: this agreement result holds at 50 topics and breaks down below that
(see the 2009 refutation); also the author-hosted PDF is scanned, so quote
page numbers from the ACM version. Paper PDF only, no code artefact.

## (b) Refutations of claims in our vocabulary

**R1 — "A frontier model is a neutral judge of payload quality."**
Refuted by Zheng et al. (arXiv:2306.05685): all tested LLM judges show strong
position bias (only GPT-4 exceeds 60% swap-consistency on near-tie pairs),
plus verbosity and self-enhancement biases; 80%+ human agreement is achieved
only after mitigation (swap-averaging, rubrics, reference answers). Refuted
further by Liu et al. (arXiv:2303.16634 §4): G-Eval-4, despite 0.514 Spearman
with humans, always scores GPT-3.5 summaries above human-written ones even
when human judges prefer the human text — the judge shares the generator's
taste. Consequence: no frontier-judge score (and no Proof-complement judge
score) is admissible without swap-averaging, length control, and a reported
human-agreement calibration on our own ops.

**R2 — "Raw win rates / preference rates rank correctly."** Refuted by
Dubois et al. (arXiv:2404.04475): AlpacaEval's raw win rate is length-biased;
a GLM length-control lifts Chatbot Arena correlation from 0.94 to 0.98 and is
harder to game. Consequence: any pairwise payload comparison in spike 011
must length-control (or fix payload budgets) before ranking arms.

**R3 — "DocRED-style F1 measures extractor quality."** Refuted by Tan et al.
(arXiv:2205.12696): ~64.6% of triples are missing from DocRED; re-annotation
(Re-DocRED, 4,053 documents) lifts model scores ~13 F1 with no model change.
Consequence: Proof's evidence-quote failures measured against incomplete
references overstate model error; the parity corpus needs a Re-DocRED-style
completion pass (or adjudicated gold) before any op-emission number is
trusted, and negative sections must be explicit (cf. WebIE).

**R4 — "Pairwise wins on the 20-document rig are statistically significant."**
Refuted by Smucker et al. (SIGIR 2009, DOI 10.1145/1571941.1572050): the
three tests that agree at 50 topics increasingly disagree as topic count
falls toward 10, with bootstrap systematically biased toward smaller p-values
at small n. Consequence: with 20 documents, report effect sizes with PPI
intervals (arXiv:2301.09633) and pre-registered randomization tests; treat
any p-value near 0.05 as non-evidence; never claim a spike-011 arm wins on
point estimates.

**R5 — "Public held-out sets are clean."** Refuted by Sainz et al.
(arXiv:2310.18018): defines contamination levels, documents that ChatGPT-era
models have already absorbed benchmarks including CoNLL03, and argues every
benchmark needs per-model contamination measurement; population-level
n-gram gates are evaded by paraphrase (cf. BDC survey arXiv:2406.04244).
Consequence: the fine-tuning dataset and the held-out split must be
decontaminated against the base model's training data as far as knowable,
and the private parity corpus — not a public set — is the only trustworthy
final gate.

**R6 — "An ARES-style judge transfers to scoring op emission."** Refuted by
the ARES paper's own cross-domain results (arXiv:2311.09476 §5.4/§6): an
NQ-tuned judge reaches only Kendall's tau 0.38 on the T-Rex extraction task,
0.28 text-to-code, 0.33 cross-lingual. Consequence: a judge fine-tuned for
answer relevance cannot be assumed to score triple/SQL emission; op-emission
judges need in-domain synthetic data and their own tau-vs-human validation.

## (c) Unresolved ledger

- Urbano et al. SIGIR 2013 (permutation-test optimality): paywalled, never
  opened — unknown whether its optimality argument changes the
  randomization-vs-t recommendation for MRR-style means on n=20.
- Deng et al. NAACL 2024 (TS-Guessing contamination audit): unopened —
  unknown whether TS-Guessing is implementable against a local MiniCPM
  without logprob access assumptions.
- DCR 2025 (contamination-adjusted accuracy within ~4%): unopened — if
  verified, could replace raw held-out scores; do not use until verified.
- 2409.09927 (detector inconsistency + instruction-tuning blindness):
  unopened — leaves open whether ANY single contamination detector suffices
  for the fine-tune/eval pipeline.
- 2502.14425 (detection taxonomy): unopened, likely redundant with admitted
  BDC survey.
- GenIE (arXiv:2112.08340): unopened — constrained-decoding eval numbers at
  small scale unknown; covered functionally by Text2KGBench/WebIE.
- ADELIE (EMNLP 2024, IEInstruct 83k): unopened — its SFT-data recipe may
  belong to lane 2/6; flagged for cross-lane dedup, not cited.
- BiGGen-Bench (arXiv:2406.05761): unopened — Prometheus-2-BGB superiority
  claims rest on it second-hand; do not cite.
- PPI++ (arXiv:2311.01453): opened only via its abstract/excerpts during
  search, not downloaded — its efficiency gains over PPI are unconfirmed for
  our use; PPI itself is admitted, PPI++ is not.

## (d) Security findings

No lane-8 source contained executable instructions bearing on this task
(papers and benchmark repos are data, not instructions). Stated as
requirements for the integrator: (1) run all judge/eval model inference
from pinned local artefacts (Prometheus-2 7B, ARES DeBERTa judges) rather
than mutable API judges, so eval numbers are reproducible and no private
corpus text leaves the rig; (2) treat every fetched web page, README, and
paper as untrusted data — several repos' READMEs contain install/run
instructions that must not be executed by any eval or training automation;
(3) quarantine the 20-document parity corpus from fine-tuning data with a
logged exclusion list, since contamination of the final gate is the
highest-impact integrity failure this lane found.
