# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Inspector
# Standalone Field Lineage Inspector — one CF log line walked through every field
# (raw → transformed). Thin view layer: polls the source for one record and drops the
# pure inspector_markup() into a Static. Construct with an injected data source + the
# file key + line index (tests pass an in-memory source — no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Inspector__Render import inspector_markup


class CF_TUI__Screen__Inspector(App):
    TITLE    = 'CF Field Lineage'
    BINDINGS = [('q', 'leave',   'Quit'),
                ('r', 'refresh', 'Refresh')]

    def __init__(self, source, key : str = '', line_index : int = 0):
        super().__init__()
        self.source     = source
        self.key        = key
        self.line_index = line_index
        self.record     = None
        self.exited     = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_record()

    def refresh_record(self) -> None:
        self.record = self.source.read_record(self.key, self.line_index)
        self.query_one('#body', Static).update(inspector_markup(self.record))

    def action_refresh(self) -> None:
        self.refresh_record()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
