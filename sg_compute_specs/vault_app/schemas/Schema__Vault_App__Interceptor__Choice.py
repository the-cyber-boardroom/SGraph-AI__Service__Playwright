# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Interceptor__Choice
# Pure data — the operator's interceptor choice for `sg va create --with-playwright`.
# kind=none → no-op; kind=inline → inline_source carries the script (read from
# --interceptor-script <file> by the CLI).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sg_compute_specs.vault_app.enums.Enum__Vault_App__Interceptor__Kind         import Enum__Vault_App__Interceptor__Kind
from sg_compute_specs.vault_app.primitives.Safe_Str__Vault_App__Interceptor__Source import Safe_Str__Vault_App__Interceptor__Source


class Schema__Vault_App__Interceptor__Choice(Type_Safe):
    kind          : Enum__Vault_App__Interceptor__Kind = Enum__Vault_App__Interceptor__Kind.NONE
    inline_source : Safe_Str__Vault_App__Interceptor__Source
