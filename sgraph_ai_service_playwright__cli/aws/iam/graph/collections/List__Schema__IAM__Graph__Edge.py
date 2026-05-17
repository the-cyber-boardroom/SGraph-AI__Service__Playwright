# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__IAM__Graph__Edge
# Ordered list of IAM graph edges. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.graph.schemas.Schema__IAM__Graph__Edge import Schema__IAM__Graph__Edge


class List__Schema__IAM__Graph__Edge(Type_Safe__List):
    expected_type = Schema__IAM__Graph__Edge
