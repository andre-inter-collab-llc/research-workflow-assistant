"""Zotero MCP Server implementation.

API Documentation: https://www.zotero.org/support/dev/web_api/v3/start
Rate limits: Not explicitly documented; be respectful.
Requires: ZOTERO_API_KEY. ZOTERO_USER_ID is optional when key-based autodiscovery is available.
"""

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from rwa_result_store import (
    store_results as _store_results,
)


def _load_dotenv_from_workspace() -> None:
    """Load .env by walking up from this file so all entrypoints share config behavior."""
    dir_path = Path(__file__).resolve().parent
    for candidate in (dir_path, *dir_path.parents):
        env_file = candidate / ".env"
        if env_file.is_file():
            load_dotenv(env_file)
            break


def _normalize_user_id(raw: str | None) -> str:
    """Normalize user ID and reject non-numeric values."""
    if raw is None:
        return ""
    value = raw.strip().strip('"').strip("'").strip()
    if not value or not value.isdigit():
        return ""
    return value


def _resolve_user_id_from_env() -> str:
    """Resolve Zotero user ID from supported environment variable aliases."""
    for key in ("ZOTERO_USER_ID", "ZOTERO_USERID", "ZOTERO_LIBRARY_ID"):
        user_id = _normalize_user_id(os.environ.get(key))
        if user_id:
            return user_id
    return ""


def _canonicalize_user_url(url: str, user_id: str) -> str:
    """Replace blank user path segments after user ID resolution."""
    return url.replace("/users//", f"/users/{user_id}/")


async def _discover_user_id(client: httpx.AsyncClient) -> str:
    """Discover Zotero user ID using the authenticated key metadata endpoint."""
    if not API_KEY:
        return ""

    resp = await client.get(f"{ZOTERO_BASE}/keys/current", headers=_headers())
    resp.raise_for_status()
    payload = resp.json() if resp.content else {}

    candidates = [
        payload.get("userID"),
        payload.get("userId"),
        payload.get("user", {}).get("userID") if isinstance(payload.get("user"), dict) else None,
        payload.get("access", {}).get("user", {}).get("id")
        if isinstance(payload.get("access"), dict)
        and isinstance(payload.get("access", {}).get("user"), dict)
        else None,
    ]

    for raw in candidates:
        user_id = _normalize_user_id(str(raw) if raw is not None else None)
        if user_id:
            return user_id
    return ""


async def _ensure_user_id(client: httpx.AsyncClient) -> str:
    """Ensure user ID is available from env or API key autodiscovery."""
    global USER_ID

    if USER_ID:
        return USER_ID

    USER_ID = await _discover_user_id(client)
    if USER_ID:
        return USER_ID

    raise RuntimeError(
        "Zotero configuration error: unable to resolve ZOTERO_USER_ID. "
        "Set ZOTERO_USER_ID (or ZOTERO_USERID / ZOTERO_LIBRARY_ID) to a numeric ID, "
        "or provide a valid ZOTERO_API_KEY for auto-discovery."
    )


_load_dotenv_from_workspace()

ZOTERO_BASE = "https://api.zotero.org"
API_KEY = os.environ.get("ZOTERO_API_KEY", "")
USER_ID = _resolve_user_id_from_env()

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
    user_id = await _ensure_user_id(client)
    url = _canonicalize_user_url(url, user_id)
    resp = await client.get(url, headers=_headers(), params=params or {})
    resp.raise_for_status()
    return resp.json()


async def _post(client: httpx.AsyncClient, url: str, json_data: Any) -> Any:
    """Make a POST request to Zotero API."""
    user_id = await _ensure_user_id(client)
    url = _canonicalize_user_url(url, user_id)
    resp = await client.post(
        url,
        headers={**_headers(), "Content-Type": "application/json"},
        json=json_data,
    )
    resp.raise_for_status()
    return resp.json()


