import argparse
import io
import subprocess

from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

try:
    from tklr.list_colors import css_named_colors
except Exception:  # pragma: no cover - fallback for running from src/tklr
    from list_colors import css_named_colors


def _hex_to_luma(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def build_color_list(sort_by: str) -> list[tuple[str, str]]:
    colors = [(name, hex_value.upper()) for name, hex_value in css_named_colors.items()]
    if sort_by == "hex":
        return sorted(colors, key=lambda item: int(item[1].lstrip("#"), 16))
    return sorted(colors, key=lambda item: _hex_to_luma(item[1]))


def show_python_named_colors(sort_by: str) -> None:
    with subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE) as proc:
        with io.TextIOWrapper(proc.stdin, encoding="utf-8") as text_stream:
            console = Console(
                file=text_stream, force_terminal=True, color_system="truecolor"
            )
            table = Table(title=f"Python Named Colors (sorted by {sort_by})")
            table.add_column("Default Background")
            table.add_column("White Background")

            for name, hex_val in build_color_list(sort_by):
                default_text = Text(f"{name} {hex_val}", style=Style(color=hex_val))
                white_text = Text(
                    f"{name} {hex_val}", style=Style(color=hex_val, bgcolor="white")
                )
                table.add_row(default_text, white_text)

            console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sort",
        choices=("luma", "hex"),
        default="luma",
        help="Sort colors by perceived brightness (luma) or raw hex value.",
    )
    args = parser.parse_args()
    show_python_named_colors(args.sort)
