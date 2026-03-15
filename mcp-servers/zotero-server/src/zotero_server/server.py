"""Zotero MCP Server implementation.

API Documentation: https://www.zotero.org/support/dev/web_api/v3/start
Rate limits: Not explicitly documented; be respectful.
Requires: ZOTERO_API_KEY. ZOTERO_USER_ID is optional when key-based autodiscovery is available.
"""

import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


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
    resp = await client.post(url, headers={**_headers(), "Content-Type": "application/json"}, json=json_data)
    resp.raise_for_status()
    return resp.json()


async def _patch(client: httpx.AsyncClient, url: str, json_data: Any, version: int) -> Any:
    """Make a PATCH request to Zotero API."""
    user_id = await _ensure_user_id(client)
    url = _canonicalize_user_url(url, user_id)
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

    result = await export_bibliography(
        collection_key=collection_key, format=format, limit=limit
    )
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
async def get_item_children(
    item_key: str, include_trashed: bool = False
) -> dict[str, Any]:
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
            notes.append({
                "key": child.get("data", {}).get("key", child.get("key", "")),
                "note": child.get("data", {}).get("note", ""),
                "tags": [t.get("tag", "") for t in child.get("data", {}).get("tags", [])],
                "date_added": child.get("data", {}).get("dateAdded", ""),
                "date_modified": child.get("data", {}).get("dateModified", ""),
            })
        elif item_type == "attachment":
            data = child.get("data", {})
            attachments.append({
                "key": data.get("key", child.get("key", "")),
                "title": data.get("title", ""),
                "filename": data.get("filename", ""),
                "content_type": data.get("contentType", ""),
                "link_mode": data.get("linkMode", ""),
                "url": data.get("url", ""),
                "tags": [t.get("tag", "") for t in data.get("tags", [])],
            })
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
        notes.append({
            "key": data.get("key", child.get("key", "")),
            "note": data.get("note", ""),
            "tags": [t.get("tag", "") for t in data.get("tags", [])],
            "date_added": data.get("dateAdded", ""),
            "date_modified": data.get("dateModified", ""),
        })

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
        attachments.append({
            "key": data.get("key", child.get("key", "")),
            "title": data.get("title", ""),
            "filename": data.get("filename", ""),
            "content_type": data.get("contentType", ""),
            "link_mode": data.get("linkMode", ""),
            "url": data.get("url", ""),
            "md5": data.get("md5", ""),
            "mtime": data.get("mtime", 0),
        })

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
        notes.append({
            "key": data.get("key", item.get("key", "")),
            "parent_item": data.get("parentItem", ""),
            "note": data.get("note", ""),
            "tags": [t.get("tag", "") for t in data.get("tags", [])],
            "date_modified": data.get("dateModified", ""),
        })

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
        return {"status": "no_results", "message": "No search results found in the project database."}

    dois = [r["doi"] for r in results if r.get("doi")]
    if not dois:
        return {"status": "no_dois", "message": "No DOIs found in search results. Cannot batch-import without DOIs."}

    return await batch_add_by_doi(dois=dois, collection_key=collection_key, confirm=confirm)


def serve() -> None:
    """Run the Zotero MCP server."""
    mcp.run(transport="stdio")
