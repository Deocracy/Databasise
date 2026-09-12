# Lane 2 findings: building fine-tuning datasets from documents

Scope: synthetic SFT-data generation from documents, quality filtering, dedup/decontamination,
data mixing ratios, and how much data a 1B-3B narrow-task fine-tune needs. All items verified
at their primary source (arXiv abs page + PDF text); every figure below was found in the
downloaded paper text. 23 admitted, 11 screened-not-admitted (see inventory.tsv).

## (a) Admitted items

**Self-Instruct (2212.10560).** Bootstraps 52K instruction/input/output triples from a
handful of seed tasks using a 175B teacher, filters by ROUGE-L similarity, and fine-tunes the
base model to +33% absolute on SuperNI, near InstructGPT-001 (ACL 2023). What MelodyScribe
should take: the seed-plus-similarity-filter loop is the minimal viable teacher pipeline, and
the ROUGE-L near-dup filter is directly reusable on synthetic op data where a teacher repeats
itself. Be careful: quality is bounded by the teacher; there is no grounding step, so nothing
here fixes quote-level evidence errors of the kind Proof rejects.

**WizardLM / Evol-Instruct (2304.12244).** Rewrites seed instructions in-depth (harder) and
in-breadth (broader), mixes all complexity levels (70K v1, 196K v2 on HF), and fine-tunes to
near-ChatGPT on high-complexity skills by human and GPT-4 eval (ICLR 2024). Takeaway: the
evolution operators are the concrete tool for turning our few gold op-emission examples into a
curriculum from trivial extractions to adversarial ones (nested dates, ambiguous entities,
multi-hop triples). Be careful: Evol-Instruct evolves instructions, not document-grounded
tasks, so each evolved item still needs a grounding pass against its source section; and spike
008 already warns that weak models do not benefit from stronger-teacher examples, so evolutions
must be validated by Proof, not by teacher authority.

**WizardCoder (2306.08568).** Ports Evol-Instruct to code (Code Evol-Instruct, ~78K scale per
extracted text) on a StarCoder base and tops code benchmarks of its generation. Takeaway: this
is the existence proof that Evol-Instruct transfers to a narrow, verifiable task with tens of
thousands of examples, which calibrates the MelodyScribe dataset budget (thousands, not
millions). Be careful: code has a unit-test oracle; our analogue is Proof-as-filter, which must
be equally automatic or the pipeline stalls on human review.

**Magpie (2406.08464).** Prompts an already-aligned teacher with only its pre-query template,
harvesting 4M instructions and filtering to 300K; SFT-only on Magpie matches the official
Instruct model that used 10M SFT + preference optimization (ICLR 2025). Takeaway: no seeds are
needed when the teacher is aligned, and SFT-only sufficiency supports spike 011's joint-loss
arm (no DPO/RL stage required to get a competitive narrow model). Be careful: it distills the
teacher's distribution including its biases and failure modes; the 300K filter is doing heavy
lifting, so replicate the filtering, not just the generation.

**PersonaHub (2406.20094).** Mines 1B personas from the web and uses them as generation lenses
for math, instructions, knowledge texts, NPCs and tools. Takeaway: personas are the cheapest
diversity multiplier for a 20-document corpus — generate candidate ops, questions and Folio
drafts from many reader personas per section to break teacher mode-collapse. Be careful:
personas add perspective, not facts; every output still needs grounding against the section,
and there is no GitHub repo (data only, HF proj-persona/PersonaHub).

**Unnatural Instructions (2212.09689).** Expands 15 seed instructions to ~64K examples by
paraphrase and trains T0-style models with format-diversity gains. Takeaway: paraphrase
expansion is the floor of the diversity stack — apply it to gold op examples before fancier
operators. Be careful: format diversity is not content diversity; at 64K it is small by current
standards and says nothing about evidence-grounded emission.

**Humpback (2308.06259).** Instruction backtranslation: take unannotated web segments (502K),
generate candidate instructions with a seed-conditioned model, filter by self-consistency, and
fine-tune — beating text-davinci-003 on win-rate. Takeaway: this is the document-to-instruction
pipeline MelodyScribe needs: start from our 20 documents (not from seeds), backtranslate
candidate op-emission tasks, keep what a consistency check (Proof + teacher re-derivation)
accepts. Be careful: segment selection decides everything on a tiny corpus; and the official
code was never released (only unofficial reimplementations), so reimplement from the paper.

