# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Start__Request
# Body for POST /api/nodes/{node_id}/pods — starts a pod on the named node.
# ports/env are passed through as raw JSON by Pod__Manager; not typed here
# because Type_Safe__Dict cannot be converted to a Pydantic schema by
# osbot_fast_api's Type_Safe__To__BaseModel converter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.Safe_Str__Docker__Image import Safe_Str__Docker__Image
from sg_compute.primitives.Safe_Str__Pod__Name     import Safe_Str__Pod__Name
from sg_compute.primitives.Safe_Str__Spec__Id      import Safe_Str__Spec__Id


class Schema__Pod__Start__Request(Type_Safe):
    name    : Safe_Str__Pod__Name    = Safe_Str__Pod__Name()
    image   : Safe_Str__Docker__Image = Safe_Str__Docker__Image()
    type_id : Safe_Str__Spec__Id     = Safe_Str__Spec__Id()
