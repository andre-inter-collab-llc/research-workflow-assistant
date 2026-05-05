"""Utilities for robust project bibliography synchronization.

This module standardizes author metadata for BibTeX output, rewrites a single
idempotent generated bibliography block, and can remap citekeys in Quarto files.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

INCLUDED_BLOCK_RE = re.compile(r"(?m)^% === Included studies \(n=\d+\) ===\s*$")
INITIALS_TOKEN_RE = re.compile(r"^[A-Z](?:[A-Z]|\.)*$")
WORD_RE = re.compile(r"[A-Za-z]+")
STOPWORDS = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "for",
    "and",
    "or",
    "to",
    "on",
    "with",
    "by",
    "from",
    "at",
    "is",
    "are",
    "its",
    "can",
    "do",
    "how",
    "what",
    "using",
    "use",
    "based",
}
SURNAME_PARTICLES = {
    "al",
    "bin",
    "da",
    "de",
    "del",
    "den",
    "der",
    "di",
    "dos",
    "du",
    "ibn",
    "la",
    "le",
    "van",
    "von",
}
CORPORATE_HINTS = {
    "academy",
    "association",
    "collaboration",
    "committee",
    "consortium",
    "foundation",
    "group",
    "initiative",
    "network",
    "panel",
    "society",
    "study group",
    "task force",
    "team",
    "working group",
}


def _clean_ws(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _strip_period(token: str) -> str:
    return token.strip().strip(".")


def _normalize_initials(token: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", token)
    if not letters:
        return ""
    if letters.isupper() and len(letters) > 1:
        return " ".join(letters)
    return letters


def _is_initials_token(token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    return bool(INITIALS_TOKEN_RE.fullmatch(token))


def _is_corporate_name(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in CORPORATE_HINTS)


def _split_family_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    if not tokens:
        return ([], [])
    family = [tokens[-1]]
    idx = len(tokens) - 2
    while idx >= 0 and tokens[idx].lower() in SURNAME_PARTICLES:
        family.insert(0, tokens[idx])
        idx -= 1
    given = tokens[: idx + 1]
    return given, family


def normalize_author_name(name: str) -> tuple[str, str]:
    """Normalize one author name to a BibTeX-friendly person string.

    Returns a tuple of (normalized_name, status).
    """
    cleaned = _clean_ws(name)
    if not cleaned:
        return ("", "empty")

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return (cleaned, "verbatim")

    if _is_corporate_name(cleaned):
        wrapped = "{" + cleaned.strip("{}") + "}"
        return (wrapped, "corporate")

    if "," in cleaned:
        family, given = cleaned.split(",", 1)
        family = _clean_ws(family)
        given = _clean_ws(given)
        if not family:
            return (cleaned, "invalid")
        if given:
            return (f"{family}, {given}", "comma")
        return (family, "comma")

    tokens = cleaned.split()
    if len(tokens) == 1:
        return (tokens[0], "single")

    if not _is_initials_token(tokens[0]) and all(_is_initials_token(t) for t in tokens[1:]):
        initials = " ".join(
            _normalize_initials(t) for t in tokens[1:] if _normalize_initials(t)
        ).strip()
        if initials:
            return (f"{tokens[0]}, {initials}", "surname_initials")
        return (tokens[0], "surname_only")

    given_tokens, family_tokens = _split_family_tokens(tokens)
    family = " ".join(family_tokens)
    given = " ".join(given_tokens)
    if family and given:
        return (f"{family}, {given}", "inferred")
    return (cleaned, "unchanged")


def parse_authors_json(authors_json: str | None) -> list[str]:
    """Parse authors_json field from results table into a list of strings."""
    if not authors_json:
        return []
    try:
        parsed = json.loads(authors_json)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []

    authors: list[str] = []
    for item in parsed:
        if isinstance(item, str):
            text = _clean_ws(item)
            if text:
                authors.append(text)
            continue
        if isinstance(item, dict):
            name = _clean_ws(str(item.get("name", "")))
            if name:
                authors.append(name)
                continue
            family = _clean_ws(str(item.get("family", "") or item.get("last", "")))
            given = _clean_ws(str(item.get("given", "") or item.get("first", "")))
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
    return authors


def normalize_author_list(authors: list[str]) -> tuple[list[str], list[str]]:
    """Normalize a list of author names while preserving original order."""
    normalized: list[str] = []
    statuses: list[str] = []
    seen: set[str] = set()

    for author in authors:
        canonical, status = normalize_author_name(author)
        if not canonical:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(canonical)
        statuses.append(status)

    return (normalized, statuses)


def normalize_name_for_key(name: str) -> str:
    """Strip accents and non-alpha chars from a name for use in citekeys."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z]", "", ascii_only).lower()


