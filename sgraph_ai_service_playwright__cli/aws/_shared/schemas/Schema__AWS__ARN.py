# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Schema__AWS__ARN
# Parsed ARN: arn:partition:service:region:account:resource
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN       import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Account_Id import Safe_Str__AWS__Account_Id


class Schema__AWS__ARN(Type_Safe):
    raw_arn    : Safe_Str__AWS__ARN
    partition  : str = ''
    service    : str = ''
    region     : Safe_Str__AWS__Region
    account_id : Safe_Str__AWS__Account_Id
    resource   : str = ''
