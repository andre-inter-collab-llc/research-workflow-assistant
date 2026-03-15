"""Test script for the new features: script-first search, BibTeX/RIS/CSL-JSON export, batch Zotero import."""

import sqlite3
import os
import sys

PROJECT = r"C:\Users\andre\Documents\research-workflow-assistant\sample_projects\chw-maternal-mental-health"
DB_PATH = os.path.join(PROJECT, "data", "search_results.db")


def check_database():
    """Check the SQLite database for stored search results."""
    print("=" * 60)
    print("1. DATABASE CHECK")
    print("=" * 60)
    print(f"DB exists: {os.path.exists(DB_PATH)}")
    if not os.path.exists(DB_PATH):
        print("ERROR: No database found. Run searches first.")
        return False

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables: {tables}")

    cur.execute("SELECT search_id, source, query, total_count, timestamp FROM searches ORDER BY timestamp DESC")
    searches = cur.fetchall()
    for row in searches:
        print(f"  Search #{row[0]}: source={row[1]}, total={row[3]}, date={row[4]}")
        print(f"    query: {row[2][:80]}...")

    cur.execute("SELECT COUNT(*) FROM results")
    total = cur.fetchone()[0]
    print(f"Total results stored: {total}")

    cur.execute("SELECT search_id, COUNT(*) FROM results GROUP BY search_id")
    for row in cur.fetchall():
        print(f"  Search #{row[0]}: {row[1]} results")

    # Check for DOIs
    cur.execute("SELECT COUNT(*) FROM results WHERE doi IS NOT NULL AND doi != ''")
    doi_count = cur.fetchone()[0]
    print(f"Results with DOIs: {doi_count}")

    conn.close()
    return total > 0


def test_script_generation():
    """Test generating standalone search scripts."""
    print("\n" + "=" * 60)
    print("2. SCRIPT-FIRST SEARCH (generate_and_run_script)")
    print("=" * 60)

    from rwa_result_store import generate_and_run_script

    query = "community health worker perinatal depression LMIC"

    # Test PubMed scripted search
    print("\n--- PubMed scripted search ---")
    result = generate_and_run_script(
        project_path=PROJECT,
        source="pubmed",
        query=query,
        parameters={"max_results": 5},
    )
    if result:
        results, total, search_id, script_path = result
        print(f"  SUCCESS: {len(results)} results, total={total}, search_id={search_id}")
        print(f"  Script: {script_path}")
        print(f"  First result: {results[0].get('title', 'N/A')[:70]}...")
    else:
        print("  Script execution returned None (may have failed, checking fallback)")

    # Test OpenAlex scripted search
    print("\n--- OpenAlex scripted search ---")
    result = generate_and_run_script(
        project_path=PROJECT,
        source="openalex",
        query=query,
        parameters={"per_page": 5},
    )
    if result:
        results, total, search_id, script_path = result
        print(f"  SUCCESS: {len(results)} results, total={total}, search_id={search_id}")
        print(f"  Script: {script_path}")
    else:
        print("  Script execution returned None")

    # Test Semantic Scholar scripted search
    print("\n--- Semantic Scholar scripted search ---")
    result = generate_and_run_script(
        project_path=PROJECT,
        source="semantic_scholar",
        query=query,
        parameters={"limit": 5},
    )
    if result:
        results, total, search_id, script_path = result
        print(f"  SUCCESS: {len(results)} results, total={total}, search_id={search_id}")
        print(f"  Script: {script_path}")
    else:
        print("  Script execution returned None")

    # Test CrossRef scripted search
    print("\n--- CrossRef scripted search ---")
    result = generate_and_run_script(
        project_path=PROJECT,
        source="crossref",
        query=query,
        parameters={"rows": 5},
    )
    if result:
        results, total, search_id, script_path = result
        print(f"  SUCCESS: {len(results)} results, total={total}, search_id={search_id}")
        print(f"  Script: {script_path}")
    else:
        print("  Script execution returned None")

    # Test Europe PMC scripted search
    print("\n--- Europe PMC scripted search ---")
    result = generate_and_run_script(
        project_path=PROJECT,
        source="europe_pmc",
        query=query,
        parameters={"page_size": 5},
    )
    if result:
        results, total, search_id, script_path = result
        print(f"  SUCCESS: {len(results)} results, total={total}, search_id={search_id}")
        print(f"  Script: {script_path}")
    else:
        print("  Script execution returned None (Europe PMC may be having API issues)")

    # List generated scripts
    scripts_dir = os.path.join(PROJECT, "scripts")
    if os.path.isdir(scripts_dir):
        scripts = [f for f in os.listdir(scripts_dir) if f.startswith("search_")]
        print(f"\n  Generated scripts in project/scripts/: {len(scripts)}")
        for s in sorted(scripts):
            print(f"    {s}")


