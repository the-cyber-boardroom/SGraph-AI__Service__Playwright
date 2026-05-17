# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__ECS__Cluster
# Ordered list of ECS cluster schemas. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List       import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Cluster import Schema__ECS__Cluster


class List__Schema__ECS__Cluster(Type_Safe__List):
    expected_type = Schema__ECS__Cluster
