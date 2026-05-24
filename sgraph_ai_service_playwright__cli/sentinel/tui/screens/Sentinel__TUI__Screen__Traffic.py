# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Screen__Traffic
# Traffic surface: press g to replay the use-case corpus in-process through the real
# L1 + L2 and show the accuracy + latency report. Thin view layer over the pure
# render module + the injected generator (no mocks; tests inject a real generator).
# The run is synchronous (the corpus is small) — a worker would be used for a large
# corpus or a slow HTTP target.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base       import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Traffic__Render  import traffic_markup
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus           import Sentinel__Traffic__Corpus
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder  import Sentinel__Traffic__Report__Builder


class Sentinel__TUI__Screen__Traffic(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel Traffic'
    BINDINGS = [('g', 'run', 'Run'), ('r', 'reset', 'Reset')]

    def __init__(self, generator, corpus=None):
        super().__init__()
        self.generator = generator
        self.cases     = list((corpus or Sentinel__Traffic__Corpus()).cases())
        self.report    = None
        self.results   = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        self.query_one('#body', Static).update(traffic_markup(self.cases, self.report, self.results))

    def action_run(self) -> None:
        self.results = self.generator.run_local(self.cases)
        self.report  = Sentinel__Traffic__Report__Builder().build(self.results, mode='local')
        self._render()

    def action_reset(self) -> None:
        self.report  = None
        self.results = []
        self._render()
