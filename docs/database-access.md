# Academic Database Access Guide

This document describes the academic databases available through the research-workflow-assistant MCP servers, their strengths, and when to use each one.

## Database Overview

| Database | Coverage | Strength | Best For |
|----------|----------|----------|----------|
| PubMed/MEDLINE | 36M+ biomedical articles | Controlled vocabulary (MeSH), clinical focus | Biomedical and clinical research |
| OpenAlex | 250M+ works across disciplines | Broad interdisciplinary coverage, open metadata | Cross-disciplinary searches, bibliometrics |
| Semantic Scholar | 200M+ papers | AI-powered relevance, TLDR summaries | CS, biomedical, discovering key papers |
| Europe PMC | 44M+ life science articles | Full-text access, text mining, European focus | Open access content, text mining, European research |
| CrossRef | 150M+ DOI records | DOI resolution, metadata verification | Citation verification, DOI validation |
| Zotero | Your personal library | Reference management, citation export | Organizing references, generating bibliographies |

## PubMed / MEDLINE

### What it covers

- Biomedical and life sciences literature
- Over 36 million citations from MEDLINE, life science journals, and online books
- Indexed with Medical Subject Headings (MeSH)

### Available tools

- **search_pubmed**: Search with keywords, MeSH terms, and filters
- **fetch_abstract**: Get full abstract and metadata for a PMID
- **fetch_mesh_terms**: Get MeSH terms assigned to an article
- **suggest_mesh_terms**: Find relevant MeSH terms for a concept
- **get_related_articles**: Find similar articles using PubMed's algorithm
- **build_search_query**: Construct a Boolean search query from concepts

### When to use

- Primary database for any biomedical systematic review
- When you need controlled vocabulary (MeSH) for precise searches
- For clinical studies, RCTs, and public health research

### Tips

- Use MeSH terms for precision; combine with free-text for sensitivity
- Use the `build_search_query` tool to structure complex searches
- PubMed's related articles algorithm is excellent for discovering missed studies

---

## OpenAlex

### What it covers

- Over 250 million scholarly works across all disciplines
- Includes journals, conference proceedings, books, datasets, theses
- Links works to authors, institutions, concepts, and funders

### Available tools

- **search_works**: Search by keywords with filters (date, type, open access)
- **get_work**: Get detailed metadata for a specific work (by OpenAlex ID or DOI)
- **get_cited_by**: Find papers that cite a given work
- **get_references**: Get the reference list of a work
- **get_concepts**: Explore hierarchical concept taxonomy
- **get_author_works**: Find all works by a specific author
- **search_sources**: Search for journals and other publication venues

### When to use

- For interdisciplinary reviews spanning multiple fields
- When you need citation network analysis
- To find grey literature, conference papers, or non-biomedical research
- For bibliometric analysis (h-index, citation counts, institutional analysis)

### Tips

- OpenAlex has excellent coverage of open access content
- Use concept filtering to narrow large result sets
- Citation and reference traversal is useful for snowball searching

---

## Semantic Scholar

### What it covers

- Over 200 million academic papers
- Strong in computer science, biomedical science, and related fields
- AI-generated features: TLDR summaries, influential citations, recommendations

### Available tools

- **search_papers**: Keyword search with year and venue filters
- **get_paper**: Detailed metadata (supports DOI, PMID, ArXiv ID)
- **get_citations**: Papers that cite a given work (with context snippets)
- **get_references**: Reference list of a work
- **get_recommendations**: AI-powered paper recommendations (single or multi-paper)
- **get_author**: Author profile with publication list

### When to use

- When you need AI-powered recommendations to discover related work
- For quick paper summaries (TLDR)
- To identify influential vs. routine citations
- For computer science and AI research

### Tips

- The recommendation tool is valuable for finding papers your search may have missed
- TLDR summaries help with rapid screening
- Influential citation counts highlight which references actually build on prior work

---

## Europe PMC

### What it covers

- Over 44 million life science articles
- Includes content from PubMed, PubMed Central, preprints, patents, and clinical guidelines
- Strong European research representation

### Available tools

- **search_europepmc**: Full-text and metadata search
- **get_full_text**: Retrieve full text (XML) for open access articles
- **get_citations**: Articles citing a given work
- **get_references**: Reference list of an article
- **get_text_mined_terms**: Extracted entities (genes, diseases, chemicals, organisms)

### When to use

- When you need full-text access for open access articles
- For text mining (extracting genes, chemicals, diseases from articles)
- To search across preprints, patents, and clinical guidelines
- For European-funded or European-focused research

### Tips

- Full-text search can find mentions in methods/results sections that abstracts miss
- Text-mined terms are useful for building concept maps of a research area
- Combine with PubMed for comprehensive biomedical searching

---

## CrossRef

### What it covers

- Over 150 million DOI records from scholarly publishers
- Comprehensive metadata: titles, authors, references, funding, licenses
- The authoritative source for DOI resolution

### Available tools

- **search_works**: Search by keywords, author, title with filters
- **get_work_by_doi**: Get full metadata for a DOI
- **get_references_by_doi**: Get the reference list registered with a DOI
- **check_doi**: Validate whether a DOI exists (anti-hallucination check)

### When to use

- To verify DOIs are valid (critical before including in references)
- To retrieve standardized metadata for citation management
- For reference list analysis
- To check funding information and licensing

### Tips

- Always use `check_doi` to validate DOIs, especially for AI-suggested references
- CrossRef metadata is the gold standard for citation formatting
- Reference lists from CrossRef are useful for backward snowball searching

---

## Zotero

### What it covers

- Your personal or group reference library
- Import from any source, organize with collections and tags
- Export in any citation format

### Available tools

- **search_library**: Search your Zotero library
- **add_item**: Add a reference manually
- **add_item_by_doi**: Add a reference by DOI (auto-fetches metadata from CrossRef)
- **get_collections**: List your Zotero collections
- **create_collection**: Create a new collection
- **add_to_collection**: Add items to a collection
- **export_bibliography**: Export references in BibTeX, CSL-JSON, RIS, etc.
- **add_note**: Add a note to a reference
- **tag_item**: Tag a reference for organization

### When to use

- To build and organize your reference library during a review
- To generate bibliographies for manuscripts
- To annotate references with screening decisions or notes
- To share references with collaborators via group libraries

### Tips

- Use `add_item_by_doi` for efficient reference import
- Create collections that mirror your review workflow (e.g., "Included", "Excluded", "Full-text screening")
- Export to BibTeX for use in Quarto manuscripts

---

## Recommended Search Strategies

### For systematic reviews

1. **Start with PubMed**: Use MeSH terms for your core biomedical search
2. **Expand with OpenAlex**: Capture interdisciplinary and grey literature
3. **Add Europe PMC**: For preprints, patents, and full-text searching
4. **Use Semantic Scholar**: For AI recommendations to find missed studies
5. **Verify with CrossRef**: Validate all DOIs before final inclusion
6. **Organize with Zotero**: Import all results, deduplicate, manage screening

### For rapid literature reviews

1. **Semantic Scholar**: Use recommendations for quick discovery
2. **PubMed**: Targeted MeSH search for key evidence
3. **CrossRef**: Verify citations
4. **Zotero**: Collect and export bibliography

### For citation verification

1. **CrossRef** `check_doi`: Validate every DOI
2. **PubMed** `fetch_abstract`: Verify title/author/year match
3. **Semantic Scholar** `get_paper`: Cross-reference metadata
