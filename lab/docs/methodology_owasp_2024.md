# Internal Methodology: Web Application Audits
**Version:** 3.2  
**Last updated:** September 2024  
**Author:** Technical Committee  
**Classification:** INTERNAL

---

## Overview

This document describes the standard methodology applied in all web application security audits. It is based on OWASP Testing Guide v4.2 and adapted to the operational context of this team.

## Phases

### 1. Reconnaissance (OSINT)
- Passive enumeration of subdomains via Certificate Transparency logs
- Identification of technologies via Wappalyzer and HTTP headers
- Search for exposed credentials in public breach databases
- Mapping of attack surface: endpoints, APIs, login portals

### 2. Vulnerability Analysis
- Automated scanning with OWASP ZAP and Nuclei
- Manual validation of all findings (eliminate false positives)
- Business logic testing not covered by automated tools

### 3. Exploitation
- Controlled exploitation to demonstrate real impact
- No persistence or destructive payloads in production environments
- Full documentation of each step with screenshots and HTTP logs

### 4. Reporting
- Executive report: summary for management (maximum 2 pages)
- Technical report: full evidence with PoC and remediation
- All reports classified CONFIDENTIAL, delivered via encrypted channel

## Severity Criteria

| Level | CVSS Range | Description |
|-------|-----------|-------------|
| Critical | 9.0 – 10.0 | Direct impact, exploitable without authentication |
| High | 7.0 – 8.9 | Significant impact with limited prerequisites |
| Medium | 4.0 – 6.9 | Moderate impact or requiring privileged position |
| Low | 0.1 – 3.9 | Minor impact or difficult to exploit |
| Informational | N/A | Observations and best practices |

## Responsible Disclosure

All findings are reported exclusively to the designated client contact. No information is shared with third parties without explicit written authorization.
