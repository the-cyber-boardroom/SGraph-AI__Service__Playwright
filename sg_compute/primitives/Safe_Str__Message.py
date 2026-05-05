# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Message
# Human-readable status / error message. Allows most printable chars.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Message(Safe_Str):
    max_length        = 512
    allow_empty       = True
    strict_validation = False
