# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Edge__Type
# Closed set of relationship types that appear as graph edges.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Edge__Type(str, Enum):
    INLINE_POLICY   = 'inline_policy'    # role → inline policy
    MANAGED_POLICY  = 'managed_policy'   # role/user/group → managed policy
    TRUST           = 'trust'            # role → trusted principal/service
    MEMBER_OF       = 'member_of'        # user → group

    def __str__(self):
        return self.value
