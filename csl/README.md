# Citation Style Library

This directory contains [Citation Style Language (CSL)](https://citationstyles.org/) files used by Quarto/Pandoc to format in-text citations and bibliographies.

## Bundled Styles

| File | Style | Type | Common In |
|------|-------|------|-----------|
| `apa.csl` | APA Style 7th edition | Author-date | Psychology, education, social sciences |
| `vancouver.csl` | Vancouver (NLM, citation-sequence) | Numbered | Medicine, biomedical sciences |
| `vancouver-superscript.csl` | Vancouver (superscript numbers) | Superscript numbered | Medicine, clinical journals |
| `american-medical-association.csl` | AMA Manual of Style 11th edition | Superscript numbered | US medical journals |
| `bmj.csl` | BMJ | Numbered | BMJ family journals |
| `nature.csl` | Nature | Numbered | Nature family journals |
| `national-library-of-medicine.csl` | NLM/Citing Medicine 2nd edition | Numbered | Library science, government reports |
| `ieee.csl` | IEEE Reference Guide | Numbered (bracketed) | Engineering, computer science |
| `harvard-cite-them-right.csl` | Cite Them Right 12th ed. (Harvard) | Author-date | UK universities, general |
| `chicago-author-date-17th-edition.csl` | Chicago 17th edition (author-date) | Author-date | History, humanities, social sciences |
| `chicago-fullnote-bibliography.csl` | Chicago 18th edition (notes & bibliography) | Footnotes | History, arts, humanities |

## Using a Style

In your Quarto (`.qmd`) document YAML front matter:

```yaml
bibliography: references.bib
csl: vancouver-superscript.csl
```

The CSL file should be in the same directory as your `.qmd` file (RWA copies the appropriate file into each project directory during project creation).

## Adding More Styles

Over 10,000 styles are available from the [Zotero Style Repository](https://www.zotero.org/styles). To add a new style:

1. **Via RWA**: Ask any agent to download a citation style — it will use the `download_csl_style` tool to fetch and save it automatically.
2. **Manually**: Download the `.csl` file from [zotero.org/styles](https://www.zotero.org/styles) and place it in this directory.

## Configuration

- **User default**: Set `default_citation_style` in `.rwa-user-config.yaml` (configured during `@setup`).
- **Per-project override**: Set `output_defaults.csl` in your project's `project-config.yaml`.
- **Resolution chain**: Project config → User config → `apa` (fallback).

## License

All CSL styles in this directory are sourced from the [Citation Style Language](https://github.com/citation-style-language/styles) project and are licensed under the [Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)](https://creativecommons.org/licenses/by-sa/3.0/) license.
