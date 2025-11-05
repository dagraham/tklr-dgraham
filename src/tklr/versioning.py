# tklr/versioning.py
from importlib.metadata import version as pkg_version, PackageNotFoundError


def get_version() -> str:
    try:
        # Installed package (wheel / editable install)
        return pkg_version("tklr-dgraham")
    except PackageNotFoundError:
        # Dev checkout fallback: read pyproject.toml
        import tomllib, pathlib

        # adjust the path if your layout differs
        root = pathlib.Path(__file__).resolve().parents[2]
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        return data["project"]["version"]
