# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Assumption
# Represents a single STS role-assumption event (as stored in audit log).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Role__ARN          import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Access_Key_Id      import Safe_Str__Creds__Access_Key_Id
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Assumption_Id      import Safe_Str__Creds__Assumption_Id
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Caller             import Safe_Str__Creds__Caller
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Scope_Name         import Safe_Str__Creds__Scope_Name
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Session_Token      import Safe_Str__Creds__Session_Token
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Timestamp          import Safe_Str__Creds__Timestamp


class Schema__Creds__Assumption(Type_Safe):
    assumption_id  : Safe_Str__Creds__Assumption_Id
    scope_name     : Safe_Str__Creds__Scope_Name
    role_arn       : Safe_Str__AWS__Role__ARN
    caller         : Safe_Str__Creds__Caller
    assumed_at     : Safe_Str__Creds__Timestamp
    expires_at     : Safe_Str__Creds__Timestamp
    access_key_id  : Safe_Str__Creds__Access_Key_Id
    session_token  : Safe_Str__Creds__Session_Token
