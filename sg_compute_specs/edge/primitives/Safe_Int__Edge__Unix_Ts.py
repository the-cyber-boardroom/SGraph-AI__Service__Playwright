# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — edge: Safe_Int__Edge__Unix_Ts
# Unix timestamp in seconds. Used for the TXT record `launched` field (staleness
# detection) and the fleet-state `updated_at` field. 0 = unset / not yet stamped.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__Edge__Unix_Ts(Safe_Int):
    min_value = 0                                                              # 0 = unset
    max_value = 9999999999                                                     # ~year 2286, comfortably past any real timestamp
