# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Stop__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Stop__Request(Type_Safe):
    region     : str = ''
    stack_name : str = ''
