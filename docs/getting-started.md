# Getting Started

This is the complete setup and orientation guide for the research-workflow-assistant. If you followed the [Quick Start in the README](../README.md#quick-start) and everything worked, you can skip ahead to [Working with Projects](#working-with-projects).

> **Prefer an interactive walkthrough?** Open Copilot Chat in VS Code and type
> `@setup`. It will guide you through every step below — environment
> validation, API key configuration, MCP server verification, and first-project
> creation — in a conversational format.
>
> **Already set up but something broke?** Use `@troubleshooter` for issue diagnosis,
> targeted repair steps, and day-to-day usage guidance.

During setup, RWA now also asks for a default author profile so future reports and manuscripts can start with the correct author metadata. New projects can then override or extend that metadata with project-specific authors.

## Quick Troubleshooting Flow

Follow this when setup appears broken:

1. Run `python scripts/validate_setup.py`
2. Run `python scripts/mcp_smoke_check.py`
3. If either fails, open Command Palette and run `MCP: List Servers`
4. If servers still fail, run `@troubleshooter` and share both script outputs

Decision path:

- No servers in MCP list: check `.vscode/mcp.json`, selected Python interpreter, then restart/reload VS Code
- Servers listed but tools unavailable: open a new Copilot Chat session
- Setup report shows wrong projects root: set `PROJECTS_ROOT=./my_projects` in `.env` and restart MCP servers

## Prerequisites

- [VS Code](https://code.visualstudio.com/) 1.99+ with GitHub Copilot (agent mode enabled)
- [Python](https://www.python.org/downloads/) 3.11 or later
- [R](https://cran.r-project.org/) 4.0+ (optional — for R-based analysis workflows)
- [Quarto](https://quarto.org/docs/get-started/) CLI (optional — for rendering templates)
- [Zotero](https://www.zotero.org/) desktop app (optional — for reference management)
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
pip install -e mcp-servers/zotero-local-server
pip install -e mcp-servers/prisma-tracker
pip install -e mcp-servers/project-tracker
```

> **VS Code task shortcut:** You can also run `Ctrl+Shift+P` → "Tasks: Run Task" → "Install All MCP Servers" to install everything with a single click.

### 3. Configure API keys

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials. Each MCP server **automatically loads** this file on startup, so you do not need to set system-level environment variables.

```ini
# Required for PubMed (increases rate limit from 3/sec to 10/sec)
NCBI_API_KEY=your_key_here

# Required for OpenAlex (free API key)
OPENALEX_API_KEY=your_key_here

# Optional for Semantic Scholar (higher rate limits)
S2_API_KEY=your_key_here

# Recommended for CrossRef (polite pool)
CROSSREF_EMAIL=your@email.com

# Required for Zotero
ZOTERO_API_KEY=your_key_here
# Numeric User ID (NOT your username) — find it at: https://www.zotero.org/settings/keys
ZOTERO_USER_ID=12345678

# Optional: custom directories for tracking data
# PRISMA_PROJECT_DIR=./review-tracking
# PROJECT_TRACKER_DIR=./project-tracking

# Projects root directory (default: ./my_projects)
# Can be an absolute path to store projects elsewhere
PROJECTS_ROOT=./my_projects
```

See [api-setup-guide.md](api-setup-guide.md) for step-by-step instructions on obtaining each key.

### 4. Verify the setup

Open the workspace in VS Code and check that MCP servers start properly:

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Select "MCP: List Servers"
3. All 9 servers should appear and show as available

You can also test individual servers from the terminal:

```bash
python -m pubmed_server --help
```

You can also run the automated validation script:

```bash
python scripts/validate_setup.py
```

> **VS Code task shortcut:** `Ctrl+Shift+P` → "Tasks: Run Task" → "Validate Research Assistant Setup"

For a quick startup check after interpreter/server changes, run:

> `Ctrl+Shift+P` → "Tasks: Run Task" → "MCP Smoke Check (Project Tracker)"

### Troubleshooting

#### MCP servers not connecting to Copilot

The most common reason servers don't appear as tools in Copilot Chat is that `.vscode/mcp.json` is pointing to the wrong Python executable. The `command` field must use your **venv Python** — not just `python`, which may resolve to a system install that doesn't have the MCP packages.

The shipped `mcp.json` already uses the correct path:

```json
"command": "${workspaceFolder}/.venv/Scripts/python"   // Windows
"command": "${workspaceFolder}/.venv/bin/python"        // macOS/Linux
```

If you are on macOS/Linux, edit `.vscode/mcp.json` and change `Scripts/python` to `bin/python` for every server entry.

After editing, restart the MCP servers:

1. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Run **"MCP: List Servers"**
3. Click the **Start** (▶) button next to any stopped server, or use **"MCP: Restart Servers"**

#### Other common issues

| Problem | Solution |
|---------|----------|
| "Module not found" errors | Install the servers: run task "Install All MCP Servers", or `pip install -e mcp-servers/pubmed-server ...` |
| Default interpreter path could not be resolved | Verify `.vscode/settings.json` has `"python.defaultInterpreterPath": ".venv"`. Then run Command Palette → "Python: Select Interpreter" → choose `.venv`. If it still appears once at startup, run "Developer: Reload Window" and select `.venv` again to clear stale cache. |
| Need a quick MCP startup check | Run task "MCP Smoke Check (Project Tracker)". If it fails, use `@troubleshooter` and share the task output. |
| Servers not listed in MCP panel | Verify `.vscode/mcp.json` exists and is valid JSON. Restart VS Code. |
| Server crashes immediately | Run `python -m <server_module>` in terminal (with venv active) to see the error. |
| API keys not loading | The `.env` file must be at the workspace root. Servers auto-load it on startup via `python-dotenv`. |
| Zotero local not detecting data | Set `ZOTERO_DATA_DIR` in `.env` to the folder containing `zotero.sqlite` (e.g., `C:\Users\you\Zotero`). |
| Servers start but tools are "not available" | Open a **new** Copilot Chat session after starting servers. Existing sessions may not pick up newly started servers. |

## Working with Projects

Research projects are stored in a **private projects folder** that is not committed to version control. By default this is the `my_projects/` directory inside the assistant repository.

### Creating a project

Ask any agent to initialize a project, or use `@project-manager` directly:

```
@project-manager Initialize a project called "My Review" in my_projects/my-review.
```

This creates the following structure inside `my_projects/my-review/`:

```
my-review/
  ai-contributions-log.md
  project-config.yaml
  project-tracking/
    project.yaml
    tasks.yaml
    decisions.yaml
  review-tracking/       (if PRISMA tracking is initialized)
    prisma-flow.json
```

When you create a project through `@setup` or `@project-manager`, RWA should also prompt for the authors who will appear on reports or manuscripts from that project. Those details belong in `project-config.yaml` under `research_assistant.authors`, while your reusable personal defaults stay in `.rwa-user-config.yaml` under `default_author`.

Recommended `project-config.yaml` pattern:

```yaml
research_assistant:
  project_type: systematic-review
  reporting_standard: prisma-2020
  authors:
    - name: "Lead Author"
      credentials: "MPH"
      corresponding: true
      email: "author@example.org"
      orcid: "0000-0000-0000-0000"
      affiliation:
        name: "Organization"
        city: "City"
        state: "State / Province"
        country: "Country"
  output_defaults:
    bibliography: references.bib
    csl: apa.csl
    include_rwa_methods_disclosure: true
    include_rwa_acknowledgments: true
```

### Using an external projects folder

If you want projects stored elsewhere (e.g., a OneDrive-synced folder), set `PROJECTS_ROOT` in your `.env`:

```ini
PROJECTS_ROOT=C:\Users\you\OneDrive\Research Projects
```

Relative project paths (like `my-review`) will then resolve under that folder instead of `my_projects/`.

### Switching between projects

Use the project-tracker or prisma-tracker tools to switch context:

```
@project-manager Switch to my-review project.
```

Or pass `project_path` directly to any tool call. Priority order:

1. Explicit `project_path` parameter on the tool call
2. Active project set via `set_active_project` / `set_active_review`
3. Relative paths resolve under `PROJECTS_ROOT` (recommended: `./my_projects`)
4. Legacy fallback: `PROJECT_DIR` / `PRISMA_PROJECT_DIR`

### Listing projects

```
@project-manager List all my projects.
```

This scans `PROJECTS_ROOT` and shows initialized projects with their status.

### Working with external / existing projects

You can point the assistant at any directory on your filesystem by providing an absolute path:

```
@project-manager Set active project to C:\Users\you\Documents\existing-project.
```

The assistant will create `project-tracking/` and `review-tracking/` folders inside that directory for its tracking data.

### Cross-workspace usage

If you work in a separate VS Code workspace, you have two options:

1. **Multi-root workspace** — add both the assistant repo and your project as workspace folders. Use the template at `templates/research-workspace.code-workspace.example`.

2. **Portable MCP config** — copy `templates/portable-mcp-config.json` to your project's `.vscode/mcp.json` and update the paths. This gives your project access to all 9 MCP servers without needing the assistant repo open.

## Using the Agents

### Starting a research workflow

1. Open Copilot Chat in agent mode
2. Tag the agent you need:
  - `@setup` for first-time setup or full environment reconfiguration
   - `@systematic-reviewer` for systematic reviews
   - `@data-analyst` for statistical analysis
   - `@academic-writer` for manuscript drafting
   - `@research-planner` for protocol and planning
   - `@project-manager` for progress tracking
  - `@troubleshooter` for diagnosing errors, fixing environment issues, and usage support

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

The manuscript, protocol, and report templates now assume cite-bearing outputs should include author front matter, `bibliography`, `csl`, a Methods mention of RWA when relevant, and an acknowledgments / AI-disclosure section. Replace placeholders with verified author metadata and references before rendering.

## ICMJE Compliance

This tool enforces ICMJE authorship guidelines. Key points:

- AI tools cannot be listed as authors
- All AI assistance must be disclosed in the Methods section or Acknowledgments
- The `compliance/` folder contains checklists and templates for proper disclosure
- Agents will remind you of these requirements and help generate disclosure statements

See `compliance/ai-disclosure-template.md` for ready-to-use disclosure language.

## Next Steps

- Run `@setup` for a guided interactive setup
- Read [database-access.md](database-access.md) to understand what each database offers
- Read [architecture.md](architecture.md) for a technical overview of the system
- Explore the `compliance/` folder for PRISMA, MOOSE, and RoB 2 checklists
- Try the agents with a sample research question
