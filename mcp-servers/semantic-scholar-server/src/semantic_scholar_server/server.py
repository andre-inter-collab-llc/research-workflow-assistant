"""Semantic Scholar MCP Server implementation.

API Documentation: https://api.semanticscholar.org/api-docs/
License: https://www.semanticscholar.org/product/api/license
Rate limits: 1 req/sec (unauthenticated), higher with API key.
Retry policy: Exponential backoff on 429 responses per license terms.
"""

import asyncio
import logging
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from rwa_result_store import register_result_store_tools, store_results as _store_results

logger = logging.getLogger(__name__)

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_RECS_BASE = "https://api.semanticscholar.org/recommendations/v1"
API_KEY = os.environ.get("S2_API_KEY", "")

MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds

PAPER_FIELDS = ",".join([
    "paperId", "externalIds", "title", "abstract", "year", "venue",
    "publicationVenue", "authors", "citationCount", "referenceCount",
    "isOpenAccess", "openAccessPdf", "fieldsOfStudy", "tldr",
])

AUTHOR_FIELDS = "authorId,externalIds,name,affiliations,paperCount,citationCount,hIndex"

mcp = FastMCP(
    "semantic-scholar",
    instructions=(
        "Search Semantic Scholar Academic Graph for papers, citations, and recommendations. "
        "Data is licensed CC BY-NC. Publications using this data must cite: "
        "Kinney et al. (2023) 'The Semantic Scholar Open Data Platform' ArXiv abs/2301.10140."
    ),
)

register_result_store_tools(mcp)


def _headers() -> dict[str, str]:
    """Return request headers including API key if available."""
    headers: dict[str, str] = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return headers


