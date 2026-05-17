# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish schemas: Schema__Vault_Publish__Bootstrap__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_Publish__Bootstrap__Response(Type_Safe):
    distribution_id : str  = ''
    domain_name     : str  = ''
    lambda_name     : str  = ''
    waker_url       : str  = ''
    zone            : str  = ''
    created         : bool = False
    message         : str  = ''
    elapsed_ms      : int  = 0
