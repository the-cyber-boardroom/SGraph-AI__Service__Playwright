# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Stack__Info
# Legacy EC2 instance state shared by all spec mappers.
# Kept for backwards compatibility; new code should use Schema__Node__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id                   import Safe_Str__AMI__Id
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id              import Safe_Str__Instance__Id
from sg_compute.primitives.Safe_Str__AWS__Region                             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Instance__Type                          import Safe_Str__Instance__Type
from sg_compute.primitives.Safe_Str__IP__Address                             import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Str__Message                                 import Safe_Str__Message
from sg_compute.primitives.Safe_Str__SG__Id                                  import Safe_Str__SG__Id
from sg_compute.primitives.Safe_Str__Stack__Name                             import Safe_Str__Stack__Name
from sg_compute.primitives.Safe_Int__Uptime__Seconds                         import Safe_Int__Uptime__Seconds


class Schema__Stack__Info(Type_Safe):
    instance_id       : Safe_Str__Instance__Id     = Safe_Str__Instance__Id()
    stack_name        : Safe_Str__Stack__Name      = Safe_Str__Stack__Name()
    stack_type        : Safe_Str__Message          = Safe_Str__Message()     # free-form type label
    region            : Safe_Str__AWS__Region      = Safe_Str__AWS__Region()
    state             : Safe_Str__Message          = Safe_Str__Message()
    public_ip         : Safe_Str__IP__Address      = Safe_Str__IP__Address()
    private_ip        : Safe_Str__IP__Address      = Safe_Str__IP__Address()
    instance_type     : Safe_Str__Instance__Type   = Safe_Str__Instance__Type()
    ami_id            : Safe_Str__AMI__Id          = Safe_Str__AMI__Id()
    security_group_id : Safe_Str__SG__Id           = Safe_Str__SG__Id()
    uptime_seconds    : Safe_Int__Uptime__Seconds  = Safe_Int__Uptime__Seconds()
