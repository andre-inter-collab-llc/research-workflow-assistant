# Literature Review Evidence Log

**Project**: CHW Interventions for Maternal Mental Health in LMICs
**Date of search**: 2026-03-02
**Search conducted by**: systematic-reviewer agent (AI-assisted)
**Human reviewer**: Demo Researcher

---

## 1. Databases Searched

| # | Database | MCP Server Used | Web Interface URL | API Key Required? |
|---|----------|----------------|-------------------|-------------------|
| 1 | PubMed / MEDLINE | `pubmed` | https://pubmed.ncbi.nlm.nih.gov/ | Optional (NCBI_API_KEY) |
| 2 | OpenAlex | `openalex` | https://openalex.org/ | Optional |
| 3 | Semantic Scholar | `semantic-scholar` | https://www.semanticscholar.org/ | Optional (CC BY-NC license) |
| 4 | Europe PMC | `europe-pmc` | https://europepmc.org/ | No |
| 5 | CrossRef | `crossref` | https://search.crossref.org/ | No (polite pool with email) |

---

## 2. Search Queries Executed

### Search 1 — PubMed

| Field | Value |
|-------|-------|
| **Database** | PubMed / MEDLINE |
| **MCP tool** | `search_pubmed` |
| **Query string** | `("Pregnant Women"[MeSH] OR "Postpartum Period"[MeSH] OR maternal[tiab] OR perinatal[tiab] OR postnatal[tiab] OR postpartum[tiab]) AND ("Depression, Postpartum"[MeSH] OR depression[tiab] OR anxiety[tiab] OR "mental health"[tiab]) AND ("Community Health Workers"[MeSH] OR "community health worker*"[tiab] OR "lay health worker*"[tiab] OR "task-shifting"[tiab]) AND ("Developing Countries"[MeSH] OR "low-income"[tiab] OR "middle-income"[tiab] OR LMIC[tiab])` |
| **Filters** | date_range: 2005–2026; language: English |
| **max_results** | 500 |
| **Total results returned** | 487 |
| **Date/time executed** | 2026-03-02 09:15 |

### Search 2 — OpenAlex

| Field | Value |
|-------|-------|
| **Database** | OpenAlex |
| **MCP tool** | `search_works` |
| **Query string** | `community health worker maternal depression low-income` |
| **Filters** | from_publication_date=2005-01-01, type=article |
| **max_results** | 400 |
| **Total results returned** | 341 |
| **Date/time executed** | 2026-03-02 09:22 |

### Search 3 — Semantic Scholar

| Field | Value |
|-------|-------|
| **Database** | Semantic Scholar |
| **MCP tool** | `search_papers` |
| **Query string** | `community health worker maternal mental health depression low middle income countries intervention` |
| **Filters** | year: 2005-2026; fields of study: Medicine, Psychology |
| **max_results** | 200 |
| **Total results returned** | 198 |
| **Date/time executed** | 2026-03-02 09:30 |

### Search 4 — Europe PMC

| Field | Value |
|-------|-------|
| **Database** | Europe PMC |
| **MCP tool** | `search_europepmc` |
| **Query string** | `(TITLE_ABS:"community health worker" OR TITLE_ABS:"lay health worker" OR TITLE_ABS:"task-shifting") AND (TITLE_ABS:"maternal depression" OR TITLE_ABS:"perinatal depression") AND (TITLE_ABS:"low-income" OR TITLE_ABS:"developing countries")` |
| **Filters** | PUB_YEAR:[2005 TO 2026] |
| **max_results** | 200 |
| **Total results returned** | 156 |
| **Date/time executed** | 2026-03-02 09:38 |

### Search 5 — CrossRef

| Field | Value |
|-------|-------|
| **Database** | CrossRef |
| **MCP tool** | `search_works` (CrossRef) |
| **Query string** | `community health worker maternal depression LMIC intervention` |
| **Filters** | from-pub-date=2005, type=journal-article |
| **max_results** | 100 |
| **Total results returned** | 65 |
| **Date/time executed** | 2026-03-02 09:45 |

---

## 3. References Included

> **Note:** This is a demo project. Below are three representative entries
> showing the expected format. A full review would have 23 such entries.

### Ref 1: rahman2008cognitive

| Field | Value |
|-------|-------|
| **Citation** | Rahman, A., Malik, A., Sikander, S., Roberts, C., & Creed, F. (2008). Cognitive behaviour therapy-based intervention by community health workers for mothers with depression and their infants in rural Pakistan: a cluster-randomised controlled trial. *The Lancet*, 372(9642), 902–909. |
| **BibTeX key** | `@rahman2008cognitive` |
| **Identified by search(es)** | Search #1 (PubMed), Search #2 (OpenAlex), Search #3 (Semantic Scholar) |
| **DOI** | 10.1016/S0140-6736(08)61400-2 |
| **PMID** | 18790313 |
| **Relevance** | Landmark cluster-RCT of the Thinking Healthy Programme in Pakistan. Demonstrated significant reduction in perinatal depression through CHW-delivered CBT. |

**Supporting quotes from source:**

> "The intervention was effective in reducing depression in the mothers (adjusted odds ratio 0.22, 95% CI 0.14–0.36, p<0.0001)." (p. 906)

> "Lady health workers with no previous mental health experience can be trained to deliver a cognitive behaviour therapy-based intervention that is effective in reducing depression in mothers." (p. 908)

