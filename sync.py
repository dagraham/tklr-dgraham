#!/usr/bin/env -S uv run python
"""
Sync master with origin using a single-branch workflow.

Steps:
  1) Ensure current branch is 'master' and clean.
  2) git pull --rebase origin master
  3) git push origin master
"""

import subprocess
import sys
from pathlib import Path

MAIN_BRANCH = "master"
REMOTE = "origin"


def run(cmd: str, *, dry_run: bool = False) -> int:
    print(f"$ {cmd}")
    if dry_run:
        return 0
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def read(cmd: str) -> str:
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Error running: {cmd}\n{result.stdout}")
        sys.exit(result.returncode)
    return result.stdout.strip()


def ensure_git_repo():
    if not (Path(".") / ".git").exists():
        print("❌ This does not look like a Git repository (no .git directory).")
        sys.exit(1)


def ensure_on_main_branch():
    branch = read("git rev-parse --abbrev-ref HEAD")
    if branch != MAIN_BRANCH:
        print(f"❌ You are on '{branch}', not '{MAIN_BRANCH}'.")
        sys.exit(1)


def ensure_clean_tree():
    status = read("git status --porcelain")
    if status:
        print("❌ Working tree has uncommitted changes:")
        print(status)
        print("\nPlease commit or stash changes before running this script.")
        sys.exit(1)


def main():
    dry_run = "--dry-run" in sys.argv

    ensure_git_repo()
    ensure_on_main_branch()
    ensure_clean_tree()

    print(f"✅ On branch '{MAIN_BRANCH}' and working tree is clean.")

    # 1) Pull --rebase master from origin
    if run(f"git pull --rebase {REMOTE} {MAIN_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Failed to pull --rebase {MAIN_BRANCH}.")
        sys.exit(1)

    # 2) Push master
    if run(f"git push {REMOTE} {MAIN_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Failed to push {MAIN_BRANCH}.")
        sys.exit(1)

    print("✅ Sync complete.")
    if dry_run:
        print("(dry-run: no commands were actually executed.)")


if __name__ == "__main__":
    main()
