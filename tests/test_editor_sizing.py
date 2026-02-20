from types import SimpleNamespace

from tklr.view import DynamicViewApp, EditorScreen


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


class _DummyEvent:
    def __init__(self, key: str):
        self.key = key

    def stop(self) -> None:
        return None


def test_on_key_ignores_week_nav_when_modal_screen_active_left():
    calls = {"prev": 0, "next": 0}
    app = SimpleNamespace(
        view="weeks",
        screen=object(),  # modal/editor-like screen, not WeeksScreen
        action_previous_week=lambda: calls.__setitem__("prev", calls["prev"] + 1),
        action_next_week=lambda: calls.__setitem__("next", calls["next"] + 1),
    )

    DynamicViewApp.on_key(app, _DummyEvent("left"))

    assert calls["prev"] == 0
    assert calls["next"] == 0


def test_on_key_ignores_week_nav_when_modal_screen_active_right():
    calls = {"prev": 0, "next": 0}
    app = SimpleNamespace(
        view="jots",
        screen=object(),  # modal/editor-like screen, not WeeksScreen
        action_previous_week=lambda: calls.__setitem__("prev", calls["prev"] + 1),
        action_next_week=lambda: calls.__setitem__("next", calls["next"] + 1),
    )

    DynamicViewApp.on_key(app, _DummyEvent("right"))

    assert calls["prev"] == 0
    assert calls["next"] == 0
