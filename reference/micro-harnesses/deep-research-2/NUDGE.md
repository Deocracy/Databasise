You stopped before producing the required output files. Nothing you found is recorded until it is on disk. Continue the same lane now, in this order, without asking questions:
1. Write inventory.tsv immediately from everything you have screened so far (header row plus one row per candidate, the exact 16 columns from your instructions). Append to it as you screen more.
2. Download the PDF for every admitted paper into papers/ as <arxiv-id>_<Title_Slug>.pdf and verify each starts with %PDF.
3. Continue screening until you have met the minimums (20 screened, 8 admitted, or say plainly the literature is thinner). Use https://export.arxiv.org/api/query?search_query=... (Atom, small) and the Semantic Scholar API, not arxiv.org/search HTML pages, which are large and return 400 for some queries.
4. Write findings.md (admitted items with sources; refutations; unresolved ledger; security findings if any) and method.md.
5. Reply with one line: LANE DONE <lane number> admitted=<n> screened=<m>.
