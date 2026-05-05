# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Log__Lines
# Count of log lines returned by the sidecar. Zero means empty or unknown.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Log__Lines(Safe_Int):
    min_value = 0
