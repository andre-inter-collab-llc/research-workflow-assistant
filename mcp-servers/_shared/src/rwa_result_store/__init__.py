"""Shared SQLite storage for MCP search results.

Provides per-project result persistence so searches can be queried
later from R (RSQLite/DBI) or Python (sqlite3 stdlib).

Database location: {project_path}/data/search_results.db
"""

import csv
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS searches (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    total_count INTEGER,
    parameters_json TEXT
);

CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER NOT NULL REFERENCES searches(search_id),
    source TEXT NOT NULL,
    doi TEXT,
    pmid TEXT,
    title TEXT,
    authors_json TEXT,
    journal TEXT,
    year TEXT,
    volume TEXT,
    issue TEXT,
    pages TEXT,
    abstract TEXT,
    extra_json TEXT,
    retrieved_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_doi
    ON results(doi) WHERE doi IS NOT NULL AND doi != '';
CREATE INDEX IF NOT EXISTS idx_results_pmid
    ON results(pmid) WHERE pmid IS NOT NULL AND pmid != '';
CREATE INDEX IF NOT EXISTS idx_results_search_id
    ON results(search_id);
"""

_DEDUP_VIEW = """\
CREATE VIEW IF NOT EXISTS deduplicated_results AS
SELECT
    MIN(result_id) AS result_id,
    doi,
    MAX(pmid) AS pmid,
    MAX(title) AS title,
    MAX(authors_json) AS authors_json,
    MAX(journal) AS journal,
    MAX(year) AS year,
    GROUP_CONCAT(DISTINCT source) AS sources,
    COUNT(*) AS occurrence_count,
    MIN(retrieved_at) AS first_retrieved
FROM results
GROUP BY
    CASE
        WHEN doi IS NOT NULL AND doi != '' THEN 'doi:' || doi
        WHEN pmid IS NOT NULL AND pmid != '' THEN 'pmid:' || pmid
        ELSE 'id:' || result_id
    END;
