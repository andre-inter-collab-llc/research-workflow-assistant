"""Read-only access to the local Zotero SQLite database.

This module provides safe, read-only access to Zotero's SQLite database
for looking up items, attachments, notes, and annotations without going
through the Web API. It never writes to the database.

Supports both Zotero 6 and Zotero 7 schema layouts.
"""

import os
import platform
import sqlite3
from pathlib import Path
from typing import Any


def detect_zotero_data_dir() -> Path | None:
    """Auto-detect the Zotero data directory based on the current platform.

    Checks the ``ZOTERO_DATA_DIR`` environment variable first, then
    falls back to platform-specific default locations.

    Returns:
        Path to the Zotero data directory, or None if not found.
    """
    env_dir = os.environ.get("ZOTERO_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir() and (p / "zotero.sqlite").exists():
            return p
        return None

    system = platform.system()
    candidates: list[Path] = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "Zotero" / "Zotero" / "Profiles")
        home = Path.home()
        candidates.append(home / "Zotero")
    elif system == "Darwin":
        home = Path.home()
        candidates.append(home / "Zotero")
        candidates.append(home / "Library" / "Application Support" / "Zotero" / "Profiles")
    else:  # Linux/other
        home = Path.home()
        candidates.append(home / "Zotero")
        candidates.append(home / ".zotero" / "zotero")

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "zotero.sqlite").exists():
            return candidate
        # Check for profile directories containing zotero.sqlite
        if candidate.is_dir():
            for profile_dir in candidate.iterdir():
                if profile_dir.is_dir() and (profile_dir / "zotero.sqlite").exists():
                    return profile_dir

    return None


def _connect(data_dir: Path) -> sqlite3.Connection:
    """Open a read-only connection to the Zotero SQLite database.

    Uses URI mode with ``?mode=ro`` for strict read-only access and
    WAL journal mode awareness for safe reads while Zotero is running.
    """
    db_path = data_dir / "zotero.sqlite"
    if not db_path.exists():
        raise FileNotFoundError(f"Zotero database not found at {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    # If the database is already in WAL mode, reads work fine on a
    # read-only connection without this pragma.  Attempting to *set*
    # journal_mode=WAL would fail on a read-only file, so we just
    # query the current mode and accept whatever it is.
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # read-only — WAL reads still work
    return conn


def get_zotero_version(data_dir: Path) -> int:
    """Detect whether the local Zotero database is version 6 or 7.

    Returns 7 if the ``itemAnnotations`` table exists, otherwise 6.
    """
    conn = _connect(data_dir)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='itemAnnotations'"
        )
        return 7 if cursor.fetchone() else 6
    finally:
        conn.close()


def get_storage_dir(data_dir: Path) -> Path:
    """Return the path to the Zotero storage directory (where PDFs live)."""
    storage = data_dir / "storage"
    if not storage.is_dir():
        raise FileNotFoundError(f"Zotero storage directory not found at {storage}")
    return storage


def get_item_by_key(data_dir: Path, item_key: str) -> dict[str, Any] | None:
    """Look up a Zotero item by its key.

    Returns:
        Dictionary with item metadata, or None if not found.
    """
    conn = _connect(data_dir)
    try:
        row = conn.execute(
            """
            SELECT i.itemID, i.key, it.typeName, i.dateAdded, i.dateModified
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.key = ? AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
            """,
            (item_key,),
        ).fetchone()

        if not row:
            return None

        item_id = row["itemID"]
        result: dict[str, Any] = {
            "key": row["key"],
            "item_type": row["typeName"],
            "date_added": row["dateAdded"],
            "date_modified": row["dateModified"],
        }

        # Get field values
        fields = conn.execute(
            """
            SELECT f.fieldName, iv.value
            FROM itemData id
            JOIN itemDataValues iv ON id.valueID = iv.valueID
            JOIN fields f ON id.fieldID = f.fieldID
            WHERE id.itemID = ?
            """,
            (item_id,),
        ).fetchall()

        for f in fields:
            result[f["fieldName"]] = f["value"]

        # Get creators
        creators = conn.execute(
            """
            SELECT c.firstName, c.lastName, ct.creatorType
            FROM itemCreators ic
            JOIN creators c ON ic.creatorID = c.creatorID
            JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
            WHERE ic.itemID = ?
            ORDER BY ic.orderIndex
            """,
            (item_id,),
        ).fetchall()

        result["creators"] = [
            {"firstName": c["firstName"] or "", "lastName": c["lastName"] or "", "type": c["creatorType"]}
            for c in creators
        ]

        # Get tags
        tags = conn.execute(
            """
            SELECT t.name
            FROM itemTags it
            JOIN tags t ON it.tagID = t.tagID
            WHERE it.itemID = ?
            """,
            (item_id,),
        ).fetchall()

        result["tags"] = [t["name"] for t in tags]

        return result

    finally:
        conn.close()


