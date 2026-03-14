# Literature Review Evidence Log

**Project**: CHW Interventions for Maternal Mental Health in LMICs — Systematic Review
**Date of search**: 2026-03-14
**Search conducted by**: systematic-reviewer agent (AI-assisted)
**Human reviewer**: Andre van Zyl, MPH — must review and approve all content

---

## 1. Databases Searched

| # | Database | MCP Server Used | Web Interface URL | API Key Required? |
|---|----------|----------------|-------------------|-------------------|
| 1 | PubMed / MEDLINE | `pubmed` | https://pubmed.ncbi.nlm.nih.gov/ | Optional (NCBI_API_KEY) |
| 2 | OpenAlex | `openalex` | https://openalex.org/ | Optional |
| 3 | Semantic Scholar | `semantic-scholar` | https://www.semanticscholar.org/ | Optional (CC BY-NC license) |
| 4 | Europe PMC | `europe-pmc` | https://europepmc.org/ | No |
| 5 | CrossRef | `crossref` | https://search.crossref.org/ | No (polite pool with email) |

**Note on Europe PMC**: The Europe PMC MCP server returned 0 results for all query variants attempted. This appears to be a server/API issue rather than a true absence of results. The search should be replicated manually via the Europe PMC web interface.

---

## 2. Search Queries Executed

### Search 1 — PubMed/MEDLINE

| Field | Value |
|-------|-------|
| **Database** | PubMed/MEDLINE |
| **MCP tool** | `search_pubmed` |
| **Query string** | `(("Community Health Workers"[MeSH] OR "community health worker*"[tiab] OR "lay health worker*"[tiab] OR "lay counselor*"[tiab] OR "peer counselor*"[tiab] OR "peer support"[tiab] OR "task shifting"[tiab] OR "task sharing"[tiab] OR "village health worker*"[tiab]) AND ("Depression"[MeSH] OR "Depressive Disorder"[MeSH] OR "Anxiety"[MeSH] OR "depression"[tiab] OR "depressive"[tiab] OR "anxiety"[tiab] OR "mental health"[tiab] OR "psychological distress"[tiab] OR "perinatal depression"[tiab] OR "postpartum depression"[tiab] OR "postnatal depression"[tiab] OR "maternal depression"[tiab] OR "antenatal depression"[tiab]) AND ("Pregnant Women"[MeSH] OR "Postpartum Period"[MeSH] OR "Pregnancy"[MeSH] OR "perinatal"[tiab] OR "antenatal"[tiab] OR "prenatal"[tiab] OR "postnatal"[tiab] OR "postpartum"[tiab] OR "maternal"[tiab] OR "pregnant"[tiab] OR "pregnancy"[tiab]) AND ("Developing Countries"[MeSH] OR "low-income"[tiab] OR "middle-income"[tiab] OR "LMIC"[tiab] OR "developing countr*"[tiab] OR "resource-limited"[tiab] OR "low-resource"[tiab])) AND (randomized controlled trial[pt] OR "randomized"[tiab] OR "randomised"[tiab] OR "RCT"[tiab] OR "cluster randomized"[tiab])` |
| **Filters** | Publication type: randomized controlled trial (built into query) |
| **max_results / limit** | 50 |
| **Total results returned by API** | 59 |
| **Results retrieved** | 50 |
| **Date/time executed** | 2026-03-14 |
| **Web replication URL** | Paste the query string into https://pubmed.ncbi.nlm.nih.gov/ advanced search |

### Search 2 — OpenAlex

| Field | Value |
|-------|-------|
| **Database** | OpenAlex |
| **MCP tool** | `search_works` |
| **Query string** | `community health worker perinatal depression anxiety low-income middle-income countries randomized controlled trial` |
| **Filters** | `type:article` |
| **per_page** | 50 |
| **Total results returned by API** | 1,442 |
| **Results retrieved** | 50 |
| **Date/time executed** | 2026-03-14 |
| **Web replication URL** | https://openalex.org/ → search "Works" with query terms |

### Search 3 — Semantic Scholar

| Field | Value |
|-------|-------|
| **Database** | Semantic Scholar (CC BY-NC data license) |
| **MCP tool** | `search_papers` |
| **Query string** | `community health worker intervention perinatal maternal depression anxiety low-income middle-income countries randomized trial` |
| **Filters** | `fields_of_study: Medicine` |
| **limit** | 50 |
| **Total results returned by API** | 162 |
| **Results retrieved** | 50 |
| **Date/time executed** | 2026-03-14 |
| **Web replication URL** | https://www.semanticscholar.org/ → search with query terms, filter to Medicine |

