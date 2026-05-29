# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Vault_App__Interceptor__Resolver
# Turns a Schema__Vault_App__Interceptor__Choice into (source: str, label: str).
# The source is written to /opt/vault-app/interceptors/active.py by the user-data
# builder and loaded by agent-mitmproxy via mitmweb --scripts.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                            import Type_Safe

from sg_compute_specs.vault_app.enums.Enum__Vault_App__Interceptor__Kind         import Enum__Vault_App__Interceptor__Kind
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Interceptor__Choice   import Schema__Vault_App__Interceptor__Choice


NO_OP_SOURCE = "# sg-vault-app: no interceptor active\n"


class Vault_App__Interceptor__Resolver(Type_Safe):

    def resolve(self, choice: Schema__Vault_App__Interceptor__Choice = None) -> tuple:   # → (source: str, label: str)
        choice = choice or Schema__Vault_App__Interceptor__Choice()

        if choice.kind == Enum__Vault_App__Interceptor__Kind.INLINE:
            source = str(choice.inline_source)
            if not source:
                raise ValueError('inline interceptor requires non-empty inline_source')
            return source, 'inline'

        return NO_OP_SOURCE, ''                                                          # NONE
