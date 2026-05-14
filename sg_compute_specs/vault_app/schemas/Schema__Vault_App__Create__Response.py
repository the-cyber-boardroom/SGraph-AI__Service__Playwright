# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Create__Response
# access_token is returned once here — it is not recoverable later.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info        import Schema__Vault_App__Info


class Schema__Vault_App__Create__Response(Type_Safe):
    stack_info   : Schema__Vault_App__Info = None
    access_token : str = ''    # shared stack secret — surfaced once on create, never again
    message      : str = ''
    elapsed_ms   : int = 0
