# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Events
# Screen 5 (Live Event Stream) — the most dynamic screen. Each poll fetches a
# snapshot, diffs it against the previous one via the T1 Differ (honest observed
# transitions), prepends new events to a capped feed, and records the T1 Metrics for
# the sparklines. space pauses; a/s/f/i filter; c clears; r forces a poll; q quits.
#
# Construct with an injected source. refresh_seconds=0 → no timer (tests call poll()).
# The first poll seeds the baseline (Differ yields nothing without a prior snapshot).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Differ                      import SG_Edge__TUI__Differ
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Metrics                     import SG_Edge__TUI__Metrics
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Events__Render              import events_markup
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS

MAX_EVENTS = 200


class SG_Edge__TUI__Screen__Events(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge Live Activity'
    BINDINGS = [('r', 'poll',    'Poll'),
                ('space', 'pause', 'Pause'),
                ('c', 'clear',   'Clear'),
                ('a', 'filter_all',    'All'),
                ('s', 'filter_slugs',  'Slugs'),
                ('f', 'filter_fleet',  'Fleet'),
                ('i', 'filter_issues', 'Issues')]

    def __init__(self, source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.refresh_seconds = refresh_seconds
        self.differ          = SG_Edge__TUI__Differ()
        self.metrics         = SG_Edge__TUI__Metrics()
        self.prev_snapshot   = None
        self.snapshot        = None
        self.events          = []                                                    # newest first
        self.active_filter   = 'all'
        self.paused          = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.poll()                                                                  # seeds the baseline
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.poll)

    def poll(self) -> None:
        if self.paused:
            return
        snap       = self.source.snapshot()
        new_events = self.differ.diff(self.prev_snapshot, snap)
        for event in new_events:                                                     # prepend so newest ends up first
            self.events.insert(0, event)
        del self.events[MAX_EVENTS:]
        self.metrics.record(snap)
        self.prev_snapshot = snap
        self.snapshot      = snap
        self.redraw()

    def redraw(self) -> None:
        self.query_one('#body', Static).update(
            events_markup(self.snapshot, self.events, self.metrics, self.active_filter, self.paused))

    def action_poll(self) -> None:
        self.poll()

    def action_pause(self) -> None:
        self.paused = not self.paused
        self.redraw()

    def action_clear(self) -> None:
        self.events = []
        self.redraw()

    def set_filter(self, name : str) -> None:
        self.active_filter = name
        self.redraw()

    def action_filter_all(self)    -> None: self.set_filter('all')
    def action_filter_slugs(self)  -> None: self.set_filter('slugs')
    def action_filter_fleet(self)  -> None: self.set_filter('fleet')
    def action_filter_issues(self) -> None: self.set_filter('issues')
