# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Stack__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.collections.List__Instance__Id           import List__Instance__Id
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id

from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Stack__Delete__Response(Type_Safe):
    target                  : Safe_Str__Instance__Id
    stack_name              : Safe_Str__Vnc__Stack__Name
    terminated_instance_ids : List__Instance__Id
