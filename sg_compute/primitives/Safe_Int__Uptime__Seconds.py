# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Uptime__Seconds
# Node uptime in seconds. Non-negative; 0 = not started or unknown.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Uptime__Seconds(Safe_Int):
    min_value = 0
