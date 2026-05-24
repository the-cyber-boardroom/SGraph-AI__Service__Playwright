# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Screen__Rules
# Rules surface: ↑/↓ select, enter → detail, esc → back, r refresh. Thin view layer —
# all content lives in the pure render module; this only wires Textual to the source.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base    import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Rules__Render import rules_markup, rule_detail_markup


class Sentinel__TUI__Screen__Rules(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel Rules'
    BINDINGS = [('r', 'refresh', 'Refresh'), ('up', 'up', 'Up'), ('down', 'down', 'Down'),
                ('enter', 'enter', 'Detail'), ('escape', 'back', 'Back')]

    def __init__(self, source):
        super().__init__()
        self.source   = source
        self.rules    = []
        self.index    = 0
        self.mode     = 'list'

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()

    def _render(self) -> None:
        if self.mode == 'detail' and self.rules:
            markup = rule_detail_markup(self.rules[self.index])
        else:
            markup = rules_markup(self.rules, self.index)
        self.query_one('#body', Static).update(markup)

    def action_refresh(self) -> None:
        self.rules = list(self.source.rules())
        self.index = min(self.index, max(0, len(self.rules) - 1))
        self._render()

    def action_up(self) -> None:
        self.index = max(0, self.index - 1)
        self._render()

    def action_down(self) -> None:
        self.index = min(max(0, len(self.rules) - 1), self.index + 1)
        self._render()

    def action_enter(self) -> None:
        self.mode = 'detail'
        self._render()

    def action_back(self) -> None:
        self.mode = 'list'
        self._render()