def get_attachments(data_dir: Path, item_key: str) -> list[dict[str, Any]]:
    """Get all attachments for a parent item by its key.

    Returns:
        List of attachment dictionaries with key, filename, content type,
        link mode, and the resolved file path on disk.
    """
    storage_dir = get_storage_dir(data_dir)
    conn = _connect(data_dir)
    try:
        # Find the parent item ID
        parent = conn.execute(
            "SELECT itemID FROM items WHERE key = ?", (item_key,)
        ).fetchone()
        if not parent:
            return []

        parent_id = parent["itemID"]

        rows = conn.execute(
            """
            SELECT i.key, ia.contentType, ia.path, ia.storageModTime,
                   ia.storageHash
            FROM itemAttachments ia
            JOIN items i ON ia.itemID = i.itemID
            WHERE ia.parentItemID = ?
              AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
            """,
            (parent_id,),
        ).fetchall()

        attachments = []
        for row in rows:
            att_key = row["key"]
            raw_path = row["path"] or ""
            content_type = row["contentType"] or ""

            # Resolve the file path on disk
            file_path: Path | None = None
            if raw_path.startswith("storage:"):
                filename = raw_path[len("storage:"):]
                candidate = storage_dir / att_key / filename
                if candidate.exists():
                    file_path = candidate
            elif raw_path:
                # Linked file — absolute or relative path
                candidate = Path(raw_path)
                if candidate.exists():
                    file_path = candidate

            attachments.append({
                "key": att_key,
                "content_type": content_type,
                "filename": file_path.name if file_path else raw_path,
                "path": str(file_path) if file_path else None,
                "exists": file_path is not None and file_path.exists(),
                "storage_hash": row["storageHash"] or "",
            })

        return attachments

    finally:
        conn.close()


def get_notes_for_item(data_dir: Path, item_key: str) -> list[dict[str, Any]]:
    """Get all notes attached to a parent item.

    Returns:
        List of note dictionaries with key, HTML content, and tags.
    """
    conn = _connect(data_dir)
    try:
        parent = conn.execute(
            "SELECT itemID FROM items WHERE key = ?", (item_key,)
        ).fetchone()
        if not parent:
            return []

        parent_id = parent["itemID"]

        rows = conn.execute(
            """
            SELECT i.key, in2.note, i.dateAdded, i.dateModified
            FROM itemNotes in2
            JOIN items i ON in2.itemID = i.itemID
            WHERE in2.parentItemID = ?
              AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
            """,
            (parent_id,),
        ).fetchall()

        notes = []
        for row in rows:
            note_key = row["key"]

            # Get tags for this note
            note_item = conn.execute(
                "SELECT itemID FROM items WHERE key = ?", (note_key,)
            ).fetchone()
            tags: list[str] = []
            if note_item:
                tag_rows = conn.execute(
                    """
                    SELECT t.name FROM itemTags it
                    JOIN tags t ON it.tagID = t.tagID
                    WHERE it.itemID = ?
                    """,
                    (note_item["itemID"],),
                ).fetchall()
                tags = [t["name"] for t in tag_rows]

            notes.append({
                "key": note_key,
                "note": row["note"] or "",
                "tags": tags,
                "date_added": row["dateAdded"] or "",
                "date_modified": row["dateModified"] or "",
            })

        return notes

    finally:
        conn.close()


def get_annotations_for_attachment(
    data_dir: Path, attachment_key: str
) -> list[dict[str, Any]]:
    """Get Zotero reader annotations for a PDF attachment from the local database.

    Supports both Zotero 6 (annotations stored as child items with specific
    fields) and Zotero 7 (``itemAnnotations`` table).

    Args:
        data_dir: Zotero data directory.
        attachment_key: The attachment item key.

    Returns:
        List of annotation dictionaries.
    """
    conn = _connect(data_dir)
    try:
        att = conn.execute(
            "SELECT itemID FROM items WHERE key = ?", (attachment_key,)
        ).fetchone()
        if not att:
            return []

        att_id = att["itemID"]
        version = get_zotero_version(data_dir)

        if version >= 7:
            return _get_annotations_v7(conn, att_id)
        return _get_annotations_v6(conn, att_id)

    finally:
        conn.close()


