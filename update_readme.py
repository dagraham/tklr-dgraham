import sys
from pathlib import Path

# Add src/ to sys.path so you can import tklr_env
sys.path.insert(0, str(Path(__file__).resolve().parent / "src/tklr"))
# print(f"{sys.path = }")
from tklr_env import TklrConfig, CONFIG_TEMPLATE
from jinja2 import Template

README_PATH = Path("README.md")


def render_config_block() -> str:
    config = TklrConfig()
    template = Template(CONFIG_TEMPLATE)
    rendered = template.render(**config.model_dump()).strip()
    return f"```toml\n{rendered}\n```"


def update_readme():
    readme = README_PATH.read_text()
    start = readme.find("<!-- BEGIN CONFIG -->")
    end = readme.find("<!-- END CONFIG -->")

    if start == -1 or end == -1:
        raise ValueError(
            "README.md must include <!-- BEGIN CONFIG --> and <!-- END CONFIG -->"
        )

    before = readme[:start]
    after = readme[end + len("<!-- END CONFIG -->") :]
    new_block = (
        f"<!-- BEGIN CONFIG -->\n\n{render_config_block()}\n\n<!-- END CONFIG -->"
    )

    README_PATH.write_text(before + new_block + after)
    print("✅ Updated config block in README.md")


if __name__ == "__main__":
    update_readme()
