# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Decimal__Currency__USD
# USD monetary amount with 4 decimal places for Cost Explorer precision.
# Extends Safe_Float__Money (Decimal-backed, non-negative, no inf/nan).
# decimal_places = 4 overrides the base class default of 2; the CLI renders
# amounts at 2dp for display — only the boundary uses 4dp.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.numerical.safe_float.Safe_Float__Money import Safe_Float__Money


class Safe_Decimal__Currency__USD(Safe_Float__Money):
    decimal_places = 4
    use_decimal    = True
    min_value      = 0.0
    allow_inf      = False
    allow_nan      = False
    round_output   = True
