# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Int__Timeout__Minutes
# Non-negative integer representing an ephemeral-stack auto-terminate timeout
# in minutes. 0 = no auto-terminate.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Timeout__Minutes(Safe_Int):
    min_value = 0
    max_value = 1440    # 24 hours hard cap
