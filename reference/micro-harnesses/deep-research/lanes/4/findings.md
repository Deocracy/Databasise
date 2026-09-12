# Lane 4 findings: Small models trained to manage memory or decide retrieval

Screened 22, admitted 18. Every admitted item was opened at its primary source
(arXiv abs page + full paper text + repository where one exists). All 18 PDFs are
filed in `papers/`. Per-row metadata (stars, pushes, licenses, artefacts) is in
`inventory.tsv`.

## (a) Admitted items

**Mem-alpha (2509.25911).** RL framework that trains an agent to construct memory
(extract, structure, update across core/episodic/semantic stores with tools),
rewarded by downstream QA accuracy over the interaction history; backbone is
Qwen3-4B under verl, and the authors report Qwen3-8B trained worse because of
instruction-following failures. Take: this is the closest existing analogue of
MelodyScribe capability 2/4 (a small model learning file/update ops over typed
memory with QA-accuracy reward). Careful: reward is sparse end-task accuracy, so
credit assignment to individual memory ops is weak; and the 4B-beats-8B result
warns that instruction-following, not scale, is the binding constraint at this
size. Code at wangyu-ustc/Mem-alpha; no confirmed official weights.

**Memory-R1 (2508.19828).** Two RL agents: a Memory Manager emitting
ADD/UPDATE/DELETE/NOOP and an Answer Agent pre-selecting entries, both tuned
with PPO/GRPO on only 152 QA pairs, evaluated on LLaMA-3.1-8B-Instruct and
Qwen-2.5-7B-Instruct across LoCoMo, MSC, LongMemEval. Take: the ADD/UPDATE/
DELETE/NOOP op set is a ready-made contract for MelodyScribe's filing step, and
152 pairs shows data efficiency is real. Careful: no code or weights released,
so this is recipe-only; verify the op-set transfers before committing the
contract to it.

**Search-R1 (2503.09516).** GRPO/PPO on Qwen2.5-3B/7B to emit search calls
mid-reasoning; the implementation detail that matters is masking retrieved
tokens out of the loss so the policy is not trained to imitate the environment.
Take: adopt retrieval masking verbatim for any MelodyScribe rollout that
contains retrieved text; 3B checkpoints are released (HF PeterJinGo) and runnable
on one 16 GB GPU. Careful: RAG-Gym (below) shows this outcome-only recipe
overfits its training domain.

**Self-RAG (2310.11511).** LLaMA2-7B/13B instruction-tuned with reflection
tokens (retrieve/no-retrieve, relevance, support) so the same weights decide
retrieval and generation; critic + generators released (HF selfrag). Take: the
canonical proof that retrieve-decisions can live inside a 7B generator, and the
released critic is a usable retrieve-decision baseline today. Careful: two-model
(generator + critic) serving cost; reflection-token overhead on every segment.

**DeepRetrieval (2503.00223, COLM 2025).** RLVR directly on retrieval metrics
(recall, NDCG, SQL execution accuracy) trains Qwen2.5-3B query/SQL rewriting
that beats GPT-4o and Claude-3.5-Sonnet on literature, evidence, classic IR, and
BIRD/Spider SQL tasks; 3B checkpoints released (HF DeepRetrieval). Take:
strongest direct evidence for the lane hypothesis at exactly MelodyScribe scale,
and the only admitted item covering text-to-SQL memory (capability 2's SQL
filing). Careful: gains are retriever-coupled (queries overfit the retriever
they were rewarded against); re-train or validate against MelodyScribe's own
Faiss/SQLite stack.

**RECOMP (2310.04408, ICLR 2024).** 110M extractive + 775M abstractive
compressors trained against end-task gain; the compressor may emit the empty
string when retrieval is useless (selective augmentation), reaching ~6% tokens
with small drops. Take: the empty-string head is the cheapest possible
retrieve/usefulness decision and composes with any frozen generator. Careful:
abstractive compressor is a GPT-3 distillation, so its faithfulness ceiling is
the teacher's; QA-transfer to larger LMs was weaker than LM-transfer.