**Semantic Scholar attribution**: Data licensed CC BY-NC. Cite: Kinney, R., et al. (2023). "The Semantic Scholar Open Data Platform." *ArXiv*, abs/2301.10140.

### Search 4 — Europe PMC

| Field | Value |
|-------|-------|
| **Database** | Europe PMC |
| **MCP tool** | `search_europepmc` |
| **Query string** | Multiple variants attempted: `(community health worker OR lay health worker OR peer counselor OR task shifting) AND (perinatal OR maternal OR postpartum OR antenatal) AND (depression OR anxiety OR mental health) AND (low-income OR middle-income OR LMIC OR developing) AND (randomized OR randomised OR RCT)` and simpler queries |
| **Filters** | None |
| **page_size** | 50 |
| **Total results returned by API** | 0 (all variants) |
| **Results retrieved** | 0 |
| **Date/time executed** | 2026-03-14 |
| **Web replication URL** | https://europepmc.org/ → paste query |
| **Note** | Server returned 0 results for all queries including `perinatal depression` alone. Likely API/server issue. Manual replication required. |

### Search 5 — CrossRef

| Field | Value |
|-------|-------|
| **Database** | CrossRef |
| **MCP tool** | `search_works` |
| **Query string** | `community health worker perinatal depression anxiety low-income countries randomized trial` |
| **Filters** | `from-pub-date:2000, type:journal-article, has-abstract:true` |
| **rows** | 50 |
| **Total results returned by API** | 263,753 |
| **Results retrieved** | 50 |
| **Date/time executed** | 2026-03-14 |
| **Web replication URL** | https://search.crossref.org/ → search with query terms |
| **Note** | Very broad text matching; high total count reflects CrossRef's relevance-ranked full-text search across all metadata |

---

## 3. Summary of Search Results

| Database | Total Hits | Retrieved | Notes |
|----------|-----------|-----------|-------|
| PubMed/MEDLINE | 59 | 50 | Most targeted; MeSH + free text + RCT filter |
| OpenAlex | 1,442 | 50 | Broad relevance matching |
| Semantic Scholar | 162 | 50 | Medicine field filter applied |
| Europe PMC | 0 | 0 | API issue; needs manual replication |
| CrossRef | 263,753 | 50 | Very broad; useful for DOI verification |
| **Total identified** | **265,416** | **200** | Before deduplication |

**Note**: The high total counts from OpenAlex and CrossRef reflect broad text matching algorithms. PubMed (59 results) and Semantic Scholar (162 results) provide the most focused result sets due to controlled vocabulary and field-specific filtering.

---

## 4. Records Retrieved for Screening

The following records were retrieved from PubMed (the most targeted search) and cross-referenced against other databases. Records are presented for title/abstract screening against the eligibility criteria defined in the protocol.

### Key for screening decisions:
- **INCLUDE**: Meets all eligibility criteria after full-text review
- **EXCLUDE**: Does not meet criteria (exclusion reason provided)

### Screening stages:
- **Title/Abstract screening**: All 185 deduplicated records passed (user decision: include all)
- **Full-text screening**: Applied protocol eligibility criteria to 46 PubMed records (below)

### Records from PubMed (top 50 by relevance)

