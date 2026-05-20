# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Differ
# Pure: given the previous and current snapshots, emit the state-transition events
# that drive the activity feed (Screen 5). These are honest observed deltas — the
# only events the MVP has (a live per-request stream needs the observability source
# / Slice 5/6, a later swap). No prior snapshot → no events (the first poll seeds).
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind      import Enum__SG_Edge__TUI__Event_Kind
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State      import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Event       import Schema__SG_Edge__TUI__Event
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot    import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.schemas.List__SG_Edge__TUI__Event         import List__SG_Edge__TUI__Event

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


class SG_Edge__TUI__Differ(Type_Safe):

    def diff(self, prev : Optional[Schema__SG_Edge__TUI__Snapshot],
                   curr : Schema__SG_Edge__TUI__Snapshot) -> List__SG_Edge__TUI__Event:
        events = List__SG_Edge__TUI__Event()
        if prev is None:                                                             # first snapshot — nothing to compare against
            return events
        ts        = int(curr.captured_at)
        prev_slug = {s.slug: s for s in prev.slugs}
        curr_slug = {s.slug: s for s in curr.slugs}

        for slug in sorted(curr_slug.keys() - prev_slug.keys()):
            self.add(events, Enum__SG_Edge__TUI__Event_Kind.SLUG_REGISTERED, slug, f'{slug} registered', ts)
        for slug in sorted(prev_slug.keys() - curr_slug.keys()):
            self.add(events, Enum__SG_Edge__TUI__Event_Kind.REMOVED, slug, f'{slug} removed', ts)
        for slug in sorted(curr_slug.keys() & prev_slug.keys()):
            was_live = prev_slug[slug].state == LIVE
            now_live = curr_slug[slug].state == LIVE
            if not was_live and now_live:
                self.add(events, Enum__SG_Edge__TUI__Event_Kind.WENT_LIVE, slug, f'{slug} went live', ts)
            elif was_live and not now_live:
                self.add(events, Enum__SG_Edge__TUI__Event_Kind.WENT_DORMANT, slug, f'{slug} lost its backend', ts)

        if len(prev.fleet_ips) != len(curr.fleet_ips):
            self.add(events, Enum__SG_Edge__TUI__Event_Kind.FLEET_CHANGED, '',
                     f'proxy fleet {len(prev.fleet_ips)} → {len(curr.fleet_ips)}', ts)

        prev_issues = {(str(i.area), str(i.message)) for i in prev.issues}
        curr_issues = {(str(i.area), str(i.message)) for i in curr.issues}
        for area, message in sorted(curr_issues - prev_issues):
            self.add(events, Enum__SG_Edge__TUI__Event_Kind.ISSUE, '', f'{area}: {message}', ts)
        for area, message in sorted(prev_issues - curr_issues):
            self.add(events, Enum__SG_Edge__TUI__Event_Kind.CLEARED, '', f'{area}: {message}', ts)
        return events

    def add(self, events, kind, slug, detail, ts) -> None:
        events.append(Schema__SG_Edge__TUI__Event(kind=kind, slug=slug, detail=detail, ts=ts))