async def _request_with_backoff(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff on 429 responses."""
    for attempt in range(MAX_RETRIES + 1):
        resp = await client.request(method, url, headers=_headers(), **kwargs)
        if resp.status_code != 429 or attempt == MAX_RETRIES:
            resp.raise_for_status()
            return resp
        wait = BASE_BACKOFF * (2 ** attempt)
        logger.warning("S2 rate limited (429). Retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, MAX_RETRIES)
        await asyncio.sleep(wait)
    return resp  # unreachable, but satisfies type checker


async def _get(client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    """Make a GET request with retry and return parsed JSON."""
    resp = await _request_with_backoff(client, "GET", url, params=params)
    return resp.json()


async def _post(client: httpx.AsyncClient, url: str, json_data: dict[str, Any]) -> dict[str, Any]:
    """Make a POST request with retry and return parsed JSON."""
    resp = await _request_with_backoff(client, "POST", url, json=json_data)
    return resp.json()


def _format_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from an S2 paper object."""
    external_ids = paper.get("externalIds") or {}
    tldr = paper.get("tldr") or {}
    oa_pdf = paper.get("openAccessPdf") or {}
    pub_venue = paper.get("publicationVenue") or {}

    return {
        "paper_id": paper.get("paperId", ""),
        "doi": external_ids.get("DOI", ""),
        "pmid": external_ids.get("PubMed", ""),
        "arxiv_id": external_ids.get("ArXiv", ""),
        "title": paper.get("title", ""),
        "abstract": paper.get("abstract", ""),
        "year": paper.get("year"),
        "venue": pub_venue.get("name", "") or paper.get("venue", ""),
        "authors": [
            {"name": a.get("name", ""), "author_id": a.get("authorId", "")}
            for a in (paper.get("authors") or [])
        ],
        "citation_count": paper.get("citationCount", 0),
        "reference_count": paper.get("referenceCount", 0),
        "is_open_access": paper.get("isOpenAccess", False),
        "open_access_pdf": oa_pdf.get("url", ""),
        "fields_of_study": paper.get("fieldsOfStudy") or [],
        "tldr": tldr.get("text", ""),
    }


@mcp.tool()
async def search_papers(
    query: str,
    year_range: str | None = None,
    fields_of_study: str | None = None,
    open_access_only: bool = False,
    limit: int = 20,
    project_path: str | None = None,
) -> dict[str, Any]:
    """Search Semantic Scholar for academic papers.

    Args:
        query: Search query string.
        year_range: Optional year filter as 'YYYY-YYYY' (e.g., '2020-2024').
        fields_of_study: Comma-separated fields (e.g., 'Medicine,Computer Science').
        open_access_only: If True, only return open access papers.
        limit: Maximum results (default 20, max 100).
        project_path: Optional project directory path. When provided, results are
            persisted to {project_path}/data/search_results.db for later analysis.

    Returns:
        Dictionary with 'total' count and list of 'papers'.
    """
    limit = min(limit, 100)
    params: dict[str, str] = {"query": query, "limit": str(limit), "fields": PAPER_FIELDS}

    if year_range and "-" in year_range:
        params["year"] = year_range
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if open_access_only:
        params["openAccessPdf"] = ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{S2_BASE}/paper/search", params)

    papers = [_format_paper(p) for p in data.get("data", [])]
    total = data.get("total", 0)

    if project_path:
        try:
            _store_results(
                project_path, "semantic_scholar", query, papers,
                total_count=total,
                parameters={"year_range": year_range, "fields_of_study": fields_of_study,
                            "open_access_only": open_access_only, "limit": limit},
            )
        except Exception:
            logger.warning("Failed to store Semantic Scholar search results", exc_info=True)

    return {"total": total, "papers": papers}


@mcp.tool()
async def get_paper(paper_id: str) -> dict[str, Any]:
    """Get detailed metadata for a single paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI (prefixed with 'DOI:'),
            PMID (prefixed with 'PMID:'), or ArXiv ID (prefixed with 'ARXIV:').
            Examples: 'DOI:10.1038/s41586-020-2649-2', 'PMID:32839624'.

    Returns:
        Detailed paper metadata including abstract and TLDR.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{S2_BASE}/paper/{paper_id}", {"fields": PAPER_FIELDS})

    return _format_paper(data)


@mcp.tool()
async def get_citations(paper_id: str, limit: int = 50) -> dict[str, Any]:
    """Get papers that cite a given paper (forward citations).

    Args:
        paper_id: Semantic Scholar paper ID, DOI (with 'DOI:' prefix), or PMID (with 'PMID:' prefix).
        limit: Maximum number of citations to return (default 50, max 1000).

    Returns:
        Dictionary with source paper ID and list of citing papers.
    """
    limit = min(limit, 1000)
    fields = "paperId,externalIds,title,year,authors,citationCount,isOpenAccess"
    params: dict[str, str] = {"fields": fields, "limit": str(limit)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{S2_BASE}/paper/{paper_id}/citations", params)

    citations = []
    for item in data.get("data", []):
        citing = item.get("citingPaper", {})
        if citing.get("paperId"):
            citations.append({
                "paper_id": citing.get("paperId", ""),
                "doi": (citing.get("externalIds") or {}).get("DOI", ""),
                "title": citing.get("title", ""),
                "year": citing.get("year"),
                "authors": [a.get("name", "") for a in (citing.get("authors") or [])],
                "citation_count": citing.get("citationCount", 0),
            })

    return {"source_paper": paper_id, "total": len(citations), "citations": citations}


@mcp.tool()
async def get_references(paper_id: str, limit: int = 50) -> dict[str, Any]:
    """Get papers referenced by a given paper (backward references).

    Args:
        paper_id: Semantic Scholar paper ID, DOI (with 'DOI:' prefix), or PMID (with 'PMID:' prefix).
        limit: Maximum number of references to return (default 50, max 1000).

    Returns:
        Dictionary with source paper ID and list of referenced papers.
    """
    limit = min(limit, 1000)
    fields = "paperId,externalIds,title,year,authors,citationCount,isOpenAccess"
    params: dict[str, str] = {"fields": fields, "limit": str(limit)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{S2_BASE}/paper/{paper_id}/references", params)

    refs = []
    for item in data.get("data", []):
        cited = item.get("citedPaper", {})
        if cited.get("paperId"):
            refs.append({
                "paper_id": cited.get("paperId", ""),
                "doi": (cited.get("externalIds") or {}).get("DOI", ""),
                "title": cited.get("title", ""),
                "year": cited.get("year"),
                "authors": [a.get("name", "") for a in (cited.get("authors") or [])],
                "citation_count": cited.get("citationCount", 0),
            })

    return {"source_paper": paper_id, "total": len(refs), "references": refs}


@mcp.tool()
async def get_recommendations(paper_ids: list[str], limit: int = 20) -> dict[str, Any]:
    """Get paper recommendations based on a set of seed papers.

    Uses Semantic Scholar's recommendation engine to suggest related papers.

    Args:
        paper_ids: List of Semantic Scholar paper IDs to use as seeds (1-5 papers).
        limit: Maximum recommendations to return (default 20, max 500).

    Returns:
        Dictionary with seed papers and list of recommended papers.
    """
    limit = min(limit, 500)
    seed_ids = paper_ids[:5]

    async with httpx.AsyncClient(timeout=30.0) as client:
        if len(seed_ids) == 1:
            # Single-paper recommendations
            params: dict[str, str] = {
                "fields": PAPER_FIELDS,
                "limit": str(limit),
            }
            data = await _get(
                client,
                f"{S2_RECS_BASE}/papers/forpaper/{seed_ids[0]}",
                params,
            )
        else:
            # Multi-paper recommendations via POST
            data = await _post(
                client,
                f"{S2_RECS_BASE}/papers/",
                {
                    "positivePaperIds": seed_ids,
                    "fields": PAPER_FIELDS,
                    "limit": limit,
                },
            )

    papers = [_format_paper(p) for p in data.get("recommendedPapers", [])]
    return {"seed_papers": seed_ids, "recommendations": papers}


@mcp.tool()
async def get_author(author_id: str) -> dict[str, Any]:
    """Get an author's profile including h-index and publication metrics.

    Args:
        author_id: Semantic Scholar author ID (numeric string).

    Returns:
        Author profile with metrics and recent papers.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Author profile
        author = await _get(client, f"{S2_BASE}/author/{author_id}", {"fields": AUTHOR_FIELDS})

        # Recent papers
        paper_fields = "paperId,title,year,citationCount,venue"
        papers_data = await _get(
            client,
            f"{S2_BASE}/author/{author_id}/papers",
            {"fields": paper_fields, "limit": "10"},
        )

    external_ids = author.get("externalIds") or {}
    return {
        "author_id": author.get("authorId", ""),
        "name": author.get("name", ""),
        "orcid": external_ids.get("ORCID", ""),
        "affiliations": author.get("affiliations") or [],
        "paper_count": author.get("paperCount", 0),
        "citation_count": author.get("citationCount", 0),
        "h_index": author.get("hIndex", 0),
        "recent_papers": [
            {
                "paper_id": p.get("paperId", ""),
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citation_count": p.get("citationCount", 0),
                "venue": p.get("venue", ""),
            }
            for p in papers_data.get("data", [])
        ],
    }


def serve() -> None:
    """Run the Semantic Scholar MCP server."""
    mcp.run(transport="stdio")
