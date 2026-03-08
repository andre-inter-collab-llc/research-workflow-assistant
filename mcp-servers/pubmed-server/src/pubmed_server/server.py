"""PubMed MCP Server implementation using NCBI E-utilities.

API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
Rate limits: 3 requests/sec without API key, 10 requests/sec with key.
"""

import os
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
API_KEY = os.environ.get("NCBI_API_KEY", "")

mcp = FastMCP(
    "pubmed",
    description="Search PubMed/MEDLINE via NCBI E-utilities",
)


def _base_params() -> dict[str, str]:
    """Return base parameters for all E-utility requests."""
    params: dict[str, str] = {"retmode": "xml"}
    if API_KEY:
        params["api_key"] = API_KEY
    return params


async def _get(client: httpx.AsyncClient, endpoint: str, params: dict[str, str]) -> str:
    """Make a GET request to an E-utility endpoint and return the response text."""
    url = f"{EUTILS_BASE}/{endpoint}"
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.text


def _parse_esearch_ids(xml_text: str) -> tuple[list[str], int]:
    """Parse ESearch XML response and return (list of IDs, total count)."""
    root = ET.fromstring(xml_text)
    count_el = root.find("Count")
    count = int(count_el.text) if count_el is not None and count_el.text else 0
    ids = [id_el.text for id_el in root.findall(".//IdList/Id") if id_el.text]
    return ids, count


def _parse_esummary(xml_text: str) -> list[dict[str, Any]]:
    """Parse ESummary XML response and return list of article summaries."""
    root = ET.fromstring(xml_text)
    articles = []
    for doc in root.findall(".//DocSum"):
        article: dict[str, Any] = {}
        id_el = doc.find("Id")
        if id_el is not None and id_el.text:
            article["pmid"] = id_el.text
        for item in doc.findall("Item"):
            name = item.get("Name", "")
            if name in ("Title", "Source", "PubDate", "FullJournalName", "DOI", "Volume", "Issue", "Pages"):
                article[name.lower()] = item.text or ""
            elif name == "AuthorList":
                authors = [a.text for a in item.findall("Item") if a.text]
                article["authors"] = authors
        articles.append(article)
    return articles


