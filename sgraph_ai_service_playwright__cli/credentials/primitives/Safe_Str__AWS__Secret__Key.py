# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__AWS__Secret__Key
# Type-safe AWS secret access key.
# __repr__ always returns '****' — secret keys must never appear in logs.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__AWS__Secret__Key(Safe_Str):
    max_length      = 64
    allow_empty     = True

    def __repr__(self):
        return '****'
