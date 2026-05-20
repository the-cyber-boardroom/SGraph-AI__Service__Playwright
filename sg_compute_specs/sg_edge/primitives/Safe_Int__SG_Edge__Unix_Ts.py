# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Safe_Int__SG_Edge__Unix_Ts
# Unix timestamp in seconds. Used for the routing TXT `launched` field (staleness
# detection) and the _state TXT `updated` field. 0 = unset / not yet stamped.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__SG_Edge__Unix_Ts(Safe_Int):
    min_value = 0                                                              # 0 = unset
    max_value = 9999999999                                                     # ~year 2286, comfortably past any real timestamp
