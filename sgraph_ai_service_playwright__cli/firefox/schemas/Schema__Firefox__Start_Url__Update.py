# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Start_Url__Update
# Request body for PUT /firefox/{stack_id}/profile/start_url.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                            import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Url import Safe_Str__Url


class Schema__Firefox__Start_Url__Update(Type_Safe):
    url : Safe_Str__Url
