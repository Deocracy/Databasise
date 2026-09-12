# MelodyScribe deep research 3: training one small model to embed and to generate structured outputs (Muse Spark 1.3 lanes, 2026-09-12)

Ten research lanes run as separate `opencode-go/muse-spark-1.3-contributor` sessions through OpenCode (`run-lanes.sh`, four at a time, each in its lane folder with `BRIEF.md` attached and `LANE-PROMPT.md` plus its `lane.txt` as the prompt; a lane that stops early is nudged on its captured session id with `NUDGE.md`). A deterministic merge (`integrate.py`) deduplicated the ten inventories and staged PDFs; a final Muse Spark session (`INTEGRATOR-PROMPT.md`) wrote `REPORT.md` from the ten `findings.md` files and the merged inventory. Claude did not write any finding; it ran the lanes, merged, verified, and filed.

| File | What |
|---|---|
| `REPORT.md` | The ten-part report: verdicts on the six questions plus the owner's working conclusion (a fine-tuning dataset and a joint recipe are the remaining problem), top twenty, refutations, per-lane findings, the recipe (dataset, joint training on one 16 GB GPU, evaluation protocol, mapped onto spike 011's arms), reusable artefacts, gaps, reading order, full inventory, method |
| `merged/SUMMARY.md` | Merge counts, admitted list by relevance, refutations, unresolved ledger |
| `merged/INVENTORY.tsv` | Every screened candidate, deduplicated across lanes, 16 columns plus `lanes` |
| `lanes/<n>/` | Each lane's `lane.txt`, `findings.md`, `inventory.tsv`, `method.md` |
| `merged/papers/`, `lanes/<n>/papers/` | Admitted PDFs, header-checked. On disk, not committed (root `.gitignore`); each is `<arxiv-id>_<title>.pdf` and re-downloadable from `https://arxiv.org/pdf/<id>` using the ids in `merged/INVENTORY.tsv` |

Counts: 326 rows screened across lanes, 288 unique, 224 admitted, 6 refuted, 58 unresolved; 227 PDFs staged.

| Lane | Subject | Screened | Admitted |
|---|---|---|---|
| 1 | Fine-tuning small models for structured and constrained generation. | 26 | 22 |
| 2 | Building fine-tuning datasets from documents. | 34 | 23 |
| 3 | Joint embedding and generation training and interference. | 39 | 22 |
| 4 | Distillation and RL recipes on one consumer GPU. | 47 | 29 |
| 5 | LoRA and PEFT science for forgetting and capacity. | 32 | 20 |
| 6 | Extraction fine-tunes and their datasets. | 36 | 33 |
| 7 | Small-model post-training recipes from the labs. | 24 | 18 |
| 8 | Evaluating fine-tuned extractors and embedders together. | 31 | 16 |
| 9 | Output composition for a frontier consumer. | 22 | 19 |
| 10 | Generative retrieval and retrieval-generation co-training. | 35 | 33 |

Verification performed after the run: all 227 staged PDFs start with `%PDF`; 223 of the 224 arXiv ids cited in report parts 1 to 8 appear in the merged inventory or the brief. Two defects, left as found: lane 9's inventory has three rows with 14 columns instead of 16 (xRAG, GSM-IC, Robust-RALM), which merged with an empty disposition and should be read as abstain until re-screened; one id cited in part 4 (2403.16634, a judge-calibration reference in lane 8's findings) is not in any inventory and is unverified.

Known limits: the same search constraints as rounds 1 and 2 (arXiv API and abs pages, Semantic Scholar, GitHub API; no search engine). The central gap the report names is that no admitted paper trains one model of 3B or smaller for contrastive retrieval and grammar-constrained emission at once and measures both; spike 011 is the primary evidence for that question.
