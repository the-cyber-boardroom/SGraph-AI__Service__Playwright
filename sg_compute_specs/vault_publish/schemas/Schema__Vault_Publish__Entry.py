# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__Entry
# Registry record for one published slug. Stored in SSM Parameter Store.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug       import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key import Safe_Str__Vault__Key


class Schema__Vault_Publish__Entry(Type_Safe):
    slug       : Safe_Str__Slug       = None
    vault_key  : Safe_Str__Vault__Key = None
    stack_name : str                  = ''
    fqdn       : str                  = ''
    region     : str                  = ''
    created_at : str                  = ''