def first_content_word(title: str) -> str:
    """Extract the first meaningful word from title for citekey generation."""
    words = WORD_RE.findall((title or "").lower())
    for word in words:
        if word not in STOPWORDS and len(word) > 2:
            return word
    return words[0] if words else "untitled"


def _surname_for_citekey(first_author: str) -> str:
    if not first_author:
        return "unknown"
    if "," in first_author:
        family = first_author.split(",", 1)[0].strip()
    else:
        family = first_author.split()[-1]
    family = normalize_name_for_key(family)
    return family or "unknown"


def make_citekey(first_author: str, year: str, title: str) -> str:
    """Generate a citekey such as busch2025current."""
    surname = _surname_for_citekey(first_author)
    year_part = str(year) if year else "nd"
    word = first_content_word(title)
    return f"{surname}{year_part}{word}"


def _legacy_make_citekey(first_author: str, year: str, title: str) -> str:
    """Reproduce the historical project citekey behavior.

    Legacy logic took the final whitespace-delimited token from first_author,
    even when names were formatted with commas.
    """
    surname = first_author.split()[-1] if first_author else "unknown"
    surname = normalize_name_for_key(surname) or "unknown"
    year_part = str(year) if year else "nd"
    word = first_content_word(title)
    return f"{surname}{year_part}{word}"


def escape_bibtex(text: str) -> str:
    """Escape special BibTeX characters while preserving braces semantics."""
    if not text:
        return ""
    escaped = text
    escaped = escaped.replace("&", r"\&")
    escaped = escaped.replace("%", r"\%")
    escaped = escaped.replace("#", r"\#")
    escaped = escaped.replace("_", r"\_")
    return escaped


def split_manual_and_generated_bibliography(text: str) -> tuple[str, int]:
    """Return manual bibliography prefix and generated block count."""
    matches = list(INCLUDED_BLOCK_RE.finditer(text))
    if not matches:
        return (text.rstrip() + "\n" if text else "", 0)

    manual_prefix = text[: matches[0].start()].rstrip()
    if manual_prefix:
        manual_prefix += "\n"
    return (manual_prefix, len(matches))


def _canonical_identity(row: sqlite3.Row) -> str:
    doi = str(row["doi"] or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    pmid = str(row["pmid"] or "").strip()
    if pmid:
        return f"pmid:{pmid}"
    title = re.sub(r"\s+", " ", str(row["title"] or "").strip().lower())
    year = str(row["year"] or "")
    return f"title_year:{title}|{year}"


def _local_author_fallback(conn: sqlite3.Connection, row: sqlite3.Row) -> list[str]:
    query = """
        SELECT authors_json
        FROM results
        WHERE result_id != ?
          AND authors_json IS NOT NULL
          AND authors_json != ''
          AND (
              (? != '' AND lower(doi) = lower(?))
              OR (? != '' AND pmid = ?)
          )
    """
    rows = conn.execute(
        query,
        (
            row["result_id"],
            row["doi"] or "",
            row["doi"] or "",
            row["pmid"] or "",
            row["pmid"] or "",
        ),
    ).fetchall()

    best: list[str] = []
    for candidate in rows:
        authors = parse_authors_json(candidate[0])
        if len(authors) > len(best):
            best = authors
    return best


def _crossref_authors_for_doi(client: httpx.Client, doi: str) -> list[str]:
    if not doi:
        return []
    params: dict[str, str] = {}
    email = os.environ.get("CROSSREF_EMAIL", "").strip()
    if email:
        params["mailto"] = email

    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    response = client.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("message", {})

    authors: list[str] = []
    for item in data.get("author", []):
        family = _clean_ws(str(item.get("family", "")))
        given = _clean_ws(str(item.get("given", "")))
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
    return authors


def _pubmed_authors_for_pmid(client: httpx.Client, pmid: str) -> list[str]:
    if not pmid:
        return []
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    }
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key

    response = client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params=params,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    authors: list[str] = []
    for author in root.findall(".//AuthorList/Author"):
        collective = author.find("CollectiveName")
        if collective is not None and collective.text:
            authors.append("{" + _clean_ws(collective.text) + "}")
            continue
        last = author.find("LastName")
        fore = author.find("ForeName")
        if last is not None and last.text:
            family = _clean_ws(last.text)
            given = _clean_ws(fore.text) if fore is not None and fore.text else ""
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)
    return authors


