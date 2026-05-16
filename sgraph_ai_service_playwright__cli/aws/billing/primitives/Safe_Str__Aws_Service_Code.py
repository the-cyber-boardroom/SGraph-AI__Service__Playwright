# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws_Service_Code
# AWS service name string as returned by Cost Explorer (e.g. 'Amazon EC2',
# 'AWS Lambda'). No regex — service names contain spaces, hyphens, and parens.
# allow_empty = True supports auto-init and the 'OTHER' roll-up bucket.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Aws_Service_Code(Safe_Str):
    max_length  = 256
    allow_empty = True