| # | PMID | Year | Title | Authors (first) | Journal | DOI | Full-Text Decision | Exclusion Reason |
|---|------|------|-------|-----------------|---------|-----|-------------------|-----------------|
| 1 | 41466232 | 2025 | The mental health benefit of a community-based home-visiting program for prenatal women: evidence from a randomized controlled trial in China | Wang N | BMC Pregnancy Childbirth | 10.1186/s12884-025-08297-2 | INCLUDE | — |
| 2 | 40933935 | 2025 | Epidemiology, pathophysiology, and interventions for postpartum depression: Systematic review | Ji QQ | World J Clin Cases | 10.12998/wjcc.v13.i29.110948 | EXCLUDE | Wrong design: systematic review |
| 3 | 40336702 | 2025 | Protocol for a RCT of the Mommy&Me study: A multi-modal approach... low-income Black perinatal populations | Le HN | Contemp Clin Trials Commun | 10.1016/j.conctc.2025.101489 | EXCLUDE | Protocol without results; HIC (US) |
| 4 | 40028388 | 2025 | Feasibility, acceptability and preliminary effectiveness of a culturally adapted Friendship Bench Intervention for perinatal psychological distress in Sierra Leone | Bah AJ | Glob Ment Health | 10.1017/gmh.2025.6 | EXCLUDE | Wrong design: pre-post waitlist-controlled (not RCT) |
| 5 | 39560615 | 2024 | Parenting with nutrition education and unconditional cash reduce maternal depressive symptoms... cluster RCT in urban Bangladesh | Hossain SJ | Glob Health Action | 10.1080/16549716.2024.2426784 | INCLUDE | — |
| 6 | 39464558 | 2024 | Peer counseling for perinatal depression in low- and middle-income countries: A scoping review | Cuncannon A | Glob Ment Health | 10.1017/gmh.2024.73 | EXCLUDE | Wrong design: scoping review |
| 7 | 39356541 | 2025 | A Group Parenting Intervention for Male Postpartum Depression: A Cluster RCT | Husain MI | JAMA Psychiatry | 10.1001/jamapsychiatry.2024.2752 | EXCLUDE | Wrong population: fathers |
| 8 | 39808016 | 2024 | [Title not retrieved — NIHR report] | Mills TA | — | 10.3310/JNWA6983 | EXCLUDE | Unable to retrieve; not peer-reviewed journal article |
| 9 | 38929226 | 2024 | Effectiveness of LTP Plus Parenting Intervention on Behaviours of Young Children of Depressed Mothers: RCT | Husain N | Children | 10.3390/children11060646 | EXCLUDE | Wrong outcome: child behaviour (ECBI), not maternal depression |
| 10 | 38645302 | 2024 | Effectiveness of interpersonal psychotherapy... for reducing depressive symptoms in women with PPD in LMICs: SR | Kang HK | Campbell Syst Rev | 10.1002/cl2.1399 | EXCLUDE | Wrong design: systematic review |
| 11 | 38615079 | 2024 | Teleintervention's effects on breastfeeding in low-income women in high income countries: SR & MA | Corkery-Hayward M | Int Breastfeed J | 10.1186/s13006-024-00631-2 | EXCLUDE | Wrong design: SR & MA; HIC; wrong outcome (breastfeeding) |
| 12 | 37626428 | 2023 | Technology-assisted CBT delivered by peers vs standard CBT by CHWs for perinatal depression: protocol for cluster RCT | Rahman A | Trials | 10.1186/s13063-023-07581-w | EXCLUDE | Protocol without results |
| 13 | 37575961 | 2023 | SMARThealth PRegnancy And Mental Health study: protocol for situational analysis... rural India | Votruba N | Front Glob Womens Health | 10.3389/fgwh.2023.1143880 | EXCLUDE | Protocol/situational analysis without results |
| 14 | 37559158 | 2023 | A community-based intervention to improve screening... pregnant and postpartum women in rural India: protocol for cluster RCT | Hirst JE | Trials | 10.1186/s13063-023-07510-x | EXCLUDE | Protocol without results |
| 15 | 37510639 | 2023 | Can a Clinic-Based CHW Intervention Buffer the Negative Impact of COVID-19 on Low-Income Families | Salaguinto T | Int J Environ Res Public Health | 10.3390/ijerph20146407 | EXCLUDE | HIC setting (United States) |
| 16 | 37183793 | 2023 | Task-sharing psychosocial interventions for prevention of common mental disorders in perinatal period in LMICs: SR & MA | Prina E | Int J Soc Psychiatry | 10.1177/00207640231174451 | EXCLUDE | Wrong design: SR & MA (mine reference list) |
| 17 | 37006596 | 2023 | Development, Implementation, and Process Evaluation of Bukhali: An Intervention from Preconception to Early Childhood | Draper CE | Glob Implement Res Appl | 10.1007/s43477-023-00073-8 | EXCLUDE | Wrong design: process evaluation (not RCT) |
| 18 | 37001280 | 2023 | Maternal depression, alcohol use, and transient effects of perinatal paraprofessional home visiting in South Africa: 8y follow-up cluster RCT | Rotheram-Borus MJ | Soc Sci Med | 10.1016/j.socscimed.2023.115853 | INCLUDE | — |
| 19 | 36806597 | 2023 | A scoping review of counseling interventions for suicide prevention in Africa | Knettel BA | J Affect Disord | 10.1016/j.jad.2023.02.038 | EXCLUDE | Wrong design: scoping review; wrong outcome (suicide) |
| 20 | 36776724 | 2022 | Implementation of a task-shared psychosocial intervention for perinatal depression in South Africa | Davies T | SSM Ment Health | 10.1016/j.ssmmh.2021.100056 | EXCLUDE | Wrong design: qualitative process evaluation |
| 21 | 36669837 | 2023 | Effect of mHealth-supported Healthy Future programme by CHWs on maternal and child health: protocol for cluster RCT | Chen Y | BMJ Open | 10.1136/bmjopen-2022-065403 | EXCLUDE | Protocol without results |
| 22 | 35887543 | 2022 | Predicting Remission among Perinatal Women with Depression in Rural Pakistan: Prognostic Model for Task-Shared Interventions | Waqas A | J Pers Med | 10.3390/jpm12071046 | EXCLUDE | Wrong outcome: prognostic modeling, not effectiveness |
| 23 | 35526062 | 2022 | Health systems strengthening interventions for perinatal CMDs and domestic violence in Cape Town: protocol for pilot | Abrahams Z | Pilot Feasibility Stud | 10.1186/s40814-022-01053-9 | EXCLUDE | Protocol without results |
| 24 | 34942447 | 2022 | Effect of peer support intervention on perinatal depression: A meta-analysis | Fang Q | Gen Hosp Psychiatry | 10.1016/j.genhosppsych.2021.12.001 | EXCLUDE | Wrong design: meta-analysis (mine reference list) |
| 25 | 34903257 | 2021 | Insika Yomama cluster RCT: combined psychological and parenting intervention for HIV+ women depressed in perinatal period | Rochat TJ | Trials | 10.1186/s13063-021-05672-0 | EXCLUDE | Protocol without results |
| 26 | 34618311 | 2021 | Incentive-Based and CHW Package Intervention to Improve Maternal Health and Nutrition: Pilot RCT | Rossouw L | Matern Child Health J | 10.1007/s10995-021-03229-w | INCLUDE | — |
| 27 | 34352116 | 2021 | Primary-level worker interventions for care of people with mental disorders in LMICs (Cochrane Review) | van Ginneken N | Cochrane Database Syst Rev | 10.1002/14651858.CD009149.pub3 | EXCLUDE | Wrong design: Cochrane SR (mine reference list) |
| 28 | 34134027 | 2021 | Effect of a lay counselor delivered integrated maternal mental health and ECD intervention in Siaya County, Kenya | Kim ET | J Affect Disord | 10.1016/j.jad.2021.06.002 | EXCLUDE | Wrong design: quasi-experimental (not RCT) |
| 29 | 34014451 | 2021 | Nurtured in Nature: Pilot RCT to Increase Time in Greenspace among Urban-Dwelling Postpartum Women | South EC | J Urban Health | 10.1007/s11524-021-00544-z | EXCLUDE | HIC setting (US); wrong intervention (greenspace) |
| 30 | 34010505 | 2021 | An integrated parenting intervention for maternal depression and child development in a low-resource setting: Cluster RCT | Husain N | Depress Anxiety | 10.1002/da.23169 | INCLUDE | — |
| 31 | 33944793 | 2021 | Effectiveness of an Integrated Care Package for Refugee Mothers and Children: Protocol for Cluster RCT | Al Azdi Z | JMIR Res Protoc | 10.2196/25047 | EXCLUDE | Protocol without results |
| 32 | 33528371 | 2021 | mHealth-Supported Family Home-Visiting Intervention in Sierra Leone: Protocol for Pilot RCT | Desrosiers A | JMIR Res Protoc | 10.2196/25443 | EXCLUDE | Protocol without results |
| 33 | 33091320 | 2021 | CHW home visiting in deeply rural South Africa: 12-month outcomes | Stansert Katzen L | Glob Public Health | 10.1080/17441692.2020.1833960 | EXCLUDE | Wrong design: non-randomized comparative cohort |
| 34 | 33016883 | 2020 | Expanding Access to Perinatal Depression Treatment in Kenya Through Automated Psychological Support | Green EP | JMIR Form Res | 10.2196/17895 | EXCLUDE | Wrong design: single-case experimental; wrong intervention (chatbot) |
| 35 | 32487250 | 2020 | Problem solving therapy (PST) for pregnant women experiencing IPV in rural Ethiopia: protocol for RCT | Keynejad RC | Trials | 10.1186/s13063-020-04331-0 | EXCLUDE | Protocol without results |
| 36 | 32090783 | 2020 | Effectiveness of Thinking Healthy Programme for perinatal depression delivered through peers: Pooled analysis of 2 RCTs (India and Pakistan) | Vanobberghen F | J Affect Disord | 10.1016/j.jad.2019.11.110 | INCLUDE | — |
| 37 | 31733813 | 2020 | Task-sharing of psychological treatment for antenatal depression in Khayelitsha, South Africa: individual RCT | Lund C | Behav Res Ther | 10.1016/j.brat.2019.103466 | INCLUDE | — |
| 38 | 31157115 | 2019 | Using technology to scale-up training and supervision of CHWs in psychosocial management of perinatal depression: RCT | Rahman A | Glob Ment Health | 10.1017/gmh.2019.7 | EXCLUDE | Wrong outcome: CHW competency (ENACT), not maternal depression |
| 39 | 31143465 | 2019 | Scaling-up psychological interventions: training and supervising peer volunteers to deliver Thinking Healthy Programme in rural Pakistan | Atif N | Glob Ment Health | 10.1017/gmh.2019.4 | EXCLUDE | Wrong outcome: peer competency, not maternal depression |
| 40 | 31033448 | 2019 | Expanding Access to Depression Treatment in Kenya Through Automated Support: Protocol for pilot | Green EP | JMIR Res Protoc | 10.2196/11800 | EXCLUDE | Protocol without results |
| 41 | 30926571 | 2019 | Home Visiting and Antenatal Depression Affect Quality of Mother and Child Interactions in South Africa | Christodoulou J | J Am Acad Child Adolesc Psychiatry | 10.1016/j.jaac.2019.03.016 | EXCLUDE | Wrong outcome: mother-child interaction quality |
| 42 | 29566680 | 2018 | Process evaluations of task sharing interventions for perinatal depression in LMICs: SR and qualitative meta-synthesis | Munodawafa M | BMC Health Serv Res | 10.1186/s12913-018-3030-0 | EXCLUDE | Wrong design: SR & qualitative synthesis |
| 43 | 28666425 | 2017 | Process evaluation of lay counsellor delivering task shared psycho-social intervention for perinatal depression in Khayelitsha, South Africa | Munodawafa M | BMC Psychiatry | 10.1186/s12888-017-1397-9 | EXCLUDE | Wrong design: qualitative process evaluation |
| 44 | 28606206 | 2018 | Antenatal depressed mood and child cognitive and physical growth at 18 months in South Africa: cluster RCT of CHW home visiting | Tomlinson M | Epidemiol Psychiatr Sci | 10.1017/S2045796017000257 | EXCLUDE | Wrong outcome: child cognitive/physical growth |
| 45 | 28349604 | 2017 | Depression Treatment by Non-Mental-Health Providers: Effectiveness of Listening Visits | Brock RL | Am J Community Psychol | 10.1002/ajcp.12129 | EXCLUDE | HIC setting (United States) |
| 46 | 27608926 | 2016 | Effectiveness of peer-delivered Thinking Healthy Plus (THPP+) for maternal depression and child development in Pakistan: protocol for 3y cluster RCT | Turner EL | Trials | 10.1186/s13063-016-1530-y | EXCLUDE | Protocol without results |