**FilCo (2311.08377).** Sentence-level context filter: Flan-T5-XL (3B)
full-tuned as M_ctx plus LLaMA-2-7B with LoRA as M_gen, trained on silver labels
from StrInc/lexical/CXMI measures; cuts prompt length 44-64% with accuracy
gains on six tasks. Take: sentence-granularity filtering with cheap silver
labels is the right granularity for Score-section filing (file the sentence,
not the passage). Careful: repo license is CC-BY-SA-4.0 (copyleft), unlike the
rest of the lane; check compatibility before vendoring code.

**RankRAG (2407.02485, NeurIPS 2024).** One Llama3-8B SFT blend for ranking
(True/False relevance + passage-index selection) and generation; a small ranking
fraction beats dedicated rankers trained on 10x data and matches GPT-4. Take:
the data-blend recipe (ranking cast as QA format alongside RAG data) is the
reusable artefact even though no weights are released. Careful: 8B training cost
32xA100 for 10h — not reproducible on one 16 GB GPU; distil the blend, not the
run.

**Adaptive-RAG (2403.14403, NAACL 2024).** T5-large (770M) classifier on
auto-collected silver labels routes each query to no-retrieval / single-step /
multi-step. Take: the cheapest proven retrieve-decision artefact in the lane;
a sub-1B router in front of MelodyScribe's stores is the lowest-risk first
shipped component. Careful: three coarse buckets only; error cascades when the
router is wrong and there is no recovery path.

**CRAG (2401.15884).** Fine-tuned T5-large (770M) evaluator scores query-doc
pairs and thresholds into Correct (refine strips) / Incorrect (discard + web
fallback) / Ambiguous (both). Take: evaluator-plus-triggered-actions maps
one-to-one onto file-vs-delegate-vs-reretrieve; thresholds are set empirically
per dataset, which MelodyScribe must automate. Careful: web-fallback leg assumes
network search at query time, which a local harness may not have.

**RAG-Gym (2502.13957).** SFT/DPO/PPO plus a trained process critic on
Llama-3.1-8B; DPO with process supervision beats outcome-only RL (Search-R1,
R1-Searcher) by 3.2-11.6% F1 on average and far more out-of-domain; critics and
actors released (HF RAG-Gym). Take: prefer process (per-search-step) supervision
over outcome-only GRPO for the filing policy, and reuse their released PRMs as
  rerank critics. Careful: process labels need an annotator (they use an external
LLM judge), so label cost moves, not disappears.

**MemAgent (2507.02259).** Multi-conversation DAPO trains a segment-reading
overwrite-memory agent; released RL-MemAgent-7B/14B extrapolate 8K training to
3.5M-context QA with <5% loss. Take: the overwrite-memory + RLVR recipe is the
best-tested way to make a small model manage an unbounded stream; 7B fits the
band. Careful: single flat memory with overwrite semantics, no typed stores or
placement decisions — it solves retention, not filing.

**ReSearch (2503.19470, NeurIPS 2025).** GRPO with retrieval masking on
Qwen2.5-7B(-Instruct), no supervised reasoning traces; search as part of the
thinking chain. Take: independent confirmation of the Search-R1 masking recipe
with cleaner ablations of reflection behavior. Careful: no released weights;
repo renamed Agent-RL/ReSearch to Agent-RL/ReCall (redirect verified).

**R1-Searcher (2503.05592) / R1-Searcher++ (2505.17005).** Two-stage outcome-RL
on Llama-3.1-8B and Qwen-2.5-7B for autonomous search; the ++ adds dynamic
acquisition rewards. Take: useful negative control — same family RAG-Gym beats
via process supervision. Careful: neither releases weights; cite for the
recipe, not the artefact.

