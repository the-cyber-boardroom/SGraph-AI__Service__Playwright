# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__ECS__Cluster
# ECS cluster summary. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Cluster__Name    import Safe_Str__ECS__Cluster__Name
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Cluster_Arn      import Safe_Str__ECS__Cluster_Arn
from sgraph_ai_service_playwright__cli.aws.fargate.primitives.Safe_Str__ECS__Status           import Safe_Str__ECS__Status


class Schema__ECS__Cluster(Type_Safe):
    cluster_name      : Safe_Str__ECS__Cluster__Name
    cluster_arn       : Safe_Str__ECS__Cluster_Arn
    status            : Safe_Str__ECS__Status               # ACTIVE | INACTIVE | PROVISIONING
    running_tasks     : int                 = 0
    pending_tasks     : int                 = 0
    active_services   : int                 = 0
    tags              : dict                                # raw {key: value} tag map
