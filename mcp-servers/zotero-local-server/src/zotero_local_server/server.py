"""Zotero Local MCP Server implementation.

Provides local filesystem access to Zotero data: PDF text and annotation
extraction, full-text keyword search across stored PDFs, local notes and
annotations from the Zotero SQLite database, and optional Better BibTeX
integration.

Requires: ZOTERO_DATA_DIR environment variable (or auto-detects).
"""

import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import pdf_reader, zotero_db

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "zotero-local",
    instructions=(
        "Access local Zotero data: extract PDF text and annotations, "
        "search PDFs for keywords, read Zotero notes and highlights, "
        "and optionally use Better BibTeX for citation key management"
    ),
)


def _data_dir() -> Path:
    """Resolve the Zotero data directory, raising if not found."""
    env = os.environ.get("ZOTERO_DATA_DIR")
    if env:
        p = Path(env)
        if p.is_dir() and (p / "zotero.sqlite").exists():
            return p
        raise FileNotFoundError(
            f"ZOTERO_DATA_DIR is set to '{env}' but no zotero.sqlite found there. "
            "Please verify the path points to your Zotero data directory."
        )

    detected = zotero_db.detect_zotero_data_dir()
    if detected:
        return detected

    raise FileNotFoundError(
        "Cannot find local Zotero data directory. Set ZOTERO_DATA_DIR "
        "environment variable to the folder containing zotero.sqlite."
    )


def _resolve_pdf_path(data_dir: Path, item_key: str) -> str | None:
    """Find the first PDF attachment file path for an item key.

    Checks whether item_key is itself an attachment, otherwise looks up
    child attachments of the parent item.
    """
    # First check if the key is directly an attachment
    attachments = zotero_db.get_attachments(data_dir, item_key)
    pdfs = [
        a for a in attachments if a.get("content_type") == "application/pdf" and a.get("exists")
    ]
    if pdfs:
        return pdfs[0]["path"]

    # Maybe item_key IS the attachment key — check the storage directory
    storage = data_dir / "storage" / item_key
    if storage.is_dir():
        for f in storage.iterdir():
            if f.suffix.lower() == ".pdf":
                return str(f)

    return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def detect_zotero_storage() -> dict[str, Any]:
    """Detect and verify the local Zotero data directory.

    Checks ZOTERO_DATA_DIR environment variable, then platform-specific
    default locations. Reports the path, Zotero version, and storage stats.

    Returns:
        Dictionary with data_dir path, Zotero version, and storage info.
    """
    try:
        data_dir = _data_dir()
    except FileNotFoundError as exc:
        return {"status": "not_found", "error": str(exc)}

    version = zotero_db.get_zotero_version(data_dir)
    storage_dir = data_dir / "storage"
    pdf_count = 0
    total_size = 0

    if storage_dir.is_dir():
        for child in storage_dir.iterdir():
            if child.is_dir():
                for f in child.iterdir():
                    if f.suffix.lower() == ".pdf":
                        pdf_count += 1
                        total_size += f.stat().st_size

    return {
        "status": "found",
        "data_dir": str(data_dir),
        "zotero_version": version,
        "storage_dir": str(storage_dir),
        "pdf_count": pdf_count,
        "total_pdf_size_mb": round(total_size / (1024 * 1024), 1),
    }


@mcp.tool()
async def list_local_attachments(item_key: str) -> dict[str, Any]:
    """List all attachments stored locally for a Zotero item.

    Args:
        item_key: The Zotero parent item key.

    Returns:
        Dictionary with a list of attachment details including file paths.
    """
    data_dir = _data_dir()
    attachments = zotero_db.get_attachments(data_dir, item_key)
    return {"item_key": item_key, "attachments": attachments}


@mcp.tool()
async def extract_pdf_text(
    item_key: str,
    pages: list[int] | None = None,
) -> dict[str, Any]:
    """Extract full text from the PDF associated with a Zotero item.

    Args:
        item_key: Zotero item key (parent item or attachment key).
        pages: Optional list of 1-based page numbers. Extracts all if omitted.

    Returns:
        Dictionary with page-by-page text content and metadata.
    """
    data_dir = _data_dir()
    pdf_path = _resolve_pdf_path(data_dir, item_key)

    if not pdf_path:
        return {"item_key": item_key, "error": "No PDF attachment found for this item"}

    result = pdf_reader.extract_text(pdf_path, pages=pages)

    if result.error:
        return {"item_key": item_key, "path": result.path, "error": result.error}

    return {
        "item_key": item_key,
        "path": result.path,
        "num_pages": result.num_pages,
        "pages": [{"page": p.page_number, "text": p.text} for p in result.pages],
    }


