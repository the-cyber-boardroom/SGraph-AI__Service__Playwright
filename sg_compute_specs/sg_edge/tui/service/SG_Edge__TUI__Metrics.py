# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Metrics
# Honest sparkline series. record() is called once per poll with the current
# snapshot; it appends one point per series and trims to max_points (a ring buffer).
# The series are counts the TUI measured itself (total slugs, live slugs, fleet
# size) — NOT rps/cost, which are not measurable here and would be fabrication.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State           import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Series_Point     import Schema__SG_Edge__TUI__Series_Point
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot         import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.schemas.List__SG_Edge__TUI__Series_Point       import List__SG_Edge__TUI__Series_Point
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                            import TUI_SERIES_MAX_POINTS

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


class SG_Edge__TUI__Metrics(Type_Safe):
    max_points  : int = TUI_SERIES_MAX_POINTS
    total_slugs : List__SG_Edge__TUI__Series_Point
    live_slugs  : List__SG_Edge__TUI__Series_Point
    fleet_size  : List__SG_Edge__TUI__Series_Point

    def record(self, snapshot : Schema__SG_Edge__TUI__Snapshot) -> None:
        ts   = int(snapshot.captured_at)
        live = sum(1 for s in snapshot.slugs if s.state == LIVE)
        self.append(self.total_slugs, ts, len(snapshot.slugs))
        self.append(self.live_slugs,  ts, live)
        self.append(self.fleet_size,  ts, len(snapshot.fleet_ips))

    def append(self, series, ts : int, value : int) -> None:
        series.append(Schema__SG_Edge__TUI__Series_Point(ts=ts, value=value))
        while len(series) > self.max_points:                                         # ring buffer — drop the oldest
            series.pop(0)

    def values(self, series) -> list:                                                # bare value list for sparkline rendering
        return [int(point.value) for point in series]
