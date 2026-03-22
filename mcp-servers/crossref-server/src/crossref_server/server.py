"""CrossRef MCP Server implementation.

API Documentation: https://api.crossref.org/swagger-ui/index.html
Rate limits: Polite pool (50 req/sec) with mailto parameter, otherwise lower.
"""

import logging
import os
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

CROSSREF_BASE = "https://api.crossref.org"
CONTACT_EMAIL = os.environ.get("CROSSREF_EMAIL", "")

mcp = FastMCP(
    "crossref",
    instructions="Search CrossRef for DOI metadata, reference verification, and bibliographic data",
)

register_result_store_tools(mcp)


def _base_params() -> dict[str, str]:
    """Return base parameters including polite pool email."""
    params: dict[str, str] = {}
    if CONTACT_EMAIL:
        params["mailto"] = CONTACT_EMAIL
    return params


def _require_project_path(project_path: str | None) -> str:
    """Validate and normalize project_path for persisted search operations."""
    if not project_path or not project_path.strip():
        raise ValueError(
            "project_path is required. Provide the absolute path to the target project directory."
        )

    resolved = Path(project_path).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(
            f"Invalid project_path: '{project_path}'."
            " It must point to an existing project directory."
        )

    return str(resolved)


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> dict[str, Any]:
    """Make a GET request to CrossRef and return parsed JSON."""
    url = f"{CROSSREF_BASE}/{path}"
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def _format_work(item: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a CrossRef work item."""
    authors = []
    for a in item.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{family}, {given}" if given else family
        if name:
            authors.append(name)

    # Get title
    titles = item.get("title", [])
    title = titles[0] if titles else ""

    # Get container (journal) title
    containers = item.get("container-title", [])
    journal = containers[0] if containers else ""

    # Get publication date
    date_parts = item.get("published-print", {}).get("date-parts", [[]])
    if not date_parts or not date_parts[0]:
        date_parts = item.get("published-online", {}).get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

    return {
        "doi": item.get("DOI", ""),
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "volume": item.get("volume", ""),
        "issue": item.get("issue", ""),
        "page": item.get("page", ""),
        "type": item.get("type", ""),
        "publisher": item.get("publisher", ""),
        "issn": item.get("ISSN", []),
        "is_referenced_by_count": item.get("is-referenced-by-count", 0),
        "references_count": item.get("references-count", 0),
        "url": item.get("URL", ""),
        "abstract": item.get("abstract", ""),
    }


@mcp.tool()
async def search_works(
    query: str,
    project_path: str,
    filters: str | None = None,
    rows: int = 20,
    sort: str = "relevance",
) -> dict[str, Any]:
    """Search CrossRef for bibliographic works.

    Args:
        query: Free-text bibliographic search query.
        filters: CrossRef filter string (e.g., 'from-pub-date:2020,type:journal-article').
            Common filters: from-pub-date, until-pub-date, type, has-abstract,
            has-orcid, is-update. See https://api.crossref.org/swagger-ui/index.html
        rows: Number of results per page (default 20, max 1000).
        sort: Sort field: 'relevance', 'published', 'indexed', 'is-referenced-by-count'.
        project_path: Project directory path. Results are persisted to
            {project_path}/data/search_results.db for later analysis.

    Returns:
        Dictionary with 'total_count' and list of 'works'.
    """
    rows = min(rows, 1000)
    resolved_project_path = _require_project_path(project_path)
    params = {**_base_params(), "query": query, "rows": str(rows), "sort": sort}
    if filters:
        params["filter"] = filters

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "works", params)

    message = data.get("message", {})
    items = message.get("items", [])
    works = [_format_work(item) for item in items]
    total_count = message.get("total-results", 0)

    _store_results(
        resolved_project_path,
        "crossref",
        query,
        works,
        total_count=total_count,
        parameters={"filters": filters, "rows": rows, "sort": sort},
    )

    return {
        "total_count": total_count,
        "works": works,
    }


@mcp.tool()
async def search_works_scripted(
    query: str,
    filters: str | None = None,
    rows: int = 20,
    sort: str = "relevance",
    project_path: str = ".",
) -> dict[str, Any]:
    """Search CrossRef and save a reproducible script to the project.

    Like search_works, but generates a standalone Python script in
    {project_path}/scripts/ that can be re-run independently.

    Falls back to the standard search if the script fails.

    Args:
        query: Free-text bibliographic search query.
        filters: CrossRef filter string.
        rows: Number of results (default 20, max 1000).
        sort: Sort field.
        project_path: Project directory path for script and result storage.

    Returns:
        Dictionary with total_count, works list, and script_path.
    """
    rows = min(rows, 1000)
    params = {"filters": filters, "rows": rows, "sort": sort}

    script_result = generate_and_run_script(project_path, "crossref", query, params)

    if script_result is not None:
        results, total_count, search_id, script_path = script_result
        return {
            "total_count": total_count,
            "works": results,
            "script_path": script_path,
            "search_id": search_id,
        }

    logger.warning("Script execution failed for CrossRef, falling back to direct API call")
    return await search_works(
        query=query,
        filters=filters,
        rows=rows,
        sort=sort,
        project_path=project_path,
    )


@mcp.tool()
async def get_work_by_doi(doi: str) -> dict[str, Any]:
    """Get full metadata for a work by its DOI.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/s41586-020-2649-2').

    Returns:
        Full bibliographic metadata for the work.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"works/{doi}", _base_params())

    item = data.get("message", {})
    return _format_work(item)


@mcp.tool()
async def get_references_by_doi(doi: str) -> dict[str, Any]:
    """Get the reference list for a work by its DOI.

    Args:
        doi: Digital Object Identifier of the citing work.

    Returns:
        Dictionary with the source DOI and its list of references.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"works/{doi}", _base_params())

    item = data.get("message", {})
    raw_refs = item.get("reference", [])

    references = []
    for ref in raw_refs:
        references.append(
            {
                "doi": ref.get("DOI", ""),
                "key": ref.get("key", ""),
                "unstructured": ref.get("unstructured", ""),
                "article_title": ref.get("article-title", ""),
                "author": ref.get("author", ""),
                "year": ref.get("year", ""),
                "journal_title": ref.get("journal-title", ""),
                "volume": ref.get("volume", ""),
                "first_page": ref.get("first-page", ""),
            }
        )

    return {
        "source_doi": doi,
        "reference_count": len(references),
        "references": references,
    }


@mcp.tool()
async def check_doi(doi: str) -> dict[str, Any]:
    """Validate whether a DOI exists and retrieve basic metadata.

    Useful for verifying references are not hallucinated.

    Args:
        doi: Digital Object Identifier to check (e.g., '10.1038/s41586-020-2649-2').

    Returns:
        Dictionary with 'valid' boolean and metadata if the DOI exists.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await _get(client, f"works/{doi}", _base_params())

        item = data.get("message", {})
        titles = item.get("title", [])
        return {
            "doi": doi,
            "valid": True,
            "title": titles[0] if titles else "",
            "type": item.get("type", ""),
            "publisher": item.get("publisher", ""),
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"doi": doi, "valid": False, "error": "DOI not found in CrossRef"}
        raise


def serve() -> None:
    """Run the CrossRef MCP server."""
    mcp.run(transport="stdio")
