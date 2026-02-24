#!/usr/bin/env -S uv run python

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import re
import shlex
import tomllib
from tomlkit import parse as toml_parse, dumps as toml_dumps
import shutil

TWINE_ENV_KEYS = (
    "TWINE_USERNAME",
    "TWINE_PASSWORD",
    "UV_PUBLISH_TOKEN",
    "PYPI_USERNAME",
    "PYPI_PASSWORD",
)

PYPROJECT_PATH = Path("pyproject.toml")
RECENT_CHANGES_PATH = Path("recent_changes.md")
MAIN_BRANCH = "master"
MAX_RECENT_RELEASES = 3

DRY_RUN = "--dry-run" in sys.argv

# optional CLI flags
CLEAN_ONLY = "--clean" in sys.argv
NO_CLEAN = "--no-clean" in sys.argv
UPLOAD_ONLY = "--upload-only" in sys.argv
SKIP_EXISTING = "--skip-existing" in sys.argv


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


def build_and_upload(
    repo="pypi", verbose=True, skip_existing=False, upload_only: bool = False
):
    """
    Build (optionally) and upload the existing dist/ artifacts with Twine.
    Set upload_only=True to reuse artifacts from a prior build stage.
    """
    dist_dir = Path("dist")
    if not upload_only:
        if not NO_CLEAN:
            clean_build_artifacts()

        ok, out = exec_cmd(
            "uv build", stream=True
        )  # or stream=False if you prefer quiet
        if not ok:
            return ok, out
    else:
        if not dist_dir.exists() or not any(dist_dir.iterdir()):
            return False, "dist/ is empty. Run without --upload-only first."

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


