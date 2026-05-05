# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Log__Content
# Arbitrary multi-line log text from a container or sidecar API. No regex —
# log output can contain any printable character. 1 MB cap guards memory.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Safe_Str__Log__Content(Safe_Str):
    max_length        = 1048576   # 1 MB — generous cap for raw container log output
    allow_empty       = True
    strict_validation = False
