---
phase: "16"
slug: "gui-connectors"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-01"
---

# Phase 16 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail. Register IDs come from the 16-*-PLAN.md threat models; statuses from the gsd-security-auditor run of 2026-11-01 (SECURED, 214 targeted tests passed, two scratchpad probes).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| operator console to launcher | unauthenticated loopback HTTP, operator routes mounted only with --operator | selectors, page bounds, node ids, aliases, trace references |
| launcher to stores | read-only probes over sqlite, Faiss, Cozo and the ledger | store contents, never paths or credentials |
| launcher to log file | GET /log tail of the --log-file | redacted log lines (D-19 exception: absolute paths and node ids may appear) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-16-01 | Information disclosure | engine._client_presence / info | high | mitigate | key presence only (engine.py:344-347, 2124-2140) | closed |
| T-16-02 | Elevation of privilege | launcher serve_rest | high | mitigate | non-loopback host refused before open_engine (serve_rest.py:180-184, 209); TrustedHost; Origin guard; CORS opt-in | closed |
| T-16-03 | Tampering | seam/operator_rest.py | medium | mitigate | every route body is one `return await engine.X(...)`; AST rule and mutant test | closed |
| T-16-04 | Tampering | refusal catalogue file | medium | mitigate | catalogue rebuilt from _status_for by test | closed |
| T-16-05 | Repudiation | selector resolution fixture | low | mitigate | pinned facts checked against computed rows | closed |
| T-16-06 | Information disclosure | GET /log mount | medium | accept | D-02 in evidence/COVERAGE.md:136-138; mount gate rest.py:545-549 | closed |
| T-16-07 | Tampering | engine wirings reachable flag | low | mitigate | engine.py:2157-2158; monkeypatch node test | closed |
| T-16-08 | Tampering | ledger read path | medium | mitigate | Ledger.open_existing(read_only=True) (engine.py:2185, 2217; ledger.py:187-202 PRAGMA query_only) | closed |
| T-16-09 | Information disclosure | operator reads | medium | accept | D-10 in COVERAGE.md:141-142 (loopback-only, unauthenticated by design) | closed |
| T-16-10 | Denial of service | ledger handles | low | mitigate | `with handle:` (engine.py:2188, 2220); fd-count test | closed |
| T-16-11 | Information disclosure | operator reads | medium | accept | D-10 in COVERAGE.md:141-142 | closed |
| T-16-12 | Information disclosure | engine._scrub_reasons | medium | mitigate | one scrubber used at engine.py:2271 and 2711; equality test | closed |
| T-16-13 | Denial of service | seam/trace_store.py | low | accept | `shortcut:` comment at trace_store.py:108 | closed |
| T-16-14 | Tampering | promote preview | high | mitigate | read-only handle or None (engine.py:2322-2329); _plan_promotion writes nothing (2878-2903); floors read-only | closed |
| T-16-15 | Repudiation | promote preview vs promote | medium | mitigate | shared _promotion_prologue and _plan_promotion (engine.py:2306, 2840-2876); differential matrix test | closed |
| T-16-16 | Information disclosure | GET /log | low | accept | D-02 in COVERAGE.md:136 | closed |
| T-16-17 | Information disclosure | chunk refs | medium | mitigate | refs minted from {"id"} only (engine.py:2374) | closed |
| T-16-18 | Tampering | stores/vector.py reads | medium | mitigate | constructor does no mkdir; list_ids reads load_committed (vector.py:271-275, 293-299); no new file on a fresh root | closed |
| T-16-19 | Denial of service | vector reconstruct | low | mitigate | reconstruct spy test | closed |
| T-16-20 | Denial of service | stores/probes.py graph registry | high | mitigate | acquire, immutable run, release in finally (probes.py:163-186, 205-223); busy maps to StoreBusyError 409 | closed |
| T-16-21 | Tampering | graph marker check | medium | mitigate | marker check under registry lock before acquire (probes.py:148-151) | closed |
| T-16-22 | Denial of service | graph node edges | low | mitigate | one batched is_in query (probes.py:180-184) | closed |
| T-16-23 | Information disclosure | graph node projection | high | mitigate | allowlist projection (probes.py:224-227); description text does not cross | closed |
| T-16-24 | Information disclosure | UnknownGraphNodeError status | medium | mitigate | absent from _NOT_FOUND_REFUSALS (rest.py:124-129) so 422 not 404 | closed |
| T-16-25 | Denial of service | graph node lookups | low | mitigate | engine.py:2453-2454 for missing database and missing id | closed |
| T-16-26 | Denial of service | info graph_busy | medium | mitigate | .locked() only (engine.py:2142-2145); list() snapshot (graph.py:186-190); 1 s bound test | closed |
| T-16-27 | Information disclosure | info booleans | low | mitigate | booleans only (engine.py:2138-2139) | closed |
| T-16-28 | Information disclosure | log_tail redaction | high | mitigate | redact_secrets plus _URL_RE on read (engine.py:2490); residual gap NEW-3 below | closed |
| T-16-29 | Elevation of privilege | GET /log mount | high | mitigate | mounted only when operator and log_path are set (rest.py:545-549); loopback rule | closed |
| T-16-30 | Repudiation | launcher logging | medium | mitigate | disable_existing_loggers=False, file handler on uvicorn, access and root (serve_rest.py:148-169) | closed |
| T-16-31 | Elevation of privilege | MCP tool set | high | mitigate | TOOL_NAMES still 10 (mcp/tools.py:79-90); REST-ONLY rows COVERAGE.md:120-129 | closed |
| T-16-32 | Repudiation | API inventory | medium | mitigate | COVERAGE.md:131-144; API-INVENTORY.md section 5.1a (plan cites "5.2") | closed |
| T-16-SC | Tampering | dependency manifests | high | accept | no phase 16 commit touched pyproject.toml or uv.lock | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-16-1 | T-16-06, T-16-16 | GET /log is mounted only with --operator and --log-file on a loopback-only launcher; its lines are redacted of secrets and URLs (D-02, COVERAGE.md:136-138). | plan 16 threat model (owner-approved plans); recorded by the autonomous run | 2026-11-01 |
| AR-16-2 | T-16-09, T-16-11 | Operator reads are unauthenticated by design on 127.0.0.1 (D-10, COVERAGE.md:141-142). | plan 16 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-16-3 | T-16-13 | Trace listing has no upper bound on stored rows beyond paging; documented as a `shortcut:` at trace_store.py:108. | plan 16 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-16-4 | T-16-SC | Supply-chain tampering out of scope; verified no manifest change in phase 16 commits. | plan 16 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-16-5 | NEW-2 (D-19) | GET /log returns absolute paths and wiring node ids in log lines; documented exception (COVERAGE.md:143; operator_rest.py:137-142). | Phase 16 D-19; recorded by the autonomous run | 2026-11-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Findings outside the register (2026-11-01 audit)

| ID | Severity | Summary | Disposition |
|----|----------|---------|-------------|
| NEW-1 | low | GET /traces?offset=2**64 unnamed 500 (sqlite OverflowError; checked_page has no ceiling); chunk_page catches only VectorStoreCorruptedError | fixed 2026-11-01 (bounds fix batch) |
| NEW-2 | low | GET /log returns absolute paths and node ids | accepted (AR-16-5) |
| NEW-3 | low | secret redaction covers four shapes only (no Basic auth, password=, token=, AKIA, AIza) | open advisory (16-REVIEW-DISPOSITION.md:47) |
| NEW-4 | low | log file on disk unredacted, created with process umask | open advisory (16-REVIEW-DISPOSITION.md:47) |
| NEW-5 | low | graph reads mutate RocksDB housekeeping files (pycozo 0.7.6 has no read-only open); logical content unchanged | documented at probes.py:11-14; owner decision on per-request open/close (audit/owner-decisions.md item 1) |
| NEW-6 | info | prefix, node_id, alias have no length limit; bound parameters, no injection | noted |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-01 | 33 | 33 | 0 | gsd-security-auditor (autonomous run) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-01 (auditor verdict SECURED; owner confirmation of the accepted-risk rows pending at the milestone close)
