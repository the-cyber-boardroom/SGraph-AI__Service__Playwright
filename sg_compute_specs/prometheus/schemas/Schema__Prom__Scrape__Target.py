# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Schema__Prom__Scrape__Target
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path      import Safe_Str__Url__Path

from sg_compute_specs.prometheus.collections.List__Str                              import List__Str


class Schema__Prom__Scrape__Target(Type_Safe):
    job_name     : Safe_Str__Id                                                     # Prometheus job label
    targets      : List__Str                                                        # 'host:port' strings
    scheme       : Safe_Str__Id        = 'http'
    metrics_path : Safe_Str__Url__Path = '/metrics'
