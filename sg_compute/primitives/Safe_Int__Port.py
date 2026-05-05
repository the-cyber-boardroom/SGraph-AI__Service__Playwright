# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Port
# TCP/UDP port number: 1–65535.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Port(Safe_Int):
    min_value = 1
    max_value = 65535
