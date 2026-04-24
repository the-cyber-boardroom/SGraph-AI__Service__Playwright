# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Deploy_Name
# Random deploy name in the style produced by scripts.provision_ec2._random_deploy_name
# (e.g. "fierce-planck", "serene-einstein"). Lowercase adjective-noun pairs
# joined by a single hyphen. Regex is permissive — the generator is the source
# of truth; this primitive just validates the shape on input.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Deploy_Name(Safe_Str):
    regex             = re.compile(r'^[a-z]{3,20}-[a-z]{3,20}$')                    # adjective-noun with 3-20 chars each side
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 41                                                          # 20 + 1 + 20
    allow_empty       = True                                                        # Auto-init support; request-side validators reject empty on POST
    to_lower_case     = True
    trim_whitespace   = True
