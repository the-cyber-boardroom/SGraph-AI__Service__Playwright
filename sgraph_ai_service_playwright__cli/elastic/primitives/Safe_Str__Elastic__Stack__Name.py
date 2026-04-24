# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Elastic__Stack__Name
# Logical name for an ephemeral Elastic+Kibana EC2 stack. Accepts both the
# auto-generated "elastic-{adjective}-{scientist}" form and user-supplied names
# (lowercase letters, digits, hyphens). The AWS Name tag always carries an
# "elastic-" prefix — see Elastic__AWS__Client.ensure_aws_name().
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Elastic__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{1,62}$')                      # Must start with a letter; 2-63 chars total (matches EC2 tag & SG naming comfort zone)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True                                                        # Auto-init support; service rejects empty on create
    to_lower_case     = True
    trim_whitespace   = True