**RAFT (2403.10131).** Fine-tunes for domain RAG by training on golden documents mixed with
distractors (P% of items keep the golden, the rest force memorization-style answering), with
CoT answers that quote sources; gains on NQ, HotpotQA and Gorilla-API RAG. Takeaway: the
golden/distractor mixture with quoted CoT is the closest published analogue of MelodyScribe's
query-time assembly job — adopt the P% mixture knob and the quote-in-reasoning format for the
retrieval-assembly training slice. Be careful: RAFT trains answering, not extraction; distractor
counts are a sensitive hyperparameter, and no official repo was found.

**Bonito (2402.18334).** Trains a conditional task generator (unannotated text + task attribute
-> instruction + response) on 1.65M examples remixed from P3 meta-templates; generates task
data for 7 held-out sets from users' private documents; code at BatsResearch/bonito
(BSD-3-Clause). Takeaway: Bonito is the closest released artefact to MelodyScribe's op
emitter — a small model that converts arbitrary sections into training tasks — and its
meta-template remixing is a recipe for manufacturing the joint dataset's generation slice.
Be careful: its outputs are free-form instruction/response pairs with no schema or grammar
constraint, so Proof-style validation must be bolted on, not assumed.

**Rephrasing the Web / WRAP (2401.16380).** An instruction-tuned model rephrases web documents
into styles (Wikipedia-like, QA) and the base model trains jointly on real + synthetic, with
multi-fold efficiency gains on C4-style setups (3x/15x figures in ablations; ACL 2024). This
resolves the brief's "WRAP" bullet: WRAP is the method inside this paper, not a separate
record. Takeaway: rephrase our 20 documents into several styles to multiply contrastive pairs
for the embedder arm almost for free. Be careful: paraphrase drift is the enemy of
verbatim-quote evidence — route every rephrase through Proof and keep rephrases on the
embedding side, never as quote sources.

**Nemotron-CC (2412.02595).** Replaces aggressive filtering (which deletes ~90% of Common
Crawl, cf. FineWeb-Edu/DCLM) with classifier ensembling + synthetic rephrasing to keep 6.3T
tokens for 15T-horizon training; +5.6 MMLU over DCLM at 8B/1T (ACL 2025); data on HF
(nvidia/Nemotron-CC-v2, -Math, -Code). Takeaway: when data is scarce — our 20 documents are
the extreme case — ensemble scorers plus rephrasing beat deletion-heavy filtering; keep
everything, weight it. Be careful: pretraining scale throughout; the classifier ensemble needs
labels we must manufacture (Proof verdicts are the natural label source).

**FineWeb (2406.17557).** 15T tokens from 96 Common Crawl snapshots with fully documented,
ablated choices for MinHash dedup, C4-style heuristic rules and classifiers; pipeline tooling
is DataTrove (huggingface/datatrove, Apache-2.0); data on HF (HuggingFaceFW/fineweb). Takeaway:
the reference dedup/filter pipeline to miniaturize — MinHash + heuristic rules + one learned
filter, with ablations deciding each stage. Be careful: web-scale heuristics (language ID,
length rules, edu classifiers) do not transfer to 20 curated documents; take the pipeline
shape, not the thresholds.

**LIMA (2305.11206).** 1,000 curated examples align a 65B model to strong human-eval results
(superficial-alignment hypothesis: pretraining holds the knowledge, SFT picks the format).
Takeaway: the single most encouraging datapoint for the joint recipe — format-following for a
narrow harness task may need only ~1K gold op-emission examples, which bounds the human
annotation bill. Be careful: curation was extreme (hand-picked for diversity/quality); 1K
random examples will not reproduce this, and it says nothing about the embedding slice.

