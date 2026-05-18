# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Safe_Str__IAM__Policy_Arn
# Ordered list of IAM managed policy ARNs. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List              import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__IAM__Policy_Arn import Safe_Str__IAM__Policy_Arn


class List__Safe_Str__IAM__Policy_Arn(Type_Safe__List):
    expected_type = Safe_Str__IAM__Policy_Arn