**How this reference is used in the review:**
- Background section: establishes the feasibility of CHW-delivered CBT for perinatal depression in LMICs
- Results section: contributes to the CBT subgroup meta-analysis (SMD = −0.55, SE = 0.07)

---

### Ref 2: patel2017effectiveness

| Field | Value |
|-------|-------|
| **Citation** | Patel, V., Weobong, B., Weiss, H. A., et al. (2017). The Healthy Activity Program (HAP), a lay counsellor-delivered brief psychological treatment for severe depression, in primary care in India: a randomised controlled trial. *The Lancet*, 389(10065), 176–185. |
| **BibTeX key** | `@patel2017effectiveness` |
| **Identified by search(es)** | Search #1 (PubMed), Search #2 (OpenAlex), Search #4 (Europe PMC) |
| **DOI** | 10.1016/S0140-6736(16)31589-6 |
| **PMID** | 27988143 |
| **Relevance** | Demonstrated effectiveness of a lay-counselor-delivered behavioral activation intervention (HAP) for severe depression in India. |

**Supporting quotes from source:**

> "Participants in the HAP group had significantly lower PHQ-9 scores at 3 months compared with enhanced usual care (adjusted mean difference −1.10, 95% CI −1.80 to −0.41)." (p. 180)

> "The HAP is an effective treatment for moderately severe to severe depression delivered by lay counsellors in primary health care." (p. 183)

**How this reference is used in the review:**
- Background: demonstrates scalability of lay-delivered interventions in India
- Results: contributes to the CBT subgroup (SMD = −0.57, SE = 0.09)

---

### Ref 3: fuhr2020delivering

| Field | Value |
|-------|-------|
| **Citation** | Fuhr, D. C., Weobong, B., Lazarus, A., et al. (2020). Delivering the Thinking Healthy Programme for perinatal depression through peers: an individually randomised controlled trial in India. *The Lancet Psychiatry*, 7(2), 133–141. |
| **BibTeX key** | `@fuhr2020delivering` |
| **Identified by search(es)** | Search #1 (PubMed), Search #3 (Semantic Scholar) |
| **DOI** | 10.1016/S2215-0366(19)30498-X |
| **PMID** | 31870676 |
| **Relevance** | Extended the Thinking Healthy Programme to peer delivery in India. Demonstrated significant reduction in perinatal depression through non-specialist delivery. |

**Supporting quotes from source:**

> "The peer-delivered Thinking Healthy Programme significantly reduced depressive symptoms at 6 months postpartum (adjusted mean difference −1.89, 95% CI −3.25 to −0.53)." (p. 137)

**How this reference is used in the review:**
- Discussion: supports the peer delivery model as an effective approach
- Results: contributes to the CBT subgroup (SMD = −0.40, SE = 0.12)

---

## 4. References Considered but Excluded

| # | Citation | Reason for Exclusion |
|---|----------|---------------------|
| 1 | Howard et al. (2014). Non-psychotic mental disorders in the perinatal period. *The Lancet*. | Review article, not primary study |
| 2 | Milgrom et al. (2016). Screening for perinatal depression. *Best Practice & Research Clin Ob Gyn*. | High-income country (Australia) |
| 3 | Clarke et al. (2019). Group therapy for maternal depression in Cape Town. | Specialist-delivered (clinical psychologist) |

---

## 5. Verification Checklist

- [x] I replicated at least one search from each database via the web interface and confirmed comparable result counts
- [x] I verified all DOIs resolve to the correct article (via https://doi.org/)
- [x] I reviewed all supporting quotes against the original source
- [x] I confirmed that the literature review narrative accurately represents each cited study's findings
- [x] I verified that no references were fabricated (all have verifiable DOIs or PMIDs)
- [x] I am satisfied that the search strategy was comprehensive for the review's scope

**Human reviewer signature**: Demo Researcher
**Date reviewed**: 2026-03-10

---

## 6. Search Replication Instructions

### PubMed (https://pubmed.ncbi.nlm.nih.gov/)

1. Go to https://pubmed.ncbi.nlm.nih.gov/
2. Paste the full PubMed query from Search #1 into the search bar
3. Apply date filter: 2005–2026
4. Apply language filter: English
5. Expected result: ~487 records (may vary slightly due to ongoing indexing)

### OpenAlex (https://openalex.org/)

1. Go to https://openalex.org/
2. Search for "community health worker maternal depression low-income" in Works
3. Filter: publication year ≥ 2005, type = article
4. Expected result: ~341 records

### Semantic Scholar (https://www.semanticscholar.org/)

1. Go to https://www.semanticscholar.org/
2. Search for "community health worker maternal mental health depression low middle income countries intervention"
3. Filter: year 2005–2026, fields: Medicine, Psychology
4. Expected result: ~198 records

### Europe PMC (https://europepmc.org/)

1. Go to https://europepmc.org/
2. Paste the Europe PMC query from Search #4
3. Filter: publication year 2005–2026
4. Expected result: ~156 records

### CrossRef (https://search.crossref.org/)

1. Go to https://search.crossref.org/
2. Search for "community health worker maternal depression LMIC intervention"
3. Expected result: ~65 records

---

*This evidence log was compiled with assistance from the Research Workflow Assistant (`@systematic-reviewer` agent). All inclusion/exclusion decisions and verification were performed by the human reviewer.*
