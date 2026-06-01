# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in SPECTRA, please report it via responsible disclosure:

**Contact:** kris.yvna@gmail.com  
**Subject line:** `[SECURITY] SPECTRA — <brief description>`

### What to include

- Description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept, curl commands, screenshots)
- Affected component (backend API, frontend, engine, Docker config)
- Suggested mitigation if known

### Response timeline

- **Acknowledgement:** within 48 hours
- **Initial assessment:** within 5 business days
- **Fix or mitigation:** within 30 days for critical/high issues

We will credit reporters in the release notes unless you prefer to remain anonymous.

## Security Design

SPECTRA is a security testing tool for AI agent pipelines. Its own security posture includes:

- **Authentication:** Argon2id password hashing, JWT (RS256-compatible), TOTP 2FA
- **Authorization:** Role-based access control (admin / senior / junior), per-resource ownership checks
- **Transport:** TLS enforced via nginx in production, HSTS headers
- **Input validation:** Pydantic schemas with strict length limits on all user inputs
- **SSRF protection:** All engine targets are validated against private IP ranges before HTTP requests
- **Rate limiting:** Auth endpoints: 5 req/IP/min with exponential backoff; public scan: 10 req/IP/hr
- **Data minimization:** System prompts in `/public/config-scan` are never persisted
- **Audit logging:** All auth events (login, logout, 2FA, password change) are logged with IP and timestamp

## Out of Scope

The following are intentionally not in scope for this policy:

- Vulnerabilities in dependencies not yet published by their maintainers
- Issues requiring physical access to the server
- Social engineering attacks
