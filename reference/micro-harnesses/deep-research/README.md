# MelodyScribe deep research (Muse Spark 1.3 lanes, 2026-09-11)

Ten research lanes run as separate `opencode-go/muse-spark-1.3-contributor` sessions through OpenCode, four at a time, each with the brief in `BRIEF-AS-RUN.md` plus `LANE-PROMPT.md` and its lane text. One lane (3) ended before writing outputs and was continued with `NUDGE.md`; the runner gained that retry for later lanes. A deterministic merge (`integrate.py`) deduplicated the ten inventories and staged PDFs; a final Muse Spark session (`INTEGRATOR-PROMPT.md`) wrote `REPORT.md` from the ten `findings.md` files and the merged inventory. Claude did not write any finding; it ran the lanes, merged, verified, and filed.

| File | What |
|---|---|
| `REPORT.md` | The ten-part report: verdict on the thesis, top twenty, refutations, per-lane findings, security requirements for the Folio gate, artefacts runnable on a 16 GB GPU, gaps, reading order, full inventory, method |
| `SUMMARY.md` | Merge counts, admitted list by relevance, refutations, unresolved ledger |
| `INVENTORY.tsv` | Every screened candidate, deduplicated across lanes, 16 columns plus `lanes` |
| `lanes/<n>/` | Each lane's `lane.txt`, `findings.md`, `inventory.tsv`, `method.md` |
| `papers/` | 240 admitted PDFs, header-checked. **On disk, not committed** (root `.gitignore`); each is `<arxiv-id>_<title>.pdf` and re-downloadable from `https://arxiv.org/pdf/<id>` using the ids in `INVENTORY.tsv` |

Counts: 364 rows screened across lanes, 280 unique, 226 admitted, 10 refuted, 44 unresolved. Verification performed after the run: all inventories have exactly 16 columns; every PDF starts with `%PDF`; every arXiv id cited in report parts 1 to 8 appears in the inventory or the brief.

Known limits of this run: the lanes could not use a search engine and relied on arXiv's API (which rate-limited them), direct abs pages, Semantic Scholar, and the GitHub API; Papers with Code's API returned errors. Vendor benchmark tables in admitted model cards are primary only for what the vendor reports. The integrator saw findings and inventories, not the PDFs themselves; a second pass that reads the top-ranked PDFs in full is the natural follow-on.
