# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui components: Debug__Panel
# A reusable Textual widget: the under-the-hood debug feed pinned to the right of any
# screen. It is a scroll container holding one Static; refresh_log() re-renders the
# injected Debug__Event_Log via the pure Debug__Panel__Render and pins the view to the
# newest line. Any TUI in the sg aws ecosystem drops one of these in and shares its
# event log with a source/service — that is the whole "component-first" point.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.containers import VerticalScroll
from textual.widgets    import Static

from sgraph_ai_service_playwright__cli.tui.debug.Debug__Panel__Render import debug_panel_markup


class Debug__Panel(VerticalScroll):
    DEFAULT_CSS = """
    Debug__Panel       { width: 52; min-width: 28; border-left: solid $panel-darken-2; padding: 0 1; background: $panel; }
    Debug__Panel.-hidden { display: none; }
    """

    def __init__(self, event_log, **kwargs):
        super().__init__(**kwargs)
        self.event_log = event_log

    def compose(self):
        yield Static('', id='debug-body')

    def refresh_log(self) -> None:
        self.query_one('#debug-body', Static).update(debug_panel_markup(self.event_log))
        self.scroll_end(animate=False)
