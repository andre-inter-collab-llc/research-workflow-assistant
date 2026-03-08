# Research Workflow Assistant

An open-source, modular AI research assistant that runs inside **VS Code + GitHub Copilot**. It connects to academic databases via MCP (Model Context Protocol) servers and encodes research best practices through custom Copilot agents. Built for reproducibility, ICMJE compliance, and human-centered research.

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

### Prerequisites

- [VS Code](https://code.visualstudio.com/) with [GitHub Copilot](https://github.com/features/copilot)
- [Python 3.11+](https://www.python.org/) (for MCP servers)
- [R 4.0+](https://www.r-project.org/) (for analysis templates, optional)
- [Quarto](https://quarto.org/) (for document generation)
- [Zotero](https://www.zotero.org/) (for reference management, optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/research-workflow-assistant.git
cd research-workflow-assistant

# Install Python dependencies (MCP servers)
pip install -e ".[dev]"

# Open in VS Code
code .
```

### Configuration

1. Copy `.vscode/mcp.json` into your research project (or use this repo as a template)
2. Set environment variables for API keys (see [API Setup Guide](docs/api-setup-guide.md)):
   - `NCBI_API_KEY` (PubMed, recommended for higher rate limits)
   - `ZOTERO_API_KEY` and `ZOTERO_USER_ID` (Zotero)
   - `SCOPUS_API_KEY` (Scopus, institutional only)
   - `OPENALEX_EMAIL` (OpenAlex, for polite pool)
3. Restart VS Code to load MCP servers

### Usage

Open Copilot Chat in VS Code and invoke an agent:

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
| OpenAlex | REST API | Free, fully open | Email (polite pool) |
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