def _resolve_authors(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    client: httpx.Client | None,
    allow_network_fallback: bool,
) -> tuple[list[str], str]:
    authors = parse_authors_json(row["authors_json"])
    if authors:
        return (authors, "results_authors_json")

    local = _local_author_fallback(conn, row)
    if local:
        return (local, "local_doi_pmid_match")

    first_author = _clean_ws(str(row["first_author"] or ""))
    if first_author:
        return ([first_author], "data_charting_first_author")

    if not allow_network_fallback or client is None:
        return ([], "unresolved")

    doi = str(row["doi"] or "").strip()
    if doi:
        try:
            crossref = _crossref_authors_for_doi(client, doi)
            if crossref:
                return (crossref, "crossref")
        except Exception:
            pass

    pmid = str(row["pmid"] or "").strip()
    if pmid:
        try:
            pubmed = _pubmed_authors_for_pmid(client, pmid)
            if pubmed:
                return (pubmed, "pubmed")
        except Exception:
            pass

    return ([], "unresolved")


def _unique_citekeys(
    rows: list[sqlite3.Row],
    first_authors: dict[int, str],
    existing_manual_keys: set[str],
) -> dict[int, str]:
    base_keys: dict[int, str] = {}
    base_counts: Counter[str] = Counter()

    for row in rows:
        result_id = int(row["result_id"])
        base = make_citekey(
            first_authors[result_id],
            str(row["year"] or ""),
            str(row["title"] or ""),
        )
        base_keys[result_id] = base
        base_counts[base] += 1

    per_base_index: Counter[str] = Counter()
    used = set(existing_manual_keys)
    final_keys: dict[int, str] = {}

    for row in rows:
        result_id = int(row["result_id"])
        base = base_keys[result_id]
        per_base_index[base] += 1

        if base_counts[base] == 1:
            candidate = base
        else:
            idx = per_base_index[base]
            if idx <= 26:
                candidate = f"{base}{chr(ord('a') + idx - 1)}"
            else:
                candidate = f"{base}{idx}"

        if candidate in used:
            suffix = 1
            while True:
                if candidate in existing_manual_keys:
                    candidate = f"{base}_inc{suffix if suffix > 1 else ''}"
                else:
                    candidate = f"{base}_{suffix}"
                if candidate not in used:
                    break
                suffix += 1

        used.add(candidate)
        final_keys[result_id] = candidate

    return final_keys


def _legacy_first_author(row: sqlite3.Row) -> str:
    first_author = _clean_ws(str(row["first_author"] or ""))
    if first_author:
        return first_author

    authors = parse_authors_json(row["authors_json"])
    if authors:
        return authors[0]

    return ""


def _legacy_citekeys(rows: list[sqlite3.Row]) -> dict[int, str]:
    """Rebuild citekeys using the legacy project script logic.

    This preserves compatibility when existing QMD files still reference
    older key forms generated from unnormalized first-author values.
    """
    base_keys: dict[int, str] = {}
    base_counts: Counter[str] = Counter()

    for row in rows:
        result_id = int(row["result_id"])
        base = _legacy_make_citekey(
            _legacy_first_author(row),
            str(row["year"] or ""),
            str(row["title"] or ""),
        )
        base_keys[result_id] = base
        base_counts[base] += 1

    per_base_index: Counter[str] = Counter()
    legacy_keys: dict[int, str] = {}

    for row in rows:
        result_id = int(row["result_id"])
        base = base_keys[result_id]
        per_base_index[base] += 1

        if base_counts[base] == 1:
            legacy_keys[result_id] = base
            continue

        idx = per_base_index[base]
        if idx <= 26:
            legacy_keys[result_id] = f"{base}{chr(ord('a') + idx - 1)}"
        else:
            legacy_keys[result_id] = f"{base}{idx}"

    return legacy_keys


def _generate_bibtex_entry(citekey: str, row: sqlite3.Row, authors: list[str]) -> str:
    lines = [f"@article{{{citekey},"]

    if authors:
        author_text = " and ".join(escape_bibtex(a) for a in authors)
        lines.append(f"  author = {{{author_text}}},")
    else:
        lines.append("  author = {{Unknown Author}},")

    title = escape_bibtex(str(row["title"] or ""))
    if title:
        lines.append(f"  title = {{{{{title}}}}},")

    journal = escape_bibtex(str(row["journal"] or ""))
    if journal:
        lines.append(f"  journal = {{{journal}}},")

    year = str(row["year"] or "")
    if year:
        lines.append(f"  year = {{{year}}},")

    volume = str(row["volume"] or "")
    if volume:
        lines.append(f"  volume = {{{volume}}},")

    issue = str(row["issue"] or "")
    if issue:
        lines.append(f"  number = {{{issue}}},")

    pages = str(row["pages"] or "")
    if pages:
        lines.append(f"  pages = {{{pages}}},")

    doi = str(row["doi"] or "").replace("https://doi.org/", "")
    if doi:
        lines.append(f"  doi = {{{doi}}},")

    pmid = str(row["pmid"] or "")
    if pmid:
        lines.append(f"  pmid = {{{pmid}}},")

    lines.append("}")
    return "\n".join(lines)


