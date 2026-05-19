# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Enum__VAF__Setup__Phase
# Setup phases in dependency order: ECR → IAM → LOGS → CLUSTER →
# IMAGE_MIRROR → TASK_DEF.  Delete runs them reversed.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__VAF__Setup__Phase(str, Enum):
    ECR          = 'ECR'
    IAM          = 'IAM'
    LOGS         = 'LOGS'
    CLUSTER      = 'CLUSTER'
    IMAGE_MIRROR = 'IMAGE_MIRROR'
    TASK_DEF     = 'TASK_DEF'

    def __str__(self):
        return self.value