async def _patch(client: httpx.AsyncClient, url: str, json_data: Any, version: int) -> Any:
    """Make a PATCH request to Zotero API."""
    user_id = await _ensure_user_id(client)
    url = _canonicalize_user_url(url, user_id)
    headers = {
        **_headers(),
        "Content-Type": "application/json",
        "If-Unmodified-Since-Version": str(version),
    }
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


def _normalize_for_storage(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a formatted Zotero item into the shared search-result schema."""
    date = str(item.get("date", "") or "")
    year = date[:4] if len(date) >= 4 and date[:4].isdigit() else ""

    return {
        "zotero_key": item.get("key", ""),
        "item_type": item.get("item_type", ""),
        "title": item.get("title", ""),
        "authors": [c.get("name", "") for c in item.get("creators", []) if c.get("name")],
        "journal": item.get("journal", ""),
        "doi": item.get("doi", ""),
        "year": year,
        "date": date,
        "url": item.get("url", ""),
        "abstract": item.get("abstract", ""),
        "tags": item.get("tags", []),
        "collections": item.get("collections", []),
    }


@mcp.tool()
async def search_library(
    query: str,
    collection: str | None = None,
    limit: int = 25,
    project_path: str = ".",
) -> dict[str, Any]:
    """Search the user's Zotero library.

    Args:
        query: Search query (searches title, creators, tags, and full-text).
        collection: Optional collection key to search within.
        limit: Maximum results (default 25, max 100).
        project_path: Project directory path. Results are persisted to
            {project_path}/data/search_results.db for later analysis.

    Returns:
        Dictionary with list of matching items.
    """
    resolved_project_path = _require_project_path(project_path)
    limit = min(limit, 100)
    if collection:
        url = _user_url(f"collections/{collection}/items")
    else:
        url = _user_url("items")

    params = {"q": query, "limit": str(limit), "sort": "relevance", "itemType": "-attachment -note"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        items = await _get(client, url, params)

    formatted_results = [_format_item(i) for i in items]
    stored_results = [_normalize_for_storage(item) for item in formatted_results]
    _store_results(
        resolved_project_path,
        "zotero",
        query,
        stored_results,
        total_count=len(stored_results),
        parameters={
            "collection": collection,
            "limit": limit,
        },
    )

    return {"results": formatted_results}


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
        creators.append(
            {
                "firstName": a.get("given", ""),
                "lastName": a.get("family", ""),
            }
        )

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


_EXPORT_ACCEPT = {
    "bibtex": "application/x-bibtex",
    "csljson": "application/json",
    "ris": "application/x-research-info-systems",
    "refer": "application/x-refer",
    "mods": "application/mods+xml",
    "coins": "text/x-coins",
    "tei": "application/x-tei+xml",
    "csv": "text/csv",
    "zotero_rdf": "application/rdf+xml",
}


@mcp.tool()
async def export_bibliography(
    collection_key: str | None = None,
    format: str = "bibtex",
    limit: int = 100,
) -> dict[str, Any]:
    """Export bibliography from Zotero in various citation formats.

    Supports pagination for collections larger than 100 items.

    Args:
        collection_key: Collection to export (None for entire library).
        format: Export format: 'bibtex', 'csljson', 'ris', 'refer', 'mods',
            'coins', 'tei', 'csv', 'zotero_rdf'. Default 'bibtex'.
        limit: Maximum items to export (default 100, max 500).

    Returns:
        Dictionary with the exported bibliography string.
    """
    limit = min(limit, 500)
    if collection_key:
        url = _user_url(f"collections/{collection_key}/items")
    else:
        url = _user_url("items")

    accept = _EXPORT_ACCEPT.get(format, f"application/{format}")
    parts: list[str] = []
    start = 0
    page_size = min(limit, 100)

    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = await _ensure_user_id(client)
        url = _canonicalize_user_url(url, user_id)
        while start < limit:
            params = {
                "limit": str(page_size),
                "start": str(start),
                "itemType": "-attachment -note",
            }
            headers = {**_headers(), "Accept": accept}
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            chunk = resp.text
            if not chunk.strip():
                break
            parts.append(chunk)
            total_results = resp.headers.get("Total-Results")
            if total_results and start + page_size >= int(total_results):
                break
            start += page_size

    content = "\n".join(parts)
    return {"format": format, "content": content}


@mcp.tool()
async def export_to_file(
    file_path: str,
    collection_key: str | None = None,
    format: str = "bibtex",
    limit: int = 500,
) -> dict[str, Any]:
    """Export bibliography directly to a file on disk.

    Writes the exported content to a file (e.g., references.bib) without
    returning the full text in the response. Useful for large exports.

    Args:
        file_path: Absolute path to the output file (e.g., '/path/to/references.bib').
        collection_key: Collection to export (None for entire library).
        format: Export format (same options as export_bibliography).
        limit: Maximum items to export (default 500, max 500).

    Returns:
        Dictionary with status, file path, and item count.
    """
    import pathlib

    result = await export_bibliography(collection_key=collection_key, format=format, limit=limit)
    content = result.get("content", "")

    out_path = pathlib.Path(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    # Rough count: BibTeX entries start with @, RIS records start with TY  -
    if format == "bibtex":
        count = content.count("@")
    elif format == "ris":
        count = content.count("TY  -")
    else:
        count = content.count("\n\n") + 1 if content.strip() else 0

    return {
        "status": "exported",
        "file_path": str(out_path),
        "format": format,
        "estimated_items": count,
    }


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
        return {
            "status": "created",
            "note_key": note.get("key", note.get("data", {}).get("key", "")),
        }

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


# ---------------------------------------------------------------------------
# Phase 1 additions: child items, notes, annotations, attachments
# ---------------------------------------------------------------------------


def _format_annotation(item: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a Zotero annotation item."""
    data = item.get("data", {})
    return {
        "key": data.get("key", item.get("key", "")),
        "annotation_type": data.get("annotationType", ""),
        "annotation_text": data.get("annotationText", ""),
        "annotation_comment": data.get("annotationComment", ""),
        "annotation_color": data.get("annotationColor", ""),
        "annotation_page_label": data.get("annotationPageLabel", ""),
        "annotation_sort_index": data.get("annotationSortIndex", ""),
        "parent_item": data.get("parentItem", ""),
        "tags": [t.get("tag", "") for t in data.get("tags", [])],
        "date_added": data.get("dateAdded", ""),
        "date_modified": data.get("dateModified", ""),
    }


@mcp.tool()
async def get_item_children(item_key: str, include_trashed: bool = False) -> dict[str, Any]:
    """Get all child items (notes, attachments, annotations) for a Zotero item.

    Args:
        item_key: The Zotero item key.
        include_trashed: Whether to include items in the trash.

    Returns:
        Dictionary with categorised child items.
    """
    url = _user_url(f"items/{item_key}/children")
    params: dict[str, str] = {}
    if include_trashed:
        params["includeTrashed"] = "1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        children = await _get(client, url, params)

    notes = []
    attachments = []
    annotations = []
    for child in children:
        item_type = child.get("data", {}).get("itemType", "")
        if item_type == "note":
            notes.append(
                {
                    "key": child.get("data", {}).get("key", child.get("key", "")),
                    "note": child.get("data", {}).get("note", ""),
                    "tags": [t.get("tag", "") for t in child.get("data", {}).get("tags", [])],
                    "date_added": child.get("data", {}).get("dateAdded", ""),
                    "date_modified": child.get("data", {}).get("dateModified", ""),
                }
            )
        elif item_type == "attachment":
            data = child.get("data", {})
            attachments.append(
                {
                    "key": data.get("key", child.get("key", "")),
                    "title": data.get("title", ""),
                    "filename": data.get("filename", ""),
                    "content_type": data.get("contentType", ""),
                    "link_mode": data.get("linkMode", ""),
                    "url": data.get("url", ""),
                    "tags": [t.get("tag", "") for t in data.get("tags", [])],
                }
            )
        elif item_type == "annotation":
            annotations.append(_format_annotation(child))

    return {
        "item_key": item_key,
        "notes": notes,
        "attachments": attachments,
        "annotations": annotations,
    }


@mcp.tool()
async def get_notes(item_key: str) -> dict[str, Any]:
    """Get all notes attached to a Zotero item.

    Args:
        item_key: The Zotero item key.

    Returns:
        Dictionary with a list of note objects containing HTML content.
    """
    url = _user_url(f"items/{item_key}/children")
    params = {"itemType": "note"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        children = await _get(client, url, params)

    notes = []
    for child in children:
        data = child.get("data", {})
        notes.append(
            {
                "key": data.get("key", child.get("key", "")),
                "note": data.get("note", ""),
                "tags": [t.get("tag", "") for t in data.get("tags", [])],
                "date_added": data.get("dateAdded", ""),
                "date_modified": data.get("dateModified", ""),
            }
        )

    return {"item_key": item_key, "notes": notes}


@mcp.tool()
async def get_annotations(item_key: str) -> dict[str, Any]:
    """Get all Zotero reader annotations for a PDF attachment.

    Zotero 6/7 stores annotations (highlights, comments, sticky notes)
    as child items of the PDF attachment.

    Args:
        item_key: The Zotero attachment (PDF) item key.

    Returns:
        Dictionary with a list of annotation objects.
    """
    url = _user_url(f"items/{item_key}/children")
    params = {"itemType": "annotation"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        children = await _get(client, url, params)

    return {
        "attachment_key": item_key,
        "annotations": [_format_annotation(child) for child in children],
    }


@mcp.tool()
async def get_attachment_metadata(item_key: str) -> dict[str, Any]:
    """Get metadata about attachments for a Zotero item without downloading files.

    Args:
        item_key: The Zotero parent item key.

    Returns:
        Dictionary with attachment metadata (filename, content type, size, link mode).
    """
    url = _user_url(f"items/{item_key}/children")
    params = {"itemType": "attachment"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        children = await _get(client, url, params)

    attachments = []
    for child in children:
        data = child.get("data", {})
        attachments.append(
            {
                "key": data.get("key", child.get("key", "")),
                "title": data.get("title", ""),
                "filename": data.get("filename", ""),
                "content_type": data.get("contentType", ""),
                "link_mode": data.get("linkMode", ""),
                "url": data.get("url", ""),
                "md5": data.get("md5", ""),
                "mtime": data.get("mtime", 0),
            }
        )

    return {"item_key": item_key, "attachments": attachments}


@mcp.tool()
async def download_attachment(item_key: str) -> dict[str, Any]:
    """Download a Zotero attachment file via the Web API.

    Returns the file content as base64-encoded string for binary files,
    or plain text for text-based formats. Useful as a fallback when
    local Zotero storage is unavailable.

    Args:
        item_key: The Zotero attachment item key.

    Returns:
        Dictionary with filename, content_type, and base64-encoded content.
    """
    import base64

    async with httpx.AsyncClient(timeout=60.0) as client:
        # First get attachment metadata
        item = await _get(client, _user_url(f"items/{item_key}"))
        data = item.get("data", {})
        filename = data.get("filename", "unknown")
        content_type = data.get("contentType", "application/octet-stream")

        # Download the file
        url = _user_url(f"items/{item_key}/file")
        user_id = await _ensure_user_id(client)
        url = _canonicalize_user_url(url, user_id)
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()

        if content_type.startswith("text/"):
            return {
                "filename": filename,
                "content_type": content_type,
                "encoding": "utf-8",
                "content": resp.text,
            }

        return {
            "filename": filename,
            "content_type": content_type,
            "encoding": "base64",
            "content": base64.b64encode(resp.content).decode("ascii"),
            "size_bytes": len(resp.content),
        }


@mcp.tool()
async def search_notes(
    query: str, collection: str | None = None, limit: int = 25
) -> dict[str, Any]:
    """Search across all notes in the Zotero library for a keyword or phrase.

    Args:
        query: Search query string.
        collection: Optional collection key to search within.
        limit: Maximum results (default 25, max 100).

    Returns:
        Dictionary with matching notes and their parent item keys.
    """
    limit = min(limit, 100)
    if collection:
        url = _user_url(f"collections/{collection}/items")
    else:
        url = _user_url("items")

    params = {
        "q": query,
        "limit": str(limit),
        "itemType": "note",
        "sort": "relevance",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        items = await _get(client, url, params)

    notes = []
    for item in items:
        data = item.get("data", {})
        notes.append(
            {
                "key": data.get("key", item.get("key", "")),
                "parent_item": data.get("parentItem", ""),
                "note": data.get("note", ""),
                "tags": [t.get("tag", "") for t in data.get("tags", [])],
                "date_modified": data.get("dateModified", ""),
            }
        )

    return {"query": query, "results": notes}


# ---------------------------------------------------------------------------
# Batch import tools
# ---------------------------------------------------------------------------

MAX_BATCH_ITEMS = 200


@mcp.tool()
async def batch_add_by_doi(
    dois: list[str],
    collection_key: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Add multiple references to Zotero by DOI (batch operation).

    First call with confirm=False to preview what will be imported.
    Then re-call with confirm=True to execute the import.

    Args:
        dois: List of DOIs to add.
        collection_key: Optional collection key to add items to.
        confirm: If False (default), return a preview. If True, execute the import.

    Returns:
        Preview (confirm=False) or import summary (confirm=True).
    """
    if not dois:
        return {"status": "error", "message": "No DOIs provided"}

    if len(dois) > MAX_BATCH_ITEMS:
        return {
            "status": "error",
            "message": f"Too many DOIs ({len(dois)}). Maximum is {MAX_BATCH_ITEMS}.",
        }

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_dois: list[str] = []
    for d in dois:
        d_lower = d.strip().lower()
        if d_lower and d_lower not in seen:
            seen.add(d_lower)
            unique_dois.append(d.strip())

    if not confirm:
        return {
            "status": "preview",
            "total_dois": len(unique_dois),
            "sample": unique_dois[:5],
            "message": (
                f"Ready to import {len(unique_dois)} DOI(s) into Zotero"
                + (f" (collection: {collection_key})" if collection_key else "")
                + ". Re-call with confirm=True to proceed."
            ),
        }

    added: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []

    for doi in unique_dois:
        try:
            result = await add_item_by_doi(doi=doi, collection_key=collection_key)
            if result.get("status") == "failed":
                errors.append({"doi": doi, "error": str(result.get("errors", ""))})
            else:
                added.append(doi)
        except Exception as exc:
            errors.append({"doi": doi, "error": str(exc)})

    return {
        "status": "completed",
        "added": len(added),
        "skipped": len(skipped),
        "errors_count": len(errors),
        "added_dois": added,
        "errors": errors[:10],
    }


@mcp.tool()
async def import_from_result_store(
    project_path: str,
    collection_key: str | None = None,
    source: str | None = None,
    deduplicated: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """Import references from the project's search result database into Zotero.

    Reads DOIs from {project_path}/data/search_results.db and batch-adds
    them to the user's Zotero library.

    Args:
        project_path: Absolute path to the project directory.
        collection_key: Optional Zotero collection key.
        source: Optional filter by database source (e.g., 'pubmed', 'openalex').
        deduplicated: If True (default), use deduplicated results.
        confirm: If False (default), return a preview. If True, execute.

    Returns:
        Preview or import summary.
    """
    from rwa_result_store import get_results

    results = get_results(project_path, source=source, deduplicated=deduplicated)
    if not results:
        return {
            "status": "no_results",
            "message": "No search results found in the project database.",
        }

    dois = [r["doi"] for r in results if r.get("doi")]
    if not dois:
        return {
            "status": "no_dois",
            "message": ("No DOIs found in search results. Cannot batch-import without DOIs."),
        }

    return await batch_add_by_doi(dois=dois, collection_key=collection_key, confirm=confirm)


# ---------------------------------------------------------------------------
# Item metadata & relations
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_item_metadata(item_key: str) -> dict[str, Any]:
    """Fetch full metadata for a single Zotero item by its key.

    Returns all available fields including abstract, notes count, and
    related items — more detail than the summary returned by search_library.

    Args:
        item_key: The Zotero item key.

    Returns:
        Dictionary with complete item metadata.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        item = await _get(client, _user_url(f"items/{item_key}"))

    data = item.get("data", {})
    formatted = _format_item(item)
    # Add fields not included in _format_item
    formatted.update(
        {
            "volume": data.get("volume", ""),
            "issue": data.get("issue", ""),
            "pages": data.get("pages", ""),
            "publisher": data.get("publisher", ""),
            "isbn": data.get("ISBN", ""),
            "issn": data.get("ISSN", ""),
            "language": data.get("language", ""),
            "rights": data.get("rights", ""),
            "extra": data.get("extra", ""),
            "date_added": data.get("dateAdded", ""),
            "date_modified": data.get("dateModified", ""),
            "relations": data.get("relations", {}),
            "num_children": item.get("meta", {}).get("numChildren", 0),
        }
    )
    return formatted


@mcp.tool()
async def update_item_metadata(
    item_key: str,
    title: str | None = None,
    abstract: str | None = None,
    date: str | None = None,
    journal: str | None = None,
    doi: str | None = None,
    url: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    pages: str | None = None,
    extra: str | None = None,
) -> dict[str, Any]:
    """Update editable fields on an existing Zotero item.

    Only non-None fields are updated; all others are left unchanged.

    Args:
        item_key: The Zotero item key.
        title: New title.
        abstract: New abstract.
        date: New date string.
        journal: New publication title / journal name.
        doi: New DOI.
        url: New URL.
        volume: New volume.
        issue: New issue.
        pages: New pages.
        extra: New "Extra" field content.

    Returns:
        Dictionary with the updated item metadata.
    """
    field_map: dict[str, str | None] = {
        "title": title,
        "abstractNote": abstract,
        "date": date,
        "publicationTitle": journal,
        "DOI": doi,
        "url": url,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "extra": extra,
    }
    patch_data = {k: v for k, v in field_map.items() if v is not None}
    if not patch_data:
        return {"status": "no_changes", "message": "No fields provided to update."}

    async with httpx.AsyncClient(timeout=30.0) as client:
        item = await _get(client, _user_url(f"items/{item_key}"))
        version = item.get("version", 0)
        await _patch(client, _user_url(f"items/{item_key}"), patch_data, version)
        updated = await _get(client, _user_url(f"items/{item_key}"))

    return {"status": "updated", "item": _format_item(updated)}


@mcp.tool()
async def get_related_items(item_key: str) -> dict[str, Any]:
    """Retrieve items linked via Zotero's "Related" feature.

    Args:
        item_key: The Zotero item key.

    Returns:
        Dictionary with the source item key and a list of related items.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        item = await _get(client, _user_url(f"items/{item_key}"))
        relations = item.get("data", {}).get("relations", {})
        # Related items are stored as dc:relation URIs
        related_uris = relations.get("dc:relation", [])
        if isinstance(related_uris, str):
            related_uris = [related_uris]

        related_items = []
        for uri in related_uris:
            # URI format: http://zotero.org/users/{id}/items/{key}
            related_key = uri.rsplit("/", 1)[-1] if "/" in uri else uri
            try:
                rel_item = await _get(client, _user_url(f"items/{related_key}"))
                related_items.append(_format_item(rel_item))
            except httpx.HTTPStatusError:
                related_items.append({"key": related_key, "error": "not_found"})

    return {"item_key": item_key, "related_items": related_items}


@mcp.tool()
async def add_related_items(item_key_a: str, item_key_b: str) -> dict[str, Any]:
    """Link two items as related in Zotero (bidirectional).

    Args:
        item_key_a: First item key.
        item_key_b: Second item key.

    Returns:
        Status of the operation.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = await _ensure_user_id(client)
        uri_a = f"http://zotero.org/users/{user_id}/items/{item_key_a}"
        uri_b = f"http://zotero.org/users/{user_id}/items/{item_key_b}"

        # Add B as related to A
        item_a = await _get(client, _user_url(f"items/{item_key_a}"))
        relations_a = item_a.get("data", {}).get("relations", {})
        existing_a = relations_a.get("dc:relation", [])
        if isinstance(existing_a, str):
            existing_a = [existing_a]
        if uri_b not in existing_a:
            existing_a.append(uri_b)
            relations_a["dc:relation"] = existing_a
            await _patch(
                client,
                _user_url(f"items/{item_key_a}"),
                {"relations": relations_a},
                item_a.get("version", 0),
            )

        # Add A as related to B
        item_b = await _get(client, _user_url(f"items/{item_key_b}"))
        relations_b = item_b.get("data", {}).get("relations", {})
        existing_b = relations_b.get("dc:relation", [])
        if isinstance(existing_b, str):
            existing_b = [existing_b]
        if uri_a not in existing_b:
            existing_b.append(uri_a)
            relations_b["dc:relation"] = existing_b
            await _patch(
                client,
                _user_url(f"items/{item_key_b}"),
                {"relations": relations_b},
                item_b.get("version", 0),
            )

    return {
        "status": "linked",
        "item_key_a": item_key_a,
        "item_key_b": item_key_b,
    }


# ---------------------------------------------------------------------------
# Collections & tags
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_collection_items(
    collection_key: str,
    limit: int = 50,
    sort: str = "dateModified",
    direction: str = "desc",
) -> dict[str, Any]:
    """List all items in a Zotero collection with full metadata.

    Args:
        collection_key: The collection key.
        limit: Maximum results (default 50, max 100).
        sort: Sort field: 'dateModified', 'dateAdded', 'title', 'creator',
            'itemType', 'date', 'publisher'. Default 'dateModified'.
        direction: Sort direction: 'asc' or 'desc'. Default 'desc'.

    Returns:
        Dictionary with collection info and list of items.
    """
    limit = min(limit, 100)
    url = _user_url(f"collections/{collection_key}/items")
    params = {
        "limit": str(limit),
        "sort": sort,
        "direction": direction,
        "itemType": "-attachment -note -annotation",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        items = await _get(client, url, params)

    return {
        "collection_key": collection_key,
        "items": [_format_item(item) for item in items],
        "count": len(items),
    }


@mcp.tool()
async def get_tags(limit: int = 100) -> dict[str, Any]:
    """List all tags in the user's Zotero library with usage counts.

    Args:
        limit: Maximum tags to return (default 100, max 500).

    Returns:
        Dictionary with list of tags and their usage counts.
    """
    limit = min(limit, 500)
    url = _user_url("tags")
    params = {"limit": str(limit)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        tags_data = await _get(client, url, params)

    tags = []
    for tag_entry in tags_data:
        meta = tag_entry.get("meta", {})
        tags.append(
            {
                "tag": tag_entry.get("tag", ""),
                "type": meta.get("type", 0),
                "num_items": meta.get("numItems", 0),
            }
        )

    tags.sort(key=lambda t: t["num_items"], reverse=True)
    return {"tags": tags, "count": len(tags)}


@mcp.tool()
async def rename_tag(old_tag: str, new_tag: str) -> dict[str, Any]:
    """Rename a tag across all items in the Zotero library.

    Finds all items with the old tag, replaces it with the new tag on each item.

    Args:
        old_tag: The existing tag name to rename.
        new_tag: The new tag name.

    Returns:
        Dictionary with the number of items updated.
    """
    url = _user_url("items")
    params = {"tag": old_tag, "limit": "100", "itemType": "-attachment -note -annotation"}

    updated_count = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        items = await _get(client, url, params)

        for item in items:
            data = item.get("data", {})
            version = item.get("version", 0)
            item_key = data.get("key", item.get("key", ""))
            existing_tags = data.get("tags", [])

            new_tags = []
            changed = False
            for t in existing_tags:
                if t.get("tag", "") == old_tag:
                    new_tags.append({"tag": new_tag})
                    changed = True
                else:
                    new_tags.append(t)

            if changed:
                await _patch(
                    client,
                    _user_url(f"items/{item_key}"),
                    {"tags": new_tags},
                    version,
                )
                updated_count += 1

    return {
        "status": "renamed",
        "old_tag": old_tag,
        "new_tag": new_tag,
        "items_updated": updated_count,
    }


@mcp.tool()
async def delete_tag(tag: str) -> dict[str, Any]:
    """Remove a tag from all items in the Zotero library.

    Args:
        tag: The tag name to remove.

    Returns:
        Dictionary with the number of items updated.
    """
    url = _user_url("items")
    params = {"tag": tag, "limit": "100", "itemType": "-attachment -note -annotation"}

    updated_count = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        items = await _get(client, url, params)

        for item in items:
            data = item.get("data", {})
            version = item.get("version", 0)
            item_key = data.get("key", item.get("key", ""))
            existing_tags = data.get("tags", [])

            new_tags = [t for t in existing_tags if t.get("tag", "") != tag]
            if len(new_tags) != len(existing_tags):
                await _patch(
                    client,
                    _user_url(f"items/{item_key}"),
                    {"tags": new_tags},
                    version,
                )
                updated_count += 1

    return {
        "status": "deleted",
        "tag": tag,
        "items_updated": updated_count,
    }


# ---------------------------------------------------------------------------
# DOI lookup in library
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_item_by_doi(doi: str) -> dict[str, Any]:
    """Look up an item in the user's Zotero library by DOI.

    Checks if the user already has a reference with this DOI.
    Does NOT search external databases — only the local library.

    Args:
        doi: Digital Object Identifier to search for.

    Returns:
        Dictionary with the matching item or a not-found status.
    """
    url = _user_url("items")
    params = {"q": doi, "limit": "10", "itemType": "-attachment -note -annotation"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        items = await _get(client, url, params)

    # Filter for exact DOI match (search may return partial matches)
    doi_lower = doi.strip().lower()
    for item in items:
        item_doi = item.get("data", {}).get("DOI", "").strip().lower()
        if item_doi == doi_lower:
            return {"status": "found", "item": _format_item(item)}

    return {"status": "not_found", "doi": doi}


# ---------------------------------------------------------------------------
# Group libraries (read-only)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_groups() -> dict[str, Any]:
    """List group libraries the user belongs to.

    Returns:
        Dictionary with list of groups (id, name, type, member count).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = await _ensure_user_id(client)
        url = f"{ZOTERO_BASE}/users/{user_id}/groups"
        groups_data = await _get(client, url)

    groups = []
    for g in groups_data:
        data = g.get("data", {})
        meta = g.get("meta", {})
        groups.append(
            {
                "id": g.get("id", data.get("id", "")),
                "name": data.get("name", ""),
                "type": data.get("type", ""),
                "owner": data.get("owner", ""),
                "num_items": meta.get("numItems", 0),
            }
        )

    return {"groups": groups}


@mcp.tool()
async def search_group_library(
    group_id: int,
    query: str,
    limit: int = 25,
) -> dict[str, Any]:
    """Search within a specific Zotero group library (read-only).

    Args:
        group_id: The group library ID (from get_groups).
        query: Search query string.
        limit: Maximum results (default 25, max 100).

    Returns:
        Dictionary with matching items from the group library.
    """
    limit = min(limit, 100)
    url = f"{ZOTERO_BASE}/groups/{group_id}/items"
    params = {
        "q": query,
        "limit": str(limit),
        "sort": "relevance",
        "itemType": "-attachment -note -annotation",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        user_id = await _ensure_user_id(client)
        url_canonical = _canonicalize_user_url(url, user_id)
        resp = await client.get(url_canonical, headers=_headers(), params=params)
        resp.raise_for_status()
        items = resp.json()

    return {
        "group_id": group_id,
        "query": query,
        "items": [_format_item(item) for item in items],
        "count": len(items),
    }


def serve() -> None:
    """Run the Zotero MCP server."""
    mcp.run(transport="stdio")
