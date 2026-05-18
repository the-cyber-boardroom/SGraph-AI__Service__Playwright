# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__AWS__Tag
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Key   import Safe_Str__AWS__Tag_Key
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value import Safe_Str__AWS__Tag_Value


class Schema__AWS__Tag(Type_Safe):
    key   : Safe_Str__AWS__Tag_Key
    value : Safe_Str__AWS__Tag_Value
