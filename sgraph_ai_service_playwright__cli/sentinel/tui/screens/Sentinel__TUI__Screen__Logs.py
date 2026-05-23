# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Screen__Logs
# Logs surface: ↑/↓ select a record, enter → trace, esc → back, r refresh. Thin view
# layer over the pure render module + the injected source.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base   import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Logs__Render import logs_markup, trace_markup


class Sentinel__TUI__Screen__Logs(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel Logs'
    BINDINGS = [('r', 'refresh', 'Refresh'), ('up', 'up', 'Up'), ('down', 'down', 'Down'),
                ('enter', 'enter', 'Trace'), ('escape', 'back', 'Back')]

    def __init__(self, source, sink_label: str = ''):
        super().__init__()
        self.source     = source
        self.sink_label = sink_label
        self.records    = []
        self.index      = 0
        self.mode       = 'list'

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()

    def _render(self) -> None:
        if self.mode == 'trace' and self.records:
            markup = trace_markup(self.records[self.index])
        else:
            markup = logs_markup(self.records, self.sink_label, self.index)
        self.query_one('#body', Static).update(markup)

    def action_refresh(self) -> None:
        self.records = list(self.source.records())
        self.index   = min(self.index, max(0, len(self.records) - 1))
        self._render()

    def action_up(self) -> None:
        self.index = max(0, self.index - 1)
        self._render()

    def action_down(self) -> None:
        self.index = min(max(0, len(self.records) - 1), self.index + 1)
        self._render()

    def action_enter(self) -> None:
        self.mode = 'trace'
        self._render()

    def action_back(self) -> None:
        self.mode = 'list'
        self._render()