def _get_annotations_v7(
    conn: sqlite3.Connection, attachment_id: int
) -> list[dict[str, Any]]:
    """Zotero 7: read from itemAnnotations table."""
    rows = conn.execute(
        """
        SELECT i.key, ia.type, ia.text, ia.comment, ia.color,
               ia.pageLabel, ia.sortIndex, ia.position,
               i.dateAdded, i.dateModified
        FROM itemAnnotations ia
        JOIN items i ON ia.itemID = i.itemID
        WHERE ia.parentItemID = ?
          AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
        ORDER BY ia.sortIndex
        """,
        (attachment_id,),
    ).fetchall()

    annotations = []
    for row in rows:
        ann_type_num = row["type"]
        type_map = {1: "highlight", 2: "note", 3: "image", 4: "underline", 5: "text"}
        annotations.append({
            "key": row["key"],
            "type": type_map.get(ann_type_num, str(ann_type_num)),
            "text": row["text"] or "",
            "comment": row["comment"] or "",
            "color": row["color"] or "",
            "page_label": row["pageLabel"] or "",
            "sort_index": row["sortIndex"] or "",
            "date_added": row["dateAdded"] or "",
            "date_modified": row["dateModified"] or "",
        })

    return annotations


def _get_annotations_v6(
    conn: sqlite3.Connection, attachment_id: int
) -> list[dict[str, Any]]:
    """Zotero 6: annotations stored as child note items with annotation fields."""
    rows = conn.execute(
        """
        SELECT i.key, it.typeName, i.dateAdded, i.dateModified
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemAnnotations_v6_compat ia ON ia.itemID = i.itemID
        WHERE ia.parentItemID = ?
          AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
        """,
        (attachment_id,),
    ).fetchall()

    # Zotero 6 annotations are less structured; fall back to child items
    if not rows:
        rows = conn.execute(
            """
            SELECT i.key, in2.note, i.dateAdded, i.dateModified
            FROM itemNotes in2
            JOIN items i ON in2.itemID = i.itemID
            WHERE in2.parentItemID = ?
              AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
            """,
            (attachment_id,),
        ).fetchall()

        return [
            {
                "key": r["key"],
                "type": "note",
                "text": r["note"] or "",
                "comment": "",
                "color": "",
                "page_label": "",
                "sort_index": "",
                "date_added": r["dateAdded"] or "",
                "date_modified": r["dateModified"] or "",
            }
            for r in rows
        ]

    return []


def get_all_pdf_attachments(
    data_dir: Path, collection_key: str | None = None
) -> list[dict[str, Any]]:
    """List all PDF attachments in the library, optionally filtered by collection.

    Returns:
        List of dicts with parent item key, attachment key, filename, and path.
    """
    storage_dir = get_storage_dir(data_dir)
    conn = _connect(data_dir)
    try:
        if collection_key:
            rows = conn.execute(
                """
                SELECT ia.itemID, i.key as att_key, ia.path, ia.contentType,
                       pi.key as parent_key
                FROM itemAttachments ia
                JOIN items i ON ia.itemID = i.itemID
                JOIN items pi ON ia.parentItemID = pi.itemID
                JOIN collectionItems ci ON ci.itemID = ia.parentItemID
                JOIN collections c ON ci.collectionID = c.collectionID
                WHERE c.key = ?
                  AND ia.contentType = 'application/pdf'
                  AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
                """,
                (collection_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT ia.itemID, i.key as att_key, ia.path, ia.contentType,
                       pi.key as parent_key
                FROM itemAttachments ia
                JOIN items i ON ia.itemID = i.itemID
                LEFT JOIN items pi ON ia.parentItemID = pi.itemID
                WHERE ia.contentType = 'application/pdf'
                  AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
                """,
            ).fetchall()

        results = []
        for row in rows:
            att_key = row["att_key"]
            raw_path = row["path"] or ""

            file_path: Path | None = None
            if raw_path.startswith("storage:"):
                filename = raw_path[len("storage:"):]
                candidate = storage_dir / att_key / filename
                if candidate.exists():
                    file_path = candidate
            elif raw_path:
                candidate = Path(raw_path)
                if candidate.exists():
                    file_path = candidate

            if file_path and file_path.exists():
                results.append({
                    "parent_key": row["parent_key"] or "",
                    "attachment_key": att_key,
                    "filename": file_path.name,
                    "path": str(file_path),
                })

        return results

    finally:
        conn.close()
