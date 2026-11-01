---
phase: "09"
slug: "inputs-errors-security"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-01"
---

# Phase 09 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail. Register IDs come from the ten 09-*-PLAN.md threat models; statuses from the gsd-security-auditor run of 2026-11-01 (SECURED, 345 targeted tests passed).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| REST caller to seam | unauthenticated loopback HTTP, every body and query parameter is untrusted | query text, selectors, document ids and bodies, aliases, trace and evidence references, page bounds |
| MCP caller to seam | stdio or loopback HTTP tool calls through the SDK | the same values as JSON tool arguments |
| seam to disk and stores | staged documents, sqlite and Cozo stores, v1 subprocess | validated ids and paths only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-09-01 | Information disclosure | seam/refusals.py refusal_body | medium | mitigate | private attributes skipped; OversizedDocumentError carries byte counts only (refusals.py:57-59, 215-225) | closed |
| T-09-02 | Denial of service | seam/rest.py validation handler | medium | mitigate | refusal looked up first, FastAPI default only when none (rest.py:293-314); residual echo cap added 2026-11-01 (response-builder hardening) | closed |
| T-09-03 | Tampering | seam/rest.py _selector_field | medium | mitigate | Selector.model_validate_json, selector rule's own refusal (rest.py:317-327, 489, 527, 531) | closed |
| T-09-04 | Information disclosure | seam/rest.py 404 mapping | low | accept | 404 only for the four caller-supplied reference lookups (rest.py:124-129, 150-155) | closed |
| T-09-05 | Tampering | seam/corpus.py document id rule, engine ingest/retry/delete | high | mitigate | fullmatch plus reserved ids and suffix allow-list (corpus.py:64, 353-369); id checked before resolve_selector (engine.py:1406, 1701, 1790); staged path built from id and suffix only | closed |
| T-09-06 | Information disclosure | seam/corpus.py checked_page | medium | mitigate | page bounds checked before any corpus op on REST and MCP (rest.py:497, 527; mcp/server.py:134, 138) | closed |
| T-09-07 | Information disclosure | mcp/server.py error passthrough | low | accept | SDK error text passed through when no refusal is found; a crash returns "Error executing tool <name>" with no reason (mcp/server.py:120-128) | closed |
| T-09-08 | Information disclosure | seam/refusals.py failure_class | high | mitigate | failure_class allow-list, private _cause, message built from operation and class only (refusals.py:807-816, 859-877) | closed |
| T-09-09 | Repudiation | seam/engine.py _foreign_fault | medium | mitigate | one ERROR record with redacted traceback in detail= (engine.py:364-372; Phase 12 D-11 replaced exc_info) | closed |
| T-09-10 | Tampering | seam/evidence.py namespace, stores/vector.py | high | mitigate | fullmatch (evidence.py:136-143); validate, is_dir, then build store (engine.py:2684-2690); reads never create a directory (vector.py:200-211, 271-275) | closed |
| T-09-11 | Denial of service | seam/query.py, seam/corpus.py empty inputs | low | mitigate | empty query refused before resolution (query.py:91-96; engine.py:2506, 1331); empty document refused at IngestDocument (corpus.py:129-132) | closed |
| T-09-12 | Elevation of privilege | seam/selectors.py, seam/compare.py | low | mitigate | selectors.py:270-272; compare.py:75 | closed |
| T-09-13 | Tampering | seam/engine.py operator preconditions | medium | mitigate | _resolve_operator_preconditions first statement before any ledger open (engine.py:2744-2745; 2868, 3078, 3233) | closed |
| T-09-14 | Denial of service | seam/engine.py compare | medium | mitigate | consumable check, keys, every resolve_selector and mutates_store check run before the first _execute_resolved (engine.py:1331-1352) | closed |
| T-09-15 | Tampering | seam/engine.py compare | low | mitigate | wirings resolved once and passed on; _execute_resolved never resolves a selector (engine.py:1336-1352, 2510) | closed |
| T-09-16 | Repudiation | seam/corpus.py, mcp/tools.py | low | mitigate | corpus.py:104-114; mcp/tools.py:113-123 ("not stored") | closed |
| T-09-17 | Information disclosure | seam/redact.py | medium | mitigate | explicit raise AssertionError at redact.py:102, 129, 131; no bare assert | closed |
| T-09-SC | Tampering | dependency manifests | high | accept | no phase 09 commit touched pyproject.toml, uv.lock or another manifest (git log) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-1 | T-09-04 | A 404 for an unknown trace, evidence, job or alias reference reveals only that the caller-supplied reference does not exist; the four lookups are enumerated in rest.py:124-129 and 150-155. | plan 09 threat model (owner-approved plans); recorded by the autonomous run | 2026-11-01 |
| AR-09-2 | T-09-07 | The MCP SDK's own error text is passed through when no refusal is found; an unexpected crash returns "Error executing tool <name>" with no cause. No store path or traceback crosses. | plan 09 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-09-3 | T-09-SC | Supply-chain tampering is out of this phase's scope; verified that no phase 09 commit touched a dependency manifest. | plan 09 threat model; recorded by the autonomous run | 2026-11-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Findings outside the register (2026-11-01 audit)

| ID | Severity | Summary | Disposition |
|----|----------|---------|-------------|
| N-1 | medium | trace debug=true returns node fault text with absolute paths and provider URLs (scheduler.py:637, 695; engine.py:2707-2709); conflicts with D-04 but matches Phase 12 D-11 | owner decision: D-04 (scrub) or D-11 (keep); see scratchpad audit/owner-decisions.md |
| N-2 | medium | caller input echoed back without a size cap in six refusals and the default 422 | fixed 2026-11-01: response builders truncate echoes and drop `input` (commits 5eb5b38a, 5c00aabc) |
| N-3 | low | no request-body size cap before validation; upload spooled by Starlette | transferred to the operator (T-04-26) |
| N-4 | low | offset >= 2**63 gave an unnamed 500 on sqlite-paged reads | fixed 2026-11-01 (bounds fix batch) |
| N-5 | low | GET /log limit out of range returns FastAPI {detail} | by design, Phase 16 D-18 |
| N-6 | low | v1 error-text path scrub is a regex heuristic | noted |
| N-7 | info | MCP HTTP transport accepts an Origin from any loopback port | noted |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-01 | 18 | 18 | 0 | gsd-security-auditor (autonomous run) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-01 (auditor verdict SECURED; owner confirmation of the accepted-risk rows pending at the milestone close)
