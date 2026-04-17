# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__State__Save__Request (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                                import Schema__Vault_Ref


class Schema__Session__State__Save__Request(Type_Safe):                             # POST /session/{id}/save-state body
    vault_ref               : Schema__Vault_Ref                                     # Where to write storage state
