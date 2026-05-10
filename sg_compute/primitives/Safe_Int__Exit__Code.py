# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Int__Exit__Code
# POSIX exit code — negative values are used by signal terminations on Linux.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Exit__Code(Safe_Int):
    min_value = -256
    max_value = 256
