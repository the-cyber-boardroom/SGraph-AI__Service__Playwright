# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Schema__Lab__Account__Identity
# Caller identity as returned by STS GetCallerIdentity + region.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Account_Id import Safe_Str__AWS__Account_Id
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN        import Safe_Str__AWS__ARN
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region     import Safe_Str__AWS__Region


class Schema__Lab__Account__Identity(Type_Safe):
    account_id : Safe_Str__AWS__Account_Id
    user_id    : str
    arn        : Safe_Str__AWS__ARN
    region     : Safe_Str__AWS__Region
