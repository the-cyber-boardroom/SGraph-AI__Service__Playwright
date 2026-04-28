# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Stack__Create__Request
# Inputs for `sp prom create [NAME]`. Mirrors Schema__OS__Stack__Create__Request
# minus the admin password (Prometheus has no built-in auth — per plan doc 5 P1
# Grafana lives elsewhere, so there is no UI password either).
# All fields optional — service generates a random name, detects caller IP,
# picks the latest AL2023 AMI when not supplied.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name


class Schema__Prom__Stack__Create__Request(Type_Safe):
    stack_name      : Safe_Str__Prom__Stack__Name = ''                              # Empty → service generates "prometheus-{adj}-{scientist}"
    region          : Safe_Str__AWS__Region       = ''                              # Empty → resolved from AWS_Config
    instance_type   : Safe_Str__Text              = ''                              # Safe_Str__Text preserves the dot in 't3.medium'
    from_ami        : Safe_Str__AMI__Id           = ''                              # Empty → latest AL2023 resolved by service
    caller_ip       : Safe_Str__IP__Address       = ''                              # Empty → service calls Caller__IP__Detector
    max_hours       : int                         = 1                               # Auto-terminate after N hours; 0 disables
    scrape_targets  : List__Schema__Prom__Scrape__Target                            # Empty list → no static scrape jobs baked at create time (per P3 baked-only flow); add later via the deferred sp prom add-target
