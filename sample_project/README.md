# Sample Project: CHW Interventions for Maternal Mental Health

> **This is a demo project.** It showcases the Research Workflow Assistant (RWA) capabilities using a realistic but fictional systematic review. No real screening decisions or data extraction were performed. All outputs are illustrative.

## About This Demo

This sample project demonstrates a systematic review on:

> **"Effectiveness of community health worker interventions for maternal mental health in low- and middle-income countries"**

It walks through the full RWA workflow using the agents described in the main README:

| Agent | What it produced | File(s) |
|-------|-----------------|---------|
| `@research-orchestrator` | End-to-end workflow plan | (coordination across all agents) |
| `@systematic-reviewer` | Search strategy, database searches, screening support | `search-strategy.qmd`, `literature-review-evidence.md`, `prisma-flow.qmd` |
| `@research-planner` | Review protocol for PROSPERO registration | `protocol.qmd` |
| `@data-analyst` | Random-effects meta-analysis script (23 studies, metafor) | `meta-analysis.qmd` |
| `@academic-writer` | PRISMA-compliant manuscript draft | `manuscript.qmd` |
| `@project-manager` | Progress brief, decision log, meeting notes | `progress-brief.qmd`, `decision-log.qmd`, `meeting-notes.qmd` |

## PICO Framework

| Element | Description |
|---------|-------------|
| **Population** | Pregnant and postpartum women in low- and middle-income countries |
| **Intervention** | Community health worker (CHW) delivered mental health interventions |
| **Comparator** | Standard care, enhanced usual care, or no intervention |
| **Outcome** | Maternal depression and anxiety symptoms (validated scales) |

## Files in This Demo

```
sample_project/
├── README.md                        ← You are here
├── project-config.yaml              ← Project settings and author metadata
├── ai-contributions-log.md          ← ICMJE-compliant AI audit trail
├── references.bib                   ← Bibliography (verified references)
│
├── protocol.qmd                     ← Review protocol (PROSPERO draft)
├── search-strategy.qmd              ← Database-specific search strategies
├── literature-review-evidence.md    ← Evidence audit trail with quotes
├── prisma-flow.qmd                  ← PRISMA 2020 flow diagram
│
├── meta-analysis.qmd                ← R meta-analysis script (metafor)
├── manuscript.qmd                   ← Full manuscript draft (PRISMA)
│
├── progress-brief.qmd               ← Status update for supervisors
├── decision-log.qmd                 ← Research decisions with rationale
└── meeting-notes.qmd                ← Team meeting notes template
```

## How to Reproduce

1. Open the repository in VS Code with GitHub Copilot enabled
2. Run `@setup` to configure your environment
3. Try the example prompts from the main README — the agents will produce outputs similar to this sample

## ICMJE Compliance

Every file in this demo includes appropriate AI disclosure language. The `ai-contributions-log.md` tracks all AI-assisted actions. This is how RWA ensures the human researcher remains the author and maintains full accountability.

---

*This sample project was generated for demonstration purposes by the Research Workflow Assistant.*
