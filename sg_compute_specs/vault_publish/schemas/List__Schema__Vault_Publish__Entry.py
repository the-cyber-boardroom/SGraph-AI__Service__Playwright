# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: List__Schema__Vault_Publish__Entry
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Entry import Schema__Vault_Publish__Entry


class List__Schema__Vault_Publish__Entry(Type_Safe__List):
    expected_type = Schema__Vault_Publish__Entry
