# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Audit__Finding
# Finding codes emitted by IAM__Policy__Auditor detectors.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Audit__Finding(str, Enum):
    WILDCARD_ACTION          = 'WILDCARD_ACTION'
    WILDCARD_RESOURCE        = 'WILDCARD_RESOURCE'
    MISSING_CONDITION        = 'MISSING_CONDITION'
    ADMIN_ACCESS             = 'ADMIN_ACCESS'
    STALE_ROLE               = 'STALE_ROLE'
    OVERLY_BROAD_SERVICE     = 'OVERLY_BROAD_SERVICE'
    MISSING_TAG_CONDITION    = 'MISSING_TAG_CONDITION'

    def __str__(self):
        return self.value
