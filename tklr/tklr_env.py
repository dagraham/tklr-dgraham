from pathlib import Path
import os
from typing import Optional
from tomlkit import parse, dumps
from tomlkit.exceptions import TOMLKitError
from pydantic import BaseModel, Field, ValidationError

# ─── Default content for a new config.toml ─────────────────────────────────────
DEFAULT_CONFIG = """\
# Tklr Configuration File

[ui]
# Theme can be 'light' or 'dark'
theme = "dark"
# Whether to show completed tasks
show_completed = true

[paths]
# Relative or absolute path to the database file
db = "data.sqlite3"
"""


# ─── Pydantic Schema for Config Validation ─────────────────────────────────────
class UIConfig(BaseModel):
    theme: str = Field("dark", pattern="^(dark|light)$")
    show_completed: bool = True


class PathsConfig(BaseModel):
    db: str = "data.sqlite3"


class TklrConfig(BaseModel):
    ui: UIConfig
    paths: PathsConfig


# ─── Main Tklr Environment Manager ─────────────────────────────────────────────
class TklrEnvironment:
    def __init__(self):
        self._home = self._resolve_home()
        self._config: Optional[TklrConfig] = None

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
        self.home.mkdir(parents=True, exist_ok=True)

        if init_config and not self.config_path.exists():
            self.config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")

        if init_db_fn and not self.db_path.exists():
            init_db_fn(self.db_path)

    def load_config(self) -> TklrConfig:
        from tomlkit import parse, dumps
        from tomlkit.exceptions import TOMLKitError
        from pydantic import ValidationError

        try:
            raw_text = self.config_path.read_text(encoding="utf-8")
            doc = parse(raw_text)
        except TOMLKitError as e:
            print(f"❌ Syntax error in config file: {self.config_path}")
            print(f"   {e.__class__.__name__}: {e}")

            # Step 1: Backup the broken config
            backup_path = self.config_path.with_suffix(".toml.bak")
            self.config_path.rename(backup_path)
            print(f"🔁 Backed up invalid config to: {backup_path}")

            # Step 2: Restore default config
            self.config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
            print(f"✅ Restored default config to: {self.config_path}")

            # Step 3: Parse defaults and continue
            raw_text = DEFAULT_CONFIG
            doc = parse(raw_text)

        # Step 4: Validate and correct
        try:
            model = TklrConfig.model_validate(doc)
        except ValidationError as e:
            print(f"⚠️ Found validation errors in {self.config_path}:")
            for err in e.errors():
                loc = " → ".join(str(part) for part in err["loc"])
                msg = err["msg"]
                print(f"  - {loc}: {msg}")

            model = TklrConfig()

            if isinstance(doc.get("ui"), dict):
                ui_doc = doc["ui"]
                if isinstance(ui_doc.get("theme"), str) and ui_doc["theme"] in (
                    "dark",
                    "light",
                ):
                    model.ui.theme = ui_doc["theme"]
                if isinstance(ui_doc.get("show_completed"), bool):
                    model.ui.show_completed = ui_doc["show_completed"]

            if isinstance(doc.get("paths"), dict):
                paths_doc = doc["paths"]
                if isinstance(paths_doc.get("db"), str):
                    model.paths.db = paths_doc["db"]

        # Step 5: Resave corrected config
        doc["ui"]["theme"] = model.ui.theme
        doc["ui"]["show_completed"] = model.ui.show_completed
        doc["paths"]["db"] = model.paths.db

        new_text = dumps(doc)
        if new_text != raw_text:
            self.config_path.write_text(new_text, encoding="utf-8")
            print(f"✅ Corrected config written to: {self.config_path}")

        self._config = model
        return model

    @property
    def config(self) -> TklrConfig:
        if self._config is None:
            return self.load_config()
        return self._config

    def _resolve_home(self) -> Path:
        cwd = Path.cwd()
        if (cwd / "config.toml").exists() and (cwd / "data.sqlite3").exists():
            return cwd

        env_home = os.getenv("TKLR_HOME")
        if env_home:
            return Path(env_home).expanduser()

        xdg_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_home:
            return Path(xdg_home).expanduser() / "tklr"
        else:
            return Path.home() / ".config" / "tklr"
