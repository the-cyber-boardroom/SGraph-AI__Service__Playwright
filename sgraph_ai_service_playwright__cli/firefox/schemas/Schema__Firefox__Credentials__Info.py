# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Credentials__Info
# Response for GET /firefox/{stack_id}/credentials.
# Never contains the password.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Username             import Safe_Str__Username
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime           import Safe_Str__ISO_Datetime


class Schema__Firefox__Credentials__Info(Type_Safe):
    username         : Safe_Str__Username
    last_rotated_at  : Safe_Str__ISO_Datetime       # empty string when never rotated
