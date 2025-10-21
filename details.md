```python
    def action_show_next(self):
        self.view = "next"
        self.set_afill(self.view)
        details = self.controller.get_next()
        self.set_afill(details, "action_show_next")

        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(FullScreenList(details, footer))
```

```python
class FullScreenList(SearchableScreen):
    """Reusable full-screen list for Last, Next, and Find views."""

    def __init__(
        self,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        if details:
            self.title = details[0]
            self.header = details[1] if len(details) > 1 else ""
            self.lines = details[2:] if len(details) > 2 else []
        else:
            self.title, self.header, self.lines = "Untitled", "", []
        self.footer_content = footer_content
        self.list_with_details: ListWithDetails | None = None

    # let global search target the currently-focused list
    def get_search_target(self):
        if not self.list_with_details:
            return None
        # if details is open, search/scroll that; otherwise main list
        return (
            self.list_with_details._details
            if self.list_with_details.has_details_open()
            else self.list_with_details._main
        )

    def compose(self) -> ComposeResult:
        yield Static(self.title, id="scroll_title", expand=True, classes="title-class")
        if self.header:
            yield Static(
                self.header, id="scroll_header", expand=True, classes="header-class"
            )
        self.list_with_details = ListWithDetails(id="list")
        # self.list_view = ListWithDetails(id="list")
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(view_name="next")  # or 'last' / 'find'
        )

        yield self.list_with_details
        yield Static(self.footer_content, id="custom_footer")

    def on_mount(self) -> None:
        if self.list_with_details:
            self.list_with_details.update_list(self.lines)

    # Called by DynamicViewApp.on_key -> screen.show_details_for_tag(tag)
    def show_details_for_tag(self, tag: str) -> None:
        app = self.app  # DynamicViewApp
        parts = app.controller.process_tag(
            tag,
            app.view,
            getattr(app, "selected_week", (0, 0)),  # ignored for these views
        )
        if not parts:
            return
        title, lines = parts[0], parts[1:]
        meta = getattr(self.app.controller, "_last_details_meta", None) or {}
        if self.list_with_details:
            self.list_with_details.show_details(title, lines, meta)
```

```python

class SearchableScreen(Screen):
    """Base class for screens that support search on a list widget."""

    def get_search_target(self) -> ScrollableList:
        """Return the ScrollableList to search.
        Default: the '#list' widget, so WeeksScreen keeps working.
        AgendaScreen will override this to point at its active pane.
        """
        return self.query_one("#list", ScrollableList)

    def perform_search(self, term: str):
        try:
            target = self.get_search_target()
            target.set_search_term(term)
            target.refresh()
        except NoMatches:
            pass

    def clear_search(self):
        try:
            target = self.get_search_target()
            target.clear_search()
            target.refresh()
        except NoMatches:
            pass

    def scroll_to_next_match(self):
        try:
            target = self.get_search_target()
            y = target.scroll_offset.y
            nxt = next((i for i in target.matches if i > y), None)
            if nxt is not None:
                target.scroll_to(0, nxt)
                target.refresh()
        except NoMatches:
            pass

    def scroll_to_previous_match(self):
        try:
            target = self.get_search_target()
            y = target.scroll_offset.y
            prv = next((i for i in reversed(target.matches) if i < y), None)
            if prv is not None:
                target.scroll_to(0, prv)
                target.refresh()
        except NoMatches:
            pass
```

```python

nnn

```
