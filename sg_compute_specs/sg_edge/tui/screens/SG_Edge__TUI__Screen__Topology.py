# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Topology
# Screen 2 (Topology) — the layered flow with keyboard navigation over slug nodes.
# Thin view layer: polls one source, tracks a selected slug index, drops the pure
# topology_markup() into a Static. ↑/↓ (or k/j) move the selection without re-fetching;
# r refreshes; q quits. Enter is reserved to open S4 (Slug detail) once it lands.
#
# Construct with an injected SG_Edge__TUI__Data_Source. refresh_seconds=0 → no timer.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Topology__Render            import topology_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS


class SG_Edge__TUI__Screen__Topology(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge Topology'
    BINDINGS = [('r', 'refresh',     'Refresh'),
                ('down', 'select_next', 'Down'),
                ('j',    'select_next', 'Down'),
                ('up',   'select_prev', 'Up'),
                ('k',    'select_prev', 'Up'),
                ('enter', 'drill',      'Detail')]

    def __init__(self, source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.refresh_seconds = refresh_seconds
        self.snapshot        = None
        self.selected_index  = 0
        self.opened_slug     = ''                                                    # set on Enter → CLI relaunches the Slug-detail screen

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
        self.clamp_selection()
        self.redraw()

    def redraw(self) -> None:
        self.query_one('#body', Static).update(topology_markup(self.snapshot, self.selected_index))

    def clamp_selection(self) -> None:
        count = len(self.snapshot.slugs) if self.snapshot else 0
        if count == 0:
            self.selected_index = -1
        else:
            self.selected_index = max(0, min(self.selected_index, count - 1))

    def action_select_next(self) -> None:
        count = len(self.snapshot.slugs) if self.snapshot else 0
        if count:
            self.selected_index = min(self.selected_index + 1, count - 1)
            self.redraw()

    def action_select_prev(self) -> None:
        count = len(self.snapshot.slugs) if self.snapshot else 0
        if count:
            self.selected_index = max(self.selected_index - 1, 0)
            self.redraw()

    def action_drill(self) -> None:                                                  # Enter on a slug → record it + exit; the CLI opens Slug detail
        if self.snapshot and 0 <= self.selected_index < len(self.snapshot.slugs):
            self.opened_slug = self.snapshot.slugs[self.selected_index].slug
            self.exit()

    def action_refresh(self) -> None:
        self.refresh_snapshot()
