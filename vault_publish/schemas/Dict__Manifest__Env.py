# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Dict__Manifest__Env
# The allowlisted env key/value settings a provisioning manifest may declare.
# Both keys and values are constrained Safe_Str — no raw strings leak in.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict import Type_Safe__Dict

from vault_publish.schemas.Safe_Str__Message                          import Safe_Str__Message


class Dict__Manifest__Env(Type_Safe__Dict):
    expected_key_type   = Safe_Str__Message
    expected_value_type = Safe_Str__Message
