# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Dict__Manifest__Routes
# The declarative route table from a provisioning manifest: request path →
# content path within the vault folder.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict import Type_Safe__Dict

from vault_publish.schemas.Safe_Str__Manifest__Path                   import Safe_Str__Manifest__Path


class Dict__Manifest__Routes(Type_Safe__Dict):
    expected_key_type   = Safe_Str__Manifest__Path
    expected_value_type = Safe_Str__Manifest__Path
