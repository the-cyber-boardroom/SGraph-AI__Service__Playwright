# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — List__Schema__ECR__Repo
# Typed list of ECR repository schemas. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ecr.schemas.Schema__ECR__Repo import Schema__ECR__Repo


class List__Schema__ECR__Repo(Type_Safe__List):
    expected_type = Schema__ECR__Repo
