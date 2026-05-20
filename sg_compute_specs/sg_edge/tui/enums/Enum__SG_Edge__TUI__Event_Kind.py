# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Enum__SG_Edge__TUI__Event_Kind
# The state-transition events the Differ emits between two snapshots. These are the
# ONLY events the MVP feed shows — honest deltas observed by polling, not a live
# request stream (that needs the observability source / Slice 5/6, a later swap).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__TUI__Event_Kind(str, Enum):
    SLUG_REGISTERED = 'slug_registered'                                              # a slug appeared
    WENT_LIVE       = 'went_live'                                                    # gained a backend (DORMANT/absent → LIVE)
    WENT_DORMANT    = 'went_dormant'                                                 # lost its backend (LIVE → not LIVE)
    REMOVED         = 'removed'                                                      # a slug disappeared
    FLEET_CHANGED   = 'fleet_changed'                                                # proxy fleet size changed
    ISSUE           = 'issue'                                                        # a new check finding appeared
    CLEARED         = 'cleared'                                                      # a check finding cleared

    def __str__(self):
        return self.value
