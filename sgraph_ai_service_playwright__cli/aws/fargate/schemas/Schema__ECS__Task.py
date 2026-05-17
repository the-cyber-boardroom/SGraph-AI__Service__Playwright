# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Task
# ECS task summary. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.enums.Enum__ECS__Task__Status              import Enum__ECS__Task__Status
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Cluster__Name    import Safe_Str__ECS__Cluster__Name
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Group            import Safe_Str__ECS__Group
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Status           import Safe_Str__ECS__Status
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Stop_Reason      import Safe_Str__ECS__Stop_Reason
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__ARN        import Safe_Str__ECS__Task__ARN
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Task__Definition import Safe_Str__ECS__Task__Definition
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Timestamp        import Safe_Str__ECS__Timestamp


class Schema__ECS__Task(Type_Safe):
    task_arn         : Safe_Str__ECS__Task__ARN
    cluster_name     : Safe_Str__ECS__Cluster__Name
    task_definition  : Safe_Str__ECS__Task__Definition
    status           : Enum__ECS__Task__Status          = Enum__ECS__Task__Status.UNKNOWN
    last_status      : Safe_Str__ECS__Status
    desired_status   : Safe_Str__ECS__Status
    started_at       : Safe_Str__ECS__Timestamp                # ISO-8601; empty = not yet started
    stopped_at       : Safe_Str__ECS__Timestamp                # ISO-8601; empty = still running
    stopped_reason   : Safe_Str__ECS__Stop_Reason
    group            : Safe_Str__ECS__Group                    # task group (e.g. service:<name>)
