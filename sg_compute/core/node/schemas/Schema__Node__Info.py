# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Info
# Current state of one ephemeral compute node.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id                   import Safe_Str__AMI__Id
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id              import Safe_Str__Instance__Id
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State
from sg_compute.primitives.Safe_Str__AWS__Region                             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Instance__Type                          import Safe_Str__Instance__Type
from sg_compute.primitives.Safe_Str__IP__Address                             import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Str__Node__Id                                import Safe_Str__Node__Id
from sg_compute.primitives.Safe_Str__Spec__Id                                import Safe_Str__Spec__Id
from sg_compute.primitives.Safe_Str__Api__Key                                import Safe_Str__Api__Key
from sg_compute.primitives.Safe_Str__SSM__Path                               import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Int__Uptime__Seconds                         import Safe_Int__Uptime__Seconds


class Schema__Node__Info(Type_Safe):
    node_id              : Safe_Str__Node__Id           = Safe_Str__Node__Id()
    spec_id              : Safe_Str__Spec__Id           = Safe_Str__Spec__Id()
    region               : Safe_Str__AWS__Region        = Safe_Str__AWS__Region()
    state                : Enum__Node__State            = Enum__Node__State.BOOTING
    public_ip            : Safe_Str__IP__Address        = Safe_Str__IP__Address()
    private_ip           : Safe_Str__IP__Address        = Safe_Str__IP__Address()
    instance_id          : Safe_Str__Instance__Id       = Safe_Str__Instance__Id()
    instance_type        : Safe_Str__Instance__Type     = Safe_Str__Instance__Type()
    ami_id               : Safe_Str__AMI__Id            = Safe_Str__AMI__Id()
    uptime_seconds       : Safe_Int__Uptime__Seconds    = Safe_Int__Uptime__Seconds()
    host_api_key         : Safe_Str__Api__Key           = Safe_Str__Api__Key()
    host_api_key_ssm_path: Safe_Str__SSM__Path          = Safe_Str__SSM__Path()
