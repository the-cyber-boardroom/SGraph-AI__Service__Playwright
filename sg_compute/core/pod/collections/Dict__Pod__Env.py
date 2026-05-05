# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Dict__Pod__Env
# str→str map of environment variable name→value for a pod.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict import Type_Safe__Dict


class Dict__Pod__Env(Type_Safe__Dict):
    expected_key_type   = str
    expected_value_type = str
