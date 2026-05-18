# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Safe_Str__Aws__Action
# Ordered list of IAM action strings. Bare "*" is structurally rejected by
# Safe_Str__Aws__Action (no colon → regex mismatch).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List          import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.iam.primitives.Safe_Str__Aws__Action import Safe_Str__Aws__Action


class List__Safe_Str__Aws__Action(Type_Safe__List):
    expected_type = Safe_Str__Aws__Action
