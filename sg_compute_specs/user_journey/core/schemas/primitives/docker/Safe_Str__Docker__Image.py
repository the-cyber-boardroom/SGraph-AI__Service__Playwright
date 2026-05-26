# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Safe_Str__Docker__Image (a docker image reference)
#
# Preserves the chars a full image ref needs (registry/namespace/repo:tag@digest),
# unlike Safe_Str__Text which mangles '/'. Validates strictly.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode

SAFE_STR__DOCKER_IMAGE__MAX_LENGTH = 512
SAFE_STR__DOCKER_IMAGE__REGEX      = re.compile(r'^[a-zA-Z0-9._/:@\-]+$')


class Safe_Str__Docker__Image(Safe_Str):                                            # e.g. diniscruz/sg-journey-runner:latest
    regex             = SAFE_STR__DOCKER_IMAGE__REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    max_length        = SAFE_STR__DOCKER_IMAGE__MAX_LENGTH
    trim_whitespace   = True
    strict_validation = True
    allow_empty       = True
