import click
from rich.table import Table
from rich.console import Console

# from rich.color import Color
from rich.style import Style
from colorsys import rgb_to_hls

import subprocess

import io

try:
    from .named_colors import css_named_colors
except Exception:  # pragma: no cover - fallback for running from src/tklr
    from named_colors import css_named_colors


def sort_colors(
    color_dict: dict[str, str], method: str = "name"
) -> list[tuple[str, str]]:
    if method == "hue":

        def hex_to_hue(hex_value: str):
            hex_value = hex_value.lstrip("#")
            r, g, b = tuple(int(hex_value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
            h, _, _ = rgb_to_hls(r, g, b)
            return h

        return sorted(color_dict.items(), key=lambda item: hex_to_hue(item[1]))
    return sorted(color_dict.items())  # default name


def get_contrasting_text_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 128 else "white"



@click.command()
@click.option(
    "--sort",
    type=click.Choice(["name", "hue"], case_sensitive=False),
    default="name",
    help="Sort colors name or by hue",
)
def show_colors(sort):
    with subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE) as proc:
        # Wrap binary stdin as a text stream
        with io.TextIOWrapper(proc.stdin, encoding="utf-8") as text_stream:
            console = Console(
                file=text_stream, force_terminal=True, color_system="truecolor"
            )

            table = Table(title=f"CSS Named Colors (--sort {sort})")
            table.add_column("Color Name")
            table.add_column("Hex Value")

            for name, hex_val in sort_colors(css_named_colors, sort):
                name_style = Style(color=hex_val)
                hex_style = Style(
                    color=get_contrasting_text_color(hex_val), bgcolor=hex_val
                )
                table.add_row(f"[{hex_val}]{name}[/]", f"[{hex_style}]{hex_val}[/]")

            console.print(table)


if __name__ == "__main__":
    show_colors()
