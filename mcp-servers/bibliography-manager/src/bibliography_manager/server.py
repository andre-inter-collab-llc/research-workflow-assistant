"""Bibliography Manager MCP Server — local reference management without Zotero.

Provides a Zotero-compatible workflow for researchers who don't use Zotero:
- Import references from BibTeX / RIS files or search results
- Link PDF files and supplementary materials to references
- Add notes, critiques, and data extraction comments
- Store and search PDF annotations
- Export to BibTeX, RIS, or CSL-JSON for Quarto/Pandoc
- Track reading progress with a reading list view
- Download and manage CSL citation styles

All data is stored per-project in SQLite (data/search_results.db),
the same database used by the search MCP servers.
"""

import logging
import shutil
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from rwa_result_store import (
    add_note,
    export_results_bibliography,
    export_results_csv,
    export_results_excel,
    get_annotations,
    get_attachments,
    get_notes,
    get_reading_list,
    get_results,
    get_searches,
    import_bibtex,
    import_ris,
    link_file,
    search_annotations,
    search_notes,
    store_annotations,
    store_results,
    update_note,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "bibliography-manager",
    instructions=(
        "Local bibliography manager for researchers who do not use Zotero. "
        "Manage references, PDFs, notes, and annotations per project. "
        "Export to BibTeX/RIS/CSL-JSON for Quarto manuscripts."
    ),
)


# ===================================================================
# Reference management
# ===================================================================


@mcp.tool()
async def bib_add_item(
    project_path: str,
    title: str,
    authors: list[str] | None = None,
    year: str = "",
    doi: str = "",
    pmid: str = "",
    journal: str = "",
    volume: str = "",
    issue: str = "",
    pages: str = "",
    abstract: str = "",
) -> dict[str, Any]:
    """Add a single reference to the project bibliography.

    Args:
        project_path: Absolute path to the project directory.
        title: The title of the work.
        authors: List of author names (e.g. ["Smith, John", "Doe, Jane"]).
        year: Publication year.
        doi: Digital Object Identifier.
        pmid: PubMed ID.
        journal: Journal or source name.
        volume: Volume number.
        issue: Issue number.
        pages: Page range.
        abstract: Abstract text.

    Returns:
        Dictionary with search_id and confirmation.
    """
    result = {
        "title": title,
        "authors": authors or [],
        "year": year,
        "doi": doi,
        "pmid": pmid,
        "journal": journal,
        "volume": volume,
        "issue": issue,
        "pages": pages,
        "abstract": abstract,
    }
    search_id = store_results(
        project_path,
        "manual",
        f"Manual entry: {title[:80]}",
        [result],
        total_count=1,
        parameters={"method": "manual_entry"},
    )
    return {"search_id": search_id, "message": f"Added: {title}"}


@mcp.tool()
async def bib_import_bibtex(
    project_path: str,
    file_path: str | None = None,
    bibtex_text: str | None = None,
) -> dict[str, Any]:
    """Import references from a BibTeX file or text.

    Provide either file_path to a .bib file, or bibtex_text with raw BibTeX content.

    Args:
        project_path: Absolute path to the project directory.
        file_path: Path to a .bib file to import.
        bibtex_text: Raw BibTeX content to import.

    Returns:
        Dictionary with search_id (0 if nothing imported).
    """
    search_id = import_bibtex(
        project_path,
        bibtex_text=bibtex_text,
        file_path=file_path,
    )
    if search_id:
        return {"search_id": search_id, "status": "imported"}
    return {"search_id": 0, "status": "no_entries"}


@mcp.tool()
async def bib_import_ris(
    project_path: str,
    file_path: str | None = None,
    ris_text: str | None = None,
) -> dict[str, Any]:
    """Import references from an RIS file or text.

    Args:
        project_path: Absolute path to the project directory.
        file_path: Path to a .ris file to import.
        ris_text: Raw RIS content to import.

    Returns:
        Dictionary with search_id (0 if nothing imported).
    """
    search_id = import_ris(
        project_path,
        ris_text=ris_text,
        file_path=file_path,
    )
    if search_id:
        return {"search_id": search_id, "status": "imported"}
    return {"search_id": 0, "status": "no_entries"}


