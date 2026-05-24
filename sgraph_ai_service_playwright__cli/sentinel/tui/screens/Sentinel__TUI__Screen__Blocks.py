# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Screen__Blocks
# Blocks surface: blocked requests grouped by reason/rule. r refresh. Thin view layer.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base     import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Blocks__Render import blocks_markup


class Sentinel__TUI__Screen__Blocks(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel Blocks'
    BINDINGS = [('r', 'refresh', 'Refresh')]

    def __init__(self, source):
        super().__init__()
        self.source = source

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()

    def action_refresh(self) -> None:
        groups = self.source.block_groups()
        total  = sum(g.count for g in groups)
        self.query_one('#body', Static).update(blocks_markup(groups, total))