---

## 4b. Full-Text Screening Summary

**Date of full-text screening**: 2026-03-14
**Screener**: Andre van Zyl, MPH (with AI-assisted eligibility assessment)

### Decision summary (PubMed records)

| Decision | Count |
|----------|-------|
| INCLUDE | 7 |
| EXCLUDE — Wrong design (SR/MA/scoping review) | 9 |
| EXCLUDE — Protocol without results | 12 |
| EXCLUDE — Wrong design (non-RCT/qualitative) | 7 |
| EXCLUDE — Wrong population | 1 |
| EXCLUDE — HIC setting | 3 |
| EXCLUDE — Wrong outcome | 6 |
| EXCLUDE — Unable to retrieve | 1 |
| **Total screened** | **46** |

### Included studies (7 RCTs)

| PMID | Author | Year | Country | Intervention | Design | Outcome |
|------|--------|------|---------|-------------|--------|---------|
| 41466232 | Wang N | 2025 | China | CHW home visits | RCT (n=592) | DASS-21 |
| 39560615 | Hossain SJ | 2024 | Bangladesh | CHW parenting/nutrition | Cluster RCT (n=547) | SRQ-20 |
| 37001280 | Rotheram-Borus MJ | 2023 | South Africa | Paraprofessional home visiting | Cluster RCT (8y follow-up) | EPDS |
| 34618311 | Rossouw L | 2021 | South Africa | CHW + incentive package | Pilot RCT (n=72) | Depression scale |
| 34010505 | Husain N | 2021 | Pakistan | LTP+ by lay health workers | Cluster RCT (n=774) | EPDS |
| 32090783 | Vanobberghen F | 2020 | India & Pakistan | Peer-delivered THP | Pooled 2 RCTs (n=850) | PHQ-9 |
| 31733813 | Lund C | 2020 | South Africa | CHW psychological treatment | Individual RCT (n=384) | HDRS, EPDS |

