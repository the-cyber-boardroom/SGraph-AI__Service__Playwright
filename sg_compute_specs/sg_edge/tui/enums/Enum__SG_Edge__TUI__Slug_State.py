# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Enum__SG_Edge__TUI__Slug_State
# A slug's edge state, derived from its DNS records:
#   LIVE           — <slug> A present AND _sg.<slug> TXT present (serve)
#   DORMANT        — A present, no TXT (registered, no live backend yet)
#   ORPHAN_BACKEND — TXT present, no A (backend with no registration)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__TUI__Slug_State(str, Enum):
    LIVE           = 'live'
    DORMANT        = 'dormant'
    ORPHAN_BACKEND = 'orphan_backend'

    def __str__(self):
        return self.value
