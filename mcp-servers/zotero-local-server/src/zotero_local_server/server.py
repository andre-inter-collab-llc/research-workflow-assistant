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
# Annotation-focused tools (evidence extraction & synthesis)
# ---------------------------------------------------------------------------

# Default color-to-category mapping (user can override in project-config.yaml)
_DEFAULT_COLOR_MAP: dict[str, str] = {
    "#ffd400": "finding",  # yellow
    "#ff6666": "concern",  # red
    "#5fb236": "method",  # green
    "#2ea8e5": "quote",  # blue
    "#a28ae5": "theory",  # purple
    "#e56eee": "definition",  # magenta
    "#f19837": "example",  # orange
}


def _color_category(color: str, color_map: dict[str, str] | None = None) -> str:
    """Map a hex color to a human-readable category."""
    cmap = color_map or _DEFAULT_COLOR_MAP
    if not color:
        return "uncategorized"
    color_lower = color.strip().lower()
    return cmap.get(color_lower, "uncategorized")


@mcp.tool()
async def extract_highlights_as_evidence(
    item_key: str,
    color_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Extract all highlights from a Zotero item as a structured evidence table.

    Combines Zotero reader annotations with PDF-embedded annotations.
    Each highlight is returned with: quote, page, color-coded category,
    and user comment.

    Args:
        item_key: Zotero item key (parent or attachment).
        color_map: Optional dict mapping hex colors to category names.
            Defaults: yellow=finding, red=concern, green=method, blue=quote.

    Returns:
        Dictionary with an evidence table (list of structured rows).
    """
    data_dir = _data_dir()
    evidence: list[dict[str, str]] = []

    # Zotero reader annotations from database
    db_annotations: list[dict[str, Any]] = []
    attachments = zotero_db.get_attachments(data_dir, item_key)
    for att in attachments:
        if att.get("content_type") == "application/pdf":
            anns = zotero_db.get_annotations_for_attachment(data_dir, att["key"])
            db_annotations.extend(anns)

    # Also try item_key directly as attachment
    direct_anns = zotero_db.get_annotations_for_attachment(data_dir, item_key)
    db_annotations.extend(direct_anns)

    for ann in db_annotations:
        if ann.get("type") in ("highlight", "underline"):
            evidence.append(
                {
                    "source": "zotero_reader",
                    "quote": ann.get("text", ""),
                    "page": ann.get("page_label", ""),
                    "color": ann.get("color", ""),
                    "category": _color_category(ann.get("color", ""), color_map),
                    "comment": ann.get("comment", ""),
                }
            )

    # PDF-embedded annotations
    pdf_path = _resolve_pdf_path(data_dir, item_key)
    if pdf_path:
        pdf_result = pdf_reader.extract_annotations(pdf_path)
        for ann in pdf_result.annotations:
            if ann.type in ("highlight", "underline"):
                hex_color = ""
                if ann.color:
                    r = int(ann.color[0] * 255)
                    g = int(ann.color[1] * 255)
                    b = int(ann.color[2] * 255)
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                evidence.append(
                    {
                        "source": "pdf_embedded",
                        "quote": ann.highlighted_text,
                        "page": str(ann.page),
                        "color": hex_color,
                        "category": _color_category(hex_color, color_map),
                        "comment": ann.content,
                    }
                )

    return {
        "item_key": item_key,
        "evidence_count": len(evidence),
        "evidence": evidence,
    }


@mcp.tool()
async def extract_annotations_by_color(
    item_key: str,
    color: str | None = None,
    category: str | None = None,
    color_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Filter annotations by color or category for a Zotero item.

    Either specify a hex color directly, or a category name that maps
    to a color via the color map.

    Args:
        item_key: Zotero item key.
        color: Hex color to filter (e.g., '#ffd400' for yellow).
        category: Category name to filter (e.g., 'finding', 'concern').
        color_map: Optional custom color-to-category mapping.

    Returns:
        Dictionary with filtered annotations.
    """
    # Get all evidence first
    result = await extract_highlights_as_evidence(item_key, color_map)
    all_evidence = result.get("evidence", [])

    if color:
        color_lower = color.strip().lower()
        filtered = [e for e in all_evidence if e.get("color", "").lower() == color_lower]
    elif category:
        cat_lower = category.strip().lower()
        filtered = [e for e in all_evidence if e.get("category", "").lower() == cat_lower]
    else:
        # Group by category
        by_category: dict[str, list[dict[str, str]]] = {}
        for e in all_evidence:
            cat = e.get("category", "uncategorized")
            by_category.setdefault(cat, []).append(e)
        return {
            "item_key": item_key,
            "total": len(all_evidence),
            "by_category": {k: {"count": len(v), "annotations": v} for k, v in by_category.items()},
        }

    return {
        "item_key": item_key,
        "filter": color or category,
        "count": len(filtered),
        "annotations": filtered,
    }


@mcp.tool()
async def search_annotations(
    query: str,
    collection_key: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search across all Zotero reader annotations in the library.

    Searches both highlighted text and user comments. Requires Zotero 7.

    Args:
        query: Search term or phrase (case-insensitive).
        collection_key: Optional collection key to limit scope.
        limit: Maximum results (default 50, max 200).

    Returns:
        Dictionary with matching annotations and their parent item info.
    """
    limit = min(limit, 200)
    data_dir = _data_dir()
    results = zotero_db.search_all_annotations(data_dir, query, collection_key, limit)

    # Enrich with parent item titles
    enriched = []
    for ann in results:
        parent_key = ann.get("parent_key", "")
        title = ""
        if parent_key:
            item_info = zotero_db.get_item_by_key(data_dir, parent_key)
            title = (item_info or {}).get("title", "")
        enriched.append({**ann, "parent_title": title})

    return {
        "query": query,
        "count": len(enriched),
        "results": enriched,
    }


@mcp.tool()
async def build_evidence_table(
    item_keys: list[str] | None = None,
    collection_key: str | None = None,
    color_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compile annotations and notes into a structured evidence synthesis table.

    Processes either a list of item keys or an entire collection.
    Returns a table suitable for evidence synthesis in systematic reviews.

    Args:
        item_keys: List of Zotero item keys. If None, uses collection_key.
        collection_key: Collection to process (used if item_keys is None).
        color_map: Optional custom color-to-category mapping.

    Returns:
        Dictionary with an evidence table grouped by item.
    """
    data_dir = _data_dir()

    keys_to_process: list[str] = []
    if item_keys:
        keys_to_process = item_keys
    elif collection_key:
        all_pdfs = zotero_db.get_all_pdf_attachments(data_dir, collection_key)
        seen: set[str] = set()
        for pdf_info in all_pdfs:
            pk = pdf_info.get("parent_key", "")
            if pk and pk not in seen:
                seen.add(pk)
                keys_to_process.append(pk)
    else:
        return {"error": "Provide either item_keys or collection_key."}

    table: list[dict[str, Any]] = []
    for key in keys_to_process:
        item_info = zotero_db.get_item_by_key(data_dir, key)
        title = (item_info or {}).get("title", key)
        creators = (item_info or {}).get("creators", [])
        date = (item_info or {}).get("date", "")

        evidence_result = await extract_highlights_as_evidence(key, color_map)
        evidence = evidence_result.get("evidence", [])

        notes = zotero_db.get_notes_for_item(data_dir, key)
        import re

        note_texts = []
        for n in notes:
            text = re.sub(r"<[^>]+>", "", n.get("note", "")).strip()
            if text:
                note_texts.append(text[:500])

        table.append(
            {
                "item_key": key,
                "title": title,
                "creators": creators,
                "date": date,
                "highlights": evidence,
                "highlight_count": len(evidence),
                "notes": note_texts,
                "note_count": len(note_texts),
            }
        )

    return {
        "items_processed": len(table),
        "evidence_table": table,
    }


@mcp.tool()
async def extract_pdf_figures(
    item_key: str,
    min_size: int = 10000,
) -> dict[str, Any]:
    """Extract embedded images/figures from the PDF associated with a Zotero item.

    Uses PyMuPDF to list images on each page with their dimensions and size.
    Does not return actual image data — returns metadata for identification.

    Args:
        item_key: Zotero item key (parent or attachment).
        min_size: Minimum image size in bytes to include (default 10000,
            to skip tiny icons/logos).

    Returns:
        Dictionary with figure metadata per page.
    """
    import pymupdf

    data_dir = _data_dir()
    pdf_path = _resolve_pdf_path(data_dir, item_key)

    if not pdf_path:
        return {"item_key": item_key, "error": "No PDF attachment found for this item"}

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        return {"item_key": item_key, "error": f"Cannot open PDF: {exc}"}

    try:
        figures: list[dict[str, Any]] = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                size = len(base_image.get("image", b""))
                if size < min_size:
                    continue

                figures.append(
                    {
                        "page": page_num + 1,
                        "index": img_index,
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                        "colorspace": base_image.get("cs-name", ""),
                        "bpc": base_image.get("bpc", 0),
                        "size_bytes": size,
                        "ext": base_image.get("ext", ""),
                    }
                )

        return {
            "item_key": item_key,
            "total_figures": len(figures),
            "figures": figures,
        }

    finally:
        doc.close()


@mcp.tool()
async def get_item_reading_progress(item_key: str) -> dict[str, Any]:
    """Report reading progress based on annotation coverage.

    Compares pages with annotations to total pages in the PDF to estimate
    how much of the paper has been actively reviewed.

    Args:
        item_key: Zotero item key (parent or attachment).

    Returns:
        Dictionary with total pages, annotated pages, and coverage percentage.
    """
    data_dir = _data_dir()
    pdf_path = _resolve_pdf_path(data_dir, item_key)

    if not pdf_path:
        return {"item_key": item_key, "error": "No PDF attachment found for this item"}

    # Get total page count
    try:
        import pymupdf

        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as exc:
        return {"item_key": item_key, "error": f"Cannot open PDF: {exc}"}

    # Count annotated pages from Zotero DB
    annotated_pages: set[str] = set()

    attachments = zotero_db.get_attachments(data_dir, item_key)
    for att in attachments:
        if att.get("content_type") == "application/pdf":
            anns = zotero_db.get_annotations_for_attachment(data_dir, att["key"])
            for ann in anns:
                pl = ann.get("page_label", "")
                if pl:
                    annotated_pages.add(pl)

    # Also try as direct attachment
    direct_anns = zotero_db.get_annotations_for_attachment(data_dir, item_key)
    for ann in direct_anns:
        pl = ann.get("page_label", "")
        if pl:
            annotated_pages.add(pl)

    # Also check PDF-embedded annotations
    pdf_result = pdf_reader.extract_annotations(pdf_path)
    for ann in pdf_result.annotations:
        annotated_pages.add(str(ann.page))

    num_annotated = len(annotated_pages)
    coverage = round((num_annotated / total_pages * 100), 1) if total_pages > 0 else 0.0

    return {
        "item_key": item_key,
        "total_pages": total_pages,
        "annotated_pages": num_annotated,
        "coverage_percent": coverage,
        "annotated_page_numbers": sorted(annotated_pages),
    }


@mcp.tool()
async def compare_annotations(
    item_keys: list[str],
    color_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compare annotations across multiple Zotero items side by side.

    Useful for evidence synthesis — shows what was highlighted/noted
    across papers in a structured comparison format.

    Args:
        item_keys: List of 2+ Zotero item keys to compare.
        color_map: Optional custom color-to-category mapping.

    Returns:
        Dictionary with per-item annotation summaries and cross-item analysis.
    """
    if len(item_keys) < 2:
        return {"error": "Provide at least 2 item keys to compare."}

    data_dir = _data_dir()
    items: list[dict[str, Any]] = []

    all_categories: dict[str, int] = {}

    for key in item_keys:
        item_info = zotero_db.get_item_by_key(data_dir, key)
        title = (item_info or {}).get("title", key)

        evidence_result = await extract_highlights_as_evidence(key, color_map)
        evidence = evidence_result.get("evidence", [])

        # Category breakdown
        categories: dict[str, int] = {}
        for e in evidence:
            cat = e.get("category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
            all_categories[cat] = all_categories.get(cat, 0) + 1

        items.append(
            {
                "item_key": key,
                "title": title,
                "total_annotations": len(evidence),
                "categories": categories,
                "annotations": evidence,
            }
        )

    return {
        "items_compared": len(items),
        "items": items,
        "overall_categories": all_categories,
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


@mcp.tool()
async def bbt_auto_pin(item_keys: list[str]) -> dict[str, Any]:
    """Pin Better BibTeX citation keys for one or more items.

    Pinned keys are never automatically changed by BBT when item
    metadata is updated. Useful for ensuring stable @citekeys in
    manuscripts.

    Args:
        item_keys: List of Zotero item keys to pin.

    Returns:
        Dictionary with pinned status for each item.
    """
    if not await _bbt_available():
        return {
            "error": "Better BibTeX is not available. Ensure Zotero is running with BBT installed.",
        }

    results: list[dict[str, str]] = []
    for key in item_keys:
        try:
            citekey = await _bbt_call("item.citationkey", [{"itemKey": key}])
            # Pin by exporting and re-setting the key explicitly
            await _bbt_call("item.citationkey.set", [{"itemKey": key, "citationKey": citekey}])
            results.append({"item_key": key, "citekey": citekey, "status": "pinned"})
        except Exception as exc:
            results.append({"item_key": key, "status": "error", "error": str(exc)})

    return {"results": results}


@mcp.tool()
async def bbt_sync_bib_file(
    file_path: str,
    collection_key: str | None = None,
    format: str = "betterbibtex",
) -> dict[str, Any]:
    """Export a BBT-managed .bib file to a project directory.

    Writes the Better BibTeX export to disk, keeping it in sync with
    the Zotero collection. Call this before rendering a Quarto document
    to ensure the bibliography is up to date.

    Args:
        file_path: Absolute path for the output .bib file.
        collection_key: Collection to export (None for entire library).
        format: BBT format: 'betterbibtex', 'betterbiblatex', 'bettercsljson'.

    Returns:
        Dictionary with status, file path, and entry count.
    """
    import pathlib

    result = await bbt_export(collection_key=collection_key, format=format)
    if "error" in result:
        return result

    content = result.get("content", "")
    if not content:
        return {"status": "empty", "message": "BBT export returned empty content."}

    out_path = pathlib.Path(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    # Count entries
    if format in ("betterbibtex", "betterbiblatex"):
        count = content.count("@")
    else:
        count = content.count('"id"')

    return {
        "status": "synced",
        "file_path": str(out_path),
        "format": format,
        "entries": count,
    }


def serve() -> None:
    """Run the Zotero Local MCP server."""
    mcp.run(transport="stdio")
