# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: Schema__OS__Stack__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sg_compute_specs.opensearch.primitives.Safe_Str__IP__Address                   import Safe_Str__IP__Address
from sg_compute_specs.opensearch.primitives.Safe_Str__OS__Password                  import Safe_Str__OS__Password
from sg_compute_specs.opensearch.primitives.Safe_Str__OS__Stack__Name               import Safe_Str__OS__Stack__Name


class Schema__OS__Stack__Create__Request(Type_Safe):
    stack_name     : Safe_Str__OS__Stack__Name = ''
    region         : Safe_Str__AWS__Region     = ''
    instance_type  : Safe_Str__Text            = ''
    from_ami       : Safe_Str__AMI__Id         = ''
    caller_ip      : Safe_Str__IP__Address     = ''
    max_hours      : int                       = 1
    admin_password : Safe_Str__OS__Password    = ''