def _is_release_tag(tag: str) -> bool:
    """Accept tags like 1.2.3, 1.2.3a1, 1.2.3b2, 1.2.3rc3."""
    return bool(re.match(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$", tag or ""))


def _discover_last_release_tag(current_version: str) -> str | None:
    ok, out = read("git tag --list")
    if not ok:
        return None
    tags = [t.strip() for t in out.splitlines() if _is_release_tag(t.strip())]
    if not tags:
        return None
    if current_version in tags:
        return current_version
    ok, out = read("git tag --list --sort=-creatordate")
    if not ok:
        return None
    for line in out.splitlines():
        tag = line.strip()
        if tag in tags:
            return tag
    return None


def _generate_since_last_release_summary(current_version: str) -> tuple[str, str]:
    """
    Return (baseline_label, summary_text) using git history from the latest
    release-like tag to HEAD. If no tag exists, summarize all history.
    """
    baseline = _discover_last_release_tag(current_version)
    if baseline:
        rev_range = f"{baseline}..HEAD"
        baseline_label = baseline
    else:
        rev_range = "HEAD"
        baseline_label = "project start"

    ok, stat_out = read(f"git diff --shortstat {rev_range}")
    shortstat = stat_out.strip() if ok and stat_out.strip() else "No file-level changes."

    ok, files_out = read(f"git diff --name-only {rev_range}")
    files = [ln.strip() for ln in files_out.splitlines() if ln.strip()] if ok else []
    files_preview = ", ".join(files[:6])
    if len(files) > 6:
        files_preview += f", +{len(files) - 6} more"
    if not files_preview:
        files_preview = "No changed files."

    ok, log_out = read(f"git log --pretty=format:%s {rev_range}")
    subjects = [ln.strip() for ln in log_out.splitlines() if ln.strip()] if ok else []
    if subjects:
        bullets = "\n".join(f"- {s}" for s in subjects[:6])
        if len(subjects) > 6:
            bullets += f"\n- (+{len(subjects) - 6} more commits)"
    else:
        bullets = "- No commit subjects found."

    summary = (
        f"Since {baseline_label}:\n"
        f"- {shortstat}\n"
        f"- Files: {files_preview}\n"
        "Highlights:\n"
        f"{bullets}"
    )
    return baseline_label, summary


def update_recent_changes_file(
    *,
    new_version: str,
    summary: str,
    note: str = "",
    max_releases: int = MAX_RECENT_RELEASES,
) -> None:
    """
    Update recent_changes.md by prepending the current release notes and
    retaining only the latest `max_releases` sections.
    """
    today = datetime.now().date().isoformat()
    section_lines = [f"## {new_version} — {today}", "", summary.strip()]
    if note.strip():
        section_lines.extend(["", f"Note: {note.strip()}"])
    new_section = "\n".join(section_lines).strip()

    header = "# Recent Changes"
    existing_text = ""
    if RECENT_CHANGES_PATH.exists():
        existing_text = RECENT_CHANGES_PATH.read_text(encoding="utf-8")

    section_pattern = re.compile(r"(?ms)^## .+?(?=^## |\Z)")
    existing_sections = section_pattern.findall(existing_text)
    existing_sections = [s.strip() for s in existing_sections if s.strip()]

    # Remove any prior section for this same version.
    version_prefix = f"## {new_version} "
    existing_sections = [s for s in existing_sections if not s.startswith(version_prefix)]

    sections = [new_section] + existing_sections[: max(0, max_releases - 1)]
    body = "\n\n".join(sections).strip()

    RECENT_CHANGES_PATH.write_text(f"{header}\n\n{body}\n", encoding="utf-8")


# --- Ensure we're on the main branch ---
ok, current_branch = read("git rev-parse --abbrev-ref HEAD")
current_branch = current_branch.strip()
if current_branch != MAIN_BRANCH:
    print(f"⚠️  You are on '{current_branch}', not '{MAIN_BRANCH}'.")
    print(f"Please switch to '{MAIN_BRANCH}' before running this script.")
    sys.exit(1)

if CLEAN_ONLY:
    clean_build_artifacts()
    print("Build artifacts removed.")
    sys.exit(0)

if UPLOAD_ONLY:
    ok, _ = build_and_upload(
        skip_existing=SKIP_EXISTING,
        upload_only=True,
    )
    sys.exit(0 if ok else 1)

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
baseline_label, auto_summary = _generate_since_last_release_summary(version)

release_subject = f"Release {new_version}"
release_body_parts = [auto_summary]
if tplus.strip():
    release_body_parts.append(f"Note: {tplus.strip()}")
release_body = "\n\n".join(release_body_parts)

tmsg = f"{release_subject}\n\n{release_body}"

print(f"\nThe tag message for the new version will be:\n{tmsg}\n")
if DRY_RUN:
    print(f"[dry-run] Would set new version: {new_version}")
    print(f"[dry-run] Would update pyproject.toml")
    print(
        f"[dry-run] Would update {RECENT_CHANGES_PATH} "
        f"(retain last {MAX_RECENT_RELEASES} releases)"
    )
    print(f"[dry-run] Would commit and tag with message:\n\n{tmsg}\n")
    sys.exit(0)

if input(f"Commit and tag new version: {new_version}? [yN] ").lower() != "y":
    print("Cancelled.")
    sys.exit()

write_version(new_version)
update_recent_changes_file(
    new_version=new_version,
    summary=auto_summary,
    note=tplus,
    max_releases=MAX_RECENT_RELEASES,
)
# Skip pre-commit hooks for version bump commits to avoid interference
run(
    "git commit -a "
    f"-m {shlex.quote(release_subject)} "
    f"-m {shlex.quote(release_body)} "
    "--no-verify"
)
ok, version_info = read("git log --pretty=format:'%ai' -n 1")
tag_msg = (
    f"Tagged {new_version}\n"
    f"Created: {version_info.strip()}\n\n"
    f"{auto_summary}"
)
run(
    f"git tag -a -f {shlex.quote(new_version)} "
    f"-m {shlex.quote(tag_msg)}"
)

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

# Sync and push on master
if input(f"Pull --rebase and push '{MAIN_BRANCH}' to origin? [yN] ").lower() == "y":
    run(f"git pull --rebase origin {MAIN_BRANCH}")
    run(f"git push origin {MAIN_BRANCH}")
    run("git push origin --tags")

    if input("Upload to PyPI using uv publish? [yN] ").lower() == "y":
        build_and_upload()
else:
    print(f"Retained version locally on '{MAIN_BRANCH}': {version}")

if not DRY_RUN:
    run("uv pip install -e .")
