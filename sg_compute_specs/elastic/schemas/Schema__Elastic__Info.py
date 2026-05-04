# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Schema__Elastic__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sg_compute_specs.elastic.enums.Enum__Elastic__State                            import Enum__Elastic__State
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name
from sg_compute_specs.elastic.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address


class Schema__Elastic__Info(Type_Safe):
    stack_name        : Safe_Str__Elastic__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    allowed_ip        : Safe_Str__IP__Address
    public_ip         : Safe_Str__Text
    kibana_url        : Safe_Str__Url
    state             : Enum__Elastic__State = Enum__Elastic__State.UNKNOWN
    launch_time       : Safe_Str__Text
    uptime_seconds    : int                  = 0
