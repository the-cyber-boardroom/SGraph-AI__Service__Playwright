# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Stack__Create__Response
# Returned once by `sp prom create`. No admin_password / admin_username (P1: no
# Grafana, no built-in auth on Prometheus); no dashboards_url (P1: no UI in
# this stack). Mirrors Schema__OS__Stack__Create__Response otherwise.
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


class Schema__Prom__Stack__Create__Response(Type_Safe):
    stack_name        : Safe_Str__Prom__Stack__Name
    aws_name_tag      : Safe_Str__Text                                              # Always 'prometheus-' prefixed (PROM_NAMING)
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text                                              # Dot preserved (e.g. 't3.medium')
    security_group_id : Safe_Str__Id
    caller_ip         : Safe_Str__IP__Address                                       # /32 allowed on 9090
    public_ip         : Safe_Str__Text                                              # Empty immediately after launch — AWS assigns async
    prometheus_url    : Safe_Str__Url                                               # http://<ip>:9090/ — Prometheus public UI + API
    targets_count     : int                       = 0                               # Number of baked scrape jobs (= len(request.scrape_targets))
    state             : Enum__Prom__Stack__State  = Enum__Prom__Stack__State.PENDING
