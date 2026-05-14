# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                                  import Type_Safe
from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Info        import Schema__Vault_App__Info


class Schema__Vault_App__List(Type_Safe):
    region : str                          = ''
    stacks : List[Schema__Vault_App__Info]
    total  : int                          = 0
