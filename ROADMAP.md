# SPECTRA Roadmap

SPECTRA is an AI agent security testing platform. This document outlines the direction of the project.

## Shipped (v1.0 — May 2026)

- Core engine: payload generation, mutation strategies, blast radius, persistence detection
- Authentication: Argon2id, JWT, TOTP 2FA, session management
- Role-based access control (admin / senior / junior)
- Run history with SSE live event streaming
- Pipeline topology graph visualization
- Audit and report system

## Shipped (v1.1 — June 2026)

### Security Hardening
- [x] Rate limiting on auth endpoints (5 req/IP/min, exponential backoff)
- [x] SSRF protection on engine targets (private IP range blocking)
- [x] HTTP security headers (HSTS, CSP, X-Frame-Options, etc.)
- [x] CORS via environment variable (no hardcoded `*`)
- [x] Startup validation for weak secret keys
- [x] Per-user ownership checks on all engine endpoints
- [x] Length limits on all Pydantic input schemas
- [x] Audit log endpoint (GET /api/v1/auth/audit-log)
- [x] 2FA enforcement signal on login (`must_setup_totp`)
- [x] JWT rotation on refresh, 15min access / 7d refresh
- [x] Data TTL via `expires_at` + configurable `DATA_RETENTION_DAYS`
- [x] Usage limits: `MAX_RUNS_PER_DAY`, `MAX_RUN_TIMEOUT_SECONDS`

### Payload Mutator v2
- [x] Class-based strategy architecture (each strategy independently testable)
- [x] `UNICODE_HOMOGLYPH` — extended table (Latin + Greek lookalikes)
- [x] `ZERO_WIDTH_INJECT` — U+200B between keyword characters
- [x] `BASE64_WRAP` — "decode and follow:" prefix
- [x] `MARKDOWN_ESCAPE` — code block + blockquote wrapping
- [x] `SEMANTIC_PARAPHRASE` — Anthropic API rewrite (graceful skip if no key)
- [x] `MULTILINGUAL_INJECT` — ES, FR, DE, ZH hardcoded translations

### Report Generator v2
- [x] Markdown technical report via Jinja2
- [x] HTML executive report with SVG risk gauge, severity table
- [x] PDF export (weasyprint, falls back to HTML)
- [x] GET /api/v1/engine/runs/{id}/report?format=markdown|pdf|html

### Public Config Scanner
- [x] POST /api/v1/public/config-scan (no auth, stateless)
- [x] 12 security rules covering: tool authorization, credential leaks, jailbreaks, SSRF, code execution
- [x] Score 0–100, per-finding fragments, concrete remediation suggestions
- [x] Rate limit: 10 req/IP/hr
- [x] Frontend /scan page with animated gauge, finding cards, "Copy as Markdown"

## Near-term (v1.2)

- [ ] **Run diff** — compare two runs on the same target, show new/fixed/unchanged findings
- [ ] **Live replay** — serialize execution events to compressed JSON, ReplayPlayer UI
- [ ] **CLI tool** — `spectra scan --url ... --fail-on critical` (typer + rich, exit code 1 on critical)
- [ ] **Export findings** — JSON, CSV, GitHub Issue template
- [ ] **Saved targets** — store URL + headers + auth config for one-click re-runs
- [ ] **Run history search** — filter by target, severity, score, date range
- [ ] **In-app notifications** — toast when a background run finishes
- [ ] **Target health check** — pre-run ping with visual green/yellow/red indicator
- [ ] **Onboarding wizard** — 3-step first-run guide (configure target → scan → report)

## Medium-term (v2.0)

- [ ] **Integrity signatures** — HMAC-SHA256 on reports, verifiable via API
- [ ] **Config export/import** — Fernet-encrypted `.spectra` bundle (user password as key)
- [ ] **Multi-agent topologies** — visual editor for pipeline graphs
- [ ] **Custom payload catalogs** — user-defined injection templates
- [ ] **Webhooks** — POST to external URL on run completion
- [ ] **Team workspaces** — shared targets and reports across a team
- [ ] **Dark mode** — optional via settings, default stays light

## Long-term

- [ ] **CI/CD integration** — GitHub Action, GitLab CI template
- [ ] **Scheduled scans** — cron-based automatic re-testing
- [ ] **Compliance mapping** — OWASP LLM Top 10, NIST AI RMF
- [ ] **Multi-model support** — test targets using different provider APIs
- [ ] **Benchmark suite** — track regression across SPECTRA versions
