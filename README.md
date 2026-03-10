# Research Workflow Assistant

An open-source, modular AI research assistant that runs inside **[VS Code](https://code.visualstudio.com/) + [GitHub Copilot](https://github.com/features/copilot)**. It connects to academic databases via MCP (Model Context Protocol) servers and encodes research best practices through custom Copilot agents. Built for reproducibility, ICMJE compliance, and human-centered research.

> **Model note:** This project was developed and tested using **Claude Opus 4.6** in GitHub Copilot agent mode. Other models available in Copilot ([model comparison](https://docs.github.com/en/copilot/reference/ai-models/model-comparison)) may work but have not been validated with these agents and instructions. If you experience issues with a different model, try switching to Claude Opus 4.6 in the Copilot model picker.

> **First time here?** Jump straight to the [Quick Start](#quick-start) below,
> or open Copilot Chat and type `@setup` for an interactive guided setup.
> If setup is complete and something is not working, use `@troubleshooter` for diagnostics and issue resolution.
> For the full walkthrough, see [docs/getting-started.md](docs/getting-started.md).

## Who Is This For?

Any researcher who wants AI-assisted support without surrendering intellectual ownership:

- **NGO and public sector researchers** managing evidence reviews or program evaluations
- **Government analysts** producing policy briefs backed by systematic evidence
- **Academic faculty and postdocs** running systematic reviews or multi-study projects
- **Independent researchers and consultants** needing structured, reproducible workflows
- **Research organizations** wanting standardized, auditable research processes

No PhD required. If you do research, this tool is for you.

## What It Does

| Capability | How |
|---|---|
| **Systematic literature reviews** | `@systematic-reviewer` agent guides PRISMA-compliant workflows: question refinement (PICO/PEO/SPIDER), search strategy development, database searching, screening, data extraction, risk of bias |
| **Academic database access** | MCP servers for PubMed, OpenAlex, Semantic Scholar, Europe PMC, CrossRef, Scopus (institutional) |
| **Reference management** | Zotero MCP server: search library, add items by DOI, tag, organize collections, export BibTeX |
| **Data analysis** | `@data-analyst` agent generates reproducible R or Python analysis scripts in Quarto documents |
| **Academic writing** | `@academic-writer` agent scaffolds IMRaD manuscripts, manages citations, enforces ICMJE AI disclosure |
| **Research planning** | `@research-planner` agent helps with protocols, ethics applications, study design, grant writing |
| **Project management** | `@project-manager` agent tracks phases, milestones, tasks, decisions; generates progress briefs for colleagues |
| **Troubleshooting and support** | `@troubleshooter` agent diagnoses environment and MCP issues, validates API keys, and provides practical how-to help for day-to-day RWA usage |
| **ICMJE compliance** | Built into every agent: human-in-the-loop mandate, audit trail, AI disclosure generation, authorship checklist |

## Architecture

```
You (researcher)
  |
  v
VS Code + GitHub Copilot Chat
  |
  |-- @systematic-reviewer    (agent: guides review workflow)
  |-- @data-analyst            (agent: statistical analysis)
  |-- @academic-writer         (agent: manuscript drafting)
  |-- @research-planner        (agent: study design, protocols)
  |-- @project-manager         (agent: tracking, briefs, decisions)
  |-- @troubleshooter          (agent: diagnostics, fixes, usage help)
  |
  |-- MCP Servers (tools available to all agents):
  |     |-- pubmed-server          (NCBI E-utilities)
  |     |-- openalex-server        (OpenAlex REST API)
  |     |-- semantic-scholar-server (S2 Academic Graph API)
  |     |-- europe-pmc-server      (Europe PMC REST API)
  |     |-- crossref-server        (CrossRef/DOI metadata)
  |     |-- zotero-server          (Zotero Web API v3)
  |     |-- prisma-tracker         (local PRISMA flow tracking)
  |     |-- project-tracker        (local project management)
  |
  v
Outputs: Quarto documents, R/Python scripts, PRISMA diagrams,
         progress briefs, structured data files
```

## ICMJE Compliance: You Are the Author

This tool is designed around the [ICMJE authorship criteria](https://www.icmje.org/recommendations/browse/roles-and-responsibilities/defining-the-role-of-authors-and-contributors.html). AI cannot be an author. You must meet all four criteria:

1. **Substantial contributions** to conception, design, data acquisition, analysis, or interpretation
2. **Drafting or critically revising** the work for important intellectual content
3. **Final approval** of the version to be published
4. **Accountability** for all aspects of the work

The tool enforces this by:
- Requiring human decisions at every substantive step
- Tracking AI contributions in an audit trail (`ai-contributions-log.md`)
- Generating ICMJE-compliant AI disclosure statements for your manuscripts
- Refusing to finalize outputs without explicit human review

Per ICMJE Section II.A.4: AI use must be disclosed in acknowledgments (writing assistance) and methods (data analysis). This tool generates those disclosures for you.

## Quick Start

> **Prefer a guided setup?** Open Copilot Chat and type `@setup`. It will
> walk you through every step interactively.

### Prerequisites

| Requirement | Notes |
|---|---|
| [VS Code](https://code.visualstudio.com/) 1.99+ with [GitHub Copilot](https://github.com/features/copilot) | Agent mode must be enabled |
| [Python 3.11+](https://www.python.org/) | Required — runs the MCP servers |
| [R 4.0+](https://www.r-project.org/) | Optional — for R-based analysis templates |
| [Quarto](https://quarto.org/) | Optional — for rendering document templates |
| [Zotero](https://www.zotero.org/) | Optional — for reference management |

### Step 1 — Clone and open the repo

```bash
git clone https://github.com/yourusername/research-workflow-assistant.git
cd research-workflow-assistant
code .
```

### Step 2 — Create a Python environment and install MCP servers

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# Install all 8 MCP servers in development mode
pip install -e mcp-servers/pubmed-server \
            -e mcp-servers/openalex-server \
            -e mcp-servers/semantic-scholar-server \
            -e mcp-servers/europe-pmc-server \
            -e mcp-servers/crossref-server \
            -e mcp-servers/zotero-server \
            -e mcp-servers/prisma-tracker \
            -e mcp-servers/project-tracker

# Install dev tools (linting, testing)
pip install -e ".[dev]"
```

### Step 3 — Configure API keys

```bash
# Copy the example env file
cp .env.example .env          # macOS / Linux
copy .env.example .env        # Windows
```

Open `.env` and add your credentials. At minimum:

| Key | Where to get it | Required? |
|---|---|---|
| `NCBI_API_KEY` | [NCBI account settings](https://www.ncbi.nlm.nih.gov/account/settings/) | Recommended |
| `OPENALEX_API_KEY` | [OpenAlex API key settings](https://openalex.org/settings/api-key) | Recommended |
| `ZOTERO_API_KEY` | [Zotero key settings](https://www.zotero.org/settings/keys) | If using Zotero |
| `ZOTERO_USER_ID` | Numeric ID shown at the top of the [Zotero keys page](https://www.zotero.org/settings/keys) (not your username) | If using Zotero |

Full details: [docs/api-setup-guide.md](docs/api-setup-guide.md)

### Step 4 — Verify everything works

```bash
python scripts/validate_setup.py
```

Or in VS Code: **Ctrl+Shift+P** → "MCP: List Servers" — all 8 servers should appear.

### Step 5 — Start using it

Open Copilot Chat and try an agent:

```
@project-manager Initialize a new project called "my-first-review" in my_projects/my-first-review.
```

See [docs/getting-started.md](docs/getting-started.md) for the full guide, including project setup, multi-project workflows, and cross-workspace usage.

### Usage examples

```
@systematic-reviewer I want to conduct a systematic review on the effectiveness
of community health worker interventions for maternal mental health in low- and
middle-income countries.
```

```
@project-manager Initialize a new project for my systematic review. Target
completion is September 2026.
```

```
@data-analyst I have extracted data from 23 studies. Help me set up a
random-effects meta-analysis using the metafor package in R.
```

## Project Structure

```
research-workflow-assistant/
├── .github/
│   ├── copilot-instructions.md      # ICMJE + research integrity rules
│   └── agents/                      # Custom Copilot agents
├── .vscode/
│   ├── settings.json
│   └── mcp.json                     # MCP server configuration
├── mcp-servers/                     # MCP server implementations (Python)
│   ├── pubmed-server/
│   ├── openalex-server/
│   ├── semantic-scholar-server/
│   ├── europe-pmc-server/
│   ├── crossref-server/
│   ├── zotero-server/
│   ├── prisma-tracker/
│   └── project-tracker/
├── templates/                       # Quarto templates
│   ├── systematic-review/
│   ├── manuscript/
│   ├── report/
│   └── project-management/
├── analysis-templates/              # Reusable R/Python analysis templates
├── compliance/                      # ICMJE checklists, reporting standards
├── docs/                            # User documentation
└── tests/
```

## Database Access

| Database | API | Access | Auth |
|---|---|---|---|
| PubMed/MEDLINE | NCBI E-utilities | Free | API key (recommended) |
| OpenAlex | REST API | Free ($1/day budget) | API key (free) |
| Semantic Scholar | Academic Graph API | Free (rate limited) | API key (optional) |
| Europe PMC | REST API | Free | None |
| CrossRef | REST API | Free | Email (polite pool) |
| Zotero | Web API v3 | Free | API key |
| Scopus | Elsevier API | Institutional | API key |

Databases without APIs (CINAHL, PsycINFO, Web of Science, Google Scholar, Cochrane Library): the agents help you build database-specific queries, but you run the searches manually and import results.

## Reporting Standards

The tool supports multiple systematic review reporting standards (user selects):
- **PRISMA 2020** (systematic reviews with meta-analysis)
- **PRISMA-ScR** (scoping reviews)
- **MOOSE** (meta-analyses of observational studies)
- **Cochrane Handbook** methods

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)

## Acknowledgments

- [ICMJE](https://www.icmje.org/) for authorship and AI disclosure guidelines
- [PRISMA](http://www.prisma-statement.org/) for systematic review reporting standards
- [MCP](https://modelcontextprotocol.io/) for the Model Context Protocol specification
- [Quarto](https://quarto.org/) for scientific publishing
- [Posit](https://posit.co/) for the R ecosystem
- Built with [GitHub Copilot](https://github.com/features/copilot) using [Claude Opus 4.6](https://docs.github.com/en/copilot/reference/ai-models/model-comparison) by Anthropic
