# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Profile__Load
# Request body for PUT /firefox/{stack_id}/profile/load.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle          import Safe_Str__Vault__Handle


class Schema__Firefox__Profile__Load(Type_Safe):
    handle : Safe_Str__Vault__Handle    # vault handle pointing at a profile tar.gz
