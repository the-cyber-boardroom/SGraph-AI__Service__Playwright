# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Enum__SG_Edge__Idle__Action
# The action an idle_check pass took on the fleet (brief 02 teardown counter):
#   RESET     traffic present — zero_streak cleared
#   INCREMENT idle, but below the teardown threshold — streak bumped
#   TEARDOWN  idle long enough — fleet drained and streak reset
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__SG_Edge__Idle__Action(str, Enum):
    RESET     = 'reset'
    INCREMENT = 'increment'
    TEARDOWN  = 'teardown'

    def __str__(self):
        return self.value
