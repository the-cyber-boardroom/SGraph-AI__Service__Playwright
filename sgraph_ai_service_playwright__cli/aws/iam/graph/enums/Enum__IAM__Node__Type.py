# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Node__Type
# Closed set of IAM entity types that appear as graph nodes.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Node__Type(str, Enum):
    ROLE   = 'role'
    POLICY = 'policy'
    USER   = 'user'
    GROUP  = 'group'

    def __str__(self):
        return self.value
