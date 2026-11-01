---
phase: "18"
slug: "gui-live"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-01"
---

# Phase 18 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail. Register IDs come from the 18-*-PLAN.md threat models; statuses from the gsd-security-auditor run of 2026-11-01 (SECURED; CSP recomputed from the shipped page).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser to launcher | the console page served at GET /console on the REST app's own loopback origin | every API response the console renders; sessionStorage history, jobs and ledger log |
| owner click-through | real clients and a real store (18-11 Task 2, D-20) | provider spend, real documents |
| console source to build | mockups/build.py concatenates databasise/console/src into one page with a hash-only CSP | inline script and style hashes |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-18-01 | Tampering | frozen mockup | medium | mitigate | sha256 bf98e79e…4d20 equals docs/gui/MOCKUP-APPROVAL.md; sources verbatim in the packaged page | closed |
| T-18-02 | Tampering | BAK records | medium | mitigate | single writer, checksum refusal (scripts/ledger-amend.py:2, 39-41); edit guard active | closed |
| T-18-03 | Elevation of privilege | --console host | high | mitigate | parser.error on non-loopback host before open_engine (serve_rest.py:185-189, 209) | closed |
| T-18-04 | Tampering | Origin guard, CORS | high | mitigate | every non-GET method guarded, Origin null rejected (serve_rest.py:116-124); --port 0 refused (190-191); CORS opt-in only | closed |
| T-18-05 | Tampering | framing | medium | mitigate | frame-ancestors 'none' plus X-Frame-Options DENY (serve_rest.py:86, 135) | closed |
| T-18-06 | Tampering | console_csp | medium | mitigate | hash-only script-src and style-src, default-src 'none', connect-src 'self'; refuses any other inline count (serve_rest.py:59-87) | closed |
| T-18-07 | Spoofing | Host on /console | medium | accept | TrustedHostMiddleware app-wide covers /console (serve_rest.py:110-111) | closed |
| T-18-08 | Tampering | DOM rendering | medium | mitigate | textContent only; no innerHTML, outerHTML, insertAdjacentHTML, document.write, eval, Function or string timers anywhere (00-app.js:56-58, 82; 05-api.js:31-63, 264) | closed |
| T-18-09 | Spoofing | badge rule | low | mitigate | exact method, template and parameters per WIRED key (05-api.js:172-180, 218-228, 269-273); failed spec keeps every badge (90-start.js:10-13) | closed |
| T-18-10 | Tampering | log tail, excerpts | medium | mitigate | slice(0, 500) and textContent (10-shared.js:370, 387; 20-query.js:178-190) | closed |
| T-18-11 | Information disclosure | GET /log | low | accept | mounted only with operator and log_path (rest.py:545-549); loopback-only; lines redacted (engine.py:2458-2470) | closed |
| T-18-12 | Information disclosure | sessionStorage | low | accept | no secret and no document text stored; query text unbounded (N-4) | closed |
| T-18-13 | Tampering | compare parsing | medium | mitigate | 10-shared.js:96; 21-compare.js:256-259, 304-313 | closed |
| T-18-14 | Tampering | stale results | low | mitigate | aborted or superseded result returns before render (21-compare.js:386-391; 20-query.js:327-364, 389-394) | closed |
| T-18-15 | Tampering | evidence rendering | medium | mitigate | renderRecord, renderTrace, fillDebug use textContent/h() only (30-evidence.js:111-142, 202-215, 280-322) | closed |
| T-18-16 | Information disclosure | debug view | low | accept | loopback-only, unauthenticated by design (Phase 16 D-10) | closed |
| T-18-17 | Tampering | corpus retry | medium | mitigate | id captured on press, encodeURIComponent, result written to the row by id (50-corpus.js:408-427, 618) | closed |
| T-18-18 | Denial of service | polling | low | mitigate | health ticks skipped while any call is in flight; counts poll pauses at zero; off by default, 30 or 60 s; health loads deduplicated | closed |
| T-18-19 | Information disclosure | log tail | low | accept | same premise as T-18-11; textContent | closed |
| T-18-20 | Tampering | delete | high | mitigate | one DELETE call site behind the confirm dialog (40-documents.js:516-527); close clears pending; Corpus delete uses the same dialog | closed |
| T-18-21 | Tampering | writes during writes | medium | mitigate | syncWrites/syncDialog follow InFlight.writing() (40-documents.js:180-204); Run gated; 409 rendered. Corpus Retry gate added 2026-11-01 (N-1) | closed |
| T-18-22 | Repudiation | delete in flight | medium | mitigate | request has no signal; dialog closes only in .then; Escape prevented while sending | closed |
| T-18-23 | Tampering | ids in URLs | low | mitigate | encodeURIComponent; typed id must match ID_RE; server validates again (refusals.py:228-234) | closed |
| T-18-24 | Tampering | promote, rollback, retire | high | mitigate | makeDialog clears pending on close; write sent only from confirm handlers; retire needs the typed version (60-ledger.js:318-363, 390-405, 663-690) | closed |
| T-18-25 | Tampering | retire head | high | mitigate | head from the server alias row; Retire disabled unless status is "none" (60-ledger.js:459-475, 533-540) | closed |
| T-18-26 | Elevation of privilege | log-only mode | medium | mitigate | Retire disabled with tooltip in log-only mode (60-ledger.js:537-539) | closed |
| T-18-27 | Tampering | graph rendering | medium | mitigate | mark text and every cell via textContent (70-graph.js:73, 129-175) | closed |
| T-18-28 | Information disclosure | graph requests | low | mitigate | bodies carry a selector only; no "namespace" in graph screen (70-graph.js:243, 252, 261) | closed |
| T-18-29 | Denial of service | graph reads | low | mitigate | one run() per click, no timer (70-graph.js:291-293) | closed |
| T-18-30 | Elevation of privilege | --console on non-loopback | high | mitigate | same code as T-18-03 | closed |
| T-18-31 | Repudiation | BAK rows done without fail-first | medium | mitigate | scripts/phase-gate.py:276-282 fails any due row with "check never failed" | closed |
| T-18-32 | Tampering | linked test files | medium | mitigate | phase-gate.py:245 flags repointed or unlocked checks; check-edit-guard needs an owner grant | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-18-1 | T-18-07 | Host spoofing against /console is covered by the app-wide TrustedHostMiddleware; no console-specific control needed. | plan 18 threat model (owner-approved plans); recorded by the autonomous run | 2026-11-01 |
| AR-18-2 | T-18-11, T-18-19 | The log tail is served only with --operator and --log-file on a loopback-only launcher and is redacted of secrets and URLs. | plan 18 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-18-3 | T-18-12 | sessionStorage holds query history, job ids and the client ledger log, never a secret or document text; the unbounded query text (R18-14) is an open advisory. | plan 18 threat model; recorded by the autonomous run | 2026-11-01 |
| AR-18-4 | T-18-16 | The trace debug view is loopback-only and unauthenticated by Phase 16 D-10. | plan 18 threat model; recorded by the autonomous run | 2026-11-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Findings outside the register (2026-11-01 audit)

| ID | Severity | Summary | Disposition |
|----|----------|---------|-------------|
| N-1 | low | Corpus Retry button not gated on InFlight.writing(); could overlap an ingest or delete | fixed 2026-11-01 (console fix batch) |
| N-2 | info | --console accepted together with --cors-origin; listed origins gain write access | documented operator choice |
| N-3 | info | hardening headers only on /console, not JSON routes | advisory (= R18-13) |
| N-4 | info | query text stored unbounded in sessionStorage | advisory (= R18-14) |
| N-5 | info | build.py does not escape `<!--` in embedded fixtures; none present | advisory (= R18-15) |
| N-6 | info | server-sourced ids skip ID_RE on two paths; server refuses such ids at ingest | noted |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-01 | 32 | 32 | 0 | gsd-security-auditor (autonomous run) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-01 (auditor verdict SECURED; owner confirmation of the accepted-risk rows pending at the click-through)
