# Conversation Export: Building the Research Workflow Assistant

**Date:** 2026-03-08
**Workspace origin:** `C:\Users\andre\Documents\Automating_Public_Health_Analytics`
**Workspace created:** `C:\Users\andre\Documents\research-workflow-assistant`

This document captures the full design conversation that produced this repository, preserving all decisions, requirements, and architectural choices for continuity.

---

## Message 1: Initial Request

**User asked:** Build an AI-enabled research assistant for PhD-level research work including systematic literature reviews, data analysis, academic writing, report generation, and research planning.

**Tech stack specified:** R/Python, Posit, Quarto, VS Code, GitHub Copilot.

**Critical requirement:** ICMJE authorship guidelines compliance (the AI must never be listed as an author; all AI contributions must be disclosed per ICMJE Section II.A.4).

### Clarification Round

The AI asked 8 clarifying questions. User answers:

1. **Scope:** Open-source for the broader community (not private/personal)
2. **Languages:** Both R and Python
3. **Literature databases:** All major databases + Europe PMC
4. **Architecture:** AI-recommended (resulted in MCP servers + Copilot custom agents)
5. **Disciplines:** Interdisciplinary (not limited to one field)
6. **Reference manager:** Zotero
7. **Repository:** New standalone repo (not inside the course project)
8. **Systematic review standards:** All major standards + user-selectable (PRISMA 2020, PRISMA-ScR, MOOSE, Cochrane handbook)

---

## Message 2: Refinements

User requested two additions:

1. **Project management capabilities**: Track phases, milestones, tasks, decisions, meetings. Generate progress briefs for supervisors/funders.
2. **Broader naming**: Rename from "PhD research assistant" to something not PhD-specific.

### Decisions made:
- **Name chosen:** `research-workflow-assistant`
- **All PM features included:** Phase tracking, milestone management, task management, decision logging, meeting notes with action items, progress brief generation (both markdown and Quarto formats)
- **Brief audience levels:** Team, supervisor, funder (with appropriate detail)
- **PM MCP server:** Project Tracker added as 8th MCP server
- **PM agent:** Project Manager added as 5th custom agent

---

## Message 3: "Start implementation"

User said: "Start implementation." The AI proceeded to build the entire repository systematically.

---

## Architecture Decision: MCP Servers + Copilot Custom Agents

**Chosen over alternatives** (standalone CLI app, web app, VS Code extension):

- MCP (Model Context Protocol) is the open standard for connecting LLMs to external tools
- GitHub Copilot in VS Code supports agent mode with MCP tool calling
- Custom agents (`.agent.md` files) encode specific workflows and compliance rules
- `copilot-instructions.md` provides persistent global context and guardrails
- Modular: each MCP server is independent; users install only what they need
- No custom UI needed; Copilot Chat is the interface

**How it works in practice:**
1. User opens VS Code in a research project
2. User invokes a custom agent (e.g., `@systematic-reviewer`) in Copilot Chat
3. The agent has access to MCP server tools (search PubMed, manage Zotero, track PRISMA)
4. The agent follows encoded workflows (PRISMA 2020, ICMJE rules) while the human makes all decisions
5. Outputs are Quarto documents, R/Python scripts, and structured data files

---

## What Was Built

### Foundation (64 files, 6,531 lines)

| Category | Files | Details |
|----------|-------|---------|
| Config/Foundation | 8 | README.md, copilot-instructions.md, .gitignore, LICENSE (MIT), pyproject.toml, .vscode/mcp.json, .vscode/settings.json, .env.example |
| MCP Servers | 32 | 8 servers x 4 files each (pyproject.toml, __init__.py, __main__.py, server.py) |
| Copilot Agents | 5 | systematic-reviewer, data-analyst, academic-writer, research-planner, project-manager |
| Compliance | 6 | ICMJE checklist, AI disclosure, PRISMA 2020, PRISMA-ScR, MOOSE, Cochrane RoB 2 |
| Templates | 9 | 4 systematic review, 1 IMRaD manuscript, 4 project management |
| Documentation | 4 | getting-started, api-setup-guide, database-access, architecture |

### MCP Servers Detail

| Server | Package | API | Tools | Auth |
|--------|---------|-----|-------|------|
| PubMed | `pubmed-server` | NCBI E-utilities (XML) | 6: search, fetch abstract, MeSH terms, suggest MeSH, related articles, build query | API key (recommended) |
| OpenAlex | `openalex-server` | OpenAlex REST (JSON) | 7: search works, get work, cited-by, references, concepts, author works, search sources | Email (polite pool) |
| Semantic Scholar | `semantic-scholar-server` | S2 Academic Graph (JSON) | 6: search, get paper, citations, references, recommendations, get author | API key (optional) |
| Europe PMC | `europe-pmc-server` | Europe PMC REST (JSON/XML) | 5: search, full text, citations, references, text-mined terms | None |
| CrossRef | `crossref-server` | CrossRef REST (JSON) | 4: search, get by DOI, references by DOI, check DOI (anti-hallucination) | Email (polite pool) |
| Zotero | `zotero-server` | Zotero Web API v3 (JSON) | 9: search, add item, add by DOI, collections, create collection, add to collection, export bibliography, add note, tag item | API key + User ID |
| PRISMA Tracker | `prisma-tracker` | Local file (JSON) | 7: init review, record search, record dedup, record screening, get status, generate diagram (Mermaid), export checklist | None (local) |
| Project Tracker | `project-tracker` | Local file (YAML) | 13: init project, define phases/milestones, update milestone, add/update task, log decision, log meeting, get status, get overdue, generate brief, get decision log, get action items | None (local) |

