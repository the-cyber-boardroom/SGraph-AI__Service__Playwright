# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Stack__Info
# Public view of one ephemeral Prometheus stack. Mirrors Schema__OS__Stack__Info
# minus the password-related field (Prometheus has no built-in auth) and minus
# the dashboards_url (P1: no UI in this stack).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name


class Schema__Prom__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Prom__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text                                              # Dot preserved
    security_group_id : Safe_Str__Id
    allowed_ip        : Safe_Str__IP__Address                                       # /32 recorded at create (sg:allowed-ip tag)
    public_ip         : Safe_Str__Text                                              # Dots preserved; URL goes in prometheus_url
    prometheus_url    : Safe_Str__Url                                               # http://<ip>:9090/
    state             : Enum__Prom__Stack__State = Enum__Prom__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text                                              # ISO-8601 EC2 LaunchTime; empty when AWS hasn't reported yet
    uptime_seconds    : int                      = 0                                # Seconds since LaunchTime; 0 when launch_time is empty
