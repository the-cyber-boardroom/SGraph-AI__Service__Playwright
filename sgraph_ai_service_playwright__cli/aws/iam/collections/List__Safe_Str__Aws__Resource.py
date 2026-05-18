# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Safe_Str__Aws__Resource
# Ordered list of IAM resource strings (ARNs or the bare wildcard "*").
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List            import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Resource import Safe_Str__Aws__Resource


class List__Safe_Str__Aws__Resource(Type_Safe__List):
    expected_type = Safe_Str__Aws__Resource
