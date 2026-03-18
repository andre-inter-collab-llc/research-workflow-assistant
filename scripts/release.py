#!/usr/bin/env python3
"""Release script for the Research Workflow Assistant.

Creates a versioned release with:
- CalVer version bump (YYYY.MM.DD format) in pyproject.toml
- Environment snapshot (pip freeze → requirements-lock.txt)
- Zip backup of all git-tracked files → local backup directory + repo root
- Git tag and commit
- Optional push to origin

Usage:
    python scripts/release.py                     # Interactive release (today's date)
    python scripts/release.py --version 2026.03.18
    python scripts/release.py --push              # Auto-push tag to origin
    python scripts/release.py --dry-run           # Preview without changes
    python scripts/release.py --backup-dir ~/MyBackups/rwa
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
VERSIONS_YAML = REPO_ROOT / "versions.yaml"
LOCK_FILE = REPO_ROOT / "requirements-lock.txt"
DEFAULT_BACKUP_DIR = Path.home() / "Backups" / "rwa"


def get_current_version() -> str:
    """Read the current version from pyproject.toml."""
    content = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("ERROR: Could not find version in pyproject.toml")
        sys.exit(1)
    return match.group(1)


def compute_next_version(requested: str | None) -> str:
    """Compute the next CalVer version.

    If no version is requested, uses today's date (YYYY.MM.DD).
    If today's date matches the current version, appends .N suffix.
    """
    today = datetime.date.today().strftime("%Y.%m.%d")
    current = get_current_version()

    if requested:
        return requested

    if current == today:
        # Same-day release — find the next suffix
        suffix = 1
        while True:
            candidate = f"{today}.{suffix}"
            # Check if this tag already exists
            result = subprocess.run(
                ["git", "tag", "-l", f"v{candidate}"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            if candidate != current and result.stdout.strip() == "":
                return candidate
            suffix += 1
    elif current.startswith(today + "."):
        # Current is a same-day suffixed version — increment
        parts = current.split(".")
        suffix = int(parts[-1]) + 1
        return f"{today}.{suffix}"

    return today


def update_pyproject_version(new_version: str, *, dry_run: bool = False) -> None:
    """Update the version string in pyproject.toml."""
    content = PYPROJECT.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(version\s*=\s*)"[^"]+"',
        f'\\1"{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if dry_run:
        print(f"  [DRY RUN] Would update pyproject.toml version to {new_version}")
        return
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"  Updated pyproject.toml version to {new_version}")


def freeze_environment(*, dry_run: bool = False) -> None:
    """Run pip freeze and save to requirements-lock.txt."""
    if dry_run:
        print(f"  [DRY RUN] Would run pip freeze → {LOCK_FILE.name}")
        return

    # Use the same Python that's running this script
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"  WARNING: pip freeze failed: {result.stderr.strip()}")
        return

    header = (
        f"# Research Workflow Assistant — Environment Snapshot\n"
        f"# Generated: {datetime.datetime.now(tz=datetime.UTC).isoformat()}\n"
        f"# Python: {sys.version.split()[0]}\n"
        f"# Platform: {sys.platform}\n"
        f"#\n"
        f"# To recreate this environment:\n"
        f"#   python -m venv .venv\n"
        f"#   .venv/Scripts/activate  (or source .venv/bin/activate)\n"
        f"#   pip install -r requirements-lock.txt\n\n"
    )
    LOCK_FILE.write_text(header + result.stdout, encoding="utf-8")
    print(f"  Saved environment snapshot to {LOCK_FILE.name}")


def get_git_tracked_files() -> list[str]:
    """Get list of all git-tracked files."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"ERROR: git ls-files failed: {result.stderr.strip()}")
        sys.exit(1)
    return [f for f in result.stdout.strip().split("\n") if f]


def create_backup_zip(version: str, backup_dir: Path, *, dry_run: bool = False) -> Path | None:
    """Create a zip of all git-tracked files."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"rwa-{version}.zip"
    zip_path = backup_dir / zip_name

    if dry_run:
        print(f"  [DRY RUN] Would create backup: {zip_path}")
        return None

    files = get_git_tracked_files()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath in files:
            full_path = REPO_ROOT / filepath
            if full_path.exists():
                zf.write(full_path, filepath)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  Created backup: {zip_path} ({size_mb:.1f} MB, {len(files)} files)")
    return zip_path


def prepend_changelog_entry(version: str, summary: str, *, dry_run: bool = False) -> None:
    """Prepend a new entry to CHANGELOG.md."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = f"\n## [{version}] — {today}\n\n{summary}\n\n### Added\n\n### Changed\n\n### Fixed\n\n"

    if dry_run:
        print(f"  [DRY RUN] Would prepend changelog entry for {version}")
        return

    content = CHANGELOG.read_text(encoding="utf-8")
    # Insert after the header block (before the first ## entry)
    marker = re.search(r"^## \[", content, re.MULTILINE)
    if marker:
        updated = content[: marker.start()] + entry + content[marker.start() :]
    else:
        updated = content + entry

    CHANGELOG.write_text(updated, encoding="utf-8")
    print(f"  Prepended changelog entry for {version}")


