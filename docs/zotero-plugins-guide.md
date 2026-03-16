# Recommended Zotero Plugins for RWA Users

This guide covers Zotero plugins that enhance the Research Workflow Assistant experience. None are strictly required, but each improves specific RWA capabilities.

## Essential: Better BibTeX (BBT)

**What it does**: Generates stable, human-readable citation keys (e.g., `smith2024climate`) and provides enhanced BibTeX/BibLaTeX export.

**Why it matters for RWA**: BBT is the only plugin with deep RWA integration via JSON-RPC. It enables:
- Stable `@citekeys` that won't change when you edit item metadata
- Enhanced BibTeX export with more accurate field mapping
- The `bbt_get_citekey`, `bbt_search_by_citekey`, `bbt_export`, `bbt_sync_bib_file`, and `bbt_auto_pin` tools in the zotero-local-server
- Cite-As-You-Write (`bbt_cayw`) for interactive citation picking

**Install**: <https://retorque.re/zotero-better-bibtex/installation/>

**Configuration tips**:
- Set your preferred citation key format in BBT Preferences → Citation Keys
- Enable "On item change: update citation key" for automatic key management
- Use `bbt_auto_pin` to lock keys for items already cited in manuscripts

---

## Recommended: Zotero DOI Manager

**What it does**: Automatically fetches missing DOIs for items in your library by searching CrossRef.

**Why it matters for RWA**:
- Improves deduplication accuracy when importing results from multiple databases
- Increases success rate of `import_from_result_store` (which matches by DOI)
- Enables `get_item_by_doi` lookups for items that previously had no DOI

**Install**: Available from the Zotero Plugin Manager or <https://github.com/bwiernik/zotero-shortdoi>

---

## Recommended: Zotero OCR

**What it does**: Adds OCR (Optical Character Recognition) to scanned PDF attachments, making their text searchable.

**Why it matters for RWA**:
- Enables `extract_pdf_text` to work on scanned documents
- Enables `search_pdf_content` to find keywords in scanned papers
- Essential for older publications that exist only as scanned images

**Install**: <https://github.com/UB-Mannheim/zotero-ocr>

**Note**: Requires Tesseract OCR installed on your system. The plugin provides a Zotero menu to OCR individual items or batches.

---

## Useful: Zotero Better Notes

**What it does**: Enhanced note-taking within Zotero with templates, Markdown support, bi-directional linking between notes, and note export.

**Why it matters for RWA**:
- Rich notes become accessible via `get_notes`, `get_local_notes`, and `search_notes`
- Template-based notes improve consistency in data extraction
- Note linking helps connect related concepts across papers

**Install**: <https://github.com/windingwind/zotero-better-notes>

---

## Useful: Zotero Storage Scanner

**What it does**: Scans your library for broken attachment links — files that Zotero references but can't find on disk.

**Why it matters for RWA**:
- Prevents `extract_pdf_text` and `extract_pdf_annotations` failures due to missing files
- Identifies sync issues before they cause problems during analysis
- Run periodically to keep your library healthy

**Install**: <https://github.com/retorquere/zotero-storage-scanner>

---

## Optional: Zotero Scite Plugin

**What it does**: Shows citation context for papers — whether each citation supports, contradicts, or mentions a finding.

**Why it matters for RWA**:
- Useful context when doing critical appraisal with `@critical-reviewer`
- Helps identify controversial findings before deep reading

**Install**: <https://github.com/scitedotai/scite-zotero-plugin>

---

## Optional: Zotero PDF Translate

**What it does**: In-reader translation of PDF text using various translation services.

**Why it matters for RWA**:
- Assists with non-English language papers encountered during systematic searches
- Translated annotations can be captured by `extract_pdf_annotations`

**Install**: <https://github.com/windingwind/zotero-pdf-translate>

---

## Plugin Installation (Zotero 7)

1. Download the `.xpi` file from the plugin's releases page
2. In Zotero: **Tools → Add-ons → Install Add-on from File**
3. Select the `.xpi` file and restart Zotero
4. Configure the plugin in **Edit → Settings** (or **Zotero → Preferences** on macOS)

After installing plugins, restart Zotero and then restart MCP servers in VS Code (Command Palette → "MCP: Restart Servers") to pick up any new capabilities.

---

## Compatibility Note

All plugins listed here are compatible with **Zotero 7**. If you are still on Zotero 6, check each plugin's documentation for version compatibility. RWA supports both Zotero 6 and 7, but Zotero 7 provides richer annotation data.
