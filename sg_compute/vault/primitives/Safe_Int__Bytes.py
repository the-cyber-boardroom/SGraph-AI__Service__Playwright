# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Bytes
# Non-negative integer representing a byte count.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Bytes(Safe_Int):
    min_value = 0
