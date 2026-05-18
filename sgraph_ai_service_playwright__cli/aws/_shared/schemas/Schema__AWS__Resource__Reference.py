# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__AWS__Resource__Reference
# Lightweight pointer to an AWS resource by ARN or name.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__AWS__Resource__Reference(Type_Safe):
    arn        : Safe_Str__AWS__ARN
    name       : str = ''
    resource_type : str = ''
    region     : Safe_Str__AWS__Region