@mcp.tool()
async def extract_pdf_annotations(item_key: str) -> dict[str, Any]:
    """Extract all annotations embedded in the PDF file for a Zotero item.

    Returns highlights, sticky notes, underlines, strikethroughs, and
    free text annotations with their content, page numbers, and colors.

    Args:
        item_key: Zotero item key (parent item or attachment key).

    Returns:
        Dictionary with a list of annotation objects.
    """
    data_dir = _data_dir()
    pdf_path = _resolve_pdf_path(data_dir, item_key)

    if not pdf_path:
        return {"item_key": item_key, "error": "No PDF attachment found for this item"}

    result = pdf_reader.extract_annotations(pdf_path)

    if result.error:
        return {"item_key": item_key, "path": result.path, "error": result.error}

    return {
        "item_key": item_key,
        "path": result.path,
        "num_pages": result.num_pages,
        "annotations": [pdf_reader.annotation_to_dict(a) for a in result.annotations],
    }


@mcp.tool()
async def get_zotero_annotations(item_key: str) -> dict[str, Any]:
    """Get Zotero reader annotations from the local database.

    Zotero's built-in PDF reader stores annotations in the database
    rather than embedding them in the PDF. This retrieves those annotations.

    Args:
        item_key: The Zotero attachment (PDF) item key.

    Returns:
        Dictionary with a list of annotation objects from the Zotero database.
    """
    data_dir = _data_dir()

    # Try item_key directly as an attachment key
    annotations = zotero_db.get_annotations_for_attachment(data_dir, item_key)

    if not annotations:
        # Maybe item_key is a parent item — find its PDF attachment
        attachments = zotero_db.get_attachments(data_dir, item_key)
        for att in attachments:
            if att.get("content_type") == "application/pdf":
                annotations = zotero_db.get_annotations_for_attachment(data_dir, att["key"])
                if annotations:
                    break

    return {"item_key": item_key, "annotations": annotations}


@mcp.tool()
async def search_pdf_content(
    query: str,
    collection_key: str | None = None,
    max_results: int = 20,
    context_chars: int = 150,
) -> dict[str, Any]:
    """Search for a keyword or phrase across all PDFs in the Zotero library.

    Performs case-insensitive text search through stored PDF files and
    returns matching items with page numbers and surrounding context.

    Args:
        query: Search term or phrase.
        collection_key: Optional collection key to limit search scope.
        max_results: Maximum number of items to return (default 20).
        context_chars: Characters of context around each match (default 150).

    Returns:
        Dictionary with matching items, pages, and text snippets.
    """
    data_dir = _data_dir()
    all_pdfs = zotero_db.get_all_pdf_attachments(data_dir, collection_key)

    results = []
    for pdf_info in all_pdfs:
        if len(results) >= max_results:
            break

        pdf_path = pdf_info.get("path")
        if not pdf_path:
            continue

        hits = pdf_reader.search_text(pdf_path, query, context_chars=context_chars)
        if hits:
            total_matches = sum(h.match_count for h in hits)
            results.append(
                {
                    "parent_key": pdf_info.get("parent_key", ""),
                    "attachment_key": pdf_info.get("attachment_key", ""),
                    "filename": pdf_info.get("filename", ""),
                    "total_matches": total_matches,
                    "pages": [
                        {
                            "page": h.page_number,
                            "match_count": h.match_count,
                            "snippet": h.snippet,
                        }
                        for h in hits
                    ],
                }
            )

    return {
        "query": query,
        "pdfs_searched": len(all_pdfs),
        "items_matched": len(results),
        "results": results,
    }


@mcp.tool()
async def get_local_notes(item_key: str) -> dict[str, Any]:
    """Get all Zotero notes for an item from the local database.

    Faster than the Web API and works offline.

    Args:
        item_key: The Zotero parent item key.

    Returns:
        Dictionary with a list of note objects.
    """
    data_dir = _data_dir()
    notes = zotero_db.get_notes_for_item(data_dir, item_key)
    return {"item_key": item_key, "notes": notes}


