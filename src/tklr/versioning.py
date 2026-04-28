# src/tklr/versioning.py
from importlib.metadata import (
    version as _version,
    PackageNotFoundError,
    packages_distributions,
)

_PYPI_PACKAGE = "tklr-dgraham"
_PYPI_TIMEOUT = 3.0


def fetch_latest_pypi_version(
    package: str = _PYPI_PACKAGE,
    timeout: float = _PYPI_TIMEOUT,
) -> str | None:
    """Return the latest published version string from PyPI, or None on any failure."""
    import json
    import os
    import ssl
    import urllib.request

    if os.environ.get("TKLR_SKIP_UPDATE_CHECK"):
        return None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    try:
        url = f"https://pypi.org/pypi/{package}/json"
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            payload = json.load(resp)
        return (payload.get("info") or {}).get("version") or None
    except Exception:
        return None


def get_version() -> str:
    # Map package → distribution(s), then pick the first match
    dist_name = next(iter(packages_distributions().get("tklr", [])), "tklr-dgraham")
    try:
        return _version(dist_name)
    except PackageNotFoundError:
        # Dev checkout fallback: read from pyproject.toml
        import tomllib
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        return data["project"]["version"]
