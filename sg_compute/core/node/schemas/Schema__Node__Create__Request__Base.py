# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Create__Request__Base
# Unified base for all per-spec node-creation requests.
# Per-spec schemas extend this and add spec-specific fields.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id                   import Safe_Str__AMI__Id
from sg_compute.primitives.enums.Enum__Stack__Creation_Mode                  import Enum__Stack__Creation_Mode
from sg_compute.primitives.Safe_Str__AWS__Region                             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Instance__Type                          import Safe_Str__Instance__Type
from sg_compute.primitives.Safe_Str__IP__Address                             import Safe_Str__IP__Address
from sg_compute.primitives.Safe_Str__Node__Name                              import Safe_Str__Node__Name
from sg_compute.primitives.Safe_Str__Spec__Id                                import Safe_Str__Spec__Id
from sg_compute.primitives.Safe_Int__Hours                                   import Safe_Int__Hours


class Schema__Node__Create__Request__Base(Type_Safe):
    spec_id       : Safe_Str__Spec__Id             = Safe_Str__Spec__Id()
    node_name     : Safe_Str__Node__Name           = Safe_Str__Node__Name()    # auto-generated when empty
    region        : Safe_Str__AWS__Region          = Safe_Str__AWS__Region()
    instance_type : Safe_Str__Instance__Type       = Safe_Str__Instance__Type()
    ami_id        : Safe_Str__AMI__Id              = Safe_Str__AMI__Id()       # empty = use latest AL2023
    caller_ip     : Safe_Str__IP__Address          = Safe_Str__IP__Address()   # empty = auto-detected
    max_hours     : Safe_Int__Hours                = Safe_Int__Hours(1)
    creation_mode : Enum__Stack__Creation_Mode     = Enum__Stack__Creation_Mode.FRESH
