# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws_Usage_Type
# AWS usage-type string as returned by Cost Explorer (e.g.
# 'EU-BoxUsage:t3.micro'). No regex — usage types are free-form identifiers
# that include region prefixes, colons, and dots.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Aws_Usage_Type(Safe_Str):
    max_length  = 256
    allow_empty = True