**AlpaGasus (2307.08701).** Scores 52K Alpaca examples with a ChatGPT judge and keeps 9K;
7B/13B trains faster and better than on the full set. Takeaway: the LLM-judge filtering recipe
is directly reusable — score every teacher-generated op with the frontier model, keep the top
slice, and log the score as training metadata. Be careful: judge-model family bias (same
family grades its own style highly); and 9K kept from 52K still dwarfs what 20 documents yield
before expansion operators are applied.

**Instruction Mining (2307.06290).** Studies automatic selection for instruction tuning and
reports a lightweight rule blending quality and diversity metrics to pick small
high-performing subsets. Takeaway: use cheap metric rules as a first sieve before spending
frontier-judge budget — the two-stage filter (rules, then judge, then Proof) is the affordable
shape. Be careful: the rule constants were tuned on their pool; re-tune thresholds on ours and
validate by downstream Proof-pass, not by rule score.

**Deduplicating Training Data (2107.06499).** MinHash near-dup + suffix-array exact-substring
dedup of C4/RealNews/LM1B/Wiki40B improves perplexity and sharply cuts memorization.
Takeaway: exact-substring dedup is mandatory hygiene for teacher-generated op data (teachers
repeat phrasing); near-dup catches cross-section leakage. Be careful: a pretraining result —
at SFT scale the effect is smaller, but the cost is near zero, so there is no excuse to skip
it.

**SemDeDup (2303.09540).** K-means over embeddings, prune semantically redundant items inside
clusters, keep ~50% of data at parity in OPT experiments; code at
facebookresearch/SemDeDup. Takeaway: semantic dedup catches what exact dedup misses — ops with
different wording but identical triples, the dominant redundancy mode in synthetic extraction
data. Be careful: it needs embeddings first, which is circular with our embedder arm — use the
base model's states or an external embedder for the clustering pass, never the adapter under
training.

**DoReMi (2305.10429).** Tunes domain weights with a 280M proxy + reference model under
group-DRO; 8B Pile training reaches target quality 2.6x faster; code at
sangmichaelxie/doremi (MIT). Takeaway: the principled answer to "mixing ratios" for our
multi-slice joint data (op emission, contrastive pairs, Folio/skills text) — fit weights on a
small proxy, then train once. Be careful: pretraining domains, not SFT slices; the proxy run
still costs real GPU time on our single card, so keep the proxy tiny.

**RegMix (2407.01492).** Assumes rank-invariance of mixture quality across scales, fits a
LightGBM regressor on 1M-token proxy runs (Pile-CC), and predicts the best mix; ICLR 2025;
code at sail-sg/regmix (MIT). Takeaway: the cheapest mixing optimizer in the lane — proxy runs
at 1M tokens fit comfortably beside spike 011 on 16 GB. Be careful: rank-invariance is
validated for pretraining mixes, not for SFT/contrastive joint mixes; treat its output as a
starting mix to refine, not a final answer.

**LESS (2402.04333).** Builds a gradient datastore from a LoRA warmup, scores candidates by
influence on target-task gradients, and selects 5% subsets that beat full-data training on
MMLU/TyDiQA/BBH; code at princeton-nlp/LESS (MIT). Takeaway: influence selection is the right
tool for targeting the op-emission skill specifically — select synthetic data by its gradient
similarity to gold Proof-passing examples. Be careful: it costs a warmup run plus gradient
features over the whole pool; worth it only once the pool exceeds what fits in a single run.

**DEITA (2312.15685).** Scores candidates on complexity, quality and diversity
(Evol-Complexity/Evol-Quality scorers plus embeddings) and selects small subsets that match or
beat much larger training sets; code + data at hkust-nlp/deita (Apache-2.0, 602 stars).
Takeaway: the most copyable scorer stack in the lane — three explicit, implementable scorers
that map 1:1 onto our filter stages (complexity ~ op difficulty, quality ~ Proof verdict,
diversity ~ embedding spread). Be careful: subset sizes and score thresholds are pool-specific;
re-calibrate on our teacher outputs rather than importing constants.

**Data-pruning scaling (Sorscher et al., 2206.14486).** Prototype-based pruning beats power-law
data scaling on CIFAR/ImageNet/SVHN, including self-supervised regimes. Takeaway: the only
scaling-law-shaped evidence that pruning is a first-class scaling axis — it justifies
measuring our own fine-tune data-scaling curve (Proof-pass vs. pool size) instead of assuming
monotonic gains. Be careful: vision, not LLM SFT — do not transfer exponents or pruning
fractions; cite as motivation, never as a number.

