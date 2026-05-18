# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — List__Schema__ECR__Image
# Typed list of ECR image schemas. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Image import Schema__ECR__Image


class List__Schema__ECR__Image(Type_Safe__List):
    expected_type = Schema__ECR__Image
