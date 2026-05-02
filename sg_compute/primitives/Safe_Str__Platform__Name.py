# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Platform__Name
# Allowlist of supported compute platform backends.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode

PLATFORM_ALLOWLIST = {'ec2', 'k8s', 'gcp', 'local'}


class Safe_Str__Platform__Name(Safe_Str):
    max_length        = 16
    regex             = re.compile(r'^(ec2|k8s|gcp|local)$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
