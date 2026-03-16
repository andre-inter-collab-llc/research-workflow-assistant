# Posit / Quarto Ecosystem Guide

This guide explains why [Quarto](https://quarto.org/) is the default output layer for the Research Workflow Assistant (RWA) and how the broader [Posit](https://posit.co/) ecosystem fits into research workflows.

## Why Quarto?

Quarto is the **default document format** for all RWA outputs — manuscripts, protocols, reports, analysis scripts, dashboards, and progress briefs. Every template in `templates/` is a `.qmd` (Quarto Markdown) file.

### Key Capabilities

| Feature | Benefit for Researchers |
|---------|----------------------|
| **Multi-language** | Execute R and Python code in the same document |
| **Multi-format** | Render to HTML, PDF, Word, PowerPoint, dashboards, websites, books, and Revealjs slides from one source |
| **Native citations** | Built-in bibliography support via Pandoc citeproc — works with `.bib`, CSL-JSON, and Zotero |
| **Native Mermaid diagrams** | Create PRISMA flows, flowcharts, Gantt charts, and concept maps with ` ```{mermaid} ` code blocks — no external tools needed |
| **Cross-references** | Label and reference figures (`@fig-`), tables (`@tbl-`), sections (`@sec-`), and equations (`@eq-`) |
| **Code execution** | Run analysis code inline — results update automatically when data changes |
| **Parameterized reports** | Generate variations of a report by changing YAML parameters |
| **Journal extensions** | Format manuscripts for specific journals using [Quarto journal templates](https://quarto.org/docs/extensions/listing-journals.html) |

### Why Not Plain Markdown?

Plain `.md` files cannot execute code, cross-reference figures, or render to multiple output formats. Quarto extends Markdown with computation, citation management, and publishing features while remaining a plain-text format that works with Git version control.

## Installing Quarto

1. Download the Quarto CLI from [quarto.org/docs/get-started](https://quarto.org/docs/get-started/)
2. Install it (Windows installer, macOS pkg, or Linux deb/tarball)
3. Verify: `quarto check` in your terminal

For PDF output, you also need a LaTeX distribution:
```bash
quarto install tinytex    # lightweight LaTeX — recommended
```

## The Posit Ecosystem

[Posit](https://posit.co/) (formerly RStudio, PBC) develops open-source tools for data science. RWA recommends Posit tools because they are designed for reproducible research and support both R and Python.

### IDEs

| IDE | Best For |
|-----|----------|
| **[Positron](https://positron.posit.co/)** | VS Code-based IDE with native R + Python support, data viewer, and Quarto integration. Recommended if you want a Posit IDE that feels like VS Code. |
| **[RStudio](https://posit.co/download/rstudio-desktop/)** | The classic R IDE. Excellent Quarto support, visual markdown editor, integrated R console. Recommended for R-heavy workflows. |
| **VS Code** | RWA's primary environment. Works with Quarto via the [Quarto extension](https://marketplace.visualstudio.com/items?itemName=quarto.quarto). |

### Key Posit Packages Used by RWA

| Package | Language | Purpose in RWA |
|---------|----------|---------------|
| **Quarto** | CLI | Document rendering, publishing |
| **`gtsummary`** | R | Default package for publication-ready summary tables |
| **`gt`** | R | Table rendering engine (used by gtsummary) |
| **`great_tables`** | Python | Default summary table package for Python users |
| **`shiny`** | R / Python | Interactive dashboards (optional) |
| **`renv`** | R | R package environment management (reproducibility) |
| **`reticulate`** | R | Use Python from R (mixed-language documents) |

### Non-Posit Alternatives

RWA recommends Posit tools as defaults but does not require them:

- **Tables (R):** `flextable`, `kableExtra`, `huxtable`
- **Tables (Python):** `itables` (interactive HTML), `tabulate`
- **Diagrams:** Graphviz, D2, PlantUML (instead of Mermaid)
- **Documents:** Jupyter Notebooks, R Markdown (`.Rmd`) — but `.qmd` is preferred

## Output Formats

Quarto renders `.qmd` files to multiple formats. RWA templates default to `format: html` but support all of these:

| Format | YAML Key | When to Use |
|--------|----------|-------------|
| **HTML** | `html` | Default. Interactive, self-contained, shareable. Best for working drafts and web publishing. |
| **PDF** | `pdf` | Formal submissions, print. Requires LaTeX (`quarto install tinytex`). |
| **Word** | `docx` | Journal submissions, collaborative editing with non-technical reviewers. |
| **PowerPoint** | `pptx` | Conference presentations, stakeholder briefings. |
| **Revealjs** | `revealjs` | Web-based slide decks. |
| **Dashboard** | `dashboard` | Interactive data dashboards (Quarto 1.4+). |
| **Website** | `website` | Multi-page project websites. |
| **Book** | `book` | Multi-chapter documents (dissertations, technical manuals). |

### Multi-Format Output

Generate multiple formats from one source:

```yaml
---
title: "My Report"
format:
  html:
    toc: true
    self-contained: true
  pdf:
    toc: true
  docx: default
---
```

Render all formats: `quarto render report.qmd`
Render one format: `quarto render report.qmd --to pdf`

## Mermaid Diagrams in Quarto

Quarto supports [Mermaid](https://mermaid.js.org/) diagrams natively — no extensions or JavaScript dependencies needed. RWA uses Mermaid as the default diagram tool.

### Supported Diagram Types

```{mermaid}
%%| label: fig-example
%%| fig-cap: "Example flowchart using Mermaid in Quarto"
flowchart LR
    A[Research Question] --> B[Search Strategy]
    B --> C[Database Searching]
    C --> D[Screening]
    D --> E[Data Extraction]
    E --> F[Synthesis]
    F --> G[Manuscript]
```

- **Flowcharts** — PRISMA flows, study selection, workflows
- **Sequence diagrams** — Process interactions
- **Gantt charts** — Project timelines
- **Mind maps** — Concept mapping
- **Entity-relationship diagrams** — Data models

### Example: PRISMA Flow

```{mermaid}
flowchart TD
    A["Records identified (n = 500)"] --> B["Duplicates removed (n = 50)"]
    B --> C["Screened (n = 450)"]
    C --> D["Excluded (n = 350)"]
    C --> E["Full-text assessed (n = 100)"]
    E --> F["Excluded (n = 60)"]
    E --> G["Included (n = 40)"]
```

## Citation Management

Quarto uses Pandoc's citeproc for citations. The workflow:

1. **Maintain a `.bib` file** — export from Zotero, or use the RWA result store's `export_results_bibtex()` function
2. **Reference it in YAML** — `bibliography: references.bib`
3. **Cite in text** — `[@smith2024]`, `[@smith2024; @jones2023]`, or `@smith2024`
4. **Apply a style** — `csl: apa.csl` (or any [CSL style](https://www.zotero.org/styles))

Zotero users with Better BibTeX get stable, auto-updating `.bib` files that sync with their Quarto documents.

## Cross-References

Label and reference elements for professional documents:

```markdown
@fig-prisma shows the study selection process.
@tbl-demographics summarizes participant characteristics.
As discussed in @sec-methods, we used a mixed-methods approach.
```

Label figures, tables, and sections with the `#` prefix:

```markdown
::: {#fig-prisma}
```{mermaid}
flowchart TD
    ...
```
PRISMA 2020 flow diagram.
:::

| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |

: Summary statistics {#tbl-demographics}
```

## Quarto Extensions for Researchers

Useful extensions for academic workflows:

- **Journal templates**: `quarto use template quarto-journals/<journal>` — formats for PLOS, Elsevier, JASA, Springer, and more
- **Lightbox**: `quarto add quarto-ext/lightbox` — click-to-zoom images
- **Fancy letters**: Drop caps and decorative elements for reports

Browse extensions: [quarto.org/docs/extensions](https://quarto.org/docs/extensions/)

## Getting Help

- [Quarto documentation](https://quarto.org/docs/guide/)
- [Quarto GitHub discussions](https://github.com/quarto-dev/quarto-cli/discussions)
- [Posit Community](https://community.rstudio.com/)
- In RWA: Ask `@troubleshooter` for Quarto rendering issues
