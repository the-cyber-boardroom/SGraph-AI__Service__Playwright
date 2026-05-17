# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__AWS__Role__Config
# JSON blob stored under sg.config.role.<name> in the keyring.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                        import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name         import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Region        import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Role__ARN     import Safe_Str__AWS__Role__ARN


class Schema__AWS__Role__Config(Type_Safe):
    name            : Safe_Str__Role__Name          # logical role name (e.g. 'admin')
    region          : Safe_Str__AWS__Region         # default AWS region
    assume_role_arn : Safe_Str__AWS__Role__ARN      # STS AssumeRole target (empty = no assume)
    session_name    : Safe_Str__Role__Name          # STS session name for traceability