def _parse_efetch_abstracts(xml_text: str) -> list[dict[str, Any]]:
    """Parse EFetch PubMed XML and return article details with abstracts."""
    root = ET.fromstring(xml_text)
    articles = []
    for art in root.findall(".//PubmedArticle"):
        record: dict[str, Any] = {}

        # PMID
        pmid_el = art.find(".//PMID")
        if pmid_el is not None and pmid_el.text:
            record["pmid"] = pmid_el.text

        # Title
        title_el = art.find(".//ArticleTitle")
        if title_el is not None and title_el.text:
            record["title"] = title_el.text

        # Abstract
        abstract_parts = []
        for abs_text in art.findall(".//Abstract/AbstractText"):
            label = abs_text.get("Label", "")
            text = "".join(abs_text.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        record["abstract"] = " ".join(abstract_parts)

        # Authors
        authors = []
        for author in art.findall(".//AuthorList/Author"):
            last = author.find("LastName")
            fore = author.find("ForeName")
            if last is not None and last.text:
                name = last.text
                if fore is not None and fore.text:
                    name = f"{last.text} {fore.text}"
                authors.append(name)
        record["authors"] = authors

        # Journal
        journal_el = art.find(".//Journal/Title")
        if journal_el is not None and journal_el.text:
            record["journal"] = journal_el.text

        # Year
        year_el = art.find(".//PubDate/Year")
        if year_el is not None and year_el.text:
            record["year"] = year_el.text

        # DOI
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi" and aid.text:
                record["doi"] = aid.text

        # MeSH terms
        mesh_terms = []
        for mesh in art.findall(".//MeshHeadingList/MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)
        record["mesh_terms"] = mesh_terms

        # Publication type
        pub_types = []
        for pt in art.findall(".//PublicationTypeList/PublicationType"):
            if pt.text:
                pub_types.append(pt.text)
        record["publication_types"] = pub_types

        articles.append(record)
    return articles


@mcp.tool()
async def search_pubmed(
    query: str,
    max_results: int = 20,
    date_range: str | None = None,
    article_types: str | None = None,
) -> dict[str, Any]:
    """Search PubMed and return article summaries.

    Args:
        query: PubMed search query (supports Boolean operators and field tags).
        max_results: Maximum number of results to return (default 20, max 200).
        date_range: Optional date filter as 'YYYY/MM/DD:YYYY/MM/DD' (mindate:maxdate).
        article_types: Optional publication type filter (e.g., 'Review', 'Clinical Trial').

    Returns:
        Dictionary with 'total_count' and 'articles' list containing summaries.
    """
    max_results = min(max_results, 200)

    # Build search query with filters
    full_query = query
    if article_types:
        full_query += f" AND {article_types}[pt]"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: ESearch to get PMIDs
        search_params = {**_base_params(), "db": "pubmed", "term": full_query, "retmax": str(max_results)}
        if date_range and ":" in date_range:
            parts = date_range.split(":")
            search_params["mindate"] = parts[0]
            search_params["maxdate"] = parts[1]
            search_params["datetype"] = "pdat"

        search_xml = await _get(client, "esearch.fcgi", search_params)
        pmids, total_count = _parse_esearch_ids(search_xml)

        if not pmids:
            return {"total_count": total_count, "articles": []}

        # Step 2: ESummary to get article details
        summary_params = {**_base_params(), "db": "pubmed", "id": ",".join(pmids)}
        summary_xml = await _get(client, "esummary.fcgi", summary_params)
        articles = _parse_esummary(summary_xml)

    return {"total_count": total_count, "articles": articles}


@mcp.tool()
async def fetch_abstract(pmid: str) -> dict[str, Any]:
    """Fetch the full abstract and metadata for a PubMed article by PMID.

    Args:
        pmid: The PubMed ID of the article.

    Returns:
        Dictionary with title, abstract, authors, journal, year, DOI, MeSH terms.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {**_base_params(), "db": "pubmed", "id": pmid}
        xml_text = await _get(client, "efetch.fcgi", params)
        articles = _parse_efetch_abstracts(xml_text)

    if articles:
        return articles[0]
    return {"error": f"No article found for PMID {pmid}"}


@mcp.tool()
async def fetch_mesh_terms(pmid: str) -> dict[str, Any]:
    """Get MeSH headings for a PubMed article.

    Args:
        pmid: The PubMed ID of the article.

    Returns:
        Dictionary with PMID, title, and list of MeSH terms.
    """
    result = await fetch_abstract(pmid)
    return {
        "pmid": result.get("pmid", pmid),
        "title": result.get("title", ""),
        "mesh_terms": result.get("mesh_terms", []),
    }


@mcp.tool()
async def suggest_mesh_terms(keyword: str) -> dict[str, Any]:
    """Suggest MeSH terms for a keyword using ESpell and a PubMed search.

    This helps build controlled-vocabulary search strategies. Returns both
    the suggested spelling correction and MeSH terms found in top results.

    Args:
        keyword: A keyword or phrase to find MeSH terms for.

    Returns:
        Dictionary with spelling suggestion and list of relevant MeSH terms.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: ESpell for spelling correction
        spell_params = {**_base_params(), "db": "pubmed", "term": keyword}
        spell_xml = await _get(client, "espell.fcgi", spell_params)
        spell_root = ET.fromstring(spell_xml)
        corrected_el = spell_root.find("CorrectedQuery")
        corrected = corrected_el.text if corrected_el is not None and corrected_el.text else keyword

        # Step 2: Search for the keyword in MeSH database
        mesh_search_params = {**_base_params(), "db": "mesh", "term": keyword, "retmax": "10"}
        mesh_xml = await _get(client, "esearch.fcgi", mesh_search_params)
        mesh_ids, _ = _parse_esearch_ids(mesh_xml)

        mesh_terms = []
        if mesh_ids:
            # Fetch MeSH term details
            mesh_fetch_params = {**_base_params(), "db": "mesh", "id": ",".join(mesh_ids[:10])}
            mesh_detail_xml = await _get(client, "esummary.fcgi", mesh_fetch_params)
            mesh_root = ET.fromstring(mesh_detail_xml)
            for doc in mesh_root.findall(".//DocSum"):
                for item in doc.findall("Item"):
                    if item.get("Name") == "DS_MeshTerms":
                        for sub in item.findall("Item"):
                            if sub.text:
                                mesh_terms.append(sub.text)

        # Step 3: Also get MeSH terms from top PubMed results for this keyword
        pubmed_params = {**_base_params(), "db": "pubmed", "term": f"{keyword}[MeSH Terms]", "retmax": "5"}
        pubmed_xml = await _get(client, "esearch.fcgi", pubmed_params)
        pubmed_ids, _ = _parse_esearch_ids(pubmed_xml)

        related_mesh = []
        if pubmed_ids:
            fetch_params = {**_base_params(), "db": "pubmed", "id": ",".join(pubmed_ids)}
            fetch_xml = await _get(client, "efetch.fcgi", fetch_params)
            articles = _parse_efetch_abstracts(fetch_xml)
            for art in articles:
                for term in art.get("mesh_terms", []):
                    if term not in related_mesh:
                        related_mesh.append(term)

    return {
        "keyword": keyword,
        "spelling_suggestion": corrected,
        "mesh_terms": mesh_terms,
        "related_mesh_from_pubmed": related_mesh[:20],
    }


@mcp.tool()
async def get_related_articles(pmid: str, max_results: int = 10) -> dict[str, Any]:
    """Find articles related to a given PubMed article using ELink.

    Args:
        pmid: The PubMed ID of the source article.
        max_results: Maximum number of related articles to return (default 10).

    Returns:
        Dictionary with source PMID and list of related article summaries.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # ELink to find related articles
        link_params = {
            **_base_params(),
            "dbfrom": "pubmed",
            "db": "pubmed",
            "id": pmid,
            "cmd": "neighbor_score",
        }
        link_xml = await _get(client, "elink.fcgi", link_params)
        link_root = ET.fromstring(link_xml)

        related_ids = []
        for link_set in link_root.findall(".//LinkSetDb"):
            link_name = link_set.find("LinkName")
            if link_name is not None and link_name.text == "pubmed_pubmed":
                for link in link_set.findall("Link/Id"):
                    if link.text and link.text != pmid:
                        related_ids.append(link.text)
                        if len(related_ids) >= max_results:
                            break

        if not related_ids:
            return {"source_pmid": pmid, "related_articles": []}

        # Get summaries for related articles
        summary_params = {**_base_params(), "db": "pubmed", "id": ",".join(related_ids)}
        summary_xml = await _get(client, "esummary.fcgi", summary_params)
        articles = _parse_esummary(summary_xml)

    return {"source_pmid": pmid, "related_articles": articles}


@mcp.tool()
async def build_search_query(
    population: str,
    intervention_or_exposure: str,
    comparison: str | None = None,
    outcome: str | None = None,
    framework: str = "PICO",
) -> dict[str, Any]:
    """Build a PubMed Boolean search query from structured question elements.

    Constructs a search query using MeSH terms and free-text synonyms for each
    concept, combined with Boolean operators. This is a starting point; the
    researcher should review and refine the query.

    Args:
        population: Description of the target population.
        intervention_or_exposure: The intervention (PICO) or exposure (PEO).
        comparison: Optional comparator group.
        outcome: Optional outcome of interest.
        framework: Question framework used: 'PICO', 'PEO', or 'PCC' (default 'PICO').

    Returns:
        Dictionary with structured query components and a combined Boolean query.
    """
    components: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get MeSH suggestions for each concept
        for label, concept in [
            ("population", population),
            ("intervention_or_exposure", intervention_or_exposure),
            ("comparison", comparison),
            ("outcome", outcome),
        ]:
            if not concept:
                continue

            # Search MeSH for this concept
            mesh_params = {**_base_params(), "db": "mesh", "term": concept, "retmax": "5"}
            mesh_xml = await _get(client, "esearch.fcgi", mesh_params)
            mesh_ids, _ = _parse_esearch_ids(mesh_xml)

            mesh_terms = []
            if mesh_ids:
                detail_params = {**_base_params(), "db": "mesh", "id": ",".join(mesh_ids[:5])}
                detail_xml = await _get(client, "esummary.fcgi", detail_params)
                detail_root = ET.fromstring(detail_xml)
                for doc in detail_root.findall(".//DocSum"):
                    for item in doc.findall("Item"):
                        if item.get("Name") == "DS_MeshTerms":
                            for sub in item.findall("Item"):
                                if sub.text:
                                    mesh_terms.append(sub.text)

            components[label] = {
                "original_term": concept,
                "mesh_terms": mesh_terms[:5],
                "free_text": concept,
            }

    # Build Boolean query
    concept_queries = []
    for label, comp in components.items():
        parts = []
        for mesh in comp["mesh_terms"]:
            parts.append(f'"{mesh}"[MeSH Terms]')
        parts.append(f'"{comp["free_text"]}"[tiab]')
        concept_query = " OR ".join(parts)
        concept_queries.append(f"({concept_query})")

    combined_query = " AND ".join(concept_queries)

    return {
        "framework": framework,
        "components": components,
        "combined_query": combined_query,
        "note": "This is a starting point. Review MeSH terms, add synonyms, and test the query before using it for a systematic review.",
    }


def serve() -> None:
    """Run the PubMed MCP server."""
    mcp.run(transport="stdio")
