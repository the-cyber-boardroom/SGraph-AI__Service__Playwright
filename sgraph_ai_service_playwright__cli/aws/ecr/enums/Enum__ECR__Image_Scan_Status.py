# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Enum__ECR__Image_Scan_Status
# ECR image scan lifecycle states reported by the AWS API. UNKNOWN is the
# fallback when an image has never been scanned.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ECR__Image_Scan_Status(str, Enum):
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETE    = 'COMPLETE'
    FAILED      = 'FAILED'
    UNKNOWN     = 'UNKNOWN'

    def __str__(self):
        return self.value
