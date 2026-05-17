# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Start__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Start__Response(Type_Safe):
    stack_name     : str  = ''
    started        : bool = False
    public_ip      : str  = ''
    dns_upserted   : bool = False
    fqdn           : str  = ''
    message        : str  = ''
    elapsed_ms     : int  = 0