**UltraChat (2305.14233).** Topic-scaffolded two-agent generation of 1.5M multi-turn dialogues
(30 topics, opening lines, iterative refinement); EMNLP 2023; code at thunlp/UltraChat (MIT),
data on HF. Takeaway: explicit topic scaffolding is the proven way to force coverage at scale —
our analogue is a section-by-operation-type matrix (every section x every op kind) that the
generator must fill. Be careful: dialogue data, not extraction; its scale is neither attainable
nor needed here — take the coverage-matrix discipline, not the volume.

## (b) Refutations

None. No lane-2 primary source contradicts a claim in the brief. The closest near-misses, checked
and cleared: Magpie's SFT-only competitiveness does not contradict the brief's "scale alone does
not buy op-emission accuracy" (Magpie varies data quality/pipeline, not just scale, and uses a
strong aligned teacher); LIMA's 1,000-example result is consistent with, not contrary to, the
brief's emphasis on dataset composition over size. No brief claim about dataset construction was
found to be false.

## (c) Unresolved ledger

- **GLAN**: brief names it as a synthetic-instruction method; no matching arXiv/OpenAlex record
  (title search returns only unrelated biomedical hits). Reason: unresolvable name, possibly
  misremembered. Nothing admitted, nothing invented.
- **Genie**: brief names it as a synthetic pipeline; title search returns only genomics/physics/
  cancer records, no LLM-data paper. Reason: unresolvable name. Document-grounded neighbours
  (Humpback, Bonito, Magpie) admitted instead.
- **Auto Evol-Instruct**: no verifiable id (recalled 2310.12964 resolves to an unrelated paper,
  verified at its abs page). Reason: unresolvable reference; Evol-Instruct line covered by
  WizardLM/WizardCoder.
- **Small-model (<=3B) SFT data-quantity scaling law**: no direct study found. LIMA and AlpaGasus
  are single operating points, Sorscher is vision, DoReMi/RegMix optimize mixes rather than
  total quantity. Reason: gap in the literature, not a search failure (see Gaps for the
  experiment this implies).
- **Humpback / RAFT / PersonaHub / Instruction Mining official code**: no official repository
  found (Humpback has only unofficial reimplementations; PersonaHub's GitHub path 404s; data
  lives on HF). Reason: artefacts partially released; reimplementation risk noted per item.
- **Tulu 3, Nemotron-4 340B, Min-K% Prob**: verified at primary sources but screened out
  (8B-70B recipe scale; base-model-scale report; evaluation-side method respectively). Reason:
  scope cuts documented in inventory, not verification failures.
- **Venue fields**: only venues confirmed from a fetched page are stated (ACL 2023 for
  Self-Instruct; ICLR 2024 for WizardLM; ICLR 2025 for Magpie/RegMix per author repos; ACL
  2024/2025 and EMNLP 2023 per fetched OpenAlex DOI records). All other rows say "venue
  unverified" rather than repeating recalled venues.

## (d) Security findings (stated as requirements)

No prompt-injection or model-safety results fall in this lane, but the dataset pipeline this
lane enables must meet these requirements, each grounded in an admitted failure mode:

1. **Provenance log**: record teacher model, prompt/template version, source section id and
   license for every synthetic example (teachers repeat copyrighted and PII-bearing text;
   cf. deduplication/memorization findings in 2107.06499).
2. **PII/secret sweep**: run pattern + classifier screening over teacher outputs before
   training, since document-grounded generation (2308.06259, 2402.18334) copies source spans
   into outputs by design.
3. **Quote isolation**: never train quote-emission on rephrased text (2401.16380 drift risk);
   keep rephrases on the embedding side and gold verbatim spans on the emission side, with
   Proof as the gate.
4. **Decontamination of evals**: hold out whole documents (not just examples) and audit with a
   contamination check (2310.16789 deferred to lane 8) before reporting Proof-pass or MRR.
