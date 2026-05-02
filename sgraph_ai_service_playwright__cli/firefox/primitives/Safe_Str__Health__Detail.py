# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Health__Detail
# Human-readable detail string included when health overall != GREEN.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text import Safe_Str__Text


class Safe_Str__Health__Detail(Safe_Str__Text):
    max_length = 512
