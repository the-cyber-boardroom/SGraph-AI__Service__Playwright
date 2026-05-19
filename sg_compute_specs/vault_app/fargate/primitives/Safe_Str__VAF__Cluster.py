# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Safe_Str__VAF__Cluster
# Vault-app Fargate cluster name.  Lowercase alphanumeric + hyphens,
# starts with alnum, 2–65 chars total.  Satisfies ECS clusterName rules.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__VAF__Cluster(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9-]{1,64}$')               # cluster rule: lower-alnum+hyphen, 2–65 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
