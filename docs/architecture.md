# Architecture

This document describes the technical architecture of the research-workflow-assistant.

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                      VS Code                             │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              GitHub Copilot (Agent Mode)           │   │
│  │                                                    │   │
│  │  ┌────────────────┐  ┌──────────────────────────┐ │   │
│  │  │ copilot-        │  │    Custom Agents          │ │   │
│  │  │ instructions.md │  │  ┌────────────────────┐  │ │   │
│  │  │ (ICMJE rules,   │  │  │ systematic-reviewer│  │ │   │
│  │  │  global policy)  │  │  │ data-analyst       │  │ │   │
│  │  └────────────────┘  │  │ academic-writer     │  │ │   │
│  │                       │  │ research-planner    │  │ │   │
│  │                       │  │ project-manager     │  │ │   │
│  │                       │  └────────────────────┘  │ │   │
│  │                       └──────────────────────────┘ │   │
│  └──────────────┬───────────────────────────────────┘   │
│                  │  MCP Protocol (stdio)                  │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │              MCP Servers (Python)                   │   │
│  │                                                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │   │
│  │  │ PubMed   │ │ OpenAlex │ │ Semantic Scholar   │ │   │
│  │  └──────────┘ └──────────┘ └────────────────────┘ │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │   │
│  │  │Europe PMC│ │ CrossRef │ │ Zotero             │ │   │
│  │  └──────────┘ └──────────┘ └────────────────────┘ │   │
│  │  ┌──────────────────┐ ┌──────────────────────────┐ │   │
│  │  │ PRISMA Tracker   │ │ Project Tracker          │ │   │
│  │  └──────────────────┘ └──────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
   External APIs                  Local File System
   (PubMed, OpenAlex,            (YAML/JSON tracking,
    S2, EPMC, CrossRef,           Zotero library,
    Zotero Web API)               templates, outputs)
```

## Components

### 1. Global Instructions (`.github/copilot-instructions.md`)

The global instructions file is loaded by Copilot for every interaction. It enforces:

- **ICMJE authorship compliance**: AI cannot be listed as an author; all AI assistance must be disclosed
- **Human-in-the-loop mandate**: AI suggests, humans decide
- **Audit trail requirements**: AI contributions are logged to `ai-contributions-log.md`
- **Citation integrity**: All references must be verified via DOI before inclusion
- **Rate limiting awareness**: Respect API rate limits across all database servers

### 2. Custom Agents (`.github/agents/`)

Each agent encodes a specialized research workflow:

| Agent | Purpose | MCP Tools Used |
|-------|---------|---------------|
| `systematic-reviewer` | Full systematic review lifecycle | pubmed, openalex, semantic-scholar, europe-pmc, crossref, zotero, prisma-tracker |
| `data-analyst` | Statistical analysis (R and Python) | None (uses language runtimes) |
| `academic-writer` | Manuscript drafting with ICMJE compliance | zotero, crossref |
| `research-planner` | Protocol development and registration | pubmed (for preliminary searches) |
| `project-manager` | Progress tracking and reporting | project-tracker |

Agents inherit global instructions and add role-specific behavior, tool restrictions, and workflow sequences.

### 3. MCP Servers (`mcp-servers/`)

MCP (Model Context Protocol) servers expose tools that Copilot agents can call. Each server is a standalone Python package using the `mcp` SDK.

#### Server Communication

All servers use **stdio transport** (stdin/stdout JSON-RPC). VS Code manages server lifecycle via `.vscode/mcp.json`.

#### Server Structure

Each server follows the same pattern:

```
mcp-servers/<server-name>/
├── pyproject.toml          # Package metadata and dependencies
└── src/<package_name>/
    ├── __init__.py          # Package initialization
    ├── __main__.py          # Entry point (runs the server)
    └── server.py            # Tool definitions and API logic
