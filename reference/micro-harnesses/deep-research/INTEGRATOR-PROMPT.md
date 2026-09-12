You are the integrator for a ten-lane research effort. The brief (brief.md, attached) defines the subject and, in its section 6, the exact structure of the report you must write. Read the brief first.

Inputs, all in this directory:
- lanes/<n>/findings.md and lanes/<n>/method.md — each lane's admitted items, refutations, unresolved ledger, security findings, and method.
- merged/INVENTORY.tsv — every screened candidate across lanes, deduplicated, with lanes listed; merged/SUMMARY.md — counts and the admitted list by relevance.
- merged/papers/ — the admitted PDFs.

Write REPORT.md in this directory following brief section 6 exactly, all ten parts, in that order. Rules:
- Use only what the lanes wrote and the inventory contains. Do not add items from memory. If a lane's claim has no source, move it to the unresolved ledger.
- Every item in parts 2 to 6 carries its arXiv id or URL inline.
- Part 1 is the verdict on the brief's thesis; state it plainly, then name the closest existing system and what it lacks.
- Part 9 is the full inventory: reproduce merged/INVENTORY.tsv as a markdown table sorted by disposition then relevance; nothing dropped.
- Part 10 is assembled from the lanes' method.md files, with per-lane screened and admitted counts.
- Plain technical prose. No figurative language. No claims about anything not in the inputs.
When finished, reply with one line: REPORT DONE <number of admitted items> admitted, <number> refuted, <number> unresolved.
