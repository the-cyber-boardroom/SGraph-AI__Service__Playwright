# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__Register__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug


class Schema__Vault_Publish__Register__Response(Type_Safe):
    slug       : Safe_Str__Slug = None
    fqdn       : str            = ''
    stack_name : str            = ''
    message    : str            = ''
    elapsed_ms : int            = 0