```

#### Database Servers

**PubMed Server** (`pubmed-server`)
- API: NCBI E-utilities (REST/XML)
- Auth: Optional API key (NCBI_API_KEY)
- Tools: search, fetch abstract, MeSH terms, related articles, query builder

**OpenAlex Server** (`openalex-server`)
- API: OpenAlex REST (JSON)
- Auth: Email for polite pool (OPENALEX_EMAIL)
- Tools: search works, citation traversal, concept exploration, author works

**Semantic Scholar Server** (`semantic-scholar-server`)
- API: Semantic Scholar Academic Graph (JSON)
- Auth: Optional API key (S2_API_KEY)
- Tools: search, paper details, citations, AI-powered recommendations

**Europe PMC Server** (`europe-pmc-server`)
- API: Europe PMC REST (JSON/XML)
- Auth: None required
- Tools: search, full text retrieval, text mining (genes, diseases, chemicals)

**CrossRef Server** (`crossref-server`)
- API: CrossRef REST (JSON)
- Auth: Email for polite pool (CROSSREF_EMAIL)
- Tools: search, DOI lookup, DOI validation (anti-hallucination)

**Zotero Server** (`zotero-server`)
- API: Zotero Web API v3 (JSON)
- Auth: API key + User ID (ZOTERO_API_KEY, ZOTERO_USER_ID)
- Tools: search, add items, collections, bibliography export, notes, tags

#### Tracking Servers

**PRISMA Tracker** (`prisma-tracker`)
- Storage: JSON file (`review-tracking/prisma-flow.json`)
- Purpose: Track systematic review progress through PRISMA stages
- Tools: Initialize review, record search/screening results, generate PRISMA flow diagram (Mermaid), export checklists

**Project Tracker** (`project-tracker`)
- Storage: YAML files in `project-tracking/` directory
- Purpose: Research project management with phases, milestones, tasks
- Tools: Phase/milestone/task management, decision logging, meeting notes, progress briefs (markdown or Quarto)

### 4. Compliance Framework (`compliance/`)

Pre-built checklists and templates:

| Document | Standard |
|----------|----------|
| `icmje-authorship-checklist.md` | ICMJE 4-criteria authorship verification |
| `ai-disclosure-template.md` | ICMJE Section II.A.4 AI disclosure language |
| `prisma-2020-checklist.md` | PRISMA 2020 (27-item) |
| `prisma-scr-checklist.md` | PRISMA-ScR (22-item) |
| `moose-checklist.md` | MOOSE (35-item) |
| `cochrane-rob2-template.md` | Cochrane Risk of Bias 2.0 |

### 5. Templates (`templates/`)

Quarto and Markdown templates organized by use case:

```
templates/
├── systematic-review/
│   ├── protocol.qmd          # PROSPERO-format review protocol
│   ├── manuscript.qmd        # PRISMA 2020 systematic review manuscript
│   ├── search-strategy.qmd   # Documented search strategy
│   └── prisma-flow.qmd       # PRISMA flow diagram (Mermaid)
├── manuscript/
│   └── imrad.qmd             # Standard IMRaD manuscript
└── project-management/
    ├── progress-brief.qmd    # Formatted progress brief
    ├── progress-brief-simple.md  # Quick markdown brief
    ├── meeting-notes.qmd     # Meeting notes template
    └── decision-log.qmd      # Decision log template
```

## Data Flow

### Systematic Review Workflow

```
1. Planning
   research-planner → protocol.qmd template

2. Searching
   systematic-reviewer → PubMed, OpenAlex, S2, EPMC servers
                       → Zotero server (store results)
                       → PRISMA tracker (record searches)

3. Screening
   systematic-reviewer → PRISMA tracker (record decisions)
                       → Zotero server (tag included/excluded)

4. Analysis
   data-analyst → Local R/Python scripts
               → metafor, meta (R) or statsmodels (Python)

5. Writing
   academic-writer → manuscript.qmd template
                   → Zotero server (export bibliography)
                   → CrossRef server (verify DOIs)
                   → compliance/ (ICMJE checklist, AI disclosure)

6. Management (throughout)
   project-manager → Project tracker (milestones, tasks, briefs)
```

### File-Based State

The PRISMA tracker and Project tracker use local file storage:

- `review-tracking/prisma-flow.json`: PRISMA flow state (created per review)
- `project-tracking/project.yaml`: Project definition and status
- `project-tracking/decisions.yaml`: Decision log
- `project-tracking/meetings.yaml`: Meeting notes and action items

This keeps all state local, version-controllable, and independent of external services.

## Security Considerations

- API keys are stored in `.env` (gitignored) and referenced via environment variables in `.vscode/mcp.json`
- No credentials are hardcoded in server code
- Servers use HTTPS for all external API calls
- Rate limiting is respected per API provider guidelines
- User data stays local; no telemetry or external data transmission beyond API calls
