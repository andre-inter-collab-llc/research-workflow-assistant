# Research Workflow Assistant — Architecture Diagram

<!-- Render with any Mermaid-compatible tool: GitHub markdown, Mermaid Live Editor, Quarto, etc. -->
<!-- For a PNG/SVG export, paste the fenced block into https://mermaid.live -->

```mermaid
graph TB
    %% ── Researcher layer ──
    YOU["👤 You · the Researcher\nAll decisions · All ownership · All accountability"]

    %% ── VS Code layer ──
    VSCODE["VS Code + GitHub Copilot Chat"]

    YOU --> VSCODE

    %% ── Agent layer ──
    subgraph AGENTS["Specialist AI Agents"]
        direction LR
        ORCH["@research-orchestrator\nEnd-to-end\nworkflow routing"]
        SR["@systematic-reviewer\nPRISMA-compliant\nevidence reviews"]
        RP["@research-planner\nProtocols &\nstudy design"]
        DA["@data-analyst\nReproducible R / Python\nanalysis scripts"]
        AW["@academic-writer\nManuscript drafting\n& citations"]
        PM["@project-manager\nMilestones, decisions\n& progress briefs"]
        TS["@troubleshooter\nDiagnostics &\nenvironment fixes"]
    end

    VSCODE --> AGENTS

    %% ── ICMJE compliance bar ──
    ICMJE["🔒 ICMJE Compliance Layer\nHuman-in-the-loop · Audit trail · AI disclosure"]

    AGENTS --> ICMJE

    %% ── MCP Server layer ──
    subgraph MCP["MCP Servers · Model Context Protocol"]
        direction LR
        subgraph LITERATURE["Literature Databases"]
            PUB["PubMed\n NCBI E-utilities"]
            OA["OpenAlex\n REST API"]
            SS["Semantic Scholar\n Academic Graph"]
            EPMC["Europe PMC\n REST API"]
            CR["CrossRef\n DOI metadata"]
        end
        subgraph REFERENCE["Reference Management"]
            ZOT["Zotero Web\n API v3"]
            ZLOC["Zotero Local\n PDFs & annotations"]
        end
        subgraph TRACKING["Project Tracking"]
            PRISMA["PRISMA Tracker\n flow diagrams"]
            PROJ["Project Tracker\n tasks & milestones"]
        end
    end

    ICMJE --> MCP

    %% ── Output layer ──
    subgraph OUTPUTS["Research Outputs"]
        direction LR
        QMD["📄 Quarto Documents\nManuscripts · Protocols · Reports"]
        SCRIPTS["📊 Analysis Scripts\nR · Python · Reproducible"]
        PFLOW["📋 PRISMA Flow\nDiagrams & Checklists"]
        BRIEFS["📝 Progress Briefs\nDecision logs · Meeting notes"]
    end

    MCP --> OUTPUTS

    %% ── Styles ──
    classDef researcher fill:#2563eb,stroke:#1e40af,color:#fff,font-weight:bold
    classDef vscode fill:#007acc,stroke:#005a9e,color:#fff,font-weight:bold
    classDef agent fill:#7c3aed,stroke:#5b21b6,color:#fff
    classDef compliance fill:#dc2626,stroke:#991b1b,color:#fff,font-weight:bold
    classDef litdb fill:#10b981,stroke:#047857,color:#fff
    classDef refmgmt fill:#14b8a6,stroke:#0d9488,color:#fff
    classDef tracking fill:#06b6d4,stroke:#0891b2,color:#fff
    classDef output fill:#d97706,stroke:#b45309,color:#fff

    class YOU researcher
    class VSCODE vscode
    class ORCH,SR,RP,DA,AW,PM,TS agent
    class ICMJE compliance
    class PUB,OA,SS,EPMC,CR litdb
    class ZOT,ZLOC refmgmt
    class PRISMA,PROJ tracking
    class QMD,SCRIPTS,PFLOW,BRIEFS output
```

## How to export a static image

1. Copy the fenced Mermaid block above.
2. Paste it into **[Mermaid Live Editor](https://mermaid.live)**.
3. Download as **PNG** or **SVG**.
4. Save to `docs/rwa-architecture.png` (or `.svg`).
5. Reference from the README:
   ```markdown
   ![RWA Architecture](docs/rwa-architecture.png)
   ```
