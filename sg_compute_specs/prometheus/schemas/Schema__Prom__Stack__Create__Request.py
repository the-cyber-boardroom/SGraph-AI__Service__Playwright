# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Schema__Prom__Stack__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.prometheus.collections.List__Schema__Prom__Scrape__Target     import List__Schema__Prom__Scrape__Target
from sg_compute_specs.prometheus.primitives.Safe_Str__IP__Address                   import Safe_Str__IP__Address
from sg_compute_specs.prometheus.primitives.Safe_Str__Prom__Stack__Name             import Safe_Str__Prom__Stack__Name


class Schema__Prom__Stack__Create__Request(Type_Safe):
    stack_name     : Safe_Str__Prom__Stack__Name  = ''                              # auto-generated when empty
    region         : Safe_Str__AWS__Region        = ''
    instance_type  : Safe_Str__Text               = ''
    from_ami       : Safe_Str__AMI__Id            = ''
    caller_ip      : Safe_Str__IP__Address        = ''                              # auto-detected when empty
    max_hours      : int                          = 1
    scrape_targets : List__Schema__Prom__Scrape__Target
