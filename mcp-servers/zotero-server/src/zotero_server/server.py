"""Zotero MCP Server implementation.

API Documentation: https://www.zotero.org/support/dev/web_api/v3/start
Rate limits: Not explicitly documented; be respectful.
Requires: ZOTERO_API_KEY and ZOTERO_USER_ID environment variables.
"""

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

ZOTERO_BASE = "https://api.zotero.org"
API_KEY = os.environ.get("ZOTERO_API_KEY", "")
USER_ID = os.environ.get("ZOTERO_USER_ID", "")

mcp = FastMCP(
    "zotero",
    instructions="Manage Zotero reference library: search, add, organize, and export citations",
)


def _headers() -> dict[str, str]:
    """Return authentication headers for Zotero API."""
    return {
        "Zotero-API-Key": API_KEY,
        "Zotero-API-Version": "3",
    }


def _user_url(path: str) -> str:
    """Build a user-scoped API URL."""
    return f"{ZOTERO_BASE}/users/{USER_ID}/{path}"


async def _get(client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None) -> Any:
    """Make a GET request to Zotero API."""
    resp = await client.get(url, headers=_headers(), params=params or {})
    resp.raise_for_status()
    return resp.json()


async def _post(client: httpx.AsyncClient, url: str, json_data: Any) -> Any:
    """Make a POST request to Zotero API."""
    resp = await client.post(url, headers={**_headers(), "Content-Type": "application/json"}, json=json_data)
    resp.raise_for_status()
    return resp.json()


async def _patch(client: httpx.AsyncClient, url: str, json_data: Any, version: int) -> Any:
    """Make a PATCH request to Zotero API."""
    headers = {**_headers(), "Content-Type": "application/json", "If-Unmodified-Since-Version": str(version)}
    resp = await client.patch(url, headers=headers, json=json_data)
    resp.raise_for_status()
    return resp.json()