@mcp.tool()
async def bib_search(
    project_path: str,
    source: str | None = None,
    query: str | None = None,
    deduplicated: bool = False,
) -> dict[str, Any]:
    """Search stored references in the project bibliography.

    Args:
        project_path: Absolute path to the project directory.
        source: Optional filter by source (e.g. 'pubmed', 'manual', 'bibtex_import').
        query: Optional query substring to filter by search query.
        deduplicated: If True, deduplicate across sources by DOI/PMID.

    Returns:
        Dictionary with results list and count.
    """
    results = get_results(project_path, source=source, query=query, deduplicated=deduplicated)
    return {"total": len(results), "results": results}


@mcp.tool()
async def bib_list_searches(
    project_path: str,
) -> dict[str, Any]:
    """List all searches and imports recorded for a project.

    Args:
        project_path: Absolute path to the project directory.

    Returns:
        Dictionary with searches list.
    """
    searches = get_searches(project_path)
    return {"total": len(searches), "searches": searches}


# ===================================================================
# File attachment
# ===================================================================


@mcp.tool()
async def bib_link_file(
    project_path: str,
    result_id: int,
    file_path: str,
    mime_type: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Link a PDF or other file to a reference.

    Args:
        project_path: Absolute path to the project directory.
        result_id: The result_id of the reference to attach to.
        file_path: Absolute or project-relative path to the file.
        mime_type: MIME type (e.g. 'application/pdf'). Auto-detected from extension if omitted.
        label: Human-readable label for the attachment.

    Returns:
        Dictionary with attachment_id.
    """
    if mime_type is None:
        ext = Path(file_path).suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".html": "text/html",
            ".txt": "text/plain",
            ".csv": "text/csv",
        }
        mime_type = mime_map.get(ext)

    attachment_id = link_file(
        project_path,
        result_id=result_id,
        file_path=file_path,
        mime_type=mime_type,
        label=label,
    )
    return {"attachment_id": attachment_id, "status": "linked"}


@mcp.tool()
async def bib_get_attachments(
    project_path: str,
    result_id: int,
) -> dict[str, Any]:
    """List all files attached to a reference.

    Args:
        project_path: Absolute path to the project directory.
        result_id: The result_id of the reference.

    Returns:
        Dictionary with attachments list.
    """
    attachments = get_attachments(project_path, result_id)
    return {"total": len(attachments), "attachments": attachments}


# ===================================================================
# Notes
# ===================================================================


@mcp.tool()
async def bib_add_note(
    project_path: str,
    result_id: int,
    content: str,
    note_type: str = "general",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Add a note to a reference.

    Args:
        project_path: Absolute path to the project directory.
        result_id: The result_id of the reference to annotate.
        content: Note text (Markdown supported).
        note_type: Category — 'general', 'critique', 'summary', 'extraction', 'methodology'.
        tags: Optional freeform tags.

    Returns:
        Dictionary with note_id.
    """
    note_id = add_note(
        project_path,
        result_id=result_id,
        content=content,
        note_type=note_type,
        tags=tags,
    )
    return {"note_id": note_id, "status": "added"}


@mcp.tool()
async def bib_update_note(
    project_path: str,
    note_id: int,
    content: str | None = None,
    note_type: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update an existing note.

    Args:
        project_path: Absolute path to the project directory.
        note_id: The note_id to update.
        content: New content (replaces existing).
        note_type: New note type.
        tags: New tags list (replaces existing).

    Returns:
        Dictionary with update status.
    """
    updated = update_note(
        project_path,
        note_id=note_id,
        content=content,
        note_type=note_type,
        tags=tags,
    )
    return {"updated": updated}


@mcp.tool()
async def bib_get_notes(
    project_path: str,
    result_id: int | None = None,
    note_type: str | None = None,
) -> dict[str, Any]:
    """Get notes for a reference, optionally filtered by type.

    Args:
        project_path: Absolute path to the project directory.
        result_id: Optional filter by specific reference.
        note_type: Optional filter by note type.

    Returns:
        Dictionary with notes list.
    """
    notes = get_notes(project_path, result_id=result_id, note_type=note_type)
    return {"total": len(notes), "notes": notes}


@mcp.tool()
async def bib_search_notes(
    project_path: str,
    query: str,
) -> dict[str, Any]:
    """Full-text search across all notes in the project.

    Args:
        project_path: Absolute path to the project directory.
        query: Search term to match in note content or tags.

    Returns:
        Dictionary with matching notes and their parent reference titles.
    """
    results = search_notes(project_path, query)
    return {"total": len(results), "results": results}


# ===================================================================
# Annotations (PDF highlights, extracted from linked files)
# ===================================================================


@mcp.tool()
async def bib_store_annotations(
    project_path: str,
    attachment_id: int,
    result_id: int,
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Store annotations extracted from a PDF attachment.

    Each annotation dict may contain: page (int), annotation_type (str),
    color (str), content (str), comment (str).

    Args:
        project_path: Absolute path to the project directory.
        attachment_id: The attachment the annotations came from.
        result_id: The reference the attachment belongs to.
        annotations: List of annotation dicts.

    Returns:
        Dictionary with count of stored annotations.
    """
    count = store_annotations(
        project_path,
        attachment_id=attachment_id,
        result_id=result_id,
        annotations=annotations,
    )
    return {"stored": count}


@mcp.tool()
async def bib_get_annotations(
    project_path: str,
    result_id: int | None = None,
    attachment_id: int | None = None,
    color: str | None = None,
) -> dict[str, Any]:
    """Get stored annotations, optionally filtered.

    Args:
        project_path: Absolute path to the project directory.
        result_id: Optional filter by reference.
        attachment_id: Optional filter by attachment.
        color: Optional filter by highlight color (hex).

    Returns:
        Dictionary with annotations list.
    """
    anns = get_annotations(
        project_path,
        result_id=result_id,
        attachment_id=attachment_id,
        color=color,
    )
    return {"total": len(anns), "annotations": anns}


@mcp.tool()
async def bib_search_annotations(
    project_path: str,
    query: str,
) -> dict[str, Any]:
    """Search annotation content and comments across all references.

    Args:
        project_path: Absolute path to the project directory.
        query: Search term.

    Returns:
        Dictionary with matching annotations and their reference titles.
    """
    results = search_annotations(project_path, query)
    return {"total": len(results), "results": results}


# ===================================================================
# Export
# ===================================================================


@mcp.tool()
async def bib_export(
    project_path: str,
    format: str = "bibtex",
    output_path: str | None = None,
    deduplicated: bool = True,
) -> dict[str, Any]:
    """Export the project bibliography to a bibliographic format.

    Supported formats: 'bibtex', 'ris', 'csljson'.
    The exported file can be used directly with Quarto/Pandoc for citations.

    Args:
        project_path: Absolute path to the project directory.
        format: Export format — 'bibtex' (default), 'ris', or 'csljson'.
        output_path: Optional custom output path.
        deduplicated: If True (default), deduplicate by DOI/PMID.

    Returns:
        Dictionary with export status and file path.
    """
    try:
        path = export_results_bibliography(
            project_path,
            fmt=format,
            output_path=output_path,
            deduplicated=deduplicated,
        )
    except ValueError as exc:
        return {"status": "error", "file": "", "message": str(exc)}
    if path:
        return {"status": "exported", "file": path}
    return {"status": "no_results", "file": ""}


@mcp.tool()
async def bib_export_excel(
    project_path: str,
    output_path: str | None = None,
    deduplicated: bool = False,
) -> dict[str, Any]:
    """Export references to a formatted Excel workbook.

    Args:
        project_path: Absolute path to the project directory.
        output_path: Optional custom output path.
        deduplicated: If True, deduplicate results.

    Returns:
        Dictionary with export status and file path.
    """
    path = export_results_excel(project_path, output_path, deduplicated)
    if path:
        return {"status": "exported", "file": path}
    return {"status": "no_results", "file": ""}


@mcp.tool()
async def bib_export_csv(
    project_path: str,
    output_path: str | None = None,
    deduplicated: bool = False,
) -> dict[str, Any]:
    """Export references to CSV.

    Args:
        project_path: Absolute path to the project directory.
        output_path: Optional custom output path.
        deduplicated: If True, deduplicate results.

    Returns:
        Dictionary with export status and file path.
    """
    path = export_results_csv(project_path, output_path, deduplicated)
    if path:
        return {"status": "exported", "file": path}
    return {"status": "no_results", "file": ""}


# ===================================================================
# Reading list
# ===================================================================


@mcp.tool()
async def bib_reading_list(
    project_path: str,
    note_type: str | None = None,
    has_attachments: bool | None = None,
    has_notes: bool | None = None,
) -> dict[str, Any]:
    """Get a reading list view of references with file/note/annotation counts.

    Use this to see which papers have been read, annotated, or need attention.

    Args:
        project_path: Absolute path to the project directory.
        note_type: Only include results that have a note of this type.
        has_attachments: True = only with files, False = only without.
        has_notes: True = only with notes, False = only without.

    Returns:
        Dictionary with enriched result list showing attachment/note/annotation counts.
    """
    items = get_reading_list(
        project_path,
        note_type=note_type,
        has_attachments=has_attachments,
        has_notes=has_notes,
    )
    return {"total": len(items), "items": items}


# ===================================================================
# Zotero migration helper
# ===================================================================


@mcp.tool()
async def bib_migrate_to_zotero(
    project_path: str,
    format: str = "ris",
) -> dict[str, Any]:
    """Export references in a format ready for Zotero import.

    When a researcher is ready to adopt Zotero, this exports their local
    bibliography to RIS (Zotero's best-supported import format) or BibTeX.
    Zotero can then import the file via File > Import.

    Notes and annotations are NOT transferred — only bibliographic metadata.
    The researcher should re-attach PDFs and rebuild notes in Zotero.

    Args:
        project_path: Absolute path to the project directory.
        format: 'ris' (default, recommended) or 'bibtex'.

    Returns:
        Dictionary with file path and migration instructions.
    """
    if format not in ("ris", "bibtex"):
        return {"status": "error", "message": "Format must be 'ris' or 'bibtex'."}

    path = export_results_bibliography(
        project_path,
        fmt=format,
        deduplicated=True,
    )
    if not path:
        return {"status": "no_results", "file": ""}

    return {
        "status": "exported",
        "file": path,
        "instructions": (
            f"Import into Zotero: File > Import > select {Path(path).name}. "
            "After import, re-attach PDFs to their entries in Zotero. "
            "Notes and annotations from the local bibliography are not "
            "transferred — recreate them in Zotero or keep them in the "
            "project database as a reference."
        ),
    }


# ===================================================================
# CSL citation style management
# ===================================================================


def _csl_dir() -> Path:
    """Return the path to the shared CSL styles directory (repo-root/csl/)."""
    # Walk up from this file to reach the repo root:
    # server.py → bibliography_manager/ → src/ → bibliography-manager/ → mcp-servers/ → repo-root
    return Path(__file__).resolve().parents[4] / "csl"


def _parse_csl_title(csl_path: Path) -> str:
    """Extract the <title> from a CSL file, or return the stem as fallback."""
    try:
        ns = {"csl": "http://purl.org/net/xbiblio/csl"}
        tree = ET.parse(csl_path)
        title_el = tree.getroot().find(".//csl:title", ns)
        if title_el is not None and title_el.text:
            return title_el.text
    except ET.ParseError:
        pass
    return csl_path.stem


@mcp.tool()
async def bib_list_csl_styles() -> dict[str, Any]:
    """List all citation styles available in the shared CSL library.

    Returns a list of style IDs (file stems) and their full titles, sourced
    from the ``csl/`` directory in the repository root.

    Returns:
        Dictionary with ``styles`` list, each containing ``id``, ``title``,
        and ``file`` keys.
    """
    csl = _csl_dir()
    if not csl.is_dir():
        return {"status": "error", "message": f"CSL directory not found: {csl}"}
    styles = []
    for p in sorted(csl.glob("*.csl")):
        styles.append(
            {
                "id": p.stem,
                "title": _parse_csl_title(p),
                "file": p.name,
            }
        )
    return {"status": "ok", "count": len(styles), "styles": styles}


@mcp.tool()
async def bib_download_csl_style(
    style_id: str,
) -> dict[str, Any]:
    """Download a CSL citation style from the Zotero Style Repository.

    Fetches the style from ``https://www.zotero.org/styles/{style_id}`` and
    saves it to the shared ``csl/`` directory.  Over 10 000 styles are
    available — browse https://www.zotero.org/styles to find the style ID
    (it is the last segment of the URL, e.g. ``elsevier-harvard``).

    If the style already exists locally, it is overwritten (updated).
    If the downloaded style is a *dependent* style (a thin redirect to a
    parent style), the parent is also fetched automatically.

    Args:
        style_id: The CSL style identifier, e.g. ``vancouver-superscript``.

    Returns:
        Dictionary with the saved file path and style title.
    """
    csl = _csl_dir()
    csl.mkdir(parents=True, exist_ok=True)

    url = f"https://www.zotero.org/styles/{style_id}"
    dest = csl / f"{style_id}.csl"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RWA/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {
                "status": "not_found",
                "message": (
                    f"Style '{style_id}' was not found in the Zotero Style "
                    "Repository. Browse https://www.zotero.org/styles to find "
                    "the correct style ID."
                ),
            }
        return {"status": "error", "message": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    # Validate: must be XML with the CSL namespace
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return {
            "status": "error",
            "message": "Downloaded file is not valid XML.",
        }

    ns = {"csl": "http://purl.org/net/xbiblio/csl"}
    title_el = root.find(".//csl:title", ns)
    title = title_el.text if (title_el is not None and title_el.text) else style_id

    dest.write_bytes(data)
    logger.info("Downloaded CSL style '%s' → %s", style_id, dest)

    result: dict[str, Any] = {
        "status": "ok",
        "style_id": style_id,
        "title": title,
        "file": str(dest),
    }

    # Check for dependent style → also fetch the parent
    links = root.findall(".//csl:link", ns)
    for link in links:
        if link.get("rel") == "independent-parent":
            parent_url = link.get("href", "")
            parent_id = parent_url.rstrip("/").rsplit("/", 1)[-1]
            if parent_id and not (csl / f"{parent_id}.csl").exists():
                logger.info(
                    "Style '%s' is dependent — also fetching parent '%s'",
                    style_id,
                    parent_id,
                )
                parent_result = await bib_download_csl_style(parent_id)
                result["parent_style"] = parent_result
            break

    return result


@mcp.tool()
async def bib_copy_csl_to_project(
    style_id: str,
    project_path: str,
) -> dict[str, Any]:
    """Copy a CSL style file from the shared library into a project directory.

    This makes the project self-contained — it carries its own citation style
    file rather than depending on a relative path to the repo-root CSL library.

    Args:
        style_id: The CSL style identifier (filename without ``.csl``),
            e.g. ``vancouver-superscript``.
        project_path: Absolute path to the project directory.

    Returns:
        Dictionary with the destination path and style title.
    """
    csl = _csl_dir()
    src = csl / f"{style_id}.csl"
    if not src.is_file():
        available = [p.stem for p in sorted(csl.glob("*.csl"))]
        return {
            "status": "not_found",
            "message": (
                f"Style '{style_id}' is not in the CSL library. "
                f"Available: {', '.join(available)}. "
                "Use bib_download_csl_style to fetch it first."
            ),
        }

    dest = Path(project_path) / f"{style_id}.csl"
    shutil.copy2(src, dest)

    return {
        "status": "ok",
        "style_id": style_id,
        "title": _parse_csl_title(src),
        "file": str(dest),
    }


def serve() -> None:
    """Run the Bibliography Manager MCP server."""
    mcp.run(transport="stdio")
