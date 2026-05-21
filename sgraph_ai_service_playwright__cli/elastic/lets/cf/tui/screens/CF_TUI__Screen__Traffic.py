# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Traffic
# Screen 5 (Traffic Reality) — the first exploratory CF-logs Textual screen. Thin
# view layer (framework carve-out from Type_Safe, like routes over Fast_API__Routes):
# it polls the injected data source, drops the pure traffic_markup() into a Static,
# and refreshes on a timer. All content/logic lives in the render module + the data
# layer; this class only wires Textual to them.
#
# Construct with an injected CF_TUI__Data_Source (tests pass an in-memory one — no
# mocks). refresh_seconds=0 disables the timer (tests drive refresh by key).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Traffic__Render import traffic_markup
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Card      import CF_TUI__Card
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import TUI_REFRESH_SECONDS


class CF_TUI__Screen__Traffic(App):
    TITLE    = 'CF Traffic Reality'
    BINDINGS = [('q', 'leave',   'Quit'),
                ('r', 'refresh', 'Refresh'),
                ('e', 'export',  'Export card')]

    def __init__(self, source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.refresh_seconds = refresh_seconds
        self.snapshot        = None
        self.exported_path   = ''
        self.exited          = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_snapshot()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.refresh_snapshot)

    def refresh_snapshot(self) -> None:
        self.snapshot = self.source.traffic_snapshot()
        self.query_one('#body', Static).update(traffic_markup(self.snapshot))

    def action_refresh(self) -> None:
        self.refresh_snapshot()

    def action_export(self) -> None:                                                 # picomon-style: write the ASCII card next to the cwd
        if self.snapshot is None:
            self.refresh_snapshot()
        path = 'cf-traffic-card.txt'
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(CF_TUI__Card().render(self.snapshot))
        self.exported_path = path

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
