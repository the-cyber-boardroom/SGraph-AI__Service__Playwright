# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Schema__SG_Edge__TUI__Event
# One state-transition event for the activity feed (Screen 5). Emitted by the
# Differ from successive snapshots — an honest observed delta. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind      import Enum__SG_Edge__TUI__Event_Kind


class Schema__SG_Edge__TUI__Event(Type_Safe):
    kind   : Enum__SG_Edge__TUI__Event_Kind = Enum__SG_Edge__TUI__Event_Kind.SLUG_REGISTERED
    slug   : str                                                                     # '' for non-slug events (e.g. fleet)
    detail : str
    ts     : int = 0                                                                 # snapshot capture time the delta was observed at
