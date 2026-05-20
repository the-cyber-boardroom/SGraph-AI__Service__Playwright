# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: List__Safe_Str__IP__Address
# Ordered list of proxy IPv4 addresses — the fleet-membership mirror carried in
# Schema__Edge__Fleet__State. The authoritative membership is the set of
# proxies.<parent> A records in Route 53; this list mirrors them in the lock
# object so a single GetObject reveals current fleet size without a DNS query.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address


class List__Safe_Str__IP__Address(Type_Safe__List):
    expected_type = Safe_Str__IP__Address
