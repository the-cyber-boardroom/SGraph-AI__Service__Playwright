# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__HTTP__Probe
# Reachability + cluster-health probes against a live OpenSearch + Dashboards
# instance. Single responsibility: read-only probes that populate
# Schema__OS__Health. No mutations live here.
#
# Two probes:
#   - cluster_health(base_url, ...)   — GET /_cluster/health on the OS REST API
#   - dashboards_ready(base_url, ...) — GET / on the Dashboards UI
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Base    import OpenSearch__HTTP__Base


class OpenSearch__HTTP__Probe(Type_Safe):
    http : OpenSearch__HTTP__Base                                                   # Composed; tests override http.request

    def cluster_health(self, base_url: str, username: str = '', password: str = '') -> dict:    # Returns {} when unreachable — caller maps to Schema__OS__Health '-1' sentinels
        url = f'{base_url.rstrip("/")}/_cluster/health'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return {}
        if resp.status_code != 200:
            return {}
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {}

    def dashboards_ready(self, base_url: str, username: str = '', password: str = '') -> bool:  # True iff Dashboards login page returns 2xx
        url = base_url.rstrip('/') + '/'
        try:
            resp = self.http.request('GET', url, username=username, password=password)
        except Exception:
            return False
        return 200 <= resp.status_code < 300
