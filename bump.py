#!/usr/bin/env python3

import os
import sys
import subprocess
from datetime import datetime
import tomllib
import tomli_w

# --- Configuration ---
PYPROJECT_PATH = "pyproject.toml"
MAIN_BRANCH = "master"
WORKING_BRANCH = "working"
DRY_RUN = "--dry-run" in sys.argv


# --- Helpers ---
def check_output(cmd):
    if not cmd:
        return
    if DRY_RUN:
        print(f"[dry-run] {cmd}")
        return True, ""
    try:
        res = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True,
            encoding="UTF-8",
        )
        return True, res
    except subprocess.CalledProcessError as e:
        print(f"Error running {cmd}\n'{e.output}'")
        return False, e.output.strip().split("\n")[-1]


def load_version():
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def write_version(new_version):
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)
    data["project"]["version"] = new_version
    with open(PYPROJECT_PATH, "wb") as f:
        f.write(tomli_w.dumps(data).encode("utf-8"))


# --- Version Bumping Logic ---
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
    print("cancelled")
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
    print("cancelled")
    sys.exit()

write_version(new_version)

check_output(f"git commit -a -m '{tmsg}'")
ok, version_info = check_output("git log --pretty=format:'%ai' -n 1")
check_output(f"git tag -a -f '{new_version}' -m '{version_info}'")

# Generate CHANGES.txt (but don't commit it)
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

if input("Switch to master, merge working, and push? [yN] ").lower() == "y":
    check_output(
        f"git checkout {MAIN_BRANCH} && git merge {WORKING_BRANCH} && "
        f"git push && git checkout {WORKING_BRANCH} && git push"
    )

    if input("Upload to PyPI using uv publish? [yN] ").lower() == "y":
        check_output("uv publish --yes")
else:
    print(f"retained version: {version}")
