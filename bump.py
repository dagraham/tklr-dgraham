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
import subprocess

TWINE_ENV_KEYS = (
    "TWINE_USERNAME",
    "TWINE_PASSWORD",
    "UV_PUBLISH_TOKEN",
    "PYPI_USERNAME",
    "PYPI_PASSWORD",
)

PYPROJECT_PATH = Path("pyproject.toml")
MAIN_BRANCH = "master"
WORKING_BRANCH = "working"

DRY_RUN = "--dry-run" in sys.argv

# optional CLI flags
CLEAN_ONLY = "--clean" in sys.argv
NO_CLEAN = "--no-clean" in sys.argv


def clean_env_for_twine() -> dict:
    """Return a copy of os.environ with variables that override ~/.pypirc removed."""
    env = os.environ.copy()
    for k in TWINE_ENV_KEYS:
        env.pop(k, None)
    return env


def exec_cmd(cmd: str, *, env=None, stream: bool = False):
    """
    Run a shell command.
    - stream=False: capture and return stdout (like check_output)
    - stream=True: inherit stdout/stderr so output appears live
    """
    if not cmd:
        return True, ""
    if DRY_RUN:
        print(f"[dry-run] {cmd}")
        return True, ""

    try:
        if stream:
            # inherit parent's stdio -> live output
            res = subprocess.run(cmd, shell=True, env=env, check=True)
            return True, ""  # nothing captured
        else:
            out = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, shell=True, encoding="utf-8", env=env
            )
            return True, out
    except subprocess.CalledProcessError as e:
        # If streaming, e.output may be empty; we still show a concise error
        msg = (
            getattr(e, "output", "") or f"Command failed with exit code {e.returncode}"
        )
        print(f"❌ Error running: {cmd}\n{msg}")
        return False, msg


def check_output(cmd, env=None):
    if not cmd:
        return True, ""
    if DRY_RUN:
        print(f"[dry-run] {cmd}")
        return True, ""
    try:
        res = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, encoding="utf-8", env=env
        )
        return True, res
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running: {cmd}\n{e.output}")
        return False, e.output.strip().split("\n")[-1]


def run(cmd: str):
    """Run state-changing commands. Suppressed in --dry-run."""
    if not cmd:
        return True, ""
    if DRY_RUN:
        print(f"[dry-run] {cmd}")
        return True, ""  # success, but no output
    try:
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, encoding="utf-8"
        )
        return True, out
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running: {cmd}\n{e.output}")
        return False, e.output.strip().split("\n")[-1]


def read(cmd: str):
    """Run read-only commands even in --dry-run (e.g., git rev-parse)."""
    if not cmd:
        return True, ""
    try:
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, encoding="utf-8"
        )
        return True, out
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running: {cmd}\n{e.output}")
        return False, e.output.strip().split("\n")[-1]


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
                # if verbose:
                #     print(f"🧹 removed dir: {p.relative_to(root)}")
            elif p.exists():
                p.unlink()
                # if verbose:
                #     print(f"🧹 removed file: {p.relative_to(root)}")
        except Exception as e:
            print(f"⚠️ could not remove {p}: {e}")


def build_and_upload(repo="pypi", verbose=True, skip_existing=False):
    clean_build_artifacts()

    ok, out = exec_cmd("uv build", stream=True)  # or stream=False if you prefer quiet
    if not ok:
        return ok, out

    ok, out = exec_cmd("uvx twine check dist/*", stream=True)
    if not ok:
        return ok, out

    flags = ["-r", repo]
    if verbose:
        flags.append("--verbose")
    if skip_existing:
        flags.append("--skip-existing")

    env = clean_env_for_twine()  # ensure ~/.pypirc is honored
    # STREAM this so PyPI/Twine logs show up live
    return exec_cmd(f"uvx twine upload {' '.join(flags)} dist/*", env=env, stream=True)


def load_version():
    with PYPROJECT_PATH.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_version(new_version: str):
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    doc = toml_parse(text)
    doc["project"]["version"] = new_version
    PYPROJECT_PATH.write_text(toml_dumps(doc), encoding="utf-8")


# --- Ensure we're on the working branch ---
ok, current_branch = read("git rev-parse --abbrev-ref HEAD")
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
# Skip pre-commit hooks for version bump commits to avoid interference
run(f"git commit -a -m '{tmsg}' --no-verify")
ok, version_info = read("git log --pretty=format:'%ai' -n 1")
run(f"git tag -a -f '{new_version}' -m '{version_info}'")

# # Generate CHANGES.txt
# changes_text = f"Recent tagged changes as of {datetime.now()}:\n"
# ok, changelog = read(
#     "git log --pretty=format:'- %ar%d %an%n    %h %ai%n%w(70,4,4)%B' "
#     "--max-count=20 --no-walk --tags"
# )
# if ok:
#     with open("CHANGES.txt", "w") as f:
#         f.write(changes_text)
#         f.write(changelog)
#     print("CHANGES.txt generated (not committed).")

# Merge to master and sync
if input("Switch to master, merge working, and push? [yN] ").lower() == "y":
    run(f"git checkout {MAIN_BRANCH}")
    run(f"git merge {WORKING_BRANCH}")
    run(f"git push origin {MAIN_BRANCH}")

    run(f"git checkout {WORKING_BRANCH}")
    run(f"git reset --hard {MAIN_BRANCH}")
    run(f"git push origin {WORKING_BRANCH} --force")

    if input("Upload to PyPI using uv publish? [yN] ").lower() == "y":
        build_and_upload()

else:
    print(f"Retained version: {version}")

if not DRY_RUN:
    run("uv pip install -e .")
