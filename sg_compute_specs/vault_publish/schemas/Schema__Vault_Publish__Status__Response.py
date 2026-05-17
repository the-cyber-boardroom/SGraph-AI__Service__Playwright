# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__Status__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Enum__Vault_Publish__State import Enum__Vault_Publish__State
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug              import Safe_Str__Slug


class Schema__Vault_Publish__Status__Response(Type_Safe):
    slug       : Safe_Str__Slug             = None
    state      : Enum__Vault_Publish__State = Enum__Vault_Publish__State.UNKNOWN
    fqdn       : str                        = ''
    vault_url  : str                        = ''
    public_ip  : str                        = ''
    stack_name : str                        = ''
    elapsed_ms : int                        = 0
