#!/usr/bin/env python3

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import tomllib
from tomlkit import parse as toml_parse, dumps as toml_dumps
import shutil
import itertools

PYPROJECT_PATH = Path("pyproject.toml")
MAIN_BRANCH = "master"
WORKING_BRANCH = "working"
DRY_RUN = "--dry-run" in sys.argv


# add near the top
def clean_build_artifacts(verbose=True):
    """
    Remove common build artifacts and caches:
      dist/, build/, *.egg-info, **/__pycache__, .pytest_cache, .mypy_cache
    """
    root = Path(__file__).resolve().parent
    dirs_to_remove = [
        root / "dist",
        root / "build",
        root / ".pytest_cache",
        root / ".mypy_cache",
    ]
    # egg-info directories/files at project root
    dirs_to_remove += list(root.glob("*.egg-info"))
    # any __pycache__ under the project
    dirs_to_remove += list(root.rglob("__pycache__"))

    for p in dirs_to_remove:
        try:
            if p.is_dir():
                shutil.rmtree(p)
                if verbose:
                    print(f"🧹 removed dir: {p.relative_to(root)}")
            elif p.exists():
                p.unlink()
                if verbose:
                    print(f"🧹 removed file: {p.relative_to(root)}")
        except Exception as e:
            print(f"⚠️ could not remove {p}: {e}")


# optional CLI flags
CLEAN_ONLY = "--clean" in sys.argv
NO_CLEAN = "--no-clean" in sys.argv


def load_version():
    with PYPROJECT_PATH.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_version(new_version: str):
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    doc = toml_parse(text)
    doc["project"]["version"] = new_version
    PYPROJECT_PATH.write_text(toml_dumps(doc), encoding="utf-8")


def check_output(cmd):
    if not cmd:
        return
    if DRY_RUN:
        print(f"[dry-run] {cmd}")
        return True, ""
    try:
        res = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, encoding="utf-8"
        )
        return True, res
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running: {cmd}\n{e.output}")
        return False, e.output.strip().split("\n")[-1]


# def load_version():
#     with open(PYPROJECT_PATH, "rb") as f:
#         data = tomllib.load(f)
#     return data["project"]["version"]
#
#
# def write_version(new_version):
#     with open(PYPROJECT_PATH, "rb") as f:
#         data = tomllib.load(f)
#     data["project"]["version"] = new_version
#     with open(PYPROJECT_PATH, "wb") as f:
#         f.write(tomli_w.dumps(data).encode("utf-8"))


# --- Ensure we're on the working branch ---
ok, current_branch = check_output("git rev-parse --abbrev-ref HEAD")
current_branch = current_branch.strip()
if current_branch != WORKING_BRANCH:
    print(f"⚠️  You are on '{current_branch}', not '{WORKING_BRANCH}'.")
    print(f"Please switch to '{WORKING_BRANCH}' before running this script.")
    sys.exit(1)

# --- Bump Logic ---
version = load_version()
pre = post = version
ext = "a"
ext_num = 1
possible_extensions = ["a", "b", "rc"]

for poss in possible_extensions:
    if poss in version:
        ext = poss
        pre, post = version.split(ext)
        ext_num = int(post) + 1
        break

extension_options = {
    "a": {"a": f"a{ext_num}", "b": "b0", "r": "rc0"},
    "b": {"b": f"b{ext_num}", "r": "rc0"},
    "rc": {"r": f"rc{ext_num}"},
}

major, minor, patch = pre.split(".")
b_patch = ".".join([major, minor, str(int(patch) + 1)])
b_minor = ".".join([major, str(int(minor) + 1), "0"])
b_major = ".".join([str(int(major) + 1), "0", "0"])

opts = [f"The current version is {version}"]
if ext and ext in extension_options:
    for k, v in extension_options[ext].items():
        opts.append(f"  {k}: {pre}{v}")
opts += [f"  p: {b_patch}", f"  n: {b_minor}", f"  j: {b_major}"]

print("\n".join(opts))
res = input("Which new version? ").lower().strip()
if not res:
    print("Cancelled.")
    sys.exit()

if res in extension_options.get(ext, {}):
    new_version = f"{pre}{extension_options[ext][res]}"
    bmsg = "release candidate version update"
elif res == "p":
    new_version = b_patch
    bmsg = "patch version update"
elif res == "n":
    new_version = b_minor
    bmsg = "minor version update"
elif res == "j":
    new_version = b_major
    bmsg = "major version update"
else:
    print("Unknown option. Cancelled.")
    sys.exit()

tplus = input(f"Optional {bmsg} message:\n")
tmsg = f"Tagged version {new_version}. {tplus}"

print(f"\nThe tag message for the new version will be:\n{tmsg}\n")
if DRY_RUN:
    print(f"[dry-run] Would set new version: {new_version}")
    print(f"[dry-run] Would update pyproject.toml")
    print(f"[dry-run] Would commit and tag with message:\n\n{tmsg}\n")
    sys.exit(0)

if input(f"Commit and tag new version: {new_version}? [yN] ").lower() != "y":
    print("Cancelled.")
    sys.exit()

write_version(new_version)
check_output(f"git commit -a -m '{tmsg}'")
ok, version_info = check_output("git log --pretty=format:'%ai' -n 1")
check_output(f"git tag -a -f '{new_version}' -m '{version_info}'")

# Generate CHANGES.txt
changes_text = f"Recent tagged changes as of {datetime.now()}:\n"
ok, changelog = check_output(
    "git log --pretty=format:'- %ar%d %an%n    %h %ai%n%w(70,4,4)%B' "
    "--max-count=20 --no-walk --tags"
)
if ok:
    with open("CHANGES.txt", "w") as f:
        f.write(changes_text)
        f.write(changelog)
    print("CHANGES.txt generated (not committed).")

# Merge to master and sync
if input("Switch to master, merge working, and push? [yN] ").lower() == "y":
    check_output(f"git checkout {MAIN_BRANCH}")
    check_output(f"git merge {WORKING_BRANCH}")
    check_output(f"git push origin {MAIN_BRANCH}")

    check_output(f"git checkout {WORKING_BRANCH}")
    check_output(f"git reset --hard {MAIN_BRANCH}")
    check_output(f"git push origin {WORKING_BRANCH} --force")

    if input("Upload to PyPI using uv publish? [yN] ").lower() == "y":
        if not NO_CLEAN:
            clean_build_artifacts()
        check_output("uv publish")

else:
    print(f"Retained version: {version}")

if not DRY_RUN:
    check_output("uv pip install -e .")
