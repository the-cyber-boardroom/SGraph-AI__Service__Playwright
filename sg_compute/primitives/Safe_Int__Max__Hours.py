# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Max__Hours
# Maximum lifetime for a compute node in hours. Zero means no auto-terminate.
# Distinct from Safe_Int__Hours (which has min=1 and is for uptime).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Max__Hours(Safe_Int):
    min_value = 0
    max_value = 168
