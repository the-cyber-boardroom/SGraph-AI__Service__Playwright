# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__Entry
# Routing record for one published slug. Stored in SSM Parameter Store.
# vault_key is NOT stored here — it lives in the operator's local keyring only.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug


class Schema__Vault_Publish__Entry(Type_Safe):
    slug       : Safe_Str__Slug = None
    stack_name : str            = ''
    fqdn       : str            = ''
    region     : str            = ''
    created_at : str            = ''