def append_versions_yaml(version: str, summary: str, *, dry_run: bool = False) -> None:
    """Append a new release entry to versions.yaml."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    entry = (
        f'\n  - version: "{version}"\n'
        f'    date: "{today}"\n'
        f'    summary: "{summary}"\n'
        f"    changes:\n"
        f"      added: []\n"
        f"      changed: []\n"
        f"      fixed: []\n"
        f"      removed: []\n"
        f"      security: []\n"
    )

    if dry_run:
        print(f"  [DRY RUN] Would append versions.yaml entry for {version}")
        return

    with open(VERSIONS_YAML, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  Appended versions.yaml entry for {version}")


def git_tag_and_commit(version: str, *, dry_run: bool = False, push: bool = False) -> None:
    """Create a git commit and tag for the release."""
    tag = f"v{version}"

    if dry_run:
        print(f"  [DRY RUN] Would commit and tag as {tag}")
        if push:
            print(f"  [DRY RUN] Would push tag {tag} to origin")
        return

    # Stage release files
    files_to_stage = [
        "pyproject.toml",
        "CHANGELOG.md",
        "versions.yaml",
        "requirements-lock.txt",
    ]
    for f in files_to_stage:
        if (REPO_ROOT / f).exists():
            subprocess.run(["git", "add", f], cwd=REPO_ROOT, check=True)

    # Commit
    subprocess.run(
        ["git", "commit", "-m", f"release: {tag}"],
        cwd=REPO_ROOT,
        check=True,
    )
    print(f"  Committed release {tag}")

    # Tag
    subprocess.run(
        ["git", "tag", "-a", tag, "-m", f"Release {version}"],
        cwd=REPO_ROOT,
        check=True,
    )
    print(f"  Created tag {tag}")

    if push:
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=REPO_ROOT,
            check=True,
        )
        subprocess.run(
            ["git", "push", "origin", tag],
            cwd=REPO_ROOT,
            check=True,
        )
        print(f"  Pushed tag {tag} to origin")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a versioned release of the Research Workflow Assistant"
    )
    parser.add_argument(
        "--version",
        help="Version string (default: today's CalVer date YYYY.MM.DD)",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Release summary for the changelog (prompted interactively if omitted)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Local backup directory (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push tag and commit to origin after creating",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all actions without making changes",
    )
    parser.add_argument(
        "--skip-changelog",
        action="store_true",
        help="Skip changelog/versions.yaml update (useful for initial setup)",
    )
    args = parser.parse_args()

    current = get_current_version()
    new_version = compute_next_version(args.version)

    print(f"\n{'=' * 60}")
    print("  Research Workflow Assistant — Release")
    print(f"{'=' * 60}")
    print(f"  Current version : {current}")
    print(f"  New version     : {new_version}")
    print(f"  Backup dir      : {args.backup_dir}")
    print(f"  Dry run         : {args.dry_run}")
    print(f"  Push to origin  : {args.push}")
    print(f"{'=' * 60}\n")

    # Get summary interactively if not provided and not skipping
    summary = args.summary
    if not summary and not args.skip_changelog and not args.dry_run:
        summary = input("Release summary (one line): ").strip()
        if not summary:
            summary = f"Release {new_version}"

    # Step 1: Update version
    print("Step 1: Updating version...")
    update_pyproject_version(new_version, dry_run=args.dry_run)

    # Step 2: Freeze environment
    print("Step 2: Freezing environment...")
    freeze_environment(dry_run=args.dry_run)

    # Step 3: Update changelog
    if not args.skip_changelog:
        print("Step 3: Updating changelog...")
        prepend_changelog_entry(
            new_version, summary or f"Release {new_version}", dry_run=args.dry_run
        )
        append_versions_yaml(new_version, summary or f"Release {new_version}", dry_run=args.dry_run)
    else:
        print("Step 3: Skipping changelog (--skip-changelog)")

    # Step 4: Create backup
    print("Step 4: Creating backup...")
    create_backup_zip(new_version, args.backup_dir, dry_run=args.dry_run)

    # Step 5: Git commit and tag
    print("Step 5: Git commit and tag...")
    git_tag_and_commit(new_version, dry_run=args.dry_run, push=args.push)

    print(f"\nRelease {new_version} complete!")
    if not args.push and not args.dry_run:
        print("\nTo push this release:")
        print("  git push origin master")
        print(f"  git push origin v{new_version}")
    print()


if __name__ == "__main__":
    # Ensure we're running from the repo root context
    os.chdir(REPO_ROOT)
    main()
