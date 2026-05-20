# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Safe_Int__SG_Edge__Cycle_Count
# Non-negative scheduled-check counter. Holds the _state TXT `zero_streak` —
# consecutive idle-checks with zero active vaults before teardown (brief 02:
# IDLE_TEARDOWN_THRESHOLD of 3-12 intervals at the 5-min cadence).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__SG_Edge__Cycle_Count(Safe_Int):
    min_value = 0
