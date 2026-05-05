# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__Config__Generator
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.prometheus.collections.List__Schema__Prom__Scrape__Target     import List__Schema__Prom__Scrape__Target


SCRAPE_INTERVAL = '15s'

CONFIG_HEADER = '''\
global:
  scrape_interval: {scrape_interval}

scrape_configs:
  - job_name: cadvisor
    static_configs:
      - targets: ['cadvisor:8080']
  - job_name: node-exporter
    static_configs:
      - targets: ['node-exporter:9100']
'''


class Prometheus__Config__Generator(Type_Safe):

    def render(self, targets: List__Schema__Prom__Scrape__Target = None) -> str:
        out = CONFIG_HEADER.format(scrape_interval=SCRAPE_INTERVAL)
        for target in (targets or List__Schema__Prom__Scrape__Target()):
            out += self._render_job(target)
        return out

    def _render_job(self, target) -> str:
        targets_quoted = ', '.join(f"'{str(t)}'" for t in target.targets)
        return (f"  - job_name: {str(target.job_name)}\n"
                f"    scheme: {str(target.scheme)}\n"
                f"    metrics_path: {str(target.metrics_path)}\n"
                f"    static_configs:\n"
                f"      - targets: [{targets_quoted}]\n")
