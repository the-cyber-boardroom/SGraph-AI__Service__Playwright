# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__Config__Generator
# Renders the prometheus.yml scrape config that ships baked into the AMI /
# instance UserData. Per plan doc 5 P3, sp prom ships one-shot baked targets
# first; the dynamic `sp prom add-target` flow is deferred.
#
# Two scrape jobs are always baked (the local cAdvisor + node-exporter
# containers) so the operator gets host-level metrics out of the box. Caller-
# supplied Schema__Prom__Scrape__Target entries append to that baseline.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target


SCRAPE_INTERVAL = '15s'                                                             # Default Prometheus value; explicit for visibility


# Baseline header — one block; variable-length jobs appended below.
CONFIG_HEADER = """\
global:
  scrape_interval: {scrape_interval}

scrape_configs:
  - job_name: cadvisor
    static_configs:
      - targets: ['cadvisor:8080']
  - job_name: node-exporter
    static_configs:
      - targets: ['node-exporter:9100']
"""


class Prometheus__Config__Generator(Type_Safe):

    def render(self, targets: List__Schema__Prom__Scrape__Target = None) -> str:
        out = CONFIG_HEADER.format(scrape_interval=SCRAPE_INTERVAL)
        for target in (targets or List__Schema__Prom__Scrape__Target()):
            out += self._render_job(target)
        return out

    def _render_job(self, target) -> str:                                           # One scrape_configs entry per Schema__Prom__Scrape__Target
        targets_quoted = ', '.join(f"'{str(t)}'" for t in target.targets)
        return (f"  - job_name: {str(target.job_name)}\n"
                f"    scheme: {str(target.scheme)}\n"
                f"    metrics_path: {str(target.metrics_path)}\n"
                f"    static_configs:\n"
                f"      - targets: [{targets_quoted}]\n")
