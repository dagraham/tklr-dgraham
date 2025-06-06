from pathlib import Path
import os
from typing import Optional

DEFAULT_CONFIG = """\
# Tklr Configuration File

[ui]
# Theme can be 'light' or 'dark'
theme = "dark"
show_completed = true

[paths]
# Relative or absolute path to the database file
db = "data.sqlite3"
"""


class TklrEnvironment:
    def __init__(self):
        self._home = self._resolve_home()

    @property
    def home(self) -> Path:
        return self._home

    @property
    def config_path(self) -> Path:
        return self.home / "config.toml"

    @property
    def db_path(self) -> Path:
        return self.home / "tklr.db"

    def ensure(self, init_config: bool = True, init_db_fn: Optional[callable] = None):
        """Ensure the directory and (optionally) config/db files exist."""
        self.home.mkdir(parents=True, exist_ok=True)

        if init_config and not self.config_path.exists():
            self.config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")

        if init_db_fn and not self.db_path.exists():
            init_db_fn(self.db_path)

    def _resolve_home(self) -> Path:
        # 1. Check current working directory for override
        cwd = Path.cwd()
        if (cwd / "config.toml").exists() and (cwd / "tklr.db").exists():
            return cwd

        # 2. TKLR_HOME environment variable
        env_home = os.getenv("TKLR_HOME")
        if env_home:
            return Path(env_home).expanduser()

        # 3. XDG_CONFIG_HOME or fallback to ~/.config/tklr
        xdg_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_home:
            return Path(xdg_home).expanduser() / "tklr"
        else:
            return Path.home() / ".config" / "tklr"
