from __future__ import annotations

import sys
from pathlib import Path

# Ensure local shared package is importable without editable install
_SHARED_SRC = Path(__file__).resolve().parents[1] / "mcp-servers" / "_shared" / "src"
if str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

from rwa_result_store import execute_search_script  # noqa: E402


def test_execute_search_script_returns_error_details_on_nonzero_exit(tmp_path: Path) -> None:
    script = tmp_path / "fail_script.py"
    script.write_text(
        "import sys\n"
        "print('stdout boom')\n"
        "print('stderr boom', file=sys.stderr)\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )

    result = execute_search_script(
        project_path=str(tmp_path),
        script_path=str(script),
        include_error_details=True,
    )

    assert isinstance(result, dict)
    assert result["error"] == "Script exited with non-zero status."
    assert result["returncode"] == 2
    assert "stderr boom" in result["stderr"]
    assert "stdout boom" in result["stdout"]


def test_execute_search_script_returns_error_details_when_search_id_is_invalid(
    tmp_path: Path,
) -> None:
    script = tmp_path / "bad_output_script.py"
    script.write_text("print('NOT_A_SEARCH_ID')\n", encoding="utf-8")

    result = execute_search_script(
        project_path=str(tmp_path),
        script_path=str(script),
        include_error_details=True,
    )

    assert isinstance(result, dict)
    assert result["error"] == "Could not parse search_id from script output."
    assert "NOT_A_SEARCH_ID" in result["stdout"]


def test_execute_search_script_returns_error_details_when_db_is_missing(tmp_path: Path) -> None:
    script = tmp_path / "id_only_script.py"
    script.write_text("print('123')\n", encoding="utf-8")

    result = execute_search_script(
        project_path=str(tmp_path),
        script_path=str(script),
        include_error_details=True,
    )

    assert isinstance(result, dict)
    assert result["error"] == "Search database was not found after script execution."


def test_execute_search_script_returns_error_details_for_missing_script(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.py"

    result = execute_search_script(
        project_path=str(tmp_path),
        script_path=str(missing),
        include_error_details=True,
    )

    assert isinstance(result, dict)
    assert result["error"] == "Script not found."
    assert result["script_path"] == str(missing)
