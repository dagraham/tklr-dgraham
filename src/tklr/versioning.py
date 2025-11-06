# src/tklr/versioning.py
from importlib.metadata import (
    version as _version,
    PackageNotFoundError,
    packages_distributions,
)


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
