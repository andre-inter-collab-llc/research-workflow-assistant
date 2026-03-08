# Getting Started

This guide walks you through setting up the research-workflow-assistant in VS Code.

## Prerequisites

- [VS Code](https://code.visualstudio.com/) 1.99+ with GitHub Copilot (agent mode enabled)
- [Python](https://www.python.org/downloads/) 3.11 or later
- [R](https://cran.r-project.org/) 4.0+ (for R-based analysis workflows)
- [Quarto](https://quarto.org/docs/get-started/) CLI
- [Zotero](https://www.zotero.org/) desktop app (for reference management)
- A GitHub Copilot subscription with chat access

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/research-workflow-assistant.git
cd research-workflow-assistant
```

### 2. Install MCP servers

Each MCP server is a standalone Python package. Install them in development mode:

```bash
# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install all MCP servers
pip install -e mcp-servers/pubmed-server
pip install -e mcp-servers/openalex-server
pip install -e mcp-servers/semantic-scholar-server
pip install -e mcp-servers/europe-pmc-server
pip install -e mcp-servers/crossref-server
pip install -e mcp-servers/zotero-server
pip install -e mcp-servers/prisma-tracker
pip install -e mcp-servers/project-tracker
```

### 3. Configure API keys

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```ini
# Required for PubMed (increases rate limit from 3/sec to 10/sec)
NCBI_API_KEY=your_key_here

# Recommended for OpenAlex (polite pool, faster responses)
OPENALEX_EMAIL=your@email.com

# Optional for Semantic Scholar (higher rate limits)
S2_API_KEY=your_key_here

# Recommended for CrossRef (polite pool)
CROSSREF_EMAIL=your@email.com

# Required for Zotero
ZOTERO_API_KEY=your_key_here
ZOTERO_USER_ID=your_user_id

# Optional: custom directories for tracking data
PRISMA_PROJECT_DIR=./review-tracking
PROJECT_TRACKER_DIR=./project-tracking
```

See [api-setup-guide.md](api-setup-guide.md) for step-by-step instructions on obtaining each key.

### 4. Verify the setup

Open the workspace in VS Code and check that MCP servers start properly:

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Select "MCP: List Servers"
3. All 8 servers should appear and show as available

You can also test individual servers from the terminal:

```bash
python -m pubmed_server --help
```

## Using the Agents

### Starting a research workflow

1. Open Copilot Chat in agent mode
2. Tag the agent you need:
   - `@systematic-reviewer` for systematic reviews
   - `@data-analyst` for statistical analysis
   - `@academic-writer` for manuscript drafting
   - `@research-planner` for protocol and planning
   - `@project-manager` for progress tracking

### Example: Starting a systematic review

```
@systematic-reviewer I want to conduct a systematic review on the effectiveness 
of mobile health interventions for maternal mental health in low-income countries. 
Help me develop a PICO framework and search strategy.
```

### Example: Tracking a project

```
@project-manager Initialize a new project called "mHealth Maternal Mental Health Review" 
with phases for protocol, searching, screening, extraction, synthesis, and writing. 
The target completion date is 2026-03-01.
```

### Example: Analyzing extracted data

```
@data-analyst I have extracted data from 23 studies on intervention effectiveness. 
Help me conduct a random-effects meta-analysis using R with the metafor package.
```

## Using Templates

Templates are in the `templates/` directory. Copy one to start your work:

```bash
# Start a new systematic review protocol
cp templates/systematic-review/protocol.qmd my-review/protocol.qmd

# Start a manuscript
cp templates/manuscript/imrad.qmd my-paper/manuscript.qmd
```

Render with Quarto:

```bash
quarto render my-review/protocol.qmd --to docx
```

## ICMJE Compliance

This tool enforces ICMJE authorship guidelines. Key points:

- AI tools cannot be listed as authors
- All AI assistance must be disclosed in the Methods section or Acknowledgments
- The `compliance/` folder contains checklists and templates for proper disclosure
- Agents will remind you of these requirements and help generate disclosure statements

See `compliance/ai-disclosure-template.md` for ready-to-use disclosure language.

## Next Steps

- Read [database-access.md](database-access.md) to understand what each database offers
- Read [architecture.md](architecture.md) for a technical overview of the system
- Explore the `compliance/` folder for PRISMA, MOOSE, and RoB 2 checklists
- Try the agents with a sample research question
