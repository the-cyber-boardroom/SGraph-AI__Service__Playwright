# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Vault_Ref (spec §5.3)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                              import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version                   import Safe_Str__Version

from sg_compute_specs.playwright.core.schemas.primitives.vault.Safe_Str__Vault_Key                    import Safe_Str__Vault_Key
from sg_compute_specs.playwright.core.schemas.primitives.vault.Safe_Str__Vault_Path                   import Safe_Str__Vault_Path


class Schema__Vault_Ref(Type_Safe):                                                 # Points to a file in a vault
    vault_key : Safe_Str__Vault_Key                                                 # "drum-hunt-6610" or opaque
    path      : Safe_Str__Vault_Path                                                # e.g. /config/proxy.json
    version   : Safe_Str__Version = None                                            # Optional snapshot pin
