# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__AMI__Info
# Single AMI entry returned by GET /api/amis.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id import Safe_Str__AMI__Id


class Schema__AMI__Info(Type_Safe):
    ami_id     : Safe_Str__AMI__Id = Safe_Str__AMI__Id()
    name       : str               = ''
    created_at : str               = ''
    state      : str               = ''
    size_gb    : int               = 0
