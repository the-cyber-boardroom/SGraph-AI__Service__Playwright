# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Stop__Response(Type_Safe):
    stack_name  : str  = ''
    stopped     : bool = False
    dns_deleted : bool = False
    message     : str  = ''
    elapsed_ms  : int  = 0
