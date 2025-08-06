import click
from rich import print
import subprocess
import io
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# from rich.console import Console
# from rich.table import Table


# @click.command()
# def show_agenda():
#     console = Console(record=True)  # Enable recording
#
#     table = Table(title="Agenda")
#     table.add_column("Time")
#     table.add_column("Event")
#     table.add_row("[bold]12–1pm[/bold]", "Lunch")
#     table.add_row("3–4pm", "Meeting with Sam")
#
#     console.print(table)
#
#     # Capture the output and send it to a pager
#     output = console.export_text()
#     click.echo_via_pager(output)
#
#
# if __name__ == "__main__":
#     show_agenda()
#


# @click.command()
# def show():
#     # Generate a long output
#     lines = [f"Line [bold yellow]{i}[/]" for i in range(1, 201)]
#     output = "\n".join(lines)
#
#     # Display through pager (e.g., less)
#     # click.echo_via_pager(output)
#     print(output)
#
#
# if __name__ == "__main__":
#     show()

lines = [f"Line [bold yellow]{i}[/]" for i in range(1, 201)]
output = "\n".join(lines)


@click.command()
def demo():
    with subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE) as proc:
        with io.TextIOWrapper(proc.stdin, encoding="utf-8") as stream:
            console = Console(
                file=stream, force_terminal=True, color_system="truecolor"
            )

            console.print("[bold magenta]Hello from Rich![/bold magenta]")
            console.print(Panel("This is a panel in a pager."))
            console.print(Markdown("# Markdown\n- in a pager\n- with colors!"))
            console.print(output)


if __name__ == "__main__":
    demo()
