# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Dict__Pod__Ports
# str→str map of host_port→container_port bindings for a pod.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict import Type_Safe__Dict


class Dict__Pod__Ports(Type_Safe__Dict):
    expected_key_type   = str
    expected_value_type = str
