# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: Schema__OS__Stack__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sg_compute_specs.opensearch.enums.Enum__OS__Stack__State                       import Enum__OS__Stack__State
from sg_compute_specs.opensearch.primitives.Safe_Str__IP__Address                   import Safe_Str__IP__Address
from sg_compute_specs.opensearch.primitives.Safe_Str__OS__Password                  import Safe_Str__OS__Password
from sg_compute_specs.opensearch.primitives.Safe_Str__OS__Stack__Name               import Safe_Str__OS__Stack__Name


class Schema__OS__Stack__Create__Response(Type_Safe):
    stack_name        : Safe_Str__OS__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    caller_ip         : Safe_Str__IP__Address
    public_ip         : Safe_Str__Text
    dashboards_url    : Safe_Str__Url
    os_endpoint       : Safe_Str__Url
    admin_username    : Safe_Str__Id           = 'admin'
    admin_password    : Safe_Str__OS__Password
    state             : Enum__OS__Stack__State = Enum__OS__Stack__State.PENDING
