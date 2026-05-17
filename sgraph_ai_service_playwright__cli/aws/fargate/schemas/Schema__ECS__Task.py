# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Task
# ECS task summary. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Task__Status      import Enum__ECS__Task__Status
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Cluster__Name  import Safe_Str__ECS__Cluster__Name
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__ARN import Safe_Str__ECS__Task__ARN
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Definition import Safe_Str__ECS__Task__Definition


class Schema__ECS__Task(Type_Safe):
    task_arn         : Safe_Str__ECS__Task__ARN
    cluster_name     : Safe_Str__ECS__Cluster__Name
    task_definition  : Safe_Str__ECS__Task__Definition
    status           : Enum__ECS__Task__Status          = Enum__ECS__Task__Status.UNKNOWN
    last_status      : str                              = ''
    desired_status   : str                              = ''
    started_at       : str                              = ''   # ISO-8601; empty = not yet started
    stopped_at       : str                              = ''   # ISO-8601; empty = still running
    stopped_reason   : str                              = ''
    group            : str                              = ''   # task group (e.g. service:<name>)
