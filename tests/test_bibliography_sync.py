from __future__ import annotations

import sys
from pathlib import Path

# Ensure local shared package is importable without editable install
_SHARED_SRC = Path(__file__).resolve().parents[1] / "mcp-servers" / "_shared" / "src"
if str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

from rwa_result_store.bibliography_sync import (  # noqa: E402
    normalize_author_name,
    rewrite_qmd_citekeys,
    split_manual_and_generated_bibliography,
)


def test_normalize_author_name_surname_initials() -> None:
    normalized, status = normalize_author_name("Tripathi A")
    assert normalized == "Tripathi, A"
    assert status == "surname_initials"


def test_normalize_author_name_handles_particle_surname() -> None:
    normalized, status = normalize_author_name("Elon H. C. van Dijk")
    assert normalized == "van Dijk, Elon H. C."
    assert status == "inferred"


def test_normalize_author_name_corporate_group() -> None:
    normalized, status = normalize_author_name("ISPOR Working Group on Generative AI")
    assert normalized == "{ISPOR Working Group on Generative AI}"
    assert status == "corporate"


def test_split_manual_and_generated_bibliography() -> None:
    source = (
        "@article{manual2024,\n"
        "  title = {Manual}\n"
        "}\n\n"
        "% === Included studies (n=2) ===\n\n"
        "@article{a,\n}\n\n"
        "% === Included studies (n=3) ===\n\n"
        "@article{b,\n}\n"
    )
    manual, block_count = split_manual_and_generated_bibliography(source)

    assert "manual2024" in manual
    assert "Included studies" not in manual
    assert block_count == 2


def test_rewrite_qmd_citekeys_updates_all_mentions(tmp_path: Path) -> None:
    qmd = tmp_path / "report.qmd"
    qmd.write_text(
        "Results [@oldkey; @other]. Narrative @oldkey and [see @oldkey, p. 4].\n",
        encoding="utf-8",
    )

    updates = rewrite_qmd_citekeys(
        project_path=tmp_path,
        old_to_new={"oldkey": "newkey"},
        apply=True,
    )

    rewritten = qmd.read_text(encoding="utf-8")
    assert "@oldkey" not in rewritten
    assert rewritten.count("@newkey") == 3
    assert updates[0]["replacements"] == 3
