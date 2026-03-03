#!/usr/bin/env python3
"""Sync this fork with the upstream template repository.

Fetches upstream changes, merges them, and auto-resolves "deleted by us"
conflicts (files you intentionally removed via cleanup scripts).

Usage:
    python scripts/sync_upstream.py                         # merge upstream/main
    python scripts/sync_upstream.py --remote upstream       # custom remote name
    python scripts/sync_upstream.py --branch main           # custom branch
    python scripts/sync_upstream.py --add-remote <URL>      # add upstream remote
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(
    cmd: list[str], *, check: bool = True, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        if capture:
            print(result.stderr or result.stdout)
        sys.exit(result.returncode)
    return result


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def add_remote(remote: str, url: str) -> None:
    result = run(["git", "remote", "get-url", remote], check=False, capture=True)
    if result.returncode == 0:
        existing = result.stdout.strip()
        if existing == url:
            print(f"Remote '{remote}' already points to {url}")
        else:
            print(f"Remote '{remote}' exists but points to {existing}")
            print(f"To update: git remote set-url {remote} {url}")
        return
    run(["git", "remote", "add", remote, url])
    print(f"Added remote '{remote}' → {url}")


def check_remote_exists(remote: str) -> bool:
    result = run(["git", "remote", "get-url", remote], check=False, capture=True)
    return result.returncode == 0


def fetch(remote: str) -> None:
    print(f"Fetching {remote}...")
    run(["git", "fetch", remote])


def get_conflict_files() -> dict[str, list[str]]:
    """Return conflict files grouped by type (porcelain XY codes)."""
    result = run(["git", "status", "--porcelain"], capture=True)
    deleted_by_us: list[str] = []
    other: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        path = line[3:].strip()
        if xy == "DU":
            deleted_by_us.append(path)
        elif xy in ("UU", "AA", "AU", "UA", "UD", "DD"):
            other.append(path)
    return {"deleted_by_us": deleted_by_us, "other": other}


def resolve_deleted_by_us(files: list[str]) -> None:
    """Keep our deletions for 'deleted by us' conflicts."""
    for f in files:
        print(f"  Keeping deletion: {f}")
        run(["git", "rm", "-f", f])


def attempt_merge(remote: str, branch: str) -> bool:
    """Attempt git merge. Returns True if clean, False if conflicts."""
    print(f"Merging {remote}/{branch}...")
    result = run(
        ["git", "merge", f"{remote}/{branch}", "--no-edit"],
        check=False,
        capture=True,
    )
    if result.returncode == 0:
        return True
    # Print the merge output so the user sees what happened
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    return False


def has_uncommitted_changes() -> bool:
    result = run(["git", "status", "--porcelain"], capture=True)
    return bool(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remote", default="upstream", help="Remote name (default: upstream)"
    )
    parser.add_argument(
        "--branch", default="main", help="Branch to merge (default: main)"
    )
    parser.add_argument(
        "--add-remote", metavar="URL", help="Add the upstream remote and exit"
    )
    args = parser.parse_args()

    root = get_project_root()
    if not (root / ".git").exists():
        print("Error: not a git repository.")
        sys.exit(1)

    if args.add_remote:
        add_remote(args.remote, args.add_remote)
        return

    if not check_remote_exists(args.remote):
        print(f"Error: remote '{args.remote}' not found.")
        print("\nAdd it first:")
        print("  python scripts/sync_upstream.py --add-remote <UPSTREAM_URL>")
        print(f"  # or: git remote add {args.remote} <UPSTREAM_URL>")
        sys.exit(1)

    if has_uncommitted_changes():
        print("Error: you have uncommitted changes. Commit or stash them first.")
        run(["git", "status", "--short"])
        sys.exit(1)

    fetch(args.remote)
    clean = attempt_merge(args.remote, args.branch)

    if clean:
        print("\nMerge completed cleanly.")
        return

    # Resolve conflicts
    conflicts = get_conflict_files()

    if conflicts["deleted_by_us"]:
        print(
            f"\nAuto-resolving {len(conflicts['deleted_by_us'])} 'deleted by us' conflict(s):"
        )
        resolve_deleted_by_us(conflicts["deleted_by_us"])

    if conflicts["other"]:
        print(f"\n{len(conflicts['other'])} conflict(s) require manual resolution:")
        for f in conflicts["other"]:
            print(f"  {f}")
        print("\nResolve these, then:")
        print("  git add <resolved files>")
        print("  git merge --continue")
        return

    if conflicts["deleted_by_us"] and not conflicts["other"]:
        print("\nAll conflicts resolved. Completing merge...")
        run(["git", "commit", "--no-edit"])
        print("Merge complete.")
    else:
        print("\nNo conflicts detected but merge did not complete cleanly.")
        print("Check: git status")


if __name__ == "__main__":
    main()
