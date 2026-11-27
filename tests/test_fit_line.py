from rich.text import Text

from tklr.view import fit_line


def test_short_line_unchanged():
    line = Text("pay bills 𝕣")
    assert fit_line(line, 40).plain == "pay bills 𝕣"


def test_long_line_gets_ellipsis_and_keeps_flags():
    line = Text(" b   58  +0d pay the quarterly estimated tax bill 𝕣𝕘")
    fitted = fit_line(line, 30)
    assert fitted.cell_len == 30
    assert fitted.plain.endswith("… 𝕣𝕘")
    assert fitted.plain.startswith(" b   58  +0d pay")


def test_long_line_without_flags():
    fitted = fit_line(Text("a" * 50), 20)
    assert fitted.plain == "a" * 19 + "…"


def test_styles_survive():
    line = Text.from_markup("[red]" + "x" * 40 + "[/red] 𝕣")
    fitted = fit_line(line, 20)
    assert fitted.plain == "x" * 17 + "… 𝕣"
    assert any(str(span.style) == "red" for span in fitted.spans)


def test_flags_dropped_when_too_narrow():
    fitted = fit_line(Text("abcdefghij 𝕒𝕘𝕠𝕣"), 6)
    assert fitted.plain == "abcde…"