### SRs/MAs excluded but flagged for reference list mining

- Prina 2023 (PMID 37183793) — 23 RCTs included
- van Ginneken 2021 (PMID 34352116) — Cochrane, 95 studies
- Fang 2022 (PMID 34942447) — peer support MA

### Notes

- The remaining ~139 records from OpenAlex, Semantic Scholar, and CrossRef databases were not individually screened in this pass. Unique studies from those databases may add to the included set.
- Europe PMC search must still be manually replicated (0 API results due to server issue).
- Reference lists of included SRs should be hand-searched for additional primary RCTs.

---

## 5. Verification Checklist

- [ ] I replicated at least one search from each database via the web interface and confirmed comparable result counts
- [ ] I verified all DOIs resolve to the correct article (via https://doi.org/)
- [ ] I reviewed all supporting quotes against the original source
- [ ] I confirmed that the literature review narrative accurately represents each cited study's findings
- [ ] I verified that no references were fabricated (all have verifiable DOIs or PMIDs)
- [ ] I am satisfied that the search strategy was comprehensive for the review's scope
- [ ] I manually searched Europe PMC to address the 0-result API issue

**Human reviewer signature**: ____________________
**Date reviewed**: ____________________

---

## 6. Search Replication Instructions

### PubMed (https://pubmed.ncbi.nlm.nih.gov/)

1. Go to https://pubmed.ncbi.nlm.nih.gov/advanced/
2. Paste the full Boolean query from Search 1 into the search builder
3. Click "Search"
4. Expected result: ~59 results (may vary slightly over time as new articles are indexed)
5. Verify that key studies appear (e.g., Vanobberghen 2020 PMID 32090783, Lund 2020 PMID 31733813, Prina 2023 PMID 37183793)

### OpenAlex (https://openalex.org/)

1. Go to https://openalex.org/
2. Click "Works" and enter: `community health worker perinatal depression anxiety low-income middle-income countries randomized controlled trial`
3. Filter by type: "Journal Article"
4. Expected result: ~1,400+ results (broad text matching)

### Semantic Scholar (https://www.semanticscholar.org/)

1. Go to https://www.semanticscholar.org/
2. Enter: `community health worker intervention perinatal maternal depression anxiety low-income middle-income countries randomized trial`
3. Filter by "Field of Study: Medicine"
4. Expected result: ~160+ results
5. Note: Semantic Scholar data is CC BY-NC licensed

### Europe PMC (https://europepmc.org/)

1. Go to https://europepmc.org/
2. Enter the Boolean query: `(community health worker OR lay health worker OR peer counselor OR task shifting) AND (perinatal OR maternal OR postpartum) AND (depression OR anxiety) AND (LMIC OR developing countries) AND (randomized OR randomised)`
3. Record the result count
4. **This search MUST be replicated manually** due to the MCP server returning 0 results

### CrossRef (https://search.crossref.org/)

1. Go to https://search.crossref.org/
2. Enter: `community health worker perinatal depression anxiety low-income countries randomized trial`
3. CrossRef provides relevance-ranked results with DOI links for verification