@mcp.tool()
async def export_annotations_report(
    item_key: str | None = None,
    collection_key: str | None = None,
) -> dict[str, Any]:
    """Generate a Markdown report of all annotations and highlights.

    Combines Zotero reader annotations (from the database) and
    PDF-embedded annotations for one item or an entire collection.

    Args:
        item_key: A specific Zotero item key. If None, processes collection.
        collection_key: Collection key (used if item_key is None).

    Returns:
        Dictionary with a formatted Markdown report string.
    """
    data_dir = _data_dir()

    items_to_process: list[dict[str, Any]] = []

    if item_key:
        pdf_path = _resolve_pdf_path(data_dir, item_key)
        item_info = zotero_db.get_item_by_key(data_dir, item_key)
        title = (item_info or {}).get("title", item_key)
        items_to_process.append(
            {
                "key": item_key,
                "title": title,
                "pdf_path": pdf_path,
            }
        )
    elif collection_key:
        all_pdfs = zotero_db.get_all_pdf_attachments(data_dir, collection_key)
        seen_parents: set[str] = set()
        for pdf_info in all_pdfs:
            parent_key = pdf_info.get("parent_key", "")
            if parent_key in seen_parents:
                continue
            seen_parents.add(parent_key)
            item_info = zotero_db.get_item_by_key(data_dir, parent_key)
            title = (item_info or {}).get("title", parent_key)
            items_to_process.append(
                {
                    "key": parent_key,
                    "title": title,
                    "pdf_path": pdf_info.get("path"),
                }
            )
    else:
        return {"error": "Provide either item_key or collection_key"}

    lines = ["# Annotations Report\n"]

    for item in items_to_process:
        lines.append(f"## {item['title']}\n")
        lines.append(f"**Zotero key**: `{item['key']}`\n")

        # Zotero reader annotations from database
        db_annotations = zotero_db.get_annotations_for_attachment(data_dir, item["key"])
        if not db_annotations:
            # Try child attachments
            attachments = zotero_db.get_attachments(data_dir, item["key"])
            for att in attachments:
                if att.get("content_type") == "application/pdf":
                    db_annotations = zotero_db.get_annotations_for_attachment(data_dir, att["key"])
                    if db_annotations:
                        break

        if db_annotations:
            lines.append("### Zotero Reader Annotations\n")
            for ann in db_annotations:
                ann_type = ann.get("type", "unknown")
                text = ann.get("text", "")
                comment = ann.get("comment", "")
                page = ann.get("page_label", "")
                page_str = f" (p. {page})" if page else ""

                if ann_type == "highlight" and text:
                    lines.append(f'- **Highlight**{page_str}: "{text}"')
                    if comment:
                        lines.append(f"  - *Comment*: {comment}")
                elif ann_type == "note" and (text or comment):
                    lines.append(f"- **Note**{page_str}: {text or comment}")
                elif text or comment:
                    lines.append(f"- **{ann_type.title()}**{page_str}: {text or comment}")
            lines.append("")

        # PDF-embedded annotations
        pdf_path = item.get("pdf_path")
        if pdf_path:
            pdf_result = pdf_reader.extract_annotations(pdf_path)
            if pdf_result.annotations:
                lines.append("### PDF Embedded Annotations\n")
                for ann in pdf_result.annotations:
                    page_str = f" (p. {ann.page})"
                    if ann.type == "highlight" and ann.highlighted_text:
                        lines.append(f'- **Highlight**{page_str}: "{ann.highlighted_text}"')
                        if ann.content:
                            lines.append(f"  - *Comment*: {ann.content}")
                    elif ann.content:
                        lines.append(f"- **{ann.type.title()}**{page_str}: {ann.content}")
                        if ann.highlighted_text:
                            lines.append(f'  - *Selected text*: "{ann.highlighted_text}"')
                lines.append("")

        # Notes
        notes = zotero_db.get_notes_for_item(data_dir, item["key"])
        if notes:
            lines.append("### Notes\n")
            for note in notes:
                # Strip HTML tags for the report
                import re

                note_text = re.sub(r"<[^>]+>", "", note.get("note", "")).strip()
                if note_text:
                    lines.append(f"- {note_text[:500]}")
                    if note.get("tags"):
                        lines.append(f"  - *Tags*: {', '.join(note['tags'])}")
            lines.append("")

        lines.append("---\n")

    report = "\n".join(lines)
    return {
        "items_processed": len(items_to_process),
        "report": report,
    }


# ---------------------------------------------------------------------------
# Optional Better BibTeX integration
# ---------------------------------------------------------------------------

_BBT_BASE_URL = "http://localhost:23119/better-bibtex/json-rpc"


async def _bbt_call(method: str, params: list[Any] | None = None) -> Any:
    """Call a Better BibTeX JSON-RPC method.

    Returns the result or raises an exception if BBT is unavailable.
    """
    import httpx

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": 1,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_BBT_BASE_URL, json=payload)
        resp.raise_for_status()
        body = resp.json()

    if "error" in body:
        raise RuntimeError(f"BBT error: {body['error']}")
    return body.get("result")


