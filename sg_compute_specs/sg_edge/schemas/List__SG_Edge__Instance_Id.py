# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: List__SG_Edge__Instance_Id
# Typed list of EC2 instance ids — the proxies launched in one reconcile pass.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id       import Safe_Str__Instance__Id


class List__SG_Edge__Instance_Id(Type_Safe__List):
    expected_type = Safe_Str__Instance__Id
