#!/usr/bin/env python3
"""
Sync working -> master and push both.

Steps:
  1) Ensure current branch is 'working' and clean.
  2) git push origin working
  3) git checkout master
  4) git merge working
  5) git push origin master
  6) git checkout working
"""

import subprocess
import sys
from pathlib import Path

WORKING_BRANCH = "working"
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


def ensure_on_working_branch():
    branch = read("git rev-parse --abbrev-ref HEAD")
    if branch != WORKING_BRANCH:
        print(f"❌ You are on '{branch}', not '{WORKING_BRANCH}'.")
        sys.exit(1)


def ensure_clean_working_tree():
    status = read("git status --porcelain")
    if status:
        print("❌ Working tree has uncommitted changes:")
        print(status)
        print("\nPlease commit or stash changes before running this script.")
        sys.exit(1)


def main():
    dry_run = "--dry-run" in sys.argv

    ensure_git_repo()
    ensure_on_working_branch()
    ensure_clean_working_tree()

    print(f"✅ On branch '{WORKING_BRANCH}' and working tree is clean.")

    # 1) Push working -> origin
    if run(f"git push {REMOTE} {WORKING_BRANCH}", dry_run=dry_run) != 0:
        print("❌ Failed to push working branch.")
        sys.exit(1)

    # 2) Checkout master
    if run(f"git checkout {MAIN_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Failed to checkout {MAIN_BRANCH}.")
        sys.exit(1)

    # 3) Merge working into master
    if run(f"git merge {WORKING_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Merge {WORKING_BRANCH} into {MAIN_BRANCH} failed.")
        print("   Resolve conflicts manually and finish the process by hand.")
        sys.exit(1)

    # 4) Push master
    if run(f"git push {REMOTE} {MAIN_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Failed to push {MAIN_BRANCH}.")
        sys.exit(1)

    # 5) Switch back to working
    if run(f"git checkout {WORKING_BRANCH}", dry_run=dry_run) != 0:
        print(f"❌ Failed to checkout {WORKING_BRANCH} at the end.")
        sys.exit(1)

    print("✅ Sync complete.")
    if dry_run:
        print("(dry-run: no commands were actually executed.)")


if __name__ == "__main__":
    main()
