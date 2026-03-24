"""One-off script to upload Arksey and Tricco PDFs to Zotero."""

import hashlib
import os
import pathlib

import httpx
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")
API_KEY = os.environ["ZOTERO_API_KEY"]
USER_ID = os.environ["ZOTERO_USER_ID"]
BASE = "https://api.zotero.org"


def _headers():
    return {"Zotero-API-Key": API_KEY, "Zotero-API-Version": "3"}


def upload_pdf(item_key: str, file_path: pathlib.Path) -> str | None:
    file_bytes = file_path.read_bytes()
    md5 = hashlib.md5(file_bytes).hexdigest()
    size = len(file_bytes)
    fname = file_path.name
    print(f"Uploading {fname} ({size:,} bytes, md5={md5}) to item {item_key}")

    with httpx.Client(timeout=120.0) as client:
        # Step 1: Create attachment child item
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
            print(f"  FAILED to create attachment: {d1.get('failed', {})}")
            return None
        att_key = success["0"]
        print(f"  Created attachment item: {att_key}")

        # Step 2: Get upload authorization
        auth_url = f"{BASE}/users/{USER_ID}/items/{att_key}/file"
        import time

        mtime = int(time.time() * 1000)
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
        r2.raise_for_status()
        d2 = r2.json()
        print(f"  Auth response: {d2}")

        if d2.get("exists"):
            print("  File already exists on server. Done.")
            return att_key

        # Step 3: Upload to S3
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
        r3.raise_for_status()
        print(f"  Uploaded to S3 ({r3.status_code})")

        # Step 4: Register upload
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
        r4.raise_for_status()
        print(f"  Registered upload. Attachment key: {att_key}")
        return att_key


if __name__ == "__main__":
    pdfs = (
        pathlib.Path(__file__).resolve().parents[1]
        / "my_projects"
        / "fluoride-children-review"
        / "pdfs"
    )

    # Arksey 2005 -> Z9CWM383
    upload_pdf("Z9CWM383", pdfs / "Arksey_2005_Scoping_studies.pdf")
    print()
    # Tricco 2018 -> W8ZTI8SK
    upload_pdf("W8ZTI8SK", pdfs / "Tricco_2018_PRISMA-ScR.pdf")
    print()
    print("All done!")
