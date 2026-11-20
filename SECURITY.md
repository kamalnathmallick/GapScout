# Security Policy

GapScout takes platform security, network isolation, and data privacy seriously.

---

## Supported Versions

| Version | Supported |
|---|---|
| `v0.1.0-beta` | :white_check_mark: |
| `main` branch | :white_check_mark: |
| `< v0.1.0` | :x: |

---

## Reporting a Vulnerability

If you discover a security vulnerability or security bug, please do **not** open a public issue.

Instead, please send an email to:
- **Email:** `security@gapscout.app` (or contact the repository maintainer directly via GitHub profile)

Include:
1. Description of the vulnerability and its potential impact.
2. Steps to reproduce or proof-of-concept.
3. Suggested fix or remediation (if known).

We aim to acknowledge reports within 48 hours and provide updates until the vulnerability is addressed.

---

## Security Architectural Guarantees

1. **SSRF Defense:** All external HTTP fetching (e.g. website auditing) resolves hostnames and strictly prohibits connections to private, loopback, link-local, multicast, and cloud metadata addresses (`169.254.169.254`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `::1`).
2. **Prompt Injection Protection:** Scraped external text (website content, customer reviews) is always wrapped in strict XML tags (`<untrusted_scraped_data>`) and treated as passive data. The LLM is explicitly forbidden from following embedded instructions.
3. **Workspace Tenant Isolation:** Every user-data database table carries a mandatory `workspace_id` foreign key. Endpoints strictly enforce workspace-level authorization boundaries.
4. **No Automated Outreach:** The system creates drafts for human review and never dispatches cold outreach messages automatically.
5. **Data Protection & Right to be Forgotten:** Supports instant JSON workspace data export and full cascading data deletion adhering to GDPR and DPDP compliance requirements.
