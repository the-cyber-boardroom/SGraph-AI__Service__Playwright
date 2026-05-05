# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Pids
# Number of processes (PIDs) running inside a container. Zero is valid.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Pids(Safe_Int):
    min_value = 0
