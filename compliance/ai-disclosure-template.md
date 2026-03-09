# AI Disclosure Statement Templates

Use these templates to disclose AI tool usage in your manuscript, following ICMJE Section II.A.4 guidelines.

## Acknowledgments Section

Use this when the AI tool assisted with writing, literature searching, or other non-analytical tasks:

> **AI Tool Disclosure:** [Tool name and version] was used during the preparation of this manuscript to [describe specific use: e.g., assist with literature searching, help draft portions of the methods section, improve language clarity]. The authors reviewed and edited all AI-assisted content and take full responsibility for the content of the publication.

### Example:

> **AI Tool Disclosure:** GitHub Copilot (Claude model, accessed via VS Code) was used during the preparation of this manuscript to assist with systematic literature searching across PubMed, OpenAlex, and Semantic Scholar databases, and to help structure initial drafts of the methods section. The authors reviewed, revised, and verified all AI-assisted content, including independently confirming all database search results and cited references. The authors take full responsibility for the content of the publication.

## Methods Section

Use this when the AI tool was involved in data analysis, screening, or systematic processes:

> **AI-Assisted Methods:** [Tool name and version] was used to [describe analytical use]. Specifically, the tool was used for: [list specific tasks]. All analytical decisions, including [list key decisions], were made by the research team. The AI tool's outputs were independently verified by [describe verification process]. Complete records of AI-assisted processes are available in the project's AI contributions log.

### Example:

> **AI-Assisted Methods:** The research-workflow-assistant platform (v0.1.0, using GitHub Copilot) was used to facilitate the systematic review process. Specifically, the tool was used for: (1) translating the search strategy across database-specific query syntaxes (PubMed, Scopus, Web of Science), (2) deduplicating records across databases, and (3) organizing screening workflow tracking. All screening decisions, inclusion/exclusion determinations, data extraction, and quality assessments were made independently by two reviewers (AB and CD). Search results were verified by re-running queries independently. Complete records of AI-assisted processes are available upon request.

## Cover Letter

Include this paragraph in the cover letter to the journal editor:

> We wish to disclose that AI tools were used during the preparation of this manuscript, as detailed in the Acknowledgments [and/or Methods] section(s). In accordance with ICMJE recommendations, we confirm that: (1) no AI tool is listed as an author, (2) all authors meet all four ICMJE authorship criteria, (3) the authors take full responsibility for the work, and (4) the use of AI tools is transparently described in the manuscript.

## Database-Specific Data Licensing

### Semantic Scholar (CC BY-NC)

Semantic Scholar data is provided under a **Creative Commons Attribution-NonCommercial (CC BY-NC)** license. If your research used Semantic Scholar for literature searching, citation retrieval, or paper recommendations, you must:

1. **Attribute** Semantic Scholar as a data source in your methods section.
2. **Cite** the platform paper:
   > Kinney, R., Anastasiades, C., Authur, R., et al. (2023). "The Semantic Scholar Open Data Platform." *ArXiv*, abs/2301.10140.
3. **Respect the non-commercial restriction**: CC BY-NC does not permit commercial use of the retrieved data. If your research has a commercial purpose, review the [Semantic Scholar API License Agreement](https://www.semanticscholar.org/product/api/license) for applicable terms.

**Example methods sentence:**

> Semantic Scholar (Allen Institute for AI) was searched via its Graph API for additional references and citation network analysis.

**Example acknowledgments addition:**

> Literature search results were supplemented using the Semantic Scholar Open Data Platform (Kinney et al., 2023), which provides bibliographic data under a CC BY-NC license.

## Contribution Log Reference

Every project using this tool generates an `ai-contributions-log.md` file that records:
- Date and time of each AI-assisted action
- Type of action (search, draft, analysis, organization)
- What the AI tool produced
- What the human researcher decided or modified
- Section of the manuscript affected

This log supports transparency and can be shared with editors upon request.
