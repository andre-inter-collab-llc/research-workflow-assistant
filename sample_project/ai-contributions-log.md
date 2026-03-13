# AI Contributions Log

This log tracks all substantive AI contributions to this research project,
in compliance with ICMJE recommendations on AI-assisted technology disclosure.

> **Note:** This is a demo project. The entries below illustrate how RWA tracks
> AI contributions throughout a real systematic review workflow.

## Log Entries

### 2026-03-01 10:15 — research-orchestrator — PROJECT_MANAGEMENT
**Action**: Orchestrated the end-to-end workflow for a systematic review on CHW interventions for maternal mental health in LMICs. Routed tasks to specialist agents in sequence: research-planner → systematic-reviewer → data-analyst → academic-writer → project-manager.
**Human Decision**: Approved the systematic review topic, PICO framework, and PRISMA 2020 as the reporting standard.
**Files Affected**: `project-config.yaml`
**Notes**: User prompt: *"I want to conduct a systematic review on the effectiveness of community health worker interventions for maternal mental health in low- and middle-income countries."*

### 2026-03-01 10:30 — project-manager — PROJECT_MANAGEMENT
**Action**: Initialized the project with phase definitions, milestones, and task breakdown. Set target completion to September 2026.
**Human Decision**: Approved six-month timeline with monthly milestones.
**Files Affected**: `project-config.yaml`, `progress-brief.qmd`
**Notes**: User prompt: *"Initialize a new project for my systematic review. Target completion is September 2026."*

### 2026-03-01 11:00 — research-planner — SEARCH_STRATEGY
**Action**: Developed PICO framework, concept decomposition with MeSH terms and free-text synonyms, and Boolean query structure for maternal mental health + CHW + LMIC search.
**Human Decision**: Approved PICO elements and concept terms. Added "task-shifting" as additional synonym.
**Files Affected**: `protocol.qmd`, `search-strategy.qmd`
**Notes**: Planner identified six databases for searching and recommended PROSPERO registration.

### 2026-03-02 09:00 — systematic-reviewer — DATABASE_SEARCH
**Action**: Executed searches across PubMed, OpenAlex, Semantic Scholar, Europe PMC, and CrossRef using MCP server tools. Retrieved 1,247 total records across all databases.
**Human Decision**: Approved search strategies before execution. Confirmed date range (2005–2026) and language filter (English).
**Files Affected**: `search-strategy.qmd`, `literature-review-evidence.md`
**Notes**: All searches are reproducible via web interfaces. Query strings and result counts documented in search-strategy.qmd.

### 2026-03-02 14:00 — systematic-reviewer — SCREENING_SUPPORT
**Action**: Presented deduplicated records (935 after removing 312 duplicates) organized by relevance for title/abstract screening. Provided structured summaries of each record.
**Human Decision**: Screened all 935 records. Excluded 847 at title/abstract stage. Advanced 88 to full-text review.
**Files Affected**: `prisma-flow.qmd`, `literature-review-evidence.md`
**Notes**: All inclusion/exclusion decisions were made by the human reviewer. AI presented information only.

### 2026-03-05 10:00 — systematic-reviewer — SCREENING_SUPPORT
**Action**: Organized 88 full-text articles for eligibility assessment. Presented structured extraction of study design, population, intervention, and outcomes for each.
**Human Decision**: Included 23 studies in qualitative synthesis after full-text review. Excluded 65 with documented reasons (wrong population: 18, wrong intervention: 22, wrong outcome: 12, wrong study design: 8, duplicates: 5).
**Files Affected**: `prisma-flow.qmd`, `literature-review-evidence.md`
**Notes**: PRISMA flow diagram updated with final numbers.

### 2026-03-05 15:00 — systematic-reviewer — PRISMA_TRACKING
**Action**: Updated PRISMA flow diagram with complete screening numbers and exclusion reasons.
**Human Decision**: Verified all numbers match screening records.
**Files Affected**: `prisma-flow.qmd`
**Notes**: Flow diagram is PRISMA 2020 compliant.

### 2026-03-07 09:00 — systematic-reviewer — DATA_EXTRACTION
**Action**: Generated data extraction form template and assisted with structuring extracted data from 23 included studies into a standardized format.
**Human Decision**: Extracted all data from original study reports. Verified effect sizes and sample sizes against published tables.
**Files Affected**: `literature-review-evidence.md`
**Notes**: 18 of 23 studies provided sufficient data for meta-analysis.

### 2026-03-08 10:00 — data-analyst — ANALYSIS_CODE
**Action**: Generated R meta-analysis script using metafor package for random-effects meta-analysis of 23 studies. Included forest plot, funnel plot, heterogeneity assessment, subgroup analyses, and sensitivity analysis.
**Human Decision**: Approved random-effects model (REML estimator), standardized mean difference as effect measure, and subgroup variables (intervention type, country income level, depression measure).
**Files Affected**: `meta-analysis.qmd`
**Notes**: User prompt: *"I have extracted data from 23 studies. Help me set up a random-effects meta-analysis using the metafor package in R."*

### 2026-03-10 09:00 — academic-writer — DRAFT_TEXT
**Action**: Drafted complete PRISMA-compliant systematic review manuscript including all IMRaD sections, PRISMA checklist references, and AI disclosure statements.
**Human Decision**: Pending — all prose remains AI-drafted and must be reviewed, revised, and approved by the human researcher before submission.
**Files Affected**: `manuscript.qmd`
**Notes**: Draft includes placeholders for results that depend on meta-analysis output. All citations verified against references.bib.

### 2026-03-10 11:00 — academic-writer — CITATION_MANAGEMENT
**Action**: Compiled and verified bibliography of 18 references using CrossRef and PubMed MCP servers. All DOIs confirmed as resolving correctly.
**Human Decision**: Approved reference list. Added two additional references from hand-searching.
**Files Affected**: `references.bib`
**Notes**: No fabricated references. All entries verified via MCP tools.

### 2026-03-12 09:00 — project-manager — PROJECT_MANAGEMENT
**Action**: Generated progress brief summarizing milestone completion, current phase status, and upcoming tasks. Formatted decision log with all recorded research decisions and rationales.
**Human Decision**: Approved brief for sharing with research supervisor.
**Files Affected**: `progress-brief.qmd`, `decision-log.qmd`, `meeting-notes.qmd`
**Notes**: Brief is factual and based on recorded project tracking data only.

### 2026-03-12 10:00 — project-manager — DECISION_LOGGED
**Action**: Recorded six major research decisions with dates, rationales, and context.
**Human Decision**: All decisions were made by the human researcher. AI recorded them for audit trail purposes.
**Files Affected**: `decision-log.qmd`
**Notes**: Decision log supports ICMJE accountability criterion.