**RA-DIT (2310.01352).** Dual instruction tuning of retriever (Dragon+) and
generator (LLaMA up to 65B) on retrieval-augmented data. Take: the only
admitted recipe for co-tuning both sides of the retrieve-generate boundary,
relevant if MelodyScribe ever tunes its embedder and filer jointly. Careful:
demo scale is 65B and the code repo is near-empty (3 stars) — scale and
reproducibility both cut against the lane thesis.

**Toolformer (2302.04761).** GPT-J (6B) self-labels API-call positions by
sampling candidate calls and keeping those that reduce perplexity — the
original small-model decide-to-delegate loop. Take: the sampling-and-filtering
data engine ports directly to grammar-constrained op emission (keep sampled op
sequences that improve a verifier score). Careful: nothing released (no code,
no weights); also predates instruction tuning, so its absolute numbers are stale.

**STaR (2203.14465).** GPT-J (6B) bootstraps rationales (generate, keep winners,
retrain; rationalize failures) to large gains on reasoning tasks. Take: the
rationalization trick (train on retrospectively justified traces, not just
winners) is the right loop for MelodyScribe's background revise pass. Careful:
reasoning-only, no retrieval; nothing released.

## (b) Refutations

No admitted primary source directly refutes the lane hypothesis (small tuned
models deciding memory/retrieval actions). Three verified tensions qualify it:

1. Scale tension: RA-DIT (2310.01352) demonstrates its dual-tuning recipe at
LLaMA 65B, i.e. the co-tuning path has no published small-model evidence.
2. RL-overfitting tension: RAG-Gym (2502.13957) shows outcome-supervised RL
agents (Search-R1, R1-Searcher) match it in-domain but lose badly out-of-domain
(+8.5-24.7% for process supervision on unseen sets) — naive GRPO on answer
reward does not yield a robust retrieve policy.
3. Size-nonmonotonicity: Mem-alpha (2509.25911) reports Qwen3-8B trained worse
than Qwen3-4B on memory ops due to instruction-following failures — bigger is
not better inside the band, and instruction-following is the binding constraint.

## (c) Unresolved ledger

- ReST (2308.08998): abstain — verified primary source, but off-lane
(machine-translation alignment; no store/update/delete/retrieve decision, no
released artefact). Kept as the named ancestor of the self-training family.
- Search-o1 (2501.05366): abstain — verified (paper + repo, 1244 stars, MIT),
but inference-only over frozen 32B models; nothing 1-8B is trained. Kept as the
agentic-search baseline that RAG-Gym's trained 8B agents beat.
- DSPy (2310.03714): abstain — title/authors verified at arXiv abs, but repo
and artefact facts not verified this session, and it optimizes prompts without
weight updates (off-lane by the lane's "trained" criterion).
- ActiveRAG (2305.06983): abstain — title/authors verified at arXiv abs;
prompting-only FLAN-T5 system, no training. Kept as the untrained ancestor of
the trained successors above.
- Mem-alpha weights: community HF upload YuWangX/Memalpha-4B exists but its
official status is unconfirmed — treat as unverified, do not depend on it.
- Memory-R1, ReSearch, R1-Searcher(++), RankRAG: papers verified, no code (R1)
or code without weights; recipes only.
- STaR, Toolformer: no official code or weights found (Toolformer org path 404
on GitHub API); recipes only.

## (d) Security findings

Lane 4 has no security lane assignment; no persistent-memory poisoning or skill
injection claims were screened here. One requirement границах the lane: every
admitted RL recipe optimizes a proxy reward (answer EM/F1, retrieval recall,
QA accuracy) that a poisoned store can inflate — e.g. DeepRetrieval-style
retrieval-metric rewards and Mem-alpha QA-accuracy rewards both assume a clean
corpus. Requirement: any MelodyScribe filing policy trained with these recipes
must train and evaluate against a held-out clean store, or reward hacking will
reinforce filing attacker-favorable content. (Follows from the reward designs
in 2503.00223, 2509.25911, 2502.13957; detailed threat literature is lane 6's
scope.)
