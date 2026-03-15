"""OpenAlex MCP Server implementation.

API Documentation: https://developers.openalex.org/
Authentication: Free API key required. Get yours at https://openalex.org/settings/api-key
Rate limits: 100 requests/sec, $1/day free budget.
"""

import logging
import os
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

OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")

mcp = FastMCP(
    "openalex",
    instructions="Search OpenAlex for academic works, authors, sources, and concepts",
)

register_result_store_tools(mcp)


def _base_params() -> dict[str, str]:
    """Return base parameters for all OpenAlex requests."""
    params: dict[str, str] = {}
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    return params


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, str]) -> dict[str, Any]:
    """Make a GET request to OpenAlex and return parsed JSON."""
    url = f"{OPENALEX_BASE}/{path}"
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def _format_work(work: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from an OpenAlex work object."""
    authorships = work.get("authorships", [])
    authors = []
    for a in authorships:
        author_info = a.get("author", {})
        name = author_info.get("display_name", "")
        if name:
            authors.append(name)

    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}

    return {
        "openalex_id": work.get("id", ""),
        "doi": work.get("doi", ""),
        "title": work.get("title", ""),
        "publication_year": work.get("publication_year"),
        "type": work.get("type", ""),
        "authors": authors,
        "journal": source.get("display_name", ""),
        "is_oa": work.get("open_access", {}).get("is_oa", False),
        "oa_url": work.get("open_access", {}).get("oa_url", ""),
        "cited_by_count": work.get("cited_by_count", 0),
        "abstract_inverted_index": bool(work.get("abstract_inverted_index")),
        "concepts": [
            {"name": c.get("display_name", ""), "score": c.get("score", 0)}
            for c in (work.get("concepts") or [])[:5]
        ],
        "pmid": work.get("ids", {}).get("pmid", ""),
    }


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


@mcp.tool()
async def search_works(
    query: str,
    filters: str | None = None,
    sort: str = "relevance_score:desc",
    per_page: int = 20,
    project_path: str | None = None,
) -> dict[str, Any]:
    """Search OpenAlex for academic works (articles, books, datasets, etc.).

    Covers 250M+ works across all disciplines.

    Args:
        query: Full-text search query.
        filters: OpenAlex filter string (e.g., 'publication_year:2020-2024,type:article').
            Common filters: publication_year, type, is_oa, concepts.id, authorships.author.id.
            See https://developers.openalex.org/guides/filtering
        sort: Sort order. Options: relevance_score:desc, cited_by_count:desc,
            publication_date:desc, publication_date:asc. Default: relevance_score:desc.
        per_page: Results per page (default 20, max 200).
        project_path: Optional project directory path. When provided, results are
            persisted to {project_path}/data/search_results.db for later analysis.

    Returns:
        Dictionary with 'total_count' and 'works' list.
    """
    per_page = min(per_page, 200)
    params = {**_base_params(), "search": query, "sort": sort, "per_page": str(per_page)}
    if filters:
        params["filter"] = filters

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "works", params)

    works = [_format_work(w) for w in data.get("results", [])]
    total_count = data.get("meta", {}).get("count", 0)

    if project_path:
        try:
            _store_results(
                project_path,
                "openalex",
                query,
                works,
                total_count=total_count,
                parameters={"filters": filters, "sort": sort, "per_page": per_page},
            )
        except Exception:
            logger.warning("Failed to store OpenAlex search results", exc_info=True)

    return {
        "total_count": total_count,
        "works": works,
    }


@mcp.tool()
async def search_works_scripted(
    query: str,
    filters: str | None = None,
    sort: str = "relevance_score:desc",
    per_page: int = 20,
    project_path: str = ".",
) -> dict[str, Any]:
    """Search OpenAlex and save a reproducible script to the project.

    Like search_works, but generates a standalone Python script in
    {project_path}/scripts/ that can be re-run independently.

    Falls back to the standard search if the script fails.

    Args:
        query: Full-text search query.
        filters: OpenAlex filter string.
        sort: Sort order.
        per_page: Results per page (default 20, max 200).
        project_path: Project directory path for script and result storage.

    Returns:
        Dictionary with total_count, works list, and script_path.
    """
    per_page = min(per_page, 200)
    params = {"filters": filters, "sort": sort, "per_page": per_page}

    script_result = generate_and_run_script(project_path, "openalex", query, params)

    if script_result is not None:
        results, total_count, search_id, script_path = script_result
        return {
            "total_count": total_count,
            "works": results,
            "script_path": script_path,
            "search_id": search_id,
        }

    logger.warning("Script execution failed for OpenAlex, falling back to direct API call")
    return await search_works(
        query=query,
        filters=filters,
        sort=sort,
        per_page=per_page,
        project_path=project_path,
    )


@mcp.tool()
async def get_work(identifier: str) -> dict[str, Any]:
    """Get detailed metadata for a single work by OpenAlex ID, DOI, or PMID.

    Args:
        identifier: OpenAlex ID (e.g., 'W2741809807'), DOI (e.g., '10.1038/s41586-020-2649-2'),
            or PMID (e.g., 'pmid:32839624').

    Returns:
        Detailed work metadata including abstract (if available).
    """
    # Normalize identifier
    if identifier.startswith("10."):
        identifier = f"https://doi.org/{identifier}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, f"works/{identifier}", _base_params())

    result = _format_work(data)
    result["abstract"] = _reconstruct_abstract(data.get("abstract_inverted_index"))
    return result


@mcp.tool()
async def get_cited_by(work_id: str, per_page: int = 25) -> dict[str, Any]:
    """Get works that cite a given work (forward citations).

    Args:
        work_id: OpenAlex ID of the source work (e.g., 'W2741809807').
        per_page: Number of citing works to return (default 25, max 100).

    Returns:
        Dictionary with 'total_count' and the list of citing 'works'.
    """
    per_page = min(per_page, 100)
    params = {
        **_base_params(),
        "filter": f"cites:{work_id}",
        "sort": "cited_by_count:desc",
        "per_page": str(per_page),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "works", params)

    works = [_format_work(w) for w in data.get("results", [])]
    return {
        "source_work": work_id,
        "total_count": data.get("meta", {}).get("count", 0),
        "citing_works": works,
    }


@mcp.tool()
async def get_references(work_id: str, per_page: int = 25) -> dict[str, Any]:
    """Get works referenced by a given work (backward references).

    Args:
        work_id: OpenAlex ID of the source work (e.g., 'W2741809807').
        per_page: Number of referenced works to return (default 25, max 100).

    Returns:
        Dictionary with 'total_count' and the list of referenced 'works'.
    """
    per_page = min(per_page, 100)
    params = {
        **_base_params(),
        "filter": f"cited_by:{work_id}",
        "per_page": str(per_page),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "works", params)

    works = [_format_work(w) for w in data.get("results", [])]
    return {
        "source_work": work_id,
        "total_count": data.get("meta", {}).get("count", 0),
        "referenced_works": works,
    }


@mcp.tool()
async def get_concepts(query: str, per_page: int = 20) -> dict[str, Any]:
    """Search the OpenAlex concept hierarchy (topics and fields of study).

    Concepts in OpenAlex form a hierarchy from broad fields (Level 0) to
    specific topics (Level 5). Useful for discovering related topics and
    cross-disciplinary connections.

    Args:
        query: Search query for concepts.
        per_page: Number of results (default 20, max 100).

    Returns:
        Dictionary with matching concepts including hierarchy level,
        work count, and related concepts.
    """
    per_page = min(per_page, 100)
    params = {**_base_params(), "search": query, "per_page": str(per_page)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "concepts", params)

    concepts = []
    for c in data.get("results", []):
        concepts.append(
            {
                "openalex_id": c.get("id", ""),
                "display_name": c.get("display_name", ""),
                "level": c.get("level"),
                "description": c.get("description", ""),
                "works_count": c.get("works_count", 0),
                "related_concepts": [
                    {
                        "name": rc.get("display_name", ""),
                        "level": rc.get("level"),
                        "score": rc.get("score", 0),
                    }
                    for rc in (c.get("related_concepts") or [])[:5]
                ],
            }
        )

    return {"total_count": data.get("meta", {}).get("count", 0), "concepts": concepts}


@mcp.tool()
async def get_author_works(author_id: str, per_page: int = 25) -> dict[str, Any]:
    """Get an author's profile and publication list.

    Args:
        author_id: OpenAlex author ID (e.g., 'A5023888391') or ORCID
            (e.g., 'https://orcid.org/0000-0002-1825-0097').

    Returns:
        Dictionary with author profile and list of their works.
    """
    per_page = min(per_page, 100)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get author profile
        author = await _get(client, f"authors/{author_id}", _base_params())

        # Get their works
        params = {
            **_base_params(),
            "filter": f"authorships.author.id:{author.get('id', author_id)}",
            "sort": "publication_date:desc",
            "per_page": str(per_page),
        }
        works_data = await _get(client, "works", params)

    works = [_format_work(w) for w in works_data.get("results", [])]
    return {
        "author": {
            "openalex_id": author.get("id", ""),
            "display_name": author.get("display_name", ""),
            "orcid": author.get("orcid", ""),
            "works_count": author.get("works_count", 0),
            "cited_by_count": author.get("cited_by_count", 0),
            "h_index": author.get("summary_stats", {}).get("h_index", 0),
            "affiliations": [
                inst.get("display_name", "") for inst in (author.get("affiliations") or [])[:3]
            ],
        },
        "works": works,
    }


@mcp.tool()
async def search_sources(query: str, per_page: int = 20) -> dict[str, Any]:
    """Search for journals, repositories, and other publication sources.

    Args:
        query: Search query for source/journal names.
        per_page: Number of results (default 20, max 100).

    Returns:
        Dictionary with matching sources and their metadata.
    """
    per_page = min(per_page, 100)
    params = {**_base_params(), "search": query, "per_page": str(per_page)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await _get(client, "sources", params)

    sources = []
    for s in data.get("results", []):
        sources.append(
            {
                "openalex_id": s.get("id", ""),
                "display_name": s.get("display_name", ""),
                "type": s.get("type", ""),
                "issn_l": s.get("issn_l", ""),
                "is_oa": s.get("is_oa", False),
                "works_count": s.get("works_count", 0),
                "cited_by_count": s.get("cited_by_count", 0),
                "homepage_url": s.get("homepage_url", ""),
            }
        )

    return {"total_count": data.get("meta", {}).get("count", 0), "sources": sources}


def serve() -> None:
    """Run the OpenAlex MCP server."""
    mcp.run(transport="stdio")
