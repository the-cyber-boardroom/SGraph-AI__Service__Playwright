# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__IAM__Statement
# Ordered list of IAM policy statements. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List              import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Statement      import Schema__IAM__Statement


class List__Schema__IAM__Statement(Type_Safe__List):
    expected_type = Schema__IAM__Statement
