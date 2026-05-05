# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__AMI__List__Response
# Response for GET /api/amis?spec_id=<id>.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.core.ami.collections.List__Schema__AMI__Info import List__Schema__AMI__Info
from sg_compute.primitives.Safe_Str__Spec__Id                 import Safe_Str__Spec__Id


class Schema__AMI__List__Response(Type_Safe):
    spec_id : Safe_Str__Spec__Id      = Safe_Str__Spec__Id()
    amis    : List__Schema__AMI__Info
