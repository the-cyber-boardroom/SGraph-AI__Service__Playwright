# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Deployment
# Screen 1 (Deployment Reality) — the first exploratory Textual screen. Thin view
# layer (framework carve-out from Type_Safe, like routes over Fast_API__Routes): it
# polls the injected data source, drops the pure deployment_markup() into a Static,
# and refreshes on a timer. All content/logic lives in the render module + the T1
# data layer; this class only wires Textual to them.
#
# Construct with an injected SG_Edge__TUI__Data_Source (tests pass an in-memory
# one — no mocks). refresh_seconds=0 disables the timer (tests drive refresh by key).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Deployment__Render          import deployment_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS


class SG_Edge__TUI__Screen__Deployment(App):
    TITLE    = 'SG/Edge Deployment Reality'
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
        self.query_one('#body', Static).update(deployment_markup(self.snapshot))

    def action_refresh(self) -> None:
        self.refresh_snapshot()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
