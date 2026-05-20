# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: Safe_Int__Edge__Cycle_Count
# Non-negative scheduled-check counter. Used for the fleet-state `zero_streak`
# (consecutive idle-checks with zero active vaults before teardown — brief 02
# uses a streak of 6 = 30 min at the 5-min cadence).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Edge__Cycle_Count(Safe_Int):
    min_value = 0
