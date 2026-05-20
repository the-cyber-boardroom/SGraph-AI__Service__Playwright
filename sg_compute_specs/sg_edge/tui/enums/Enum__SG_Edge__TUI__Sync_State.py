# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Enum__SG_Edge__TUI__Sync_State
# A comparison row's verdict for Screen 3 (local vs edge). IN_SYNC means both sides
# agree (both present or both absent); the others name which side has it. There is
# no "deployed" third axis — that is out of scope for this sg_edge tool.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__TUI__Sync_State(str, Enum):
    IN_SYNC    = 'in_sync'
    LOCAL_ONLY = 'local_only'
    EDGE_ONLY  = 'edge_only'

    def __str__(self):
        return self.value
