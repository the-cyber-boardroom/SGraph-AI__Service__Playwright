# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: List__SG_Edge__IP
# Typed list of IP addresses — the proxy IPs drained in one teardown pass.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address


class List__SG_Edge__IP(Type_Safe__List):
    expected_type = Safe_Str__IP__Address