def test_bibtex_export():
    """Test BibTeX export."""
    print("\n" + "=" * 60)
    print("3. BIBTEX EXPORT")
    print("=" * 60)

    from rwa_result_store import export_results_bibtex

    output = os.path.join(PROJECT, "exports", "test_results.bib")
    os.makedirs(os.path.dirname(output), exist_ok=True)

    result = export_results_bibtex(PROJECT, output_path=output, deduplicated=True)
    print(f"  Result: {result}")
    if os.path.exists(output):
        with open(output, "r", encoding="utf-8") as f:
            content = f.read()
        entries = content.count("@article{")
        print(f"  BibTeX entries: {entries}")
        # Show first entry
        lines = content.split("\n")
        print(f"  First 10 lines:")
        for line in lines[:10]:
            print(f"    {line}")
        print(f"  File size: {len(content)} chars")


def test_ris_export():
    """Test RIS export."""
    print("\n" + "=" * 60)
    print("4. RIS EXPORT")
    print("=" * 60)

    from rwa_result_store import export_results_ris

    output = os.path.join(PROJECT, "exports", "test_results.ris")
    os.makedirs(os.path.dirname(output), exist_ok=True)

    result = export_results_ris(PROJECT, output_path=output, deduplicated=True)
    print(f"  Result: {result}")
    if os.path.exists(output):
        with open(output, "r", encoding="utf-8") as f:
            content = f.read()
        entries = content.count("TY  - ")
        print(f"  RIS entries: {entries}")
        lines = content.split("\n")
        print(f"  First 15 lines:")
        for line in lines[:15]:
            print(f"    {line}")
        print(f"  File size: {len(content)} chars")


def test_csljson_export():
    """Test CSL-JSON export."""
    print("\n" + "=" * 60)
    print("5. CSL-JSON EXPORT")
    print("=" * 60)

    from rwa_result_store import export_results_csljson

    output = os.path.join(PROJECT, "exports", "test_results.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)

    result = export_results_csljson(PROJECT, output_path=output, deduplicated=True)
    print(f"  Result: {result}")
    if os.path.exists(output):
        import json
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  CSL-JSON entries: {len(data)}")
        if data:
            print(f"  First entry keys: {list(data[0].keys())}")
            print(f"  First title: {data[0].get('title', 'N/A')[:70]}...")


def test_batch_zotero_import():
    """Test batch Zotero import (preview only, not actually importing)."""
    print("\n" + "=" * 60)
    print("6. BATCH ZOTERO IMPORT (preview only)")
    print("=" * 60)

    # Gather DOIs from the database
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT doi FROM results WHERE doi IS NOT NULL AND doi != '' LIMIT 5")
    dois = [r[0] for r in cur.fetchall()]
    conn.close()

    print(f"  DOIs available for import: {len(dois)}")
    for d in dois:
        print(f"    {d}")

    print("\n  NOTE: Batch Zotero import via import_from_result_store() requires")
    print("  a running Zotero server with API access. Testing will be done via MCP tool.")


def summary():
    """Print final summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Check what was generated
    scripts_dir = os.path.join(PROJECT, "scripts")
    exports_dir = os.path.join(PROJECT, "exports")

    if os.path.isdir(scripts_dir):
        scripts = [f for f in os.listdir(scripts_dir) if f.startswith("search_")]
        print(f"  Generated search scripts: {len(scripts)}")
    else:
        print("  Generated search scripts: 0")

    if os.path.isdir(exports_dir):
        exports = os.listdir(exports_dir)
        print(f"  Export files: {len(exports)}")
        for e in exports:
            path = os.path.join(exports_dir, e)
            size = os.path.getsize(path)
            print(f"    {e} ({size:,} bytes)")
    else:
        print("  Export files: 0")

    # Final DB stats
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM searches")
        searches = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM results")
        results = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT doi) FROM results WHERE doi IS NOT NULL AND doi != ''")
        unique_dois = cur.fetchone()[0]
        conn.close()
        print(f"  Total searches in DB: {searches}")
        print(f"  Total results in DB: {results}")
        print(f"  Unique DOIs: {unique_dois}")


if __name__ == "__main__":
    ok = check_database()
    if not ok:
        print("No data to test with. Exiting.")
        sys.exit(1)

    test_script_generation()
    test_bibtex_export()
    test_ris_export()
    test_csljson_export()
    test_batch_zotero_import()
    summary()

    print("\nAll tests completed.")
