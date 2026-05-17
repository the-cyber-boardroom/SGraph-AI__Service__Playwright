# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Task__Definition
# ECS task definition summary. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                       import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Launch__Type           import Enum__ECS__Launch__Type
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Definition import Safe_Str__ECS__Task__Definition


class Schema__ECS__Task__Definition(Type_Safe):
    family          : str                         = ''
    revision        : int                         = 0
    task_def_arn    : str                         = ''
    status          : str                         = ''   # ACTIVE | INACTIVE | DELETE_IN_PROGRESS
    cpu             : str                         = ''   # string from ECS API, e.g. "256"
    memory          : str                         = ''   # string from ECS API, e.g. "512"
    launch_type     : Enum__ECS__Launch__Type     = Enum__ECS__Launch__Type.FARGATE
    family_revision : Safe_Str__ECS__Task__Definition    # e.g. "my-task:3"
