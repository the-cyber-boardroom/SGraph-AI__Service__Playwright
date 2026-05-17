# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Task__Definition
# ECS task definition summary. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Launch__Type              import Enum__ECS__Launch__Type
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__CPU              import Safe_Str__ECS__CPU
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Memory           import Safe_Str__ECS__Memory
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Status           import Safe_Str__ECS__Status
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Def_Arn    import Safe_Str__ECS__Task__Def_Arn
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Definition import Safe_Str__ECS__Task__Definition
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Family     import Safe_Str__ECS__Task__Family


class Schema__ECS__Task__Definition(Type_Safe):
    family          : Safe_Str__ECS__Task__Family
    revision        : int                         = 0
    task_def_arn    : Safe_Str__ECS__Task__Def_Arn
    status          : Safe_Str__ECS__Status                    # ACTIVE | INACTIVE | DELETE_IN_PROGRESS
    cpu             : Safe_Str__ECS__CPU                       # string from ECS API, e.g. "256"
    memory          : Safe_Str__ECS__Memory                    # string from ECS API, e.g. "512"
    launch_type     : Enum__ECS__Launch__Type     = Enum__ECS__Launch__Type.FARGATE
    family_revision : Safe_Str__ECS__Task__Definition          # e.g. "my-task:3"
