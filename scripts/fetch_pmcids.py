"""Fetch PMC IDs for included studies and retrieve full text where available."""
import json
import time

import httpx

pmids = ["41466232", "39560615", "37001280", "34618311", "34010505", "32090783", "31733813"]
url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

results = {}
for pmid in pmids:
    try:
        r = httpx.get(
            url,
            params={
                "ids": pmid,
                "format": "json",
                "tool": "rwa",
                "email": "test@example.com",
            },
            timeout=15,
        )
        data = r.json()
        records = data.get("records", [])
        if records and "pmcid" in records[0]:
            pmcid = records[0]["pmcid"]
            print(f"PMID {pmid} -> {pmcid}")
            results[pmid] = pmcid
        else:
            print(f"PMID {pmid} -> No PMC ID (not open access in PMC)")
            results[pmid] = None
        time.sleep(0.5)
    except Exception as e:
        print(f"PMID {pmid} -> Error: {e}")
        results[pmid] = None

print("\n--- Summary ---")
print(json.dumps(results, indent=2))
