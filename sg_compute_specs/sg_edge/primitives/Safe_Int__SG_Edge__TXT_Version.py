# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Safe_Int__SG_Edge__TXT_Version
# Schema version carried in the `v=` field of an _sg.<slug> routing TXT record.
# Only v=1 exists today; the field is version-prefixed so the routing record can
# evolve without breaking older proxies. SG_Edge__TXT__Builder rejects unknown
# versions.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int import Safe_Int


class Safe_Int__SG_Edge__TXT_Version(Safe_Int):
    min_value = 1

    @classmethod
    def __default__value__(cls):                                              # called when value is None and min_value > 0
        return 1                                                              # current TXT schema version