def rewrite_qmd_citekeys(
    project_path: Path,
    old_to_new: dict[str, str],
    apply: bool,
) -> list[dict[str, Any]]:
    """Rewrite citekeys in all QMD files under project_path."""
    if not old_to_new:
        return []

    keys = sorted(old_to_new, key=len, reverse=True)
    escaped = "|".join(re.escape(key) for key in keys)
    pattern = re.compile(r"@(" + escaped + r")(?=[^A-Za-z0-9_:-]|$)")

    updates: list[dict[str, Any]] = []
    for qmd_path in sorted(project_path.rglob("*.qmd")):
        text = qmd_path.read_text(encoding="utf-8")

        def _repl(match: re.Match[str]) -> str:
            old_key = match.group(1)
            return "@" + old_to_new[old_key]

        updated_text, replacements = pattern.subn(_repl, text)
        if replacements:
            updates.append({"file": str(qmd_path), "replacements": replacements})
            if apply:
                qmd_path.write_text(updated_text, encoding="utf-8")

    return updates


def _build_subgroups(
    rows: list[sqlite3.Row],
    citekeys: dict[int, str],
) -> dict[str, dict[str, list[str]]]:
    subgroups: dict[str, dict[str, list[str]]] = {
        "tasks": {},
        "families": {},
        "metrics": {},
        "prompt": {},
        "access": {},
        "comparison": {},
        "domains": {},
    }

    for row in rows:
        result_id = int(row["result_id"])
        citekey = citekeys[result_id]

        def _add_values(group_name: str, value: str, skip_not_identified: bool = True) -> None:
            for part in value.split("; "):
                cleaned = part.strip()
                if not cleaned:
                    continue
                if skip_not_identified and cleaned == "Not identified":
                    continue
                subgroups[group_name].setdefault(cleaned, []).append(citekey)

        _add_values("tasks", str(row["sr_task"] or ""))
        _add_values("families", str(row["llm_families"] or ""))
        _add_values("metrics", str(row["metrics"] or ""))
        _add_values("prompt", str(row["prompt_engineering"] or ""), skip_not_identified=False)
        _add_values("access", str(row["access_method"] or ""), skip_not_identified=False)
        _add_values("comparison", str(row["comparison_method"] or ""), skip_not_identified=False)
        _add_values("domains", str(row["health_domain"] or ""))

    return subgroups


