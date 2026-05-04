# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Credentials (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Dict

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Name            import Safe_Str__Http__Header__Name
from osbot_utils.type_safe.primitives.domains.http.safe_str.Safe_Str__Http__Header__Value           import Safe_Str__Http__Header__Value

from sgraph_ai_service_playwright.schemas.artefact.Schema__Vault_Ref                                import Schema__Vault_Ref


class Schema__Session__Credentials(Type_Safe):                                      # Per-session auth / cookies
    cookies_vault_ref       : Schema__Vault_Ref = None                              # Load cookies from vault at session open
    storage_state_vault_ref : Schema__Vault_Ref = None                              # Playwright storage state JSON
    extra_http_headers      : Dict[Safe_Str__Http__Header__Name,
                                   Safe_Str__Http__Header__Value]                   # E.g. bearer tokens
