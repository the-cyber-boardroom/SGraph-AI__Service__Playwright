# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Distribution__Status
# CloudFront distribution deployment status values returned by the API.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Distribution__Status(str, Enum):
    DEPLOYED    = 'Deployed'
    IN_PROGRESS = 'InProgress'

    def __str__(self):
        return self.value