def sync_project_bibliography(
    project_path: str | Path,
    *,
    apply: bool = True,
    update_qmd: bool = True,
    allow_network_fallback: bool = True,
    audit_output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Synchronize references.bib and citation map from project database.

    This function expects data_charting and results tables with the usual
    RWA project schema.
    """
    project_dir = Path(project_path)
    db_path = project_dir / "data" / "search_results.db"
    bib_path = project_dir / "references.bib"
    map_path = project_dir / "data" / "citation_map.json"

    if audit_output_path is None:
        audit_output = project_dir / "data" / "bibliography_sync_audit.json"
    else:
        audit_output = Path(audit_output_path)

    if not db_path.exists():
        raise FileNotFoundError(f"search_results.db not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT
                dc.result_id,
                dc.first_author,
                dc.year,
                dc.doi,
                dc.title,
                dc.journal,
                dc.sr_task,
                dc.llm_families,
                dc.metrics,
                dc.prompt_engineering,
                dc.access_method,
                dc.comparison_method,
                dc.health_domain,
                dc.study_design,
                dc.llm_models,
                r.authors_json,
                r.volume,
                r.issue,
                r.pages,
                r.pmid
            FROM data_charting dc
            LEFT JOIN results r ON dc.result_id = r.result_id
            ORDER BY dc.first_author, dc.year, dc.result_id
            """
        ).fetchall()

        existing_bib = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
        manual_bib, generated_block_count = split_manual_and_generated_bibliography(existing_bib)
        existing_manual_keys = set(re.findall(r"@\w+\{([^,\s]+),", manual_bib))

        previous_map: dict[str, str] = {}
        if map_path.exists():
            try:
                parsed = json.loads(map_path.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    id_to_key = parsed.get("id_to_citekey", {})
                    if isinstance(id_to_key, dict):
                        previous_map = {str(k): str(v) for k, v in id_to_key.items()}
            except (json.JSONDecodeError, OSError, TypeError):
                previous_map = {}

        resolved_authors: dict[int, list[str]] = {}
        first_authors: dict[int, str] = {}
        resolution_source: dict[int, str] = {}
        normalized_records = 0
        unresolved_records: list[dict[str, Any]] = []

        fallback_network_count = 0
        fallback_local_count = 0

        client: httpx.Client | None = None
        if allow_network_fallback:
            client = httpx.Client(timeout=20.0)

        for row in rows:
            result_id = int(row["result_id"])
            authors, source = _resolve_authors(conn, row, client, allow_network_fallback)
            if source == "crossref" or source == "pubmed":
                fallback_network_count += 1
            if source == "local_doi_pmid_match":
                fallback_local_count += 1

            normalized, statuses = normalize_author_list(authors)
            if any(status in {"surname_initials", "inferred"} for status in statuses):
                normalized_records += 1

            if not normalized:
                unresolved_records.append(
                    {
                        "result_id": result_id,
                        "title": row["title"] or "",
                        "doi": row["doi"] or "",
                        "pmid": row["pmid"] or "",
                        "source": source,
                    }
                )
                normalized = ["{Unknown Author}"]

            resolved_authors[result_id] = normalized
            resolution_source[result_id] = source
            first_authors[result_id] = normalized[0]

        if client is not None:
            client.close()

        citekeys = _unique_citekeys(rows, first_authors, existing_manual_keys)

        bib_entries: list[str] = []
        for row in rows:
            result_id = int(row["result_id"])
            bib_entries.append(
                _generate_bibtex_entry(
                    citekeys[result_id],
                    row,
                    resolved_authors[result_id],
                )
            )

        generated_header = f"% === Included studies (n={len(rows)}) ==="
        generated_block = generated_header + "\n\n" + "\n\n".join(bib_entries) + "\n"

        if manual_bib.strip():
            new_bib = manual_bib.rstrip() + "\n\n" + generated_block
        else:
            new_bib = generated_block

        id_to_citekey = {
            str(int(row["result_id"])): citekeys[int(row["result_id"])] for row in rows
        }
        subgroups = _build_subgroups(rows, citekeys)

        legacy_citekeys = _legacy_citekeys(rows)

        old_to_new: dict[str, str] = {}
        for row in rows:
            result_id_int = int(row["result_id"])
            result_id = str(result_id_int)
            new_key = citekeys[result_id_int]

            legacy_key = legacy_citekeys[result_id_int]
            if legacy_key != new_key:
                old_to_new.setdefault(legacy_key, new_key)
                old_to_new.setdefault(f"{legacy_key}_inc", new_key)

            old_key = previous_map.get(result_id)
            if old_key and old_key != new_key:
                old_to_new.setdefault(old_key, new_key)

        qmd_updates: list[dict[str, Any]] = []
        if update_qmd and old_to_new:
            qmd_updates = rewrite_qmd_citekeys(project_dir, old_to_new, apply=apply)

        citation_map = {
            "id_to_citekey": id_to_citekey,
            "subgroups": subgroups,
            "old_to_new": old_to_new,
        }

        audit = {
            "project_path": str(project_dir),
            "included_count": len(rows),
            "generated_blocks_detected": generated_block_count,
            "normalized_records": normalized_records,
            "local_fallback_count": fallback_local_count,
            "network_fallback_count": fallback_network_count,
            "unresolved_count": len(unresolved_records),
            "unresolved_records": unresolved_records,
            "qmd_updates": qmd_updates,
            "qmd_replacements_total": sum(item["replacements"] for item in qmd_updates),
            "old_to_new_count": len(old_to_new),
        }

        if apply:
            bib_path.write_text(new_bib, encoding="utf-8")
            map_path.write_text(json.dumps(citation_map, indent=2), encoding="utf-8")

        audit_output.parent.mkdir(parents=True, exist_ok=True)
        audit_output.write_text(json.dumps(audit, indent=2), encoding="utf-8")

        return {
            "bib_path": str(bib_path),
            "map_path": str(map_path),
            "audit_path": str(audit_output),
            "included_count": len(rows),
            "old_to_new_count": len(old_to_new),
            "qmd_updates": qmd_updates,
            "unresolved_count": len(unresolved_records),
            "generated_blocks_detected": generated_block_count,
            "apply": apply,
            "resolution_source": {str(k): v for k, v in resolution_source.items()},
        }
    finally:
        conn.close()