def _format_item(item: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a Zotero item."""
    data = item.get("data", {})
    creators = []
    for c in data.get("creators", []):
        name = c.get("name", "")
        if not name:
            last = c.get("lastName", "")
            first = c.get("firstName", "")
            name = f"{last}, {first}" if first else last
        if name:
            creators.append({"name": name, "type": c.get("creatorType", "author")})

    return {
        "key": data.get("key", item.get("key", "")),
        "version": item.get("version", data.get("version", 0)),
        "item_type": data.get("itemType", ""),
        "title": data.get("title", ""),
        "creators": creators,
        "date": data.get("date", ""),
        "journal": data.get("publicationTitle", ""),
        "doi": data.get("DOI", ""),
        "url": data.get("url", ""),
        "abstract": data.get("abstractNote", ""),
        "tags": [t.get("tag", "") for t in data.get("tags", [])],
        "collections": data.get("collections", []),
    }


@mcp.tool()
async def search_library(query: str, collection: str | None = None, limit: int = 25) -> dict[str, Any]:
    """Search the user's Zotero library.

    Args:
        query: Search query (searches title, creators, tags, and full-text).
        collection: Optional collection key to search within.
        limit: Maximum results (default 25, max 100).

    Returns:
        Dictionary with list of matching items.
    """
    limit = min(limit, 100)
    if collection:
        url = _user_url(f"collections/{collection}/items")
    else:
        url = _user_url("items")

    params = {"q": query, "limit": str(limit), "sort": "relevance", "itemType": "-attachment -note"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        items = await _get(client, url, params)

    return {"results": [_format_item(i) for i in items]}


@mcp.tool()
async def add_item(
    item_type: str,
    title: str,
    creators: list[dict[str, str]],
    date: str = "",
    journal: str = "",
    doi: str = "",
    abstract: str = "",
    url: str = "",
    volume: str = "",
    issue: str = "",
    pages: str = "",
    collection_key: str | None = None,
) -> dict[str, Any]:
    """Add a new reference item to the Zotero library.

    Args:
        item_type: Zotero item type (e.g., 'journalArticle', 'book', 'conferencePaper').
        title: Title of the work.
        creators: List of creator dictionaries with 'firstName', 'lastName', and
            'creatorType' (default 'author').
        date: Publication date string (e.g., '2024' or '2024-01-15').
        journal: Journal/publication title.
        doi: Digital Object Identifier.
        abstract: Abstract text.
        url: URL for the work.
        volume: Volume number.
        issue: Issue number.
        pages: Page range.
        collection_key: Optional collection to add the item to.

    Returns:
        Dictionary with the created item's key and metadata.
    """
    item_data: dict[str, Any] = {
        "itemType": item_type,
        "title": title,
        "creators": [
            {
                "creatorType": c.get("creatorType", "author"),
                "firstName": c.get("firstName", ""),
                "lastName": c.get("lastName", ""),
            }
            for c in creators
        ],
        "date": date,
        "publicationTitle": journal,
        "DOI": doi,
        "abstractNote": abstract,
        "url": url,
        "volume": volume,
        "issue": issue,
        "pages": pages,
    }

    if collection_key:
        item_data["collections"] = [collection_key]

    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await _post(client, _user_url("items"), [item_data])

    success = result.get("successful", {})
    if success:
        first_key = list(success.keys())[0]
        return {"status": "created", "item": _format_item(success[first_key])}

    failed = result.get("failed", {})
    return {"status": "failed", "errors": failed}


@mcp.tool()
async def add_item_by_doi(doi: str, collection_key: str | None = None) -> dict[str, Any]:
    """Add a reference to Zotero by looking up its DOI.

    Uses CrossRef to fetch metadata, then creates the Zotero item.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/s41586-020-2649-2').
        collection_key: Optional collection to add the item to.

    Returns:
        Dictionary with the created item's key and metadata.
    """
    # Fetch metadata from CrossRef
    async with httpx.AsyncClient(timeout=15.0) as client:
        cr_resp = await client.get(f"https://api.crossref.org/works/{doi}")
        cr_resp.raise_for_status()
        cr_data = cr_resp.json().get("message", {})

    # Map CrossRef to Zotero format
    titles = cr_data.get("title", [])
    title = titles[0] if titles else ""

    creators = []
    for a in cr_data.get("author", []):
        creators.append({
            "firstName": a.get("given", ""),
            "lastName": a.get("family", ""),
        })

    containers = cr_data.get("container-title", [])
    journal = containers[0] if containers else ""

    date_parts = cr_data.get("published-print", {}).get("date-parts", [[]])
    if not date_parts or not date_parts[0]:
        date_parts = cr_data.get("published-online", {}).get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

    return await add_item(
        item_type="journalArticle",
        title=title,
        creators=creators,
        date=year,
        journal=journal,
        doi=doi,
        abstract=cr_data.get("abstract", ""),
        volume=cr_data.get("volume", ""),
        issue=cr_data.get("issue", ""),
        pages=cr_data.get("page", ""),
        collection_key=collection_key,
    )


@mcp.tool()
async def get_collections() -> dict[str, Any]:
    """List all collections in the user's Zotero library.

    Returns:
        Dictionary with list of collections (key, name, parent, item count).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        collections = await _get(client, _user_url("collections"))

    return {
        "collections": [
            {
                "key": c.get("key", c.get("data", {}).get("key", "")),
                "name": c.get("data", {}).get("name", ""),
                "parent": c.get("data", {}).get("parentCollection", False),
                "num_items": c.get("meta", {}).get("numItems", 0),
            }
            for c in collections
        ]
    }


@mcp.tool()
async def create_collection(name: str, parent_key: str | None = None) -> dict[str, Any]:
    """Create a new collection in the Zotero library.

    Args:
        name: Name for the new collection.
        parent_key: Optional parent collection key for nested collections.

    Returns:
        Dictionary with the created collection's key and name.
    """
    collection_data: dict[str, Any] = {"name": name}
    if parent_key:
        collection_data["parentCollection"] = parent_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await _post(client, _user_url("collections"), [collection_data])

    success = result.get("successful", {})
    if success:
        first_key = list(success.keys())[0]
        col = success[first_key]
        return {
            "status": "created",
            "key": col.get("key", col.get("data", {}).get("key", "")),
            "name": col.get("data", {}).get("name", name),
        }

    return {"status": "failed", "errors": result.get("failed", {})}


@mcp.tool()
async def add_to_collection(item_key: str, collection_key: str) -> dict[str, Any]:
    """Add an existing item to a collection.

    Args:
        item_key: The Zotero item key.
        collection_key: The collection key to add the item to.

    Returns:
        Status of the operation.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current item to find its version and existing collections
        item = await _get(client, _user_url(f"items/{item_key}"))
        version = item.get("version", 0)
        current_collections = item.get("data", {}).get("collections", [])

        if collection_key not in current_collections:
            current_collections.append(collection_key)
            await _patch(
                client,
                _user_url(f"items/{item_key}"),
                {"collections": current_collections},
                version,
            )

    return {"status": "added", "item_key": item_key, "collection_key": collection_key}


@mcp.tool()
async def export_bibliography(
    collection_key: str | None = None,
    format: str = "bibtex",
    limit: int = 100,
) -> dict[str, Any]:
    """Export bibliography from Zotero in various citation formats.

    Args:
        collection_key: Collection to export (None for entire library).
        format: Export format: 'bibtex', 'csljson', 'ris', 'refer', 'mods',
            'coins', 'tei'. Default 'bibtex'.
        limit: Maximum items to export (default 100, max 100).

    Returns:
        Dictionary with the exported bibliography string.
    """
    limit = min(limit, 100)
    if collection_key:
        url = _user_url(f"collections/{collection_key}/items")
    else:
        url = _user_url("items")

    params = {"limit": str(limit), "itemType": "-attachment -note"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {**_headers(), "Accept": f"application/{format}" if format != "bibtex" else "application/x-bibtex"}
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        content = resp.text

    return {"format": format, "content": content}


@mcp.tool()
async def add_note(item_key: str, note_text: str) -> dict[str, Any]:
    """Attach a note to a Zotero item (e.g., screening notes, coding).

    Args:
        item_key: The parent item key to attach the note to.
        note_text: Note content (supports HTML).

    Returns:
        Dictionary with status and the note's key.
    """
    note_data = {
        "itemType": "note",
        "parentItem": item_key,
        "note": note_text,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await _post(client, _user_url("items"), [note_data])

    success = result.get("successful", {})
    if success:
        first_key = list(success.keys())[0]
        note = success[first_key]
        return {"status": "created", "note_key": note.get("key", note.get("data", {}).get("key", ""))}

    return {"status": "failed", "errors": result.get("failed", {})}


@mcp.tool()
async def tag_item(item_key: str, tags: list[str]) -> dict[str, Any]:
    """Add tags to a Zotero item (e.g., 'included', 'excluded-wrong-population').

    Args:
        item_key: The Zotero item key.
        tags: List of tag strings to add.

    Returns:
        Status of the operation.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        item = await _get(client, _user_url(f"items/{item_key}"))
        version = item.get("version", 0)
        existing_tags = item.get("data", {}).get("tags", [])

        existing_tag_names = {t.get("tag", "") for t in existing_tags}
        for tag in tags:
            if tag not in existing_tag_names:
                existing_tags.append({"tag": tag})

        await _patch(
            client,
            _user_url(f"items/{item_key}"),
            {"tags": existing_tags},
            version,
        )

    return {"status": "tagged", "item_key": item_key, "tags": tags}


def serve() -> None:
    """Run the Zotero MCP server."""
    mcp.run(transport="stdio")
