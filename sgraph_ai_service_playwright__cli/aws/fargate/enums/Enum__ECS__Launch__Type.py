# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__ECS__Launch__Type
# ECS launch type. Only FARGATE is accepted in this slice; EC2 is out of scope.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ECS__Launch__Type(str, Enum):
    FARGATE = 'FARGATE'
    EC2     = 'EC2'
    EXTERNAL= 'EXTERNAL'

    def __str__(self):
        return self.value
