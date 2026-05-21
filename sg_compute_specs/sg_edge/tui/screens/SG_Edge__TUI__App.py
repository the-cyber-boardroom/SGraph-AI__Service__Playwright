# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__App (the canonical dashboard)
# Top-level navigation across all screens in ONE Textual app, using TabbedContent —
# the idiomatic Textual way to switch views (clickable tab bar + 1..6 / ←→ keys).
# Each tab reuses the SAME pure render the standalone screens use, fed by the shared
# data sources; a single timer polls and the active tab redraws. Per-tab interaction
# kept to the high-value bits (↑/↓ select on Topology & Slug); the focused standalone
# commands keep the full per-screen controls. The base provides q / ? / t / e.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static, TabbedContent, TabPane

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Deployment__Render          import deployment_markup
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Topology__Render            import topology_markup
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Compare__Render             import compare_markup
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Slug_Detail__Render         import slug_detail_markup
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Events__Render              import events_markup
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Docker__Render              import docker_markup
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Differ                      import SG_Edge__TUI__Differ
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Metrics                     import SG_Edge__TUI__Metrics
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS

TABS       = [('deployment', 'Deployment'), ('topology', 'Topology'), ('compare', 'Compare'),
              ('slug', 'Slug'), ('events', 'Events'), ('docker', 'Docker')]
MAX_EVENTS = 200


class SG_Edge__TUI__App(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge'
    BINDINGS = [('r', 'refresh', 'Refresh'),
                ('down', 'nav_next', 'Down'), ('j', 'nav_next', 'Down'),
                ('up',   'nav_prev', 'Up'),   ('k', 'nav_prev', 'Up'),
                ('1', 'tab_1', 'Deploy'), ('2', 'tab_2', 'Topo'), ('3', 'tab_3', 'Compare'),
                ('4', 'tab_4', 'Slug'),   ('5', 'tab_5', 'Events'), ('6', 'tab_6', 'Docker')]

    def __init__(self, local_source, aws_source, docker_source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.local_source    = local_source
        self.aws_source      = aws_source
        self.docker_source   = docker_source
        self.refresh_seconds = refresh_seconds
        self.local_snapshot  = None
        self.aws_snapshot    = None
        self.differ          = SG_Edge__TUI__Differ()
        self.metrics         = SG_Edge__TUI__Metrics()
        self.events          = []
        self.prev_snapshot   = None
        self.topo_index      = 0
        self.slug_focus      = ''

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial='deployment', id='tabs'):
            for tab_id, title in TABS:
                with TabPane(title, id=tab_id):
                    yield VerticalScroll(Static('', id=f'body-{tab_id}'))
        yield Footer()

    def on_mount(self) -> None:
        self.poll()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.poll)

    # ── state ───────────────────────────────────────────────────────────────────
    @property
    def active_tab(self) -> str:
        return self.query_one('#tabs', TabbedContent).active

    def card_snapshot(self):                                                         # `e` export uses the local snapshot
        return self.local_snapshot

    def slug_names(self) -> list:
        return [s.slug for s in self.local_snapshot.slugs] if self.local_snapshot else []

    # ── poll + render ─────────────────────────────────────────────────────────────
    def poll(self) -> None:
        snap       = self.local_source.snapshot()
        new_events = self.differ.diff(self.prev_snapshot, snap)
        for event in new_events:
            self.events.insert(0, event)
        del self.events[MAX_EVENTS:]
        self.metrics.record(snap)
        self.prev_snapshot  = snap
        self.local_snapshot = snap
        self.render_active()

    def render_active(self) -> None:
        tab  = self.active_tab
        body = self.query_one(f'#body-{tab}', Static)
        if tab == 'deployment':
            body.update(deployment_markup(self.local_snapshot, self.docker_source.containers(), self.docker_source.available()))
        elif tab == 'topology':
            self.topo_index = self._clamp(self.topo_index, self.slug_names())
            body.update(topology_markup(self.local_snapshot, self.topo_index))
        elif tab == 'compare':
            self.aws_snapshot = self.aws_source.snapshot()
            body.update(compare_markup(self.local_snapshot, self.aws_snapshot))
        elif tab == 'slug':
            names = self.slug_names()
            if self.slug_focus not in names:
                self.slug_focus = names[0] if names else ''
            body.update(slug_detail_markup(self.local_snapshot, self.slug_focus))
        elif tab == 'events':
            body.update(events_markup(self.local_snapshot, self.events, self.metrics, 'all', False))
        elif tab == 'docker':
            body.update(docker_markup(self.docker_source.containers(), self.docker_source.available()))

    def on_tabbed_content_tab_activated(self, event) -> None:
        self.render_active()

    # ── navigation ────────────────────────────────────────────────────────────────
    def switch_to(self, tab_id : str) -> None:
        self.query_one('#tabs', TabbedContent).active = tab_id                       # fires on_tabbed_content_tab_activated → render

    def action_tab_1(self) -> None: self.switch_to('deployment')
    def action_tab_2(self) -> None: self.switch_to('topology')
    def action_tab_3(self) -> None: self.switch_to('compare')
    def action_tab_4(self) -> None: self.switch_to('slug')
    def action_tab_5(self) -> None: self.switch_to('events')
    def action_tab_6(self) -> None: self.switch_to('docker')

    def action_nav_next(self) -> None: self._nav(+1)
    def action_nav_prev(self) -> None: self._nav(-1)

    def _nav(self, delta : int) -> None:
        names = self.slug_names()
        if not names:
            return
        if self.active_tab == 'topology':
            self.topo_index = self._clamp(self.topo_index + delta, names)
            self.render_active()
        elif self.active_tab == 'slug':
            index = names.index(self.slug_focus) if self.slug_focus in names else 0
            self.slug_focus = names[self._clamp(index + delta, names)]
            self.render_active()

    def _clamp(self, index : int, names : list) -> int:
        if not names:
            return 0
        return max(0, min(index, len(names) - 1))

    def action_refresh(self) -> None:
        self.poll()