### Custom Agents Detail

| Agent | File | Purpose | Key MCP Tools |
|-------|------|---------|---------------|
| Systematic Reviewer | `systematic-reviewer.agent.md` | Full systematic review lifecycle (9 phases) | pubmed, openalex, semantic-scholar, europe-pmc, crossref, zotero, prisma-tracker |
| Data Analyst | `data-analyst.agent.md` | Statistical analysis in R and Python | None (uses language runtimes) |
| Academic Writer | `academic-writer.agent.md` | ICMJE-compliant manuscript drafting | zotero, crossref |
| Research Planner | `research-planner.agent.md` | Protocol development, registration, ethics/IRB, grants | pubmed (preliminary searches) |
| Project Manager | `project-manager.agent.md` | Progress tracking, briefs, decisions, meetings | project-tracker |

### ICMJE Compliance Implementation

ICMJE compliance is enforced at three levels:

1. **Global (`copilot-instructions.md`)**: All 4 authorship criteria explained with enforcement rules. AI disclosure requirements. Human-in-the-loop mandate with specific decision points. Audit trail via `ai-contributions-log.md`.

2. **Per-agent (`.agent.md` files)**: Each agent reinforces ICMJE at relevant points. Academic writer starts every session with an authorship reminder. Systematic reviewer requires human decisions at PRISMA stages. Project manager marks all briefs as "AI-assisted."

3. **Compliance documents**: Pre-built checklists and templates in `compliance/` for pre-submission use.

---

## Remaining Work

### Immediate (high priority)

1. **Python environment setup**: Create venv, install MCP servers, verify they start
2. **API key configuration**: `.env` file with real credentials
3. **MCP server testing**: Verify each server connects to its API and returns data
4. **Unit tests**: `tests/` directory is empty; needs pytest tests with mocked API responses

### Medium priority

5. **Analysis templates**: `analysis-templates/R/` and `analysis-templates/python/` are empty
   - Planned: meta-analysis.qmd, descriptive-stats.qmd, survival-analysis.qmd (R)
   - Planned: nlp-screening.py, network-analysis.py (Python)
6. **Report and protocol templates**: `templates/report/` and `templates/research-protocol/` are empty
   - Planned: technical-report.qmd, general protocol.qmd
7. **GitHub remote**: Create GitHub repo and push
8. **CI/CD**: GitHub Actions for linting (ruff), testing (pytest), type checking (mypy)

### Future enhancements

9. **Scopus MCP server** (requires institutional API key from dev.elsevier.com)
10. **Unpaywall MCP server** (free, finds open access PDFs by DOI)
11. **Quarto journal extensions** for common journal formats
12. **Cross-database deduplication** logic in systematic-reviewer agent
13. **Tutorial documents**: "Your first systematic review with the assistant"
14. **R environment management** with renv
15. **Web of Science, CINAHL/PsycINFO** MCP servers (institutional access)

---

## Key Technical Details

### Python Dependencies

All MCP servers use:
- `mcp>=1.0.0` (Model Context Protocol SDK)
- `httpx>=0.27.0` (async HTTP client)
- `pydantic>=2.0.0` (data validation)

Individual servers add:
- PubMed: `defusedxml>=0.7.0` (safe XML parsing)
- PRISMA Tracker: `pyyaml>=6.0`
- Project Tracker: `pyyaml>=6.0`

Dev dependencies: `pytest>=8.0`, `pytest-asyncio`, `ruff`, `mypy`

### Build System

All packages use `hatchling` as the build backend. Each MCP server is a standalone installable package with `pip install -e mcp-servers/<server-name>`.

### MCP Communication

All servers use **stdio transport** (stdin/stdout JSON-RPC). VS Code manages server lifecycle through `.vscode/mcp.json`. Each server is launched as `python -m <package_name>`.

### Environment Variables

Configured in `.env` (gitignored), referenced in `.vscode/mcp.json`:
- `NCBI_API_KEY`, `OPENALEX_EMAIL`, `S2_API_KEY`, `CROSSREF_EMAIL`
- `ZOTERO_API_KEY`, `ZOTERO_USER_ID`
- `PRISMA_PROJECT_DIR`, `PROJECT_TRACKER_DIR`

### File Storage

- PRISMA Tracker: `review-tracking/prisma-flow.json` (JSON)
- Project Tracker: `project-tracking/` directory (YAML files: project.yaml, tasks.yaml, decisions.yaml, meetings/)

---

## Design Principles

1. **ICMJE compliance is non-negotiable**: The human is always the author. AI assists but never decides.
2. **Modular**: Each MCP server is independent. Users install only what they need.
3. **Open source (MIT)**: For broad adoption across NGOs, government, academia, and independent researchers.
4. **Free-tier databases only**: No institutional access required for core functionality.
5. **Human-in-the-loop**: AI presents options; humans decide. All decisions are logged.
6. **Audit trail**: Every AI contribution is trackable for ICMJE compliance and research integrity.
7. **Standard formats**: Quarto for documents, BibTeX for references, YAML/JSON for tracking data.
8. **Both R and Python**: Analysis in whichever language the researcher prefers.

---

## Repository Information

- **Location:** `C:\Users\andre\Documents\research-workflow-assistant`
- **License:** MIT (Andre van Zyl / Intersect Collaborations LLC, 2026)
- **Initial commit:** `1d2219e` on master branch
- **Git status:** Clean (all files committed as of 2026-03-08)
