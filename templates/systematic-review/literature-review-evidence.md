# Literature Review Evidence Log

<!--
This file provides a fully reproducible audit trail for the literature review
conducted by the systematic-reviewer agent. It captures the exact search strings,
databases queried, result counts, included references, and supporting quotes so
that the human author can independently verify and replicate every search through
each database's web interface.

ICMJE Compliance: The human author must be able to explain and defend every
decision in the literature review. This file makes that possible.
-->

**Project**: [Project name]
**Date of search**: YYYY-MM-DD
**Search conducted by**: systematic-reviewer agent (AI-assisted)
**Human reviewer**: [Name — must review and approve all content]

---

## 1. Databases Searched

<!-- List every MCP server / database used, with the web interface URL
     so the author can replicate each search manually. -->

| # | Database | MCP Server Used | Web Interface URL | API Key Required? |
|---|----------|----------------|-------------------|-------------------|
| 1 | PubMed / MEDLINE | `pubmed` | https://pubmed.ncbi.nlm.nih.gov/ | Optional (NCBI_API_KEY) |
| 2 | OpenAlex | `openalex` | https://openalex.org/ | Optional |
| 3 | Semantic Scholar | `semantic-scholar` | https://www.semanticscholar.org/ | Optional (CC BY-NC license) |
| 4 | Europe PMC | `europe-pmc` | https://europepmc.org/ | No |
| 5 | CrossRef | `crossref` | https://search.crossref.org/ | No (polite pool with email) |

---

## 2. Search Queries Executed

<!-- For EACH search, record:
     - The exact query string passed to the MCP tool
     - Any filters (date range, article type, fields of study)
     - The MCP tool function called
     - The total result count returned by the API
     - The max_results / limit parameter used
     - The equivalent web-interface search URL or instructions to replicate
-->

### Search 1

| Field | Value |
|-------|-------|
| **Database** | |
| **MCP tool** | e.g. `search_pubmed` |
| **Query string** | `exact query string here` |
| **Filters** | date_range: ; article_types: ; fields_of_study: |
| **max_results / limit** | |
| **Total results returned by API** | |
| **Results retrieved** | |
| **Date/time executed** | |
| **Web replication URL** | e.g. `https://pubmed.ncbi.nlm.nih.gov/?term=...` |

<!-- Copy and repeat this block for each search. Number sequentially. -->

---

## 3. References Included

<!-- For each reference included in the literature review, provide:
     - Full citation
     - BibTeX key (as used in references.bib)
     - Which search(es) identified it (by search number above)
     - DOI (verified via CrossRef or database)
     - PMID (if applicable)
     - Direct quotes from the source article that support claims made in the review
     - Relevance note: why this reference was included
-->

### Ref 1: [BibTeX key]

| Field | Value |
|-------|-------|
| **Citation** | Authors (Year). Title. *Journal*, Volume(Issue), Pages. |
| **BibTeX key** | `@key` |
| **Identified by search(es)** | Search #, Search # |
| **DOI** | |
| **PMID** | |
| **Relevance** | Brief explanation of why this paper is relevant to the review. |

**Supporting quotes from source:**

> "Direct quote from the article abstract or full text that supports the claim made in the literature review." (p. X)

> "Another direct quote if applicable." (p. Y)

**How this reference is used in the review:**
- [Section of the literature review where this reference appears and what claim it supports]

<!-- Copy and repeat this block for each included reference. -->

---

## 4. References Considered but Excluded

<!-- Optional: list references that appeared in search results and seemed
     relevant but were ultimately not included, with brief reason. -->

| # | Citation | Reason for Exclusion |
|---|----------|---------------------|
| 1 | | |

---

## 5. Verification Checklist

<!-- The human author should check each item before finalizing the review. -->

- [ ] I replicated at least one search from each database via the web interface and confirmed comparable result counts
- [ ] I verified all DOIs resolve to the correct article (via https://doi.org/)
- [ ] I reviewed all supporting quotes against the original source
- [ ] I confirmed that the literature review narrative accurately represents each cited study's findings
- [ ] I verified that no references were fabricated (all have verifiable DOIs or PMIDs)
- [ ] I am satisfied that the search strategy was comprehensive for the review's scope

**Human reviewer signature**: ____________________
**Date reviewed**: ____________________

---

## 6. Search Replication Instructions

<!-- Provide step-by-step instructions for the author to replicate each
     database search via the web interface. This is the "recipe" that
     makes the review independently reproducible. -->

### PubMed (https://pubmed.ncbi.nlm.nih.gov/)

1. Go to https://pubmed.ncbi.nlm.nih.gov/
2. Paste the query string from Search # into the search bar
3. Apply any date filters noted in the search record
4. Compare the result count with the "Total results returned by API" field

### OpenAlex (https://openalex.org/)

1. Go to https://openalex.org/
2. Enter the search query in the "Works" search
3. Compare the result count

### Semantic Scholar (https://www.semanticscholar.org/)

1. Go to https://www.semanticscholar.org/
2. Enter the search query
3. Apply year filters if noted
4. Compare the result count

### Europe PMC (https://europepmc.org/)

1. Go to https://europepmc.org/
2. Enter the search query
3. Compare the result count

### CrossRef (https://search.crossref.org/)

1. Go to https://search.crossref.org/
2. Enter the search query or use DOI lookup
3. Verify metadata matches
