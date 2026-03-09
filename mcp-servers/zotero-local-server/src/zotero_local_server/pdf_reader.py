"""PDF text and annotation extraction using PyMuPDF.

Provides functions to extract full text, embedded annotations (highlights,
sticky notes, underlines, strike-throughs, free text), and to search
PDF content for keywords with surrounding context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf  # PyMuPDF


@dataclass
class PdfAnnotation:
    """A single annotation extracted from a PDF."""

    page: int
    type: str
    content: str  # The annotation popup/comment text
    highlighted_text: str  # The text that was highlighted/underlined
    color: tuple[float, ...] | None = None
    author: str = ""
    created: str = ""
    modified: str = ""
    rect: tuple[float, float, float, float] | None = None


@dataclass
class PdfPage:
    """Text content of a single PDF page."""

    page_number: int  # 1-based
    text: str = ""


@dataclass
class SearchHit:
    """A keyword search match within a PDF."""

    page_number: int  # 1-based
    snippet: str = ""
    match_count: int = 0


@dataclass
class PdfExtractionResult:
    """Full result of extracting text and/or annotations from a PDF."""

    path: str
    num_pages: int = 0
    pages: list[PdfPage] = field(default_factory=list)
    annotations: list[PdfAnnotation] = field(default_factory=list)
    error: str | None = None


# Mapping from PyMuPDF annotation type ids to human-readable names
_ANNOT_TYPE_NAMES = {
    0: "text",
    1: "link",
    2: "free_text",
    3: "line",
    4: "square",
    5: "circle",
    6: "polygon",
    7: "polyline",
    8: "highlight",
    9: "underline",
    10: "squiggly",
    11: "strikeout",
    12: "stamp",
    13: "caret",
    14: "ink",
    15: "popup",
    16: "file_attachment",
    17: "sound",
    18: "movie",
    19: "widget",
    20: "screen",
    21: "printer_mark",
    22: "trap_net",
    23: "watermark",
    24: "3d",
}

# Annotation types that carry user-created content
_CONTENT_ANNOT_TYPES = {0, 2, 8, 9, 10, 11}  # text, free_text, highlight, underline, squiggly, strikeout

# Maximum file size to process (default 50 MB)
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024


def extract_text(
    pdf_path: str | Path,
    pages: list[int] | None = None,
    max_size: int = MAX_PDF_SIZE_BYTES,
) -> PdfExtractionResult:
    """Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        pages: Optional list of 1-based page numbers to extract.
            If None, extracts all pages.
        max_size: Maximum file size in bytes. Files larger than this are skipped.

    Returns:
        PdfExtractionResult with page text content.
    """
    path = Path(pdf_path)
    if not path.exists():
        return PdfExtractionResult(path=str(path), error=f"File not found: {path}")

    if path.stat().st_size > max_size:
        return PdfExtractionResult(
            path=str(path),
            error=f"File too large ({path.stat().st_size} bytes, max {max_size})",
        )

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        return PdfExtractionResult(path=str(path), error=f"Cannot open PDF: {exc}")

    try:
        result = PdfExtractionResult(path=str(path), num_pages=len(doc))
        target_pages = set(pages) if pages else None

        for page_num in range(len(doc)):
            one_based = page_num + 1
            if target_pages and one_based not in target_pages:
                continue
            page = doc[page_num]
            text = page.get_text("text")
            result.pages.append(PdfPage(page_number=one_based, text=text))

        return result

    finally:
        doc.close()


def extract_annotations(
    pdf_path: str | Path,
    max_size: int = MAX_PDF_SIZE_BYTES,
) -> PdfExtractionResult:
    """Extract all user-created annotations from a PDF.

    Extracts highlights, sticky notes, underlines, strikethroughs,
    and free text annotations with their content and metadata.

    Args:
        pdf_path: Path to the PDF file.
        max_size: Maximum file size in bytes.

    Returns:
        PdfExtractionResult with annotation data.
    """
    path = Path(pdf_path)
    if not path.exists():
        return PdfExtractionResult(path=str(path), error=f"File not found: {path}")

    if path.stat().st_size > max_size:
        return PdfExtractionResult(
            path=str(path),
            error=f"File too large ({path.stat().st_size} bytes, max {max_size})",
        )

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        return PdfExtractionResult(path=str(path), error=f"Cannot open PDF: {exc}")

    try:
        result = PdfExtractionResult(path=str(path), num_pages=len(doc))

        for page_num in range(len(doc)):
            page = doc[page_num]
            for annot in page.annots() or []:
                annot_type_id = annot.type[0]

                if annot_type_id not in _CONTENT_ANNOT_TYPES:
                    continue

                type_name = _ANNOT_TYPE_NAMES.get(annot_type_id, f"unknown_{annot_type_id}")

                # Get the text content of the annotation popup/comment
                content = annot.info.get("content", "") or ""

                # For highlight/underline/strikeout — extract the underlying text
                highlighted_text = ""
                if annot_type_id in {8, 9, 10, 11}:
                    try:
                        quads = annot.vertices
                        if quads:
                            # Build a rect covering all quads
                            rects = []
                            for i in range(0, len(quads), 4):
                                r = pymupdf.Quad(quads[i : i + 4]).rect
                                rects.append(r)
                            for r in rects:
                                text = page.get_text("text", clip=r).strip()
                                if text:
                                    if highlighted_text:
                                        highlighted_text += " "
                                    highlighted_text += text
                    except Exception:
                        pass

                info = annot.info
                color_value = annot.colors.get("stroke") or annot.colors.get("fill")

                result.annotations.append(
                    PdfAnnotation(
                        page=page_num + 1,
                        type=type_name,
                        content=content,
                        highlighted_text=highlighted_text,
                        color=tuple(color_value) if color_value else None,
                        author=info.get("title", ""),
                        created=info.get("creationDate", ""),
                        modified=info.get("modDate", ""),
                        rect=(annot.rect.x0, annot.rect.y0, annot.rect.x1, annot.rect.y1),
                    )
                )

        return result

    finally:
        doc.close()


def search_text(
    pdf_path: str | Path,
    query: str,
    context_chars: int = 150,
    max_size: int = MAX_PDF_SIZE_BYTES,
) -> list[SearchHit]:
    """Search a PDF for a keyword or phrase and return matching pages with context.

    Args:
        pdf_path: Path to the PDF file.
        query: Search term or phrase (case-insensitive).
        context_chars: Number of characters of context around each match.
        max_size: Maximum file size in bytes.

    Returns:
        List of SearchHit objects with page numbers and surrounding context.
    """
    path = Path(pdf_path)
    if not path.exists() or path.stat().st_size > max_size:
        return []

    try:
        doc = pymupdf.open(str(path))
    except Exception:
        return []

    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        hits: list[SearchHit] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            matches = list(pattern.finditer(text))
            if not matches:
                continue

            # Build snippets around each match
            snippets = []
            for m in matches[:5]:  # cap snippets per page
                start = max(0, m.start() - context_chars)
                end = min(len(text), m.end() + context_chars)
                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                snippets.append(snippet)

            hits.append(
                SearchHit(
                    page_number=page_num + 1,
                    snippet="\n---\n".join(snippets),
                    match_count=len(matches),
                )
            )

        return hits

    finally:
        doc.close()


def annotation_to_dict(ann: PdfAnnotation) -> dict[str, Any]:
    """Convert a PdfAnnotation to a serializable dictionary."""
    return {
        "page": ann.page,
        "type": ann.type,
        "content": ann.content,
        "highlighted_text": ann.highlighted_text,
        "color": list(ann.color) if ann.color else None,
        "author": ann.author,
        "created": ann.created,
        "modified": ann.modified,
    }
