#!/usr/bin/env python3
import sys

if sys.version_info < (3, 11):
    print("❌ Tklr requires Python 3.11 or newer.")
    print(f"   You are using: Python {sys.version.split()[0]}")
    sys.exit(1)

from pathlib import Path
import os
from typing import Optional
from tklr.controller import Controller
from tklr.view import DynamicViewApp
from tklr.common import log_msg, display_messages
from tklr.tklr_env import TklrEnvironment


def initialize_database(path):
    import sqlite3

    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)"
    )
    conn.commit()
    conn.close()


def get_tklr_home() -> Path:
    # 1. Current working directory override (if config + db found)
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


env = TklrEnvironment()
env.ensure(init_db_fn=initialize_database)
config = env.config  # ← validated, corrected, comment-preserving config

print("Using config:", env.config_path)
print("Using database:", env.db_path)


def main():
    tklr_home = get_tklr_home()
    tklr_db = os.path.join(tklr_home, "tklr.db")
    controller = Controller(tklr_db)
    view = DynamicViewApp(controller)
    view.run()


if __name__ == "__main__":
    main()
