# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__AWS__Credentials
# Live AWS credentials for a role (access key + secret key).
# Never logged — __repr__ redacts all fields.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Access__Key     import Safe_Str__AWS__Access__Key
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Secret__Key     import Safe_Str__AWS__Secret__Key
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name           import Safe_Str__Role__Name


class Schema__AWS__Credentials(Type_Safe):
    role_name       : Safe_Str__Role__Name
    access_key      : Safe_Str__AWS__Access__Key
    secret_key      : Safe_Str__AWS__Secret__Key
