# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Dict__ALB__Tag
# Typed dict mapping ALB tag keys to tag values.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict import Type_Safe__Dict

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Key   import Safe_Str__AWS__Tag_Key
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value import Safe_Str__AWS__Tag_Value


class Dict__ALB__Tag(Type_Safe__Dict):
    expected_key_type   = Safe_Str__AWS__Tag_Key
    expected_value_type = Safe_Str__AWS__Tag_Value
