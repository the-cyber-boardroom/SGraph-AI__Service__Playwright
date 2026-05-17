# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__Secret__Value
# Type-safe container for a secret string value.
# __repr__ and __str__ always return '****' to prevent accidental logging.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Secret__Value(Safe_Str):
    max_length      = 4096
    allow_empty     = True

    def __repr__(self):                                 # never leak the secret
        return '****'
