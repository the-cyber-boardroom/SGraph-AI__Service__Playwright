# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Arch
# Deployed Architecture screen — the live CF/S3/CloudWatch wiring at a glance. Thin
# view layer: polls the injected arch source and drops the pure arch_markup() into a
# Static. Construct with an injected CF_TUI__Arch_Source (tests pass one over fake
# clients — no AWS, no mocks). refresh_seconds=0 disables the timer.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Arch__Render import arch_markup
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import TUI_REFRESH_SECONDS


class CF_TUI__Screen__Arch(App):
    TITLE    = 'CF Deployed Architecture'
    BINDINGS = [('q', 'leave',   'Quit'),
                ('r', 'refresh', 'Refresh')]

    def __init__(self, source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.refresh_seconds = refresh_seconds
        self.snapshot        = None
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
        self.snapshot = self.source.snapshot()
        self.query_one('#body', Static).update(arch_markup(self.snapshot))

    def action_refresh(self) -> None:
        self.refresh_snapshot()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
