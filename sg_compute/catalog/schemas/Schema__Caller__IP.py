# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Caller__IP
# Response schema for GET /catalog/caller-ip.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.Safe_Str__IP__Address                             import Safe_Str__IP__Address


class Schema__Caller__IP(Type_Safe):
    ip : Safe_Str__IP__Address = Safe_Str__IP__Address()
