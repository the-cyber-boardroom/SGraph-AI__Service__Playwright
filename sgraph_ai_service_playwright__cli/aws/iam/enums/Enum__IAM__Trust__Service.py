# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Trust__Service
# Closed set of AWS service principals allowed in an IAM trust policy.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Trust__Service(str, Enum):
    LAMBDA      = 'lambda.amazonaws.com'
    EC2         = 'ec2.amazonaws.com'
    ECS_TASKS   = 'ecs-tasks.amazonaws.com'
    API_GATEWAY = 'apigateway.amazonaws.com'

    def __str__(self):
        return self.value
