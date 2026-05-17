# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__ECS__Task
# Ordered list of ECS task schemas. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List      import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.fargate.schemas.Schema__ECS__Task import Schema__ECS__Task


class List__Schema__ECS__Task(Type_Safe__List):
    expected_type = Schema__ECS__Task
