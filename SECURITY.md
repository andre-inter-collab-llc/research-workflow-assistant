# Security Policy

## Supported Versions

| Version       | Supported          |
| ------------- | ------------------ |
| 2026.x.x      | :white_check_mark: |
| < 2026.01.01   | :x:                |

We follow [Calendar Versioning](https://calver.org/) (YYYY.MM.DD). Security updates are provided for the latest release only.

## Reporting a Vulnerability

If you discover a security vulnerability in the Research Workflow Assistant, please report it responsibly.

### How to Report

Use GitHub's private vulnerability reporting channel:

**Security Advisories**: https://github.com/andre-inter-collab-llc/research-workflow-assistant/security/advisories/new

**Subject line**: `[SECURITY] RWA - Brief description`

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### What to Expect

- **Acknowledgment** within 48 hours
- **Assessment** within 7 days
- **Fix or mitigation** timeline communicated after assessment
- **Credit** in the changelog and release notes (unless you prefer anonymity)

### Please Do NOT

- Open a public GitHub issue for security vulnerabilities
- Exploit the vulnerability beyond what is necessary to demonstrate it
- Share the vulnerability with others before it has been resolved

## Scope

The following areas are in scope for security reports:

### API Key and Credential Handling
- Exposure of API keys (NCBI, Zotero, OpenAlex, Semantic Scholar, CrossRef) through logs, error messages, or misconfiguration
- Insecure storage or transmission of credentials in `.env` files or MCP server communications

### MCP Server Security
- Injection vulnerabilities in MCP server tool inputs (search queries, DOIs, file paths)
- Path traversal in file-handling tools (Zotero local server, bibliography manager, PRISMA tracker, project tracker)
- Unauthorized file system access beyond intended project directories

### Zotero Integration
- Unauthorized access to Zotero library data
- Leakage of Zotero API keys or user IDs
- Unintended exposure of local Zotero database or PDF contents

### Data Integrity
- Manipulation of PRISMA tracking data
- Tampering with project tracking records or decision logs
- Unauthorized modification of research data or citations

## Out of Scope

- Vulnerabilities in upstream dependencies (report these to the dependency maintainers)
- Vulnerabilities in the Zotero desktop application itself
- Issues requiring physical access to the user's machine
- Social engineering attacks
- Denial of service against external APIs (PubMed, OpenAlex, etc.)

## Security Best Practices for Users

1. **Never commit `.env` files** — they are in `.gitignore` by default
2. **Use the project virtual environment** — never install into the system Python
3. **Keep API keys scoped** — use read-only keys where possible (e.g., Zotero read-only access)
4. **Review AI-generated code** before executing, especially analysis scripts
5. **Keep dependencies updated** — run `pip install --upgrade` periodically within the venv
