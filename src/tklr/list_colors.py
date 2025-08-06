import click
from rich.table import Table
from rich.console import Console

# from rich.color import Color
from rich.style import Style
from colorsys import rgb_to_hls

import subprocess

import io

#

css_named_colors = {
    "aliceblue": "#F0F8FF",
    "antiquewhite": "#FAEBD7",
    "aqua": "#00FFFF",
    "aquamarine": "#7FFFD4",
    "azure": "#F0FFFF",
    "beige": "#F5F5DC",
    "bisque": "#FFE4C4",
    "black": "#000000",
    "blue": "#0000FF",
    "blueviolet": "#8A2BE2",
    "brown": "#A52A2A",
    "burlywood": "#DEB887",
    "cadetblue": "#5F9EA0",
    "chartreuse": "#7FFF00",
    "chocolate": "#D2691E",
    "coral": "#FF7F50",
    "cornflowerblue": "#6495ED",
    "cornsilk": "#FFF8DC",
    "crimson": "#DC143C",
    "cyan": "#00FFFF",
    "darkblue": "#00008B",
    "darkcyan": "#008B8B",
    "darkgoldenrod": "#B8860B",
    "darkgray": "#A9A9A9",
    "darkgreen": "#006400",
    "darkkhaki": "#BDB76B",
    "darkmagenta": "#8B008B",
    "darkolivegreen": "#556B2F",
    "darkorange": "#FF8C00",
    "darkorchid": "#9932CC",
    "darkred": "#8B0000",
    "darksalmon": "#E9967A",
    "darkseagreen": "#8FBC8F",
    "darkslateblue": "#483D8B",
    "darkslategray": "#2F4F4F",
    "darkturquoise": "#00CED1",
    "darkviolet": "#9400D3",
    "deeppink": "#FF1493",
    "deepskyblue": "#00BFFF",
    "dimgray": "#696969",
    "dodgerblue": "#1E90FF",
    "firebrick": "#B22222",
    "floralwhite": "#FFFAF0",
    "forestgreen": "#228B22",
    "fuchsia": "#FF00FF",
    "gainsboro": "#DCDCDC",
    "ghostwhite": "#F8F8FF",
    "gold": "#FFD700",
    "goldenrod": "#DAA520",
    "gray": "#808080",
    "green": "#008000",
    "greenyellow": "#ADFF2F",
    "honeydew": "#F0FFF0",
    "hotpink": "#FF69B4",
    "indianred": "#CD5C5C",
    "indigo": "#4B0082",
    "ivory": "#FFFFF0",
    "khaki": "#F0E68C",
    "lavender": "#E6E6FA",
    "lavenderblush": "#FFF0F5",
    "lawngreen": "#7CFC00",
    "lemonchiffon": "#FFFACD",
    "lightblue": "#ADD8E6",
    "lightcoral": "#F08080",
    "lightcyan": "#E0FFFF",
    "lightgoldenrodyellow": "#FAFAD2",
    "lightgray": "#D3D3D3",
    "lightgreen": "#90EE90",
    "lightpink": "#FFB6C1",
    "lightsalmon": "#FFA07A",
    "lightseagreen": "#20B2AA",
    "lightskyblue": "#87CEFA",
    "lightslategray": "#778899",
    "lightsteelblue": "#B0C4DE",
    "lightyellow": "#FFFFE0",
    "lime": "#00FF00",
    "limegreen": "#32CD32",
    "linen": "#FAF0E6",
    "magenta": "#FF00FF",
    "maroon": "#800000",
    "mediumaquamarine": "#66CDAA",
    "mediumblue": "#0000CD",
    "mediumorchid": "#BA55D3",
    "mediumpurple": "#9370DB",
    "mediumseagreen": "#3CB371",
    "mediumslateblue": "#7B68EE",
    "mediumspringgreen": "#00FA9A",
    "mediumturquoise": "#48D1CC",
    "mediumvioletred": "#C71585",
    "midnightblue": "#191970",
    "mintcream": "#F5FFFA",
    "mistyrose": "#FFE4E1",
    "moccasin": "#FFE4B5",
    "navajowhite": "#FFDEAD",
    "navy": "#000080",
    "oldlace": "#FDF5E6",
    "olive": "#808000",
    "olivedrab": "#6B8E23",
    "orange": "#FFA500",
    "orangered": "#FF4500",
    "orchid": "#DA70D6",
    "palegoldenrod": "#EEE8AA",
    "palegreen": "#98FB98",
    "paleturquoise": "#AFEEEE",
    "palevioletred": "#DB7093",
    "papayawhip": "#FFEFD5",
    "peachpuff": "#FFDAB9",
    "peru": "#CD853F",
    "pink": "#FFC0CB",
    "plum": "#DDA0DD",
    "powderblue": "#B0E0E6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#FF0000",
    "rosybrown": "#BC8F8F",
    "royalblue": "#4169E1",
    "saddlebrown": "#8B4513",
    "salmon": "#FA8072",
    "sandybrown": "#F4A460",
    "seagreen": "#2E8B57",
    "seashell": "#FFF5EE",
    "sienna": "#A0522D",
    "silver": "#C0C0C0",
    "skyblue": "#87CEEB",
    "slateblue": "#6A5ACD",
    "slategray": "#708090",
    "snow": "#FFFAFA",
    "springgreen": "#00FF7F",
    "steelblue": "#4682B4",
    "tan": "#D2B48C",
    "teal": "#008080",
    "thistle": "#D8BFD8",
    "tomato": "#FF6347",
    "turquoise": "#40E0D0",
    "violet": "#EE82EE",
    "wheat": "#F5DEB3",
    "white": "#FFFFFF",
    "whitesmoke": "#F5F5F5",
    "yellow": "#FFFF00",
    "yellowgreen": "#9ACD32",
}


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


# @click.command()
# @click.option(
#     "--sort",
#     type=click.Choice(["name", "hue"], case_sensitive=False),
#     default="name",
#     help="Sort colors name or by hue",
# )
# def show_colors(sort):
#     console = Console(record=True)
#     table = Table(title=f"CSS Named Colors (--sort {sort})")
#     table.add_column("Color Name")
#     table.add_column("Hex Value")
#
#     for name, hex_val in sort_colors(css_named_colors, sort):
#         name_style = Style(color=hex_val)
#         hex_style = Style(color=get_contrasting_text_color(hex_val), bgcolor=hex_val)
#         table.add_row(f"[{hex_val}]{name}[/]", f"[{hex_style}]{hex_val}[/]")
#
#     console.print(table)
#     output = console.export_text()
#     click.echo_via_pager(output)


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
