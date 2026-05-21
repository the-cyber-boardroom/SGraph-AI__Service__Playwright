# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Slug_Detail
# Screen 4 (Slug detail) — the deep-dive on one slug. Thin view layer: polls one
# source, focuses a slug by name, drops the pure slug_detail_markup() into a Static.
# ↑/↓ (or k/j) switch the focused slug; r refreshes (keeping focus by name); q quits.
# STATE + DNS are real; instance/cost/activity render as labelled pending panes.
#
# Construct with an injected source and an optional initial slug (Topology's Enter
# passes the selected one). refresh_seconds=0 → no timer.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Slug_Detail__Render         import slug_detail_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS


class SG_Edge__TUI__Screen__Slug_Detail(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge Slug Detail'
    BINDINGS = [('r', 'refresh',     'Refresh'),
                ('down', 'select_next', 'Next slug'),
                ('j',    'select_next', 'Next slug'),
                ('up',   'select_prev', 'Prev slug'),
                ('k',    'select_prev', 'Prev slug')]

    def __init__(self, source, slug : str = '', refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.focus_name      = slug
        self.refresh_seconds = refresh_seconds
        self.snapshot        = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_snapshot()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.refresh_snapshot)

    def names(self) -> list:
        return [s.slug for s in self.snapshot.slugs] if self.snapshot else []

    def refresh_snapshot(self) -> None:
        self.snapshot = self.source.snapshot()
        names = self.names()
        if self.focus_name not in names:                                             # focus gone (or unset) → first slug
            self.focus_name = names[0] if names else ''
        self.redraw()

    def redraw(self) -> None:
        self.query_one('#body', Static).update(slug_detail_markup(self.snapshot, self.focus_name))

    def step(self, delta : int) -> None:
        names = self.names()
        if not names:
            return
        index           = names.index(self.focus_name) if self.focus_name in names else 0
        index           = max(0, min(index + delta, len(names) - 1))
        self.focus_name = names[index]
        self.redraw()

    def action_select_next(self) -> None:
        self.step(+1)

    def action_select_prev(self) -> None:
        self.step(-1)

    def action_refresh(self) -> None:
        self.refresh_snapshot()
