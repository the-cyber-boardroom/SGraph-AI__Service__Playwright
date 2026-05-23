# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Screen__Status
# Status / Deployed-code surface: locally-derivable reality + the exact materialised
# L1 engine. r refresh. Thin view layer over the pure render module + the source.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base     import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Status__Render import status_markup


class Sentinel__TUI__Screen__Status(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel Status'
    BINDINGS = [('r', 'refresh', 'Refresh')]

    def __init__(self, source, sink_label: str = ''):
        super().__init__()
        self.source     = source
        self.sink_label = sink_label

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()

    def action_refresh(self) -> None:
        status = self.source.status()
        self.query_one('#body', Static).update(status_markup(status, self.sink_label, self.source.engine_code()))
