"""Re-upload to existing attachment items that were created but never got files."""

import hashlib
import os
import pathlib
import time

import httpx
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
API_KEY = os.environ["ZOTERO_API_KEY"]
USER_ID = os.environ["ZOTERO_USER_ID"]
BASE = "https://api.zotero.org"


def _headers():
    return {"Zotero-API-Key": API_KEY, "Zotero-API-Version": "3"}


def upload_file_to_attachment(att_key: str, file_path: pathlib.Path) -> bool:
    file_bytes = file_path.read_bytes()
    md5 = hashlib.md5(file_bytes).hexdigest()
    size = len(file_bytes)
    fname = file_path.name
    mtime = int(time.time() * 1000)
    print(f"Uploading {fname} ({size:,} bytes) to attachment {att_key}")

    with httpx.Client(timeout=120.0) as client:
        auth_url = f"{BASE}/users/{USER_ID}/items/{att_key}/file"
        auth_body = f"md5={md5}&filename={fname}&filesize={size}&mtime={mtime}"
        r2 = client.post(
            auth_url,
            headers={
                **_headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
            },
            content=auth_body,
        )
        print(f"  Auth status: {r2.status_code}")
        print(f"  Auth body: {r2.text[:500]}")
        r2.raise_for_status()
        d2 = r2.json()

        if d2.get("exists"):
            print("  File already exists on server.")
            return True

        # Upload to S3
        upload_url = d2["url"]
        prefix = d2.get("prefix", "")
        suffix = d2.get("suffix", "")
        ct = d2.get("contentType", "application/pdf")

        if isinstance(prefix, str):
            prefix = prefix.encode("latin-1")
        if isinstance(suffix, str):
            suffix = suffix.encode("latin-1")

        body = prefix + file_bytes + suffix
        r3 = client.post(upload_url, headers={"Content-Type": ct}, content=body)
        print(f"  S3 status: {r3.status_code}")
        r3.raise_for_status()

        # Register
        upload_key = d2.get("uploadKey", "")
        r4 = client.post(
            auth_url,
            headers={
                **_headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "If-None-Match": "*",
            },
            content=f"upload={upload_key}",
        )
        print(f"  Register status: {r4.status_code}")
        r4.raise_for_status()
        print("  Success!")
        return True


def create_and_upload(item_key: str, file_path: pathlib.Path) -> str | None:
    fname = file_path.name
    print(f"\n=== {fname} -> parent {item_key} ===")

    with httpx.Client(timeout=120.0) as client:
        # Create attachment
        attach = [
            {
                "itemType": "attachment",
                "parentItem": item_key,
                "linkMode": "imported_file",
                "title": fname,
                "contentType": "application/pdf",
                "filename": fname,
                "tags": [],
                "relations": {},
            }
        ]
        r1 = client.post(
            f"{BASE}/users/{USER_ID}/items",
            headers={**_headers(), "Content-Type": "application/json"},
            json=attach,
        )
        r1.raise_for_status()
        d1 = r1.json()
        success = d1.get("success", {})
        if not success:
            print(f"  FAILED: {d1.get('failed', {})}")
            return None
        att_key = success["0"]
        print(f"  Created attachment: {att_key}")

    # Now upload
    upload_file_to_attachment(att_key, file_path)
    return att_key


if __name__ == "__main__":
    pdfs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "my_projects"
        / "fluoride-children-review"
        / "pdfs"
    )

    # First try uploading to the already-created ZKBC8D73 (Arksey)
    print("=== Trying existing attachment ZKBC8D73 (Arksey) ===")
    try:
        upload_file_to_attachment("ZKBC8D73", pdfs / "Arksey_2005_Scoping_studies.pdf")
    except Exception as e:
        print(f"  Failed: {e}")
        print("  Creating new attachment...")
        create_and_upload("Z9CWM383", pdfs / "Arksey_2005_Scoping_studies.pdf")

    # Tricco
    create_and_upload("W8ZTI8SK", pdfs / "Tricco_2018_PRISMA-ScR.pdf")

    print("\nAll done!")
