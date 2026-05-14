# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vault_App__Health
# Health snapshot for one vault-app stack. vault_ok means sg-send-vault
# /info/health returns 200. playwright_ok means the playwright service
# /health/status returns 200. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State  import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.primitives.Safe_Str__Vault_App__Stack__Name import Safe_Str__Vault_App__Stack__Name


class Schema__Vault_App__Health(Type_Safe):
    stack_name    : Safe_Str__Vault_App__Stack__Name
    state         : Enum__Vault_App__Stack__State = Enum__Vault_App__Stack__State.UNKNOWN
    vault_ok      : bool                          = False                           # True iff sg-send-vault /info/health returns 200
    playwright_ok : bool                          = False                           # True iff playwright /health/status returns 200
    error         : Safe_Str__Text                                                  # Set when any probe failed; empty otherwise