async def _bbt_available() -> bool:
    """Check whether Better BibTeX is running and reachable."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                _BBT_BASE_URL,
                json={"jsonrpc": "2.0", "method": "user.groups", "params": [], "id": 1},
            )
            return resp.status_code == 200
    except Exception:
        return False


@mcp.tool()
async def bbt_status() -> dict[str, Any]:
    """Check if Better BibTeX (BBT) is installed and running in Zotero.

    BBT provides stable citation keys, enhanced BibTeX/BibLaTeX export,
    and the Cite-As-You-Write feature. It must be installed as a Zotero
    plugin and Zotero must be running.

    Returns:
        Dictionary with availability status and BBT version if available.
    """
    available = await _bbt_available()
    if not available:
        return {
            "available": False,
            "message": (
                "Better BibTeX is not reachable. Ensure Zotero is running "
                "and BBT is installed (https://retorque.re/zotero-better-bibtex/)."
            ),
        }

    try:
        # BBT doesn't have a direct version method via JSON-RPC,
        # but we can confirm connectivity
        return {
            "available": True,
            "endpoint": _BBT_BASE_URL,
            "message": "Better BibTeX is running and reachable.",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


@mcp.tool()
async def bbt_get_citekey(item_key: str) -> dict[str, Any]:
    """Get the Better BibTeX citation key for a Zotero item.

    Requires Zotero to be running with Better BibTeX installed.

    Args:
        item_key: The Zotero item key.

    Returns:
        Dictionary with the BBT citation key.
    """
    if not await _bbt_available():
        return {
            "error": "Better BibTeX is not available. Ensure Zotero is running with BBT installed.",
        }

    try:
        # Use BBT's JSON-RPC to export a single item and extract the citekey
        result = await _bbt_call(
            "item.citationkey",
            [{"itemKey": item_key}],
        )
        return {"item_key": item_key, "citekey": result}
    except Exception as exc:
        return {"item_key": item_key, "error": str(exc)}


@mcp.tool()
async def bbt_search_by_citekey(citekey: str) -> dict[str, Any]:
    """Look up a Zotero item by its Better BibTeX citation key.

    Args:
        citekey: The BBT citation key (e.g., 'smith2024climate').

    Returns:
        Dictionary with the Zotero item key and metadata.
    """
    if not await _bbt_available():
        return {
            "error": "Better BibTeX is not available. Ensure Zotero is running with BBT installed.",
        }

    try:
        result = await _bbt_call(
            "item.search",
            [citekey],
        )
        return {"citekey": citekey, "results": result}
    except Exception as exc:
        return {"citekey": citekey, "error": str(exc)}


@mcp.tool()
async def bbt_export(
    collection_key: str | None = None,
    format: str = "betterbibtex",
) -> dict[str, Any]:
    """Export references via Better BibTeX's enhanced export formats.

    Supports 'betterbibtex', 'betterbiblatex', and 'bettercsljson'.
    Provides more accurate and customizable exports than Zotero's built-in.

    Args:
        collection_key: Collection key to export. Exports entire library if None.
        format: Export format. One of 'betterbibtex', 'betterbiblatex', 'bettercsljson'.

    Returns:
        Dictionary with the exported bibliography text.
    """
    if not await _bbt_available():
        return {
            "error": "Better BibTeX is not available. Ensure Zotero is running with BBT installed.",
        }

    valid_formats = {"betterbibtex", "betterbiblatex", "bettercsljson"}
    if format not in valid_formats:
        return {
            "error": (
                f"Invalid format '{format}'. Must be one of: {', '.join(sorted(valid_formats))}"
            ),
        }

    try:
        translator_map = {
            "betterbibtex": "Better BibTeX",
            "betterbiblatex": "Better BibLaTeX",
            "bettercsljson": "Better CSL JSON",
        }
        params: list[Any] = [
            collection_key,
            {"translator": translator_map[format]},
        ]
        result = await _bbt_call(
            "collection.export" if collection_key else "library.export",
            params,
        )
        return {"format": format, "content": result}
    except Exception as exc:
        return {"format": format, "error": str(exc)}


@mcp.tool()
async def bbt_cayw() -> dict[str, Any]:
    """Trigger Better BibTeX's Cite-As-You-Write picker.

    Opens the BBT citation picker dialog in Zotero for the user to select
    references interactively. Requires Zotero to be running with BBT.

    Returns:
        Dictionary with the selected citation(s) in pandoc format.
    """
    if not await _bbt_available():
        return {
            "error": "Better BibTeX is not available. Ensure Zotero is running with BBT installed.",
        }

    try:
        result = await _bbt_call("item.picker", [{"format": "pandoc"}])
        return {"citations": result}
    except Exception as exc:
        return {"error": str(exc)}


def serve() -> None:
    """Run the Zotero Local MCP server."""
    mcp.run(transport="stdio")
