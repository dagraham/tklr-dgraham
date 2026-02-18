from tklr.view import EditorScreen


def test_entry_height_has_practical_minimum():
    h = EditorScreen.compute_editor_entry_height(
        text="~ one line",
        usable_width=80,
        available_height=40,
    )
    assert h >= 4


def test_entry_height_respects_half_height_cap():
    h = EditorScreen.compute_editor_entry_height(
        text="~ " + ("very long " * 500),
        usable_width=20,
        available_height=24,
    )
    assert h == 12  # 50% cap


def test_entry_height_grows_for_wrapped_single_line():
    short = EditorScreen.compute_editor_entry_height(
        text="~ short",
        usable_width=40,
        available_height=40,
    )
    wrapped = EditorScreen.compute_editor_entry_height(
        text="~ " + ("x" * 180),
        usable_width=20,
        available_height=40,
    )
    assert wrapped > short


def test_entry_height_grows_with_multiline_text_before_cap():
    h = EditorScreen.compute_editor_entry_height(
        text="\n".join(
            [
                "~ subject",
                "@d one",
                "@d two",
                "@d three",
                "@d four",
            ]
        ),
        usable_width=80,
        available_height=40,
    )
    assert 4 < h < 20

