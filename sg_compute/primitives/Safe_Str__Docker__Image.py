# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Docker__Image
# Full Docker image reference: registry/repo:tag, repo:tag, or repo@sha256:digest.
# Allows lowercase + uppercase (registry hostnames, repo namespaces) plus
# the separator characters used in image refs. Empty allowed (pull not required).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Docker__Image(Safe_Str):
    max_length        = 256
    regex             = re.compile(r'^[a-zA-Z0-9._/:@\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
