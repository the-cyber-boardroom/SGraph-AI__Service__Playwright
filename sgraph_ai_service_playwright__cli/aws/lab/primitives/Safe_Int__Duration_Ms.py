# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Safe_Int__Duration_Ms
# Duration in milliseconds. Zero is valid (instantaneous / not measured).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Duration_Ms(Safe_Int):
    min_value = 0
    max_value = 86_400_000                                                         # 24 h upper bound
