# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Scope
# Scope catalogue entry — maps a logical name to a role ARN + max TTL.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Role__ARN  import Safe_Str__AWS__Role__ARN
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Max_TTL    import Safe_Str__Creds__Max_TTL
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Scope_Name import Safe_Str__Creds__Scope_Name
from sgraph_ai_service_playwright__cli.aws.creds.primitives.Safe_Str__Creds__Timestamp  import Safe_Str__Creds__Timestamp


class Schema__Creds__Scope(Type_Safe):
    name       : Safe_Str__Creds__Scope_Name
    role_arn   : Safe_Str__AWS__Role__ARN
    max_ttl    : Safe_Str__Creds__Max_TTL
    created_at : Safe_Str__Creds__Timestamp
