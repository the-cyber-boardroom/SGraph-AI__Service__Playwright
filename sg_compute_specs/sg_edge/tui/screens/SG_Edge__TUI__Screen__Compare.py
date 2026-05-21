# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Compare
# Screen 3 (Local vs Edge) — the highest-value exploratory screen. Unlike the other
# screens it reads TWO sources at once (a local source + an AWS source), diffs them,
# and renders drift. Thin view layer: it fetches both snapshots, calls the pure
# compare_markup(), and drops it into a Static. q quit / r refresh.
#
# Construct with two injected SG_Edge__TUI__Data_Source instances (tests pass an
# in-memory local + an in-memory AWS source — no mocks). refresh_seconds=0 → no timer.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Compare__Render             import compare_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS


class SG_Edge__TUI__Screen__Compare(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge — Local vs Edge'
    BINDINGS = [('r', 'refresh', 'Refresh')]

    def __init__(self, local_source, aws_source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.local_source    = local_source
        self.aws_source      = aws_source
        self.refresh_seconds = refresh_seconds
        self.local_snapshot  = None
        self.aws_snapshot    = None

    def card_snapshot(self):                                                         # export the local side (Card is single-snapshot)
        return self.local_snapshot

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_snapshot()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.refresh_snapshot)

    def refresh_snapshot(self) -> None:
        self.local_snapshot = self.local_source.snapshot()
        self.aws_snapshot   = self.aws_source.snapshot()
        self.query_one('#body', Static).update(compare_markup(self.local_snapshot, self.aws_snapshot))

    def action_refresh(self) -> None:
        self.refresh_snapshot()
