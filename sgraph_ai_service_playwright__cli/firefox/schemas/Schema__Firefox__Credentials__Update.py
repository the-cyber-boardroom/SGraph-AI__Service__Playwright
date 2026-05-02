# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Credentials__Update
# Request body for PUT /firefox/{stack_id}/credentials.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Password__Write_Only import Safe_Str__Password__Write_Only
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Username             import Safe_Str__Username


class Schema__Firefox__Credentials__Update(Type_Safe):
    username : Safe_Str__Username
    password : Safe_Str__Password__Write_Only   # never echoed back in GET responses
