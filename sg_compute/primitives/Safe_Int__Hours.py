# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Hours
# Maximum lifetime of a compute node in hours: 1–168 (1 week cap).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Hours(Safe_Int):
    min_value = 1
    max_value = 168
