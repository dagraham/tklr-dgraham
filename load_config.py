# load_config.py

import tomllib  # Python 3.11+ (use `import tomli` for earlier versions)
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path

CONFIG_FILE = Path("config.toml")


class AppSettings(BaseModel):
    theme: str = Field("light", description="Theme must be 'light' or 'dark'")
    refresh_rate: int = Field(
        ..., ge=1, description="How often the UI should refresh (in seconds)"
    )
    plugins: list[str] = Field(default_factory=list)


class Config(BaseModel):
    app: AppSettings


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_FILE}")

    with CONFIG_FILE.open("rb") as f:
        raw = tomllib.load(f)

    return Config(**raw)


if __name__ == "__main__":
    try:
        config = load_config()
        print("✅ Config loaded successfully!")
        print(config.model_dump())
    except ValidationError as e:
        print("❌ Validation error in config.toml:")
        print(e)
    except Exception as ex:
        print(f"❌ Error: {ex}")
