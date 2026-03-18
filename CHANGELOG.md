# Changelog

All notable changes to the Research Workflow Assistant (RWA) are documented in this file.

This project uses [Calendar Versioning](https://calver.org/) with the format `YYYY.MM.DD`.
Same-day releases use a `.N` suffix (e.g., `2026.03.18.1`).

A machine-readable mirror of this log is maintained in [versions.yaml](versions.yaml).

## [2026.03.18] — 2026-03-18

Initial public release of the Research Workflow Assistant.

### Added

#### MCP Servers (11 total)
- **pubmed-server**: Search PubMed/MEDLINE via NCBI E-utilities (search, fetch abstracts, MeSH terms, related articles)
- **openalex-server**: Search OpenAlex for works, authors, sources, concepts, citations, and references
- **semantic-scholar-server**: Search Semantic Scholar Academic Graph; get paper details, citations, references, recommendations
- **europe-pmc-server**: Search Europe PMC for biomedical literature; access full text, citations, references, text-mined terms
- **crossref-server**: DOI resolution, metadata verification, reference validation, and scripted search
- **zotero-server**: Manage Zotero reference library via Web API (search, add items, tag, export, notes, annotations, collections)
- **zotero-local-server**: Access local Zotero data — PDF text/annotation extraction, full-text keyword search, Better BibTeX integration
- **bibliography-manager**: Local reference management for non-Zotero users — import BibTeX/RIS, link PDFs, notes, annotations, export for Quarto
- **prisma-tracker**: Track PRISMA 2020 systematic review flow — record searches, screening, deduplication; generate flow diagrams
- **project-tracker**: Track research project phases, milestones, tasks, decisions, meetings; generate progress briefs
- **chat-exporter**: Export Copilot Chat sessions to Quarto Markdown (QMD) files for reproducibility audit trails

#### Shared Library
- **mcp-servers/_shared**: Common utilities shared across all MCP servers (rate limiting, error handling, HTTP client helpers)

#### Custom Copilot Agents (10 total)
- **systematic-reviewer**: Guides PRISMA/PRISMA-ScR/MOOSE/Cochrane systematic reviews end-to-end
- **data-analyst**: Generates reproducible R/Python analysis scripts in Quarto documents
- **academic-writer**: Scaffolds manuscripts, manages citations, drafts sections with ICMJE compliance
- **research-planner**: Helps plan research projects, protocols, ethics applications, study design
- **project-manager**: Phase tracking, milestones, tasks, progress briefs, decision logging, meeting notes
- **critical-reviewer**: Structured critical appraisal using validated checklists (CASP, JBI, STROBE, CONSORT)
- **research-orchestrator**: Orchestrates end-to-end workflows across specialist agents
- **developer**: Resolves bugs, implements features, improves the RWA codebase
- **setup**: Guided first-time configuration — prerequisites, environment, API keys, MCP servers
- **troubleshooter**: Diagnoses environment, configuration, and MCP server issues

#### Compliance Documents (6)
- ICMJE authorship checklist
- AI disclosure template
- PRISMA 2020 checklist
- PRISMA-ScR checklist
- MOOSE checklist
- Cochrane RoB 2 template

#### Templates (12+)
- Systematic review: protocol, manuscript, search strategy, PRISMA flow diagram
- Manuscript: IMRaD format
- Project management: progress brief (Quarto + markdown), meeting notes, decision log
- Critical appraisal: CASP RCT, CASP qualitative, STROBE, cross-study summary
- Analysis: R and Python citation helpers, R summary table
- Project configuration: project-config.yaml, portable MCP config

#### CSL Citation Styles (11)
- APA (7th edition), AMA, BMJ, Chicago (author-date + fullnote), Harvard Cite Them Right, IEEE, NLM, Nature, Vancouver, Vancouver (superscript)

#### Documentation
- Getting started guide
- API setup guide
- Database access reference
- Architecture overview with diagram
- Posit/Quarto ecosystem guide
- Zotero plugins guide
- Quick start guide

#### Infrastructure
- GitHub Actions CI/CD: multi-platform validation (Ubuntu, Windows, macOS) + ruff linting
- Python virtual environment configuration with hatchling build system
- `.vscode/mcp.json` for MCP server configuration
- `.env.example` for API key setup
- Comprehensive `.gitignore` for Python, R, Quarto, and IDE artifacts

#### Versioning & Community Standards
- CalVer versioning scheme (YYYY.MM.DD)
- CHANGELOG.md (human-readable) + versions.yaml (machine-readable) dual changelog
- Local release script (`scripts/release.py`) with backup and tagging
- GitHub Actions release workflow for automated GitHub Releases
- CONTRIBUTING.md with development guidelines
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- SECURITY.md with responsible disclosure policy
- Feature request issue template
- Pull request template

### Notes
- All databases are free-tier (no institutional access required for core functionality)
- ICMJE compliance is enforced globally via `.github/copilot-instructions.md`
- Python 3.11+ required; R optional (for analysis templates only)
- License: MIT
