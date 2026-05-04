# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Scrape__Target
# One scrape job baked into prometheus.yml at create time. Maps directly onto
# Prometheus' `scrape_configs` entry: `job_name` + `static_configs.targets` +
# `scheme` + `metrics_path`. Per plan doc 5 P3, sp prom ships one-shot baked
# targets first; the dynamic `sp prom add-target` flow is deferred.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url__Path      import Safe_Str__Url__Path

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Str             import List__Str


class Schema__Prom__Scrape__Target(Type_Safe):
    job_name     : Safe_Str__Id                                                     # Prometheus job label — e.g. 'playwright', 'cadvisor', 'node-exporter'
    targets      : List__Str                                                        # 'host:port' strings — e.g. ['1.2.3.4:8000']
    scheme       : Safe_Str__Id          = 'http'                                   # 'http' (default) or 'https' — Safe_Str__Id is the right shape for an alphanumeric scheme
    metrics_path : Safe_Str__Url__Path   = '/metrics'                               # Defaults to /metrics; Safe_Str__Url__Path preserves slashes
