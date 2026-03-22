"""Europe PMC MCP Server implementation.

API Documentation: https://europepmc.org/RestfulWebService
Rate limits: No explicit limit, but be respectful.
"""

import logging
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from rwa_result_store import (
    generate_and_run_script,
    register_result_store_tools,
)
from rwa_result_store import (
    store_results as _store_results,
)

logger = logging.getLogger(__name__)

EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"

mcp = FastMCP(
    "europe-pmc",
    instructions="Search Europe PMC for biomedical and life sciences literature",
)

register_result_store_tools(mcp)


def _require_project_path(project_path: str | None) -> str:
    """Validate and normalize project_path for persisted search operations."""
    if not project_path or not project_path.strip():
        raise ValueError(
            "project_path is required. Provide the absolute path to the target project directory."
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(
            f"Invalid project_path: '{project_path}'. It must point to an existing project directory."
        )

    return str(resolved)


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> dict[str, Any]:
    """Make a GET request to Europe PMC and return parsed JSON."""
    url = f"{EPMC_BASE}/{path}"
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def _format_result(r: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a Europe PMC search result."""
    return {
        "id": r.get("id", ""),
        "source": r.get("source", ""),
        "pmid": r.get("pmid", ""),
        "pmcid": r.get("pmcid", ""),
        "doi": r.get("doi", ""),
        "title": r.get("title", ""),
        "authors": r.get("authorString", ""),
        "journal": r.get("journalTitle", ""),
        "year": r.get("pubYear", ""),
        "abstract": r.get("abstractText", ""),
        "is_open_access": r.get("isOpenAccess", "N") == "Y",
        "cited_by_count": r.get("citedByCount", 0),
        "first_publication_date": r.get("firstPublicationDate", ""),
        "publication_type": r.get("pubType", ""),
    }


@mcp.tool()
async def search_europepmc(
    query: str,
    result_type: str = "core",
    page_size: int = 25,
    sort: str = "relevance",
    open_access_only: bool = False,
    project_path: str,
) -> dict[str, Any]:
    """Search Europe PMC for biomedical and life sciences literature.

    Covers PubMed, PubMed Central, Agricola, and other sources.

    Args:
        query: Search query. Supports Europe PMC query syntax including field tags
            (e.g., 'AUTH:"Smith J" AND TITLE:diabetes').
        result_type: 'core' (full metadata) or 'lite' (minimal). Default 'core'.
        page_size: Results per page (default 25, max 1000).
        sort: Sort order: 'relevance', 'date', or 'cited'. Default 'relevance'.
        open_access_only: If True, only return open access articles.
        project_path: Project directory path. Results are persisted to
            {project_path}/data/search_results.db for later analysis.

    Returns:
        Dictionary with 'total_count' and list of 'results'.
    """
    page_size = min(page_size, 1000)
    resolved_project_path = _require_project_path(project_path)
    full_query = query
    if open_access_only:
        full_query += " AND OPEN_ACCESS:y"

    sort_map = {"relevance": "RELEVANCE", "date": "P_PDATE_D desc", "cited": "CITED desc"}
    params: dict[str, str] = {
        "query": full_query,
        "resultType": result_type,
        "pageSize": str(page_size),
        "sort": sort_map.get(sort, "RELEVANCE"),
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "search", params)

    result_list = data.get("resultList", {}).get("result", [])
    results = [_format_result(r) for r in result_list]
    total_count = data.get("hitCount", 0)

    _store_results(
        resolved_project_path,
        "europe_pmc",
        query,
        results,
        total_count=total_count,
        parameters={
            "result_type": result_type,
            "page_size": page_size,
            "sort": sort,
            "open_access_only": open_access_only,
        },
    )

    return {
        "total_count": total_count,
        "results": results,
    }


@mcp.tool()
async def search_europepmc_scripted(
    query: str,
    result_type: str = "core",
    page_size: int = 25,
    sort: str = "relevance",
    open_access_only: bool = False,
    project_path: str = ".",
) -> dict[str, Any]:
    """Search Europe PMC and save a reproducible script to the project.

    Like search_europepmc, but generates a standalone Python script in
    {project_path}/scripts/ that can be re-run independently.

    Falls back to the standard search if the script fails.

    Args:
        query: Search query (supports Europe PMC syntax).
        result_type: 'core' or 'lite'.
        page_size: Results per page (default 25, max 1000).
        sort: Sort order: 'relevance', 'date', or 'cited'.
        open_access_only: If True, only open access articles.
        project_path: Project directory path for script and result storage.

    Returns:
        Dictionary with total_count, results list, and script_path.
    """
    page_size = min(page_size, 1000)
    params = {
        "result_type": result_type,
        "page_size": page_size,
        "sort": sort,
        "open_access_only": open_access_only,
    }

    script_result = generate_and_run_script(project_path, "europe_pmc", query, params)

    if script_result is not None:
        results_list, total_count, search_id, script_path = script_result
        return {
            "total_count": total_count,
            "results": results_list,
            "script_path": script_path,
            "search_id": search_id,
        }

    logger.warning("Script execution failed for Europe PMC, falling back to direct API call")
    return await search_europepmc(
        query=query,
        result_type=result_type,
        page_size=page_size,
        sort=sort,
        open_access_only=open_access_only,
        project_path=project_path,
    )


@mcp.tool()
async def get_full_text(pmcid: str) -> dict[str, Any]:
    """Retrieve the full text of an open access article from PMC.

    Args:
        pmcid: PubMed Central ID (e.g., 'PMC7029158').

    Returns:
        Dictionary with article ID and full text XML content (if available).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{EPMC_BASE}/{pmcid}/fullTextXML"
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.text

    if content.strip().startswith("<?xml") or content.strip().startswith("<"):
        return {"pmcid": pmcid, "format": "xml", "full_text": content}
    return {"pmcid": pmcid, "error": "Full text not available for this article"}


@mcp.tool()
async def get_citations(source: str, ext_id: str, page_size: int = 25) -> dict[str, Any]:
    """Get articles that cite a given article (forward citations).

    Args:
        source: Source database ('MED' for PubMed, 'PMC' for PubMed Central).
        ext_id: Article ID in the source database (PMID or PMCID).
        page_size: Number of results (default 25, max 1000).

    Returns:
        Dictionary with citation count and list of citing articles.
    """
    page_size = min(page_size, 1000)
    params: dict[str, str] = {
        "format": "json",
        "pageSize": str(page_size),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{source}/{ext_id}/citations", params)

    citation_list = data.get("citationList", {}).get("citation", [])
    citations = []
    for c in citation_list:
        citations.append(
            {
                "id": c.get("id", ""),
                "source": c.get("source", ""),
                "title": c.get("title", ""),
                "authors": c.get("authorString", ""),
                "journal": c.get("journalAbbreviation", ""),
                "year": c.get("pubYear", ""),
            }
        )

    return {
        "source_id": f"{source}/{ext_id}",
        "total_count": data.get("hitCount", 0),
        "citations": citations,
    }


@mcp.tool()
async def get_references(source: str, ext_id: str, page_size: int = 25) -> dict[str, Any]:
    """Get articles referenced by a given article (backward references).

    Args:
        source: Source database ('MED' for PubMed, 'PMC' for PubMed Central).
        ext_id: Article ID in the source database (PMID or PMCID).
        page_size: Number of results (default 25, max 1000).

    Returns:
        Dictionary with reference count and list of referenced articles.
    """
    page_size = min(page_size, 1000)
    params: dict[str, str] = {
        "format": "json",
        "pageSize": str(page_size),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"{source}/{ext_id}/references", params)

    ref_list = data.get("referenceList", {}).get("reference", [])
    refs = []
    for r in ref_list:
        refs.append(
            {
                "id": r.get("id", ""),
                "source": r.get("source", ""),
                "title": r.get("title", ""),
                "authors": r.get("authorString", ""),
                "journal": r.get("journalAbbreviation", ""),
                "year": r.get("pubYear", ""),
            }
        )

    return {
        "source_id": f"{source}/{ext_id}",
        "total_count": data.get("hitCount", 0),
        "references": refs,
    }


@mcp.tool()
async def get_text_mined_terms(pmcid: str) -> dict[str, Any]:
    """Get text-mined annotations from an article (genes, diseases, chemicals, etc.).

    Europe PMC applies text mining to open access articles to extract named entities.

    Args:
        pmcid: PubMed Central ID (e.g., 'PMC7029158').

    Returns:
        Dictionary with annotations grouped by type (Gene, Disease, Chemical, etc.).
    """
    params: dict[str, str] = {"format": "json", "pageSize": "1000"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"PMC/{pmcid}/textMinedTerms", params)

    terms_by_type: dict[str, list[dict[str, Any]]] = {}
    for term in data.get("semanticTypeList", {}).get("semanticType", []):
        sem_type = term.get("name", "Unknown")
        for t in term.get("tmSummary", []):
            entry = {
                "term": t.get("term", ""),
                "count": t.get("count", 0),
                "database_id": t.get("dbId", ""),
                "database_name": t.get("dbName", ""),
            }
            terms_by_type.setdefault(sem_type, []).append(entry)

    return {"pmcid": pmcid, "annotations": terms_by_type}


def serve() -> None:
    """Run the Europe PMC MCP server."""
    mcp.run(transport="stdio")
