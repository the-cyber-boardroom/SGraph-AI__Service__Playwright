# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Profile
# Response for GET /firefox/{stack_id}/profile.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Url                 import Safe_Str__Url
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle          import Safe_Str__Vault__Handle


class Schema__Firefox__Profile(Type_Safe):
    start_url              : Safe_Str__Url             # current Firefox start page
    loaded_profile_handle  : Safe_Str__Vault__Handle   # empty = no profile loaded
