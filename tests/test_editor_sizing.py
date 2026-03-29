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


class _DummyTextArea:
    def __init__(self):
        self.text = ""
        self.focused = False
        self.cursor_location = (0, 0)

    def focus(self) -> None:
        self.focused = True


class _DummyApp:
    def __init__(self):
        self.notifications = []

    def notify(self, message: str, **kwargs) -> None:
        self.notifications.append((message, kwargs))


def test_create_use_registers_existing_u_token_without_cursor_dependency(
    test_controller,
):
    screen = EditorScreen(test_controller, seed_text="~ note about plants")
    screen.entry_text = "~ note about plants @u garden"
    screen._text = _DummyTextArea()
    screen.app = _DummyApp()
    screen.item.relative_tokens = [{"k": "u", "token": "@u garden", "s": 20, "e": 29}]
    screen._cursor_abs_index = lambda: 0
    screen._token_at = lambda idx: None
    screen._live_parse_and_feedback = lambda final=False, refresh_from_widget=False: (
        None
    )

    screen.action_create_use()

    use = test_controller.lookup_use("garden")
    assert use is not None
    assert use["name"] == "garden"
    assert screen.entry_text.endswith("@u garden")
    assert screen._text.text == screen.entry_text
    assert any('Use "garden" created.' in msg for msg, _ in screen.app.notifications)


def test_create_use_replaces_existing_u_token_with_canonical_name(test_controller):
    test_controller.add_use("Garden", "")
    screen = EditorScreen(test_controller, seed_text="~ note @u garden")
    screen.entry_text = "~ note @u garden"
    screen._text = _DummyTextArea()
    screen.app = _DummyApp()
    screen.item.relative_tokens = [{"k": "u", "token": "@u garden", "s": 7, "e": 16}]
    screen._cursor_abs_index = lambda: 0
    screen._token_at = lambda idx: None
    screen._live_parse_and_feedback = lambda final=False, refresh_from_widget=False: (
        None
    )

    screen.action_create_use()

    assert screen.entry_text == "~ note @u Garden"
    assert screen._text.text == "~ note @u Garden"
    assert any('Use "Garden" created.' in msg for msg, _ in screen.app.notifications)


def test_create_use_requires_existing_u_token_when_absent(test_controller):
    screen = EditorScreen(test_controller, seed_text="~ note without use")
    screen.entry_text = "~ note without use"
    screen._text = _DummyTextArea()
    screen.app = _DummyApp()
    screen.item.relative_tokens = []
    screen._cursor_abs_index = lambda: len(screen.entry_text)
    screen._token_at = lambda idx: None
    screen._live_parse_and_feedback = lambda final=False, refresh_from_widget=False: (
        None
    )

    screen.action_create_use()

    assert test_controller.lookup_use("use") is None
    assert any(
        "This reminder has no @u token." in msg for msg, _ in screen.app.notifications
    )