"""

# Fields extracted into dedicated columns (everything else goes to extra_json)
_CORE_KEYS = frozenset({
    "doi", "pmid", "title", "authors", "journal", "year",
    "volume", "issue", "pages", "page", "abstract",
    "source", "fulljournalname", "venue", "publication_year", "pubdate",
})


def _db_path(project_path: str) -> Path:
    """Return the SQLite database path for a project."""
    return Path(project_path) / "data" / "search_results.db"


def init_db(project_path: str) -> sqlite3.Connection:
    """Initialize the search results database for a project.

    Creates the data/ directory and search_results.db if they don't exist.
    Returns an open connection.
    """
    db = _db_path(project_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.executescript(_SCHEMA)
    # Create dedup view (separate because CREATE VIEW IF NOT EXISTS
    # doesn't play well inside executescript with other statements on some builds)
    try:
        conn.executescript(_DEDUP_VIEW)
    except sqlite3.OperationalError:
        pass  # View already exists
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _normalize_authors(authors: Any) -> str:
    """Normalize authors from various formats to a JSON array of strings."""
    if isinstance(authors, str):
        # Europe PMC returns comma-separated string
        return json.dumps([a.strip() for a in authors.split(",") if a.strip()])
    if isinstance(authors, list):
        if authors and isinstance(authors[0], dict):
            # Semantic Scholar returns [{name, author_id}, ...]
            return json.dumps([a.get("name", str(a)) for a in authors])
        return json.dumps(authors)
    return json.dumps([])


def _extract_year(result: dict[str, Any]) -> str:
    """Extract a 4-digit year from various result formats."""
    for key in ("year", "publication_year", "pubdate"):
        val = result.get(key)
        if val is not None:
            s = str(val).strip()
            if len(s) >= 4 and s[:4].isdigit():
                return s[:4]
            if s:
                return s
    return ""


def store_results(
    project_path: str,
    source: str,
    query: str,
    results: list[dict[str, Any]],
    total_count: int | None = None,
    parameters: dict[str, Any] | None = None,
) -> int:
    """Store search results in the project database.

    Args:
        project_path: Absolute path to the project directory.
        source: Search source identifier (e.g., 'pubmed', 'openalex').
        query: The search query that was executed.
        results: List of result dicts from the search server's format function.
        total_count: Total results available (not just returned).
        parameters: Search parameters for reproducibility.

    Returns:
        The search_id of the stored search.
    """
    conn = init_db(project_path)
    try:
        now = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute(
            "INSERT INTO searches (source, query, timestamp, total_count, parameters_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (source, query, now, total_count,
             json.dumps(parameters) if parameters else None),
        )
        search_id = cursor.lastrowid

        for r in results:
            authors_json = _normalize_authors(r.get("authors", []))
            journal = (r.get("journal", "")
                       or r.get("fulljournalname", "")
                       or r.get("venue", "")
                       or "")
            year = _extract_year(r)
            pages = r.get("pages", "") or r.get("page", "") or ""
            extra = {k: v for k, v in r.items() if k not in _CORE_KEYS and v}

            conn.execute(
                "INSERT INTO results "
                "(search_id, source, doi, pmid, title, authors_json, journal, "
                "year, volume, issue, pages, abstract, extra_json, retrieved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    search_id,
                    source,
                    r.get("doi", "") or "",
                    r.get("pmid", "") or "",
                    r.get("title", "") or "",
                    authors_json,
                    journal,
                    year,
                    r.get("volume", "") or "",
                    r.get("issue", "") or "",
                    pages,
                    r.get("abstract", "") or "",
                    json.dumps(extra) if extra else None,
                    now,
                ),
            )

        conn.commit()
        return search_id
    finally:
        conn.close()


def get_results(
    project_path: str,
    source: str | None = None,
    query: str | None = None,
    deduplicated: bool = False,
) -> list[dict[str, Any]]:
    """Query stored results from the project database.

    Args:
        project_path: Absolute path to the project directory.
        source: Optional filter by source (e.g., 'pubmed').
        query: Optional filter by query substring.
        deduplicated: If True, return deduplicated results across sources.

    Returns:
        List of result dicts.
    """
    db = _db_path(project_path)
    if not db.exists():
        return []

    conn = init_db(project_path)
    conn.row_factory = sqlite3.Row
    try:
        table = "deduplicated_results" if deduplicated else "results"
        where_clauses: list[str] = []
        params: list[str] = []

        if source and not deduplicated:
            where_clauses.append("source = ?")
            params.append(source)
        if query and not deduplicated:
            where_clauses.append(
                "search_id IN (SELECT search_id FROM searches WHERE query LIKE ?)"
            )
            params.append(f"%{query}%")

        sql = f"SELECT * FROM {table}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_searches(project_path: str) -> list[dict[str, Any]]:
    """List all recorded searches for a project."""
    db = _db_path(project_path)
    if not db.exists():
        return []

    conn = init_db(project_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT s.*, COUNT(r.result_id) AS result_count "
            "FROM searches s LEFT JOIN results r ON s.search_id = r.search_id "
            "GROUP BY s.search_id ORDER BY s.timestamp DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def export_results_csv(
    project_path: str,
    output_path: str | None = None,
    deduplicated: bool = False,
) -> str:
    """Export stored results to CSV. Returns the output file path."""
    results = get_results(project_path, deduplicated=deduplicated)
    if not results:
        return ""

    if output_path is None:
        suffix = "_deduplicated" if deduplicated else ""
        output_path = str(Path(project_path) / "data" / f"search_results{suffix}.csv")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(results[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    return output_path


def register_result_store_tools(mcp_instance: Any) -> None:
    """Register search result query/export tools on an MCP server instance.

    Call this at module level in each search server to add
    get_stored_results and export_stored_results tools.
    """

    @mcp_instance.tool()
    async def get_stored_results(
        project_path: str,
        source: str | None = None,
        deduplicated: bool = False,
    ) -> dict[str, Any]:
        """Query previously stored search results from the project database.

        Args:
            project_path: Absolute path to the project directory.
            source: Optional filter by source (e.g., 'pubmed', 'openalex').
            deduplicated: If True, return deduplicated results across all sources.

        Returns:
            Dictionary with total counts, result list, and search history.
        """
        results = get_results(project_path, source=source, deduplicated=deduplicated)
        searches = get_searches(project_path)
        return {
            "total_results": len(results),
            "total_searches": len(searches),
            "results": results,
            "searches": searches,
        }

    @mcp_instance.tool()
    async def export_stored_results(
        project_path: str,
        output_path: str | None = None,
        deduplicated: bool = False,
    ) -> dict[str, str]:
        """Export stored search results to a CSV file.

        Args:
            project_path: Absolute path to the project directory.
            output_path: Optional custom output file path. Defaults to
                {project_path}/data/search_results.csv.
            deduplicated: If True, export deduplicated results.

        Returns:
            Dictionary with export status and file path.
        """
        path = export_results_csv(project_path, output_path, deduplicated)
        if path:
            return {"status": "exported", "file": path}
        return {"status": "no_results", "file": ""}
